from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import median
from typing import Any

import polars as pl
import structlog

from networking_intel.enrichment import ENRICHMENT_VERSION
from networking_intel.enrichment.cache import RawArtifact, RawCache
from networking_intel.enrichment.conflicts import Conflict, detect_conflicts, merge_review_queue
from networking_intel.enrichment.cvm import (
    INF_DIARIO_URL,
    FundClass,
    ManagerRecord,
    parse_daily_report,
    parse_fund_classes,
    parse_managers,
    parse_portfolio_directors,
)
from networking_intel.enrichment.geocode import GeocodeResult, geocode, parse_address
from networking_intel.enrichment.http import Fetcher, SourceUnavailableError
from networking_intel.enrichment.identity import IdentityRegistry, format_cnpj, load_registry
from networking_intel.enrichment.quality import (
    SourceRun,
    as_dict,
    check_freshness,
    write_reports,
)
from networking_intel.enrichment.returns import (
    ShareClassMetrics,
    broad_reference_date,
    compute_all,
)
from networking_intel.enrichment.sources import get_source
from networking_intel.etl.schemas import load_pilot_csv
from networking_intel.etl.transform import stable_hash, transform_accounts
from networking_intel.universe import ifdata

logger = structlog.get_logger("networking_intel.enrichment.pipeline")

ROLE_EMAIL_KEYWORDS = (
    "compliance",
    "juridico",
    "legal",
    "grc",
    "relacionamento",
    "contato",
    "institucional",
    "atendimento",
    "reguladores",
    "info",
    "ri",
    "risco",
    "ouvidoria",
)
RULES = (
    "Fundos ligados a contas apenas por igualdade exata de CNPJ do gestor "
    "(registro_fundo.CPF_CNPJ_Gestor) contra o registro curado; sem similaridade de nome.",
    "Retorno calculado por classe/subclasse, em BRL, somente com observação inicial até 7 dias "
    "antes do início da janela, sem lacunas > 10 dias e série atualizada até 5 dias da data de "
    "referência; caso contrário o campo fica nulo com o motivo.",
    "Variação diária que se afasta mais de 25 p.p. da mediana do mesmo dia na mesma "
    "classificação CVM é tratada como suspeita de evento de cota (amortização, grupamento) e "
    "torna a janela não comparável; choques de mercado amplos continuam contando como retorno.",
    "Data de referência = último dia reportado por pelo menos 50% das séries do dia mais "
    "completo, para não ancorar a janela num dia com poucas classes publicadas.",
    "Captação líquida 12m só é somada quando a janela de 12m da série está completa.",
    "PL agregado exclui classes FIC/CIC para reduzir dupla contagem e usa o nível de classe "
    "quando existe; ainda pode haver dupla contagem master-feeder.",
    "Endereços geocodificados são apenas os registrados na CVM; 'address' só quando o número "
    "da porta retornado coincide. Excel não confirmado não é geocodificado.",
    "E-mails individuais são descartados; apenas caixas institucionais/funcionais são mantidas.",
    "Diretores coletados apenas para a função de gestão de carteiras (Res. CVM 21) das entidades "
    "principais; compliance, risco e PLD não são coletados.",
    "Fontes sandbox/fictícias (ex.: ANBIMA sandbox) são bloqueadas no cache e no fetcher.",
)


@dataclass
class EnrichmentPaths:
    pilot_csv: Path
    registry: Path
    raw_dir: Path
    output_dir: Path
    review_queue: Path
    report_doc: Path


@dataclass
class Observation:
    observation_id: str
    account_id: str
    entity_cnpj: str
    field: str
    value: str
    source_id: str
    source_url: str
    raw_sha256: str
    as_of_date: str
    collected_at: str
    evidence_class: str
    confidence: str
    note: str = ""


@dataclass
class RunContext:
    fetcher: Fetcher
    today: date
    run_at: str
    source_runs: dict[str, SourceRun] = field(default_factory=dict)


def zip_member_date(content: bytes, member: str) -> date:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        year, month, day, *_ = archive.getinfo(member).date_time
    return date(year, month, day)


def is_role_email(email: str | None) -> bool:
    if not email or "@" not in email:
        return False
    local = email.split("@", 1)[0].lower()
    tokens = set(local.replace(".", "-").replace("_", "-").split("-"))
    return any(keyword in tokens or local.startswith(keyword) for keyword in ROLE_EMAIL_KEYWORDS)


def months_back(reference: date, count: int) -> list[str]:
    periods = []
    year, month = reference.year, reference.month
    for _ in range(count):
        periods.append(f"{year:04d}{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return sorted(periods)


def fetch_cvm_cadastres(ctx: RunContext) -> tuple[RawArtifact, RawArtifact]:
    adm_spec = get_source("cvm_cad_adm_cart")
    reg_spec = get_source("cvm_registro_fundo_classe")
    adm = ctx.fetcher.fetch(adm_spec.source_id, adm_spec.base_url, suffix=".zip")
    reg = ctx.fetcher.fetch(reg_spec.source_id, reg_spec.base_url, suffix=".zip")
    return adm, reg


def fetch_daily_reports(
    ctx: RunContext, class_cnpjs: Sequence[str], months: int
) -> tuple[pl.DataFrame, list[RawArtifact], list[str]]:
    frames: list[pl.DataFrame] = []
    artifacts: list[RawArtifact] = []
    missing: list[str] = []
    periods = months_back(ctx.today, months)
    for period in periods:
        url = INF_DIARIO_URL.format(period=period)
        # Recent months are revised by CVM; older files are effectively closed.
        recent = period >= periods[-2]
        try:
            artifact = ctx.fetcher.fetch(
                "cvm_inf_diario",
                url,
                suffix=".zip",
                max_age_seconds=None if recent else 90 * 86400,
            )
        except SourceUnavailableError as error:
            missing.append(f"{period}: {error.reason}")
            continue
        artifacts.append(artifact)
        frames.append(
            parse_daily_report(ctx.fetcher.cache.read_bytes(artifact), class_cnpjs).with_columns(
                pl.lit(artifact.sha256).alias("raw_sha256")
            )
        )
    frame = pl.concat(frames) if frames else pl.DataFrame()
    return frame, artifacts, missing


def try_ifdata(ctx: RunContext) -> SourceRun:
    """IF.data cadastro for the latest published quarter (bank identity cross-check).

    A quarter not yet published answers HTTP 200 with an empty list: that is a
    missing period, so the probe moves to the previous quarter.
    """
    try:
        found, skipped = ifdata.latest_cadastro(ctx.fetcher, ctx.today)
    except ifdata.IfDataUnavailableError as error:
        return SourceRun(
            "bcb_ifdata_cadastro", "unavailable", ctx.run_at, None, 0, "; ".join(error.reasons)
        )
    note = "; ".join([f"período {found.period}", *skipped])
    return SourceRun("bcb_ifdata_cadastro", "ok", found.artifact.fetched_at, None, 1, note)


def _dedup_class_nav(rows: Iterable[dict[str, Any]]) -> dict[str, float]:
    """One NAV per class: class-level row if present, else the sum of its subclasses."""
    by_class: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        if row["latest_nav_brl"] is not None:
            by_class[row["class_cnpj"]][row["subclass_id"]] = row["latest_nav_brl"]
    return {
        cnpj: values[""] if "" in values else sum(values.values())
        for cnpj, values in by_class.items()
    }


def account_fund_summary(
    classes: Sequence[FundClass], metrics: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    active = [c for c in classes if c.is_active]
    active_cnpjs = {c.class_cnpj for c in active}
    fic_cnpjs = {c.class_cnpj for c in active if c.is_fund_of_funds}
    rows = [m for m in metrics if m["class_cnpj"] in active_cnpjs and m["status_reference_ok"]]
    with_report = {m["class_cnpj"] for m in rows}
    non_fic_rows = [m for m in rows if m["class_cnpj"] not in fic_cnpjs]
    nav_by_class = _dedup_class_nav(non_fic_rows)
    flows = [m for m in non_fic_rows if m["net_flow_status"] == "ok"]
    flow_nav = sum(nav_by_class.get(m["class_cnpj"], 0.0) for m in flows if m["subclass_id"] == "")
    comparable = [m for m in rows if m["return_12m_status"] == "ok"]
    by_class_type: dict[str, list[float]] = defaultdict(list)
    meta = {c.class_cnpj: c for c in active}
    for m in comparable:
        if m["class_cnpj"] in fic_cnpjs:
            continue
        cls = meta[m["class_cnpj"]]
        label = cls.anbima_classification or cls.classification or "Sem classificação"
        by_class_type[label].append(m["return_12m"])
    total_nav = sum(nav_by_class.values()) if nav_by_class else None
    without_report: dict[str, int] = defaultdict(int)
    for cls in {c.class_cnpj: c for c in active}.values():
        if cls.class_cnpj not in with_report:
            label = (cls.class_type or cls.fund_type or "sem tipo").removeprefix(
                "Classes de Cotas de Fundos "
            )
            without_report[label] += 1
    return {
        "active_classes": len(active_cnpjs),
        "fic_classes": len(fic_cnpjs),
        "classes_with_daily_report": len(with_report),
        "classes_without_daily_report_by_type": dict(sorted(without_report.items())),
        "share_classes_with_daily_report": len(rows),
        "comparable_12m_share": (len(comparable) / len(rows)) if rows else None,
        "nav_brl_non_fic": total_nav,
        "net_flow_12m_brl_non_fic": sum(m["net_flow_12m_brl"] for m in flows) if flows else None,
        "net_flow_nav_coverage": (flow_nav / total_nav) if total_nav else None,
        "median_return_12m_by_classification": {
            label: {"median": median(values), "share_classes": len(values)}
            for label, values in sorted(by_class_type.items())
        },
    }


def _write_csv(
    path: Path, rows: Sequence[dict[str, Any]], columns: Sequence[str] | None = None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(columns or (rows[0].keys() if rows else []))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _observation(
    account_id: str,
    entity_cnpj: str,
    field_name: str,
    value: object,
    artifact: RawArtifact,
    as_of: date,
    evidence_class: str,
    confidence: str,
    note: str = "",
) -> Observation:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    key = "|".join((account_id, entity_cnpj, field_name, text, artifact.sha256))
    return Observation(
        observation_id=stable_hash(key)[:20],
        account_id=account_id,
        entity_cnpj=entity_cnpj,
        field=field_name,
        value=text,
        source_id=artifact.source_id,
        source_url=artifact.url,
        raw_sha256=artifact.sha256,
        as_of_date=as_of.isoformat(),
        collected_at=artifact.fetched_at,
        evidence_class=evidence_class,
        confidence=confidence,
        note=note,
    )


def run_enrichment(
    paths: EnrichmentPaths,
    *,
    fetcher: Fetcher | None = None,
    today: date | None = None,
    months: int = 13,
    geocode_addresses: bool = True,
) -> dict[str, Any]:
    run_at = datetime.now(UTC).isoformat(timespec="seconds")
    ctx = RunContext(
        fetcher=fetcher or Fetcher(RawCache(paths.raw_dir)),
        today=today or datetime.now(UTC).date(),
        run_at=run_at,
    )
    pilots = load_pilot_csv(paths.pilot_csv)
    offices = {
        t.pilot.account_id: [o.address_raw for o in t.offices] for t in transform_accounts(pilots)
    }
    registry: IdentityRegistry = load_registry(paths.registry)
    registry.check_accounts(p.account_id for p in pilots)

    adm_artifact, reg_artifact = fetch_cvm_cadastres(ctx)
    adm_bytes = ctx.fetcher.cache.read_bytes(adm_artifact)
    reg_bytes = ctx.fetcher.cache.read_bytes(reg_artifact)
    adm_as_of = zip_member_date(adm_bytes, "cad_adm_cart_pj.csv")
    reg_as_of = zip_member_date(reg_bytes, "registro_fundo.csv")
    ctx.source_runs["cvm_cad_adm_cart"] = SourceRun(
        "cvm_cad_adm_cart", "ok", adm_artifact.fetched_at, adm_as_of, 1
    )
    ctx.source_runs["cvm_registro_fundo_classe"] = SourceRun(
        "cvm_registro_fundo_classe", "ok", reg_artifact.fetched_at, reg_as_of, 1
    )

    managers = parse_managers(adm_bytes)
    owner = registry.account_for_cnpj()
    manager_cnpjs = [c for account in registry.accounts.values() for c in account.manager_cnpjs()]
    primary_cnpjs = [account.primary_cnpj for account in registry.accounts.values()]
    directors = parse_portfolio_directors(adm_bytes, primary_cnpjs)
    fund_classes = parse_fund_classes(reg_bytes, manager_cnpjs)
    classes_by_account: dict[str, list[FundClass]] = defaultdict(list)
    for fund_class in fund_classes:
        classes_by_account[owner[fund_class.manager_cnpj]].append(fund_class)
    active_class_cnpjs = sorted({c.class_cnpj for c in fund_classes if c.is_active})

    daily, daily_artifacts, missing_months = fetch_daily_reports(ctx, active_class_cnpjs, months)
    reference_date = broad_reference_date(daily) if daily.height else None
    ctx.source_runs["cvm_inf_diario"] = SourceRun(
        "cvm_inf_diario",
        "ok" if daily_artifacts else "unavailable",
        max((a.fetched_at for a in daily_artifacts), default=None),
        reference_date,
        len(daily_artifacts),
        "; ".join(missing_months),
    )
    peer_groups = {c.class_cnpj: c.classification or c.fund_type or "all" for c in fund_classes}
    metrics: list[ShareClassMetrics] = (
        compute_all(daily, reference_date, peer_groups) if reference_date else []
    )
    metric_rows = [m.as_row() for m in metrics]
    class_meta = {c.class_cnpj: c for c in fund_classes}
    for row in metric_rows:
        cls = class_meta[row["class_cnpj"]]
        row["account_id"] = owner[cls.manager_cnpj]
        row["manager_cnpj"] = cls.manager_cnpj
        row["class_name"] = cls.class_name
        row["is_fund_of_funds"] = cls.is_fund_of_funds
        row["status_reference_ok"] = "stale_series" not in row["series_flags"]
    ctx.source_runs["bcb_ifdata_cadastro"] = try_ifdata(ctx)

    observations: list[Observation] = []
    conflicts: list[Conflict] = []
    geocodes: dict[str, GeocodeResult] = {}
    entity_rows: list[dict[str, Any]] = []
    people_rows: list[dict[str, Any]] = []
    account_rows: list[dict[str, Any]] = []
    geocode_runs = 0

    for pilot in pilots:
        account = registry.accounts[pilot.account_id]
        entities: list[ManagerRecord] = []
        gaps: list[str] = []
        for entity in account.entities:
            record = managers.get(entity.cnpj)
            if record is None:
                gaps.append(f"CNPJ {format_cnpj(entity.cnpj)} ausente do cadastro CVM")
                continue
            if entity.cnpj == account.primary_cnpj:
                entities.insert(0, record)
            else:
                entities.append(record)
            geo: GeocodeResult | None = None
            address_status = "not_geocoded"
            if record.street and record.is_active and geocode_addresses:
                parsed = parse_address(record.street, record.city, record.state, record.postal_code)
                if parsed.key not in geocodes:
                    geocodes[parsed.key] = geocode(ctx.fetcher, parsed)
                    geocode_runs += 1
                geo = geocodes[parsed.key]
                address_status = geo.status
            elif not record.is_active:
                address_status = "entity_not_active"
            entity_rows.append(
                {
                    "account_id": pilot.account_id,
                    "cnpj": record.cnpj,
                    "cnpj_formatted": format_cnpj(record.cnpj),
                    "relation": entity.relation,
                    "business_unit": entity.business_unit or "",
                    "approval_status": entity.approval_status,
                    "relation_evidence": entity.relation_evidence,
                    "legal_name": record.legal_name,
                    "trade_name": record.trade_name or "",
                    "cvm_status": record.status,
                    "cvm_status_since": record.status_since,
                    "cvm_registration_date": record.registration_date,
                    "registration_category": record.registration_category or "",
                    "address_official": record.address_line or "",
                    "city": record.city or "",
                    "state": record.state or "",
                    "postal_code": record.postal_code or "",
                    "phone_official": record.phone or "",
                    "email_institutional": record.email if is_role_email(record.email) else "",
                    "email_suppressed_personal": bool(record.email)
                    and not is_role_email(record.email),
                    "website_official": record.website or "",
                    "geocode_status": address_status,
                    "latitude": geo.latitude if geo else None,
                    "longitude": geo.longitude if geo else None,
                    "geocode_precision": geo.precision if geo else "none",
                    "geocode_is_exact": geo.is_exact if geo else False,
                    "geocode_provider": geo.provider if geo else "",
                    "geocode_fetched_at": geo.fetched_at if geo else "",
                    "geocode_raw_sha256": geo.raw_sha256 if geo else "",
                    "source_id": adm_artifact.source_id,
                    "source_as_of": adm_as_of,
                    "raw_sha256": adm_artifact.sha256,
                }
            )
            evidence = (
                "verified_fact" if entity.relation != "affiliate_manager" else "source_stated"
            )
            for field_name, value in (
                ("legal_name", record.legal_name),
                ("cnpj", record.cnpj),
                ("cvm_status", record.status),
                ("address_official", record.address_line),
                ("phone_official", record.phone),
                ("website_official", record.website),
                ("email_institutional", record.email if is_role_email(record.email) else None),
            ):
                if value:
                    observations.append(
                        _observation(
                            pilot.account_id,
                            record.cnpj,
                            field_name,
                            value,
                            adm_artifact,
                            adm_as_of,
                            evidence,
                            "high",
                            f"relation={entity.relation}",
                        )
                    )
        primary = entities[0] if entities and entities[0].cnpj == account.primary_cnpj else None
        for name in directors.get(account.primary_cnpj, []):
            people_rows.append(
                {
                    "account_id": pilot.account_id,
                    "entity_cnpj": account.primary_cnpj,
                    "full_name": name,
                    "role_title": "Diretor responsável pela administração de carteiras (Res. CVM 21)",
                    "is_public_professional_data": True,
                    "lawful_basis_note": "Registro regulatório público; uso restrito a planejamento de conta (LGPD art. 7º, IX).",
                    "source_id": adm_artifact.source_id,
                    "source_as_of": adm_as_of,
                    "raw_sha256": adm_artifact.sha256,
                }
            )
            observations.append(
                _observation(
                    pilot.account_id,
                    account.primary_cnpj,
                    "portfolio_director",
                    name,
                    adm_artifact,
                    adm_as_of,
                    "verified_fact",
                    "high",
                )
            )
        conflicts.extend(
            detect_conflicts(pilot, offices.get(pilot.account_id, []), entities, run_at)
        )

        classes = classes_by_account.get(pilot.account_id, [])
        account_metrics = [m for m in metric_rows if m["account_id"] == pilot.account_id]
        summary = account_fund_summary(classes, account_metrics)
        if summary["active_classes"] and reference_date and daily_artifacts:
            for field_name in ("nav_brl_non_fic", "net_flow_12m_brl_non_fic", "active_classes"):
                if summary[field_name] is not None:
                    observations.append(
                        _observation(
                            pilot.account_id,
                            account.primary_cnpj,
                            field_name,
                            summary[field_name],
                            daily_artifacts[-1],
                            reference_date,
                            "inference",
                            "medium",
                            "agregado de classes mapeadas por CNPJ do gestor",
                        )
                    )
        if primary is None:
            gaps.append("entidade principal não encontrada no cadastro CVM")
        elif not primary.is_active:
            gaps.append(f"entidade principal com status CVM '{primary.status}'")
        if pilot.institution_type == "banco":
            gaps.append(
                "dados prudenciais do banco dependem do IF.data (BCB)"
                + (
                    " — indisponível nesta execução"
                    if ctx.source_runs["bcb_ifdata_cadastro"].status != "ok"
                    else ""
                )
            )
            gaps.append("mesas/áreas e decisores do banco exigem validação comercial")
        if not summary["active_classes"]:
            gaps.append("nenhuma classe de fundo ativa mapeada às entidades da conta")
        elif summary["comparable_12m_share"] is not None and summary["comparable_12m_share"] < 0.5:
            gaps.append("menos da metade das classes com retorno 12m comparável")
        if summary["classes_without_daily_report_by_type"]:
            detail = ", ".join(
                f"{label}: {count}"
                for label, count in summary["classes_without_daily_report_by_type"].items()
            )
            gaps.append(f"classes ativas sem Informe Diário atualizado ({detail})")
        if not directors.get(account.primary_cnpj):
            gaps.append("sem diretor de gestão (Res. CVM 21) no cadastro")
        geo_primary = next(
            (
                row
                for row in entity_rows
                if row["account_id"] == pilot.account_id and row["cnpj"] == account.primary_cnpj
            ),
            None,
        )
        if geo_primary and not geo_primary["geocode_is_exact"]:
            gaps.append(
                f"geocodificação da sede não exata ({geo_primary['geocode_status']}, "
                f"precisão {geo_primary['geocode_precision']})"
            )
        account_rows.append(
            {
                "account_id": pilot.account_id,
                "canonical_name": pilot.canonical_name,
                "institution_type": pilot.institution_type,
                "analysis_unit": pilot.analysis_unit,
                "primary_cnpj": account.primary_cnpj,
                "primary_cnpj_formatted": format_cnpj(account.primary_cnpj),
                "legal_name": primary.legal_name if primary else None,
                "official_address": primary.address_line if primary else None,
                "official_phone": primary.phone if primary else None,
                "entities_registered": len(account.entities),
                "entities_found": len(entities),
                "geocode_precision": geo_primary["geocode_precision"] if geo_primary else None,
                "latitude": geo_primary["latitude"] if geo_primary else None,
                "longitude": geo_primary["longitude"] if geo_primary else None,
                "portfolio_directors": len(directors.get(account.primary_cnpj, [])),
                **summary,
                "gaps": gaps,
            }
        )

    review = merge_review_queue(paths.review_queue, conflicts)
    open_by_account: dict[str, int] = defaultdict(int)
    for conflict in review:
        if conflict.resolution_status == "pending_review":
            open_by_account[conflict.account_id] += 1
    for row in account_rows:
        row["open_conflicts"] = open_by_account.get(row["account_id"], 0)

    nominatim_artifacts = [r for r in geocodes.values() if r.raw_sha256]
    ctx.source_runs["osm_nominatim"] = SourceRun(
        "osm_nominatim",
        "ok" if nominatim_artifacts else ("not_used" if not geocode_addresses else "unavailable"),
        max((r.fetched_at for r in nominatim_artifacts if r.fetched_at), default=None),
        None,
        len(nominatim_artifacts),
        f"{sum(r.is_exact for r in geocodes.values())}/{len(geocodes)} endereços com precisão de porta",
    )

    out = paths.output_dir
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(
        out / "account_enrichment.csv",
        [
            {
                **row,
                "gaps": " | ".join(row["gaps"]),
                "median_return_12m_by_classification": json.dumps(
                    row["median_return_12m_by_classification"], ensure_ascii=False
                ),
            }
            for row in account_rows
        ],
    )
    _write_csv(out / "legal_entities.csv", entity_rows)
    _write_csv(out / "people_public_registry.csv", people_rows)
    _write_csv(
        out / "fund_classes.csv",
        [
            {
                **asdict(c),
                "account_id": owner[c.manager_cnpj],
                "is_active": c.is_active,
                "is_fund_of_funds": c.is_fund_of_funds,
            }
            for c in fund_classes
        ],
    )
    _write_csv(out / "fund_metrics.csv", metric_rows)
    _write_csv(out / "geocodes.csv", [asdict(g) for g in geocodes.values()])
    _write_csv(out / "observations.csv", [asdict(o) for o in observations])
    used_artifacts = {adm_artifact.sha256: adm_artifact, reg_artifact.sha256: reg_artifact}
    used_artifacts.update({a.sha256: a for a in daily_artifacts})
    geocode_shas = {g.raw_sha256 for g in geocodes.values() if g.raw_sha256}
    for entry in ctx.fetcher.cache.entries():
        if entry.sha256 in geocode_shas:
            used_artifacts.setdefault(entry.sha256, entry)
    _write_csv(
        out / "source_manifest.csv",
        [
            {
                "source_id": a.source_id,
                "url": a.url,
                "raw_sha256": a.sha256,
                "fetched_at": a.fetched_at,
                "http_status": a.http_status,
                "size_bytes": a.size_bytes,
            }
            for a in sorted(used_artifacts.values(), key=lambda item: (item.source_id, item.sha256))
        ],
    )
    if daily.height:
        daily.write_parquet(out / "fund_daily.parquet")

    counts: dict[str, int] = {
        "legal_entities": len(entity_rows),
        "fund_classes": len(fund_classes),
        "share_class_metrics": len(metric_rows),
        "daily_rows": daily.height,
        "observations": len(observations),
        "geocoded_addresses": len(geocodes),
        "geocode_requests_this_run": geocode_runs,
        "people_public_registry": len(people_rows),
    }
    freshness = [as_dict(check_freshness(run, ctx.today)) for run in ctx.source_runs.values()]
    payload = {
        "version": ENRICHMENT_VERSION,
        "run_at": run_at,
        "fund_reference_date": reference_date,
        "freshness": freshness,
        "accounts": account_rows,
        "rules": list(RULES),
        "review_queue": paths.review_queue.as_posix(),
        "conflicts_total": len(review),
        "conflicts_pending": sum(c.resolution_status == "pending_review" for c in review),
        "counts": counts,
    }
    write_reports(out, paths.report_doc, payload)
    logger.info("enrichment_complete", **counts)
    return payload
