"""Universe pipeline: registries, groups, series, fund documents, banks and benchmarks.

Online the first time, then cache-first (data/raw, outside git). Writes the versioned
snapshot to data/universe/ and the review suggestions to data/review/.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl
import structlog

from networking_intel.enrichment.cache import RawArtifact, RawCache
from networking_intel.enrichment.cvm import (
    INF_DIARIO_URL,
    ManagerRecord,
    parse_managers,
    zip_csv_rows,
)
from networking_intel.enrichment.geocode import GeocodeResult, geocode, parse_address
from networking_intel.enrichment.http import Fetcher, SourceUnavailableError
from networking_intel.enrichment.identity import format_cnpj
from networking_intel.enrichment.pipeline import months_back, zip_member_date
from networking_intel.enrichment.sources import get_source
from networking_intel.universe import UNIVERSE_VERSION, fund_docs, ifdata, sgs
from networking_intel.universe.curated import CuratedAccount, load_curated
from networking_intel.universe.geo import (
    MAPPED_CENTRES,
    building_key,
    centre_of,
    h3_cells,
    in_universe,
    street_with_number,
)
from networking_intel.universe.groups import name_suggestions, resolve_groups
from networking_intel.universe.history import manager_events
from networking_intel.universe.registries import (
    IntermediaryRecord,
    UniverseClass,
    administrator_stats,
    manager_fund_counts,
    parse_intermediaries,
    parse_universe_classes,
)
from networking_intel.universe.series import build_series, trim_daily

logger = structlog.get_logger("networking_intel.universe.pipeline")

CVM = "https://dados.cvm.gov.br/dados/"
CDA_URL = CVM + "FI/DOC/CDA/DADOS/cda_fi_{period}.zip"
PERFIL_URL = CVM + "FI/DOC/PERFIL_MENSAL/DADOS/perfil_mensal_fi_{period}.csv"
LAMINA_URL = CVM + "FI/DOC/LAMINA/DADOS/lamina_fi_{period}.zip"
RADAR_DAYS = 730
# Daily series kept in the snapshot: curated classes with NAV >= R$ 50 mi, alive in 45 days.
DAILY_MIN_NAV_BRL = 5e7
DAILY_RECENT_DAYS = 45
KIND_PRECEDENCE = (
    "banco_multiplo",
    "banco_investimento",
    "caixa_economica",
    "infraestrutura_mercado",
    "corretora",
    "gestora",
    "distribuidora",
    "administrador_fiduciario",
    "custodiante",
    "escriturador",
    "outro",
)
BANK_KINDS = frozenset({"banco_multiplo", "banco_investimento", "caixa_economica"})
IFDATA_STATES = frozenset({"SP", "RJ"})


@dataclass
class UniversePaths:
    root: Path

    @property
    def raw_dir(self) -> Path:
        return self.root / "data/raw"

    @property
    def out_dir(self) -> Path:
        return self.root / "data/universe"

    @property
    def review_dir(self) -> Path:
        return self.root / "data/review"

    @property
    def docs_dir(self) -> Path:
        return self.root / "docs"


@dataclass
class SourceStatus:
    source_id: str
    status: str
    data_as_of: str | None
    artifacts: int
    note: str = ""


@dataclass
class Run:
    fetcher: Fetcher
    today: date
    window_start: date
    used: dict[str, RawArtifact] = field(default_factory=dict)
    sources: dict[str, SourceStatus] = field(default_factory=dict)

    def use(self, artifact: RawArtifact) -> RawArtifact:
        self.used[artifact.sha256] = artifact
        return artifact

    def read(self, artifact: RawArtifact) -> bytes:
        return self.fetcher.cache.read_bytes(self.use(artifact))


def _fetch_static(run: Run, source_id: str) -> tuple[RawArtifact, bytes]:
    spec = get_source(source_id)
    artifact = run.fetcher.fetch(source_id, spec.base_url, suffix=".zip")
    return artifact, run.read(artifact)


def _newest_monthly(
    run: Run, source_id: str, url: str, suffix: str, wanted: int
) -> tuple[list[tuple[str, RawArtifact]], list[str]]:
    """Newest monthly documents (CDA, Perfil, Lâmina); unpublished months answer 404."""
    found: list[tuple[str, RawArtifact]] = []
    skipped: list[str] = []
    for period in reversed(months_back(run.today, 6)):
        try:
            artifact = run.fetcher.fetch(source_id, url.format(period=period), suffix=suffix)
        except SourceUnavailableError as error:
            skipped.append(f"{period}: {error.reason}")
            continue
        found.append((period, run.use(artifact)))
        if len(found) == wanted:
            break
    run.sources[source_id] = SourceStatus(
        source_id,
        "ok" if found else "unavailable",
        found[0][0] if found else None,
        len(found),
        "; ".join(skipped),
    )
    return found, skipped


def _primary_kind(kinds: set[str], active_classes: int) -> str:
    if "gestora" in kinds and active_classes and not kinds & BANK_KINDS:
        return "gestora"
    return next(kind for kind in KIND_PRECEDENCE if kind in kinds or kind == "outro")


@dataclass
class EntityDraft:
    cnpj: str
    legal_name: str
    trade_name: str | None
    kinds: set[str]
    registration_category: str | None
    registration_date: date | None
    street: str | None
    complement: str | None
    district: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    phone: str | None
    website: str | None
    source_id: str


def _from_manager(record: ManagerRecord, kinds: set[str]) -> EntityDraft:
    return EntityDraft(
        cnpj=record.cnpj,
        legal_name=record.legal_name,
        trade_name=record.trade_name,
        kinds=kinds,
        registration_category=record.registration_category,
        registration_date=record.registration_date,
        street=record.street,
        complement=record.complement,
        district=record.district,
        city=record.city,
        state=record.state,
        postal_code=record.postal_code,
        phone=record.phone,
        website=record.website,
        source_id="cvm_cad_adm_cart",
    )


def _from_intermediary(record: IntermediaryRecord) -> EntityDraft:
    return EntityDraft(
        cnpj=record.cnpj,
        legal_name=record.legal_name,
        trade_name=record.trade_name,
        kinds=set(record.kinds),
        registration_category=None,
        registration_date=record.registration_date,
        street=record.street,
        complement=record.complement,
        district=record.district,
        city=record.city,
        state=record.state,
        postal_code=record.postal_code,
        phone=record.phone,
        website=record.website,
        source_id="cvm_cad_intermed",
    )


def collect_entities(
    managers: dict[str, ManagerRecord],
    intermediaries: dict[str, IntermediaryRecord],
    administrators: set[str],
    curated: Sequence[CuratedAccount],
) -> tuple[dict[str, EntityDraft], list[str]]:
    """Active managers, fiduciary administrators and intermediaries in SP/RJ/Osasco,
    plus every curated CNPJ wherever it is. Returns the drafts and curated gaps."""
    drafts: dict[str, EntityDraft] = {}
    for record in managers.values():
        if not record.is_active or not in_universe(record.state, record.city):
            continue
        category = record.registration_category or ""
        kinds = set()
        if "Gestor" in category:
            kinds.add("gestora")
        if "Administrador Fiduci" in category or record.cnpj in administrators:
            kinds.add("administrador_fiduciario")
        if kinds:
            drafts[record.cnpj] = _from_manager(record, kinds)
    for intermediary in intermediaries.values():
        if not in_universe(intermediary.state, intermediary.city):
            continue
        if intermediary.cnpj in drafts:
            drafts[intermediary.cnpj].kinds |= intermediary.kinds
        else:
            drafts[intermediary.cnpj] = _from_intermediary(intermediary)
    gaps: list[str] = []
    for account in curated:
        for entity in account.entities:
            if entity.cnpj in drafts:
                continue
            manager = managers.get(entity.cnpj)
            if manager is not None and manager.is_active:
                drafts[entity.cnpj] = _from_manager(manager, {"gestora"})
            elif entity.cnpj in intermediaries:
                drafts[entity.cnpj] = _from_intermediary(intermediaries[entity.cnpj])
            else:
                gaps.append(
                    f"{account.account_key}: CNPJ {format_cnpj(entity.cnpj)} ausente ou inativo "
                    "nos cadastros da CVM"
                )
    for cnpj in administrators & drafts.keys():
        drafts[cnpj].kinds.add("administrador_fiduciario")
    return drafts, gaps


def _ifdata(run: Run) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    """SP/RJ institutions and their report values; empty lists when IF.data is down."""
    try:
        cadastro, skipped = ifdata.latest_cadastro(run.fetcher, run.today)
    except ifdata.IfDataUnavailableError as error:
        run.sources["bcb_ifdata_cadastro"] = SourceStatus(
            "bcb_ifdata_cadastro", "unavailable", None, 0, "; ".join(error.reasons)
        )
        run.sources["bcb_ifdata_valores"] = SourceStatus("bcb_ifdata_valores", "not_used", None, 0)
        return [], [], None
    run.use(cadastro.artifact)
    run.sources["bcb_ifdata_cadastro"] = SourceStatus(
        "bcb_ifdata_cadastro", "ok", cadastro.period, 1, "; ".join(skipped)
    )
    institutions = ifdata.institutions(cadastro.rows, IFDATA_STATES)
    cod_insts = {row["cod_inst"] for row in institutions}
    values: list[dict[str, Any]] = []
    summary, skipped_summary = ifdata.latest_periods(
        run.fetcher,
        "bcb_ifdata_valores",
        lambda p: ifdata.valores_url(p, ifdata.SUMMARY_REPORT),
        run.today,
        wanted=5,
    )
    income, _ = ifdata.latest_periods(
        run.fetcher,
        "bcb_ifdata_valores",
        lambda p: ifdata.valores_url(p, ifdata.INCOME_REPORT),
        run.today,
        wanted=1,
    )
    for period in summary:
        run.use(period.artifact)
        for row in ifdata.report_values(period.rows, cod_insts):
            values.append({**row, "raw_sha256": period.artifact.sha256})
    for period in income:
        run.use(period.artifact)
        for row in ifdata.report_values(period.rows, cod_insts, lines=ifdata.INCOME_LINES):
            values.append({**row, "raw_sha256": period.artifact.sha256})
    run.sources["bcb_ifdata_valores"] = SourceStatus(
        "bcb_ifdata_valores",
        "ok" if summary else "unavailable",
        summary[0].period if summary else None,
        len(summary) + len(income),
        "resumo: "
        + ", ".join(p.period for p in summary)
        + "; DRE: "
        + ", ".join(p.period for p in income)
        + ("; " + "; ".join(skipped_summary) if skipped_summary else ""),
    )
    for row in institutions:
        row["raw_sha256"] = cadastro.artifact.sha256
    return institutions, values, cadastro.period


def _benchmarks(run: Run) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    notes = []
    for spec in sgs.SERIES:
        try:
            artifact, series = sgs.fetch_series(
                run.fetcher, spec, run.window_start - timedelta(days=31), run.today
            )
        except SourceUnavailableError as error:
            notes.append(f"{spec.key}: {error.reason}")
            continue
        run.use(artifact)
        rows += series
        notes.append(f"{spec.key}: {len(series)} pontos até {max(str(r['date']) for r in series)}")
    last = max((r["date"] for r in rows if r["series_key"] == "cdi"), default=None)
    run.sources["bcb_sgs"] = SourceStatus(
        "bcb_sgs",
        "ok" if rows else "unavailable",
        str(last) if last else None,
        len(sgs.SERIES),
        "; ".join(notes),
    )
    return rows


def _inf_diario_months(run: Run, months: int) -> Iterable[tuple[str, RawArtifact, bytes]]:
    periods = months_back(run.today, months)
    missing = []
    count = 0
    for period in periods:
        recent = period >= periods[-2]
        try:
            artifact = run.fetcher.fetch(
                "cvm_inf_diario",
                INF_DIARIO_URL.format(period=period),
                suffix=".zip",
                max_age_seconds=None if recent else 90 * 86400,
            )
        except SourceUnavailableError as error:
            missing.append(f"{period}: {error.reason}")
            continue
        count += 1
        yield period, artifact, run.read(artifact)
    run.sources["cvm_inf_diario"] = SourceStatus(
        "cvm_inf_diario", "ok" if count else "unavailable", periods[-1], count, "; ".join(missing)
    )


def _geocode_buildings(
    run: Run, drafts: dict[str, EntityDraft], wanted: set[str], enabled: bool
) -> dict[str, GeocodeResult]:
    results: dict[str, GeocodeResult] = {}
    seen: dict[str, EntityDraft] = {}
    for cnpj in sorted(wanted):
        draft = drafts[cnpj]
        key = building_key(draft.street, draft.city, draft.state, draft.complement)
        if key and key not in seen:
            seen[key] = draft
    if not enabled:
        run.sources["osm_nominatim"] = SourceStatus("osm_nominatim", "not_used", None, 0)
        return results
    for key, draft in sorted(seen.items()):
        line = street_with_number(draft.street, draft.complement) or ""
        address = parse_address(line, draft.city, draft.state, draft.postal_code)
        results[key] = geocode(run.fetcher, address)
    by_sha = {entry.sha256: entry for entry in run.fetcher.cache.entries()}
    for result in results.values():
        if result.raw_sha256 in by_sha:
            run.use(by_sha[result.raw_sha256])
    exact = sum(r.is_exact for r in results.values())
    run.sources["osm_nominatim"] = SourceStatus(
        "osm_nominatim",
        "ok" if results else "unavailable",
        None,
        len(results),
        f"{exact}/{len(results)} prédios com precisão de porta",
    )
    return results


def _write_csv(
    path: Path, rows: Sequence[dict[str, Any]], columns: Sequence[str] | None = None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(columns or (rows[0].keys() if rows else []))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _parquet(frame: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(path, compression="zstd", compression_level=19, statistics=False)


def run_universe(
    paths: UniversePaths,
    *,
    fetcher: Fetcher | None = None,
    today: date | None = None,
    months: int = 37,
    geocode_buildings: bool = True,
    progress: Callable[[str], None] = lambda message: None,
) -> dict[str, Any]:
    run_at = datetime.now(UTC).isoformat(timespec="seconds")
    current = today or datetime.now(UTC).date()
    window = months_back(current, months)
    run = Run(
        fetcher=fetcher or Fetcher(RawCache(paths.raw_dir)),
        today=current,
        window_start=date(int(window[0][:4]), int(window[0][4:]), 1),
    )
    root = paths.root
    curated = load_curated(
        root / "data/staging/pilot_accounts.csv",
        root / "data/reference/identity_registry.yaml",
        root / "data/reference/curated_wave2.yaml",
    )
    curated_owner = {e.cnpj: a.account_key for a in curated for e in a.entities}
    curated_side = {e.cnpj: a.side for a in curated for e in a.entities}

    progress("cadastros CVM")
    adm_artifact, adm_bytes = _fetch_static(run, "cvm_cad_adm_cart")
    _, reg_bytes = _fetch_static(run, "cvm_registro_fundo_classe")
    int_artifact, int_bytes = _fetch_static(run, "cvm_cad_intermed")
    hist_artifact, hist_bytes = _fetch_static(run, "cvm_cad_fi_hist")
    as_of = {
        "cvm_cad_adm_cart": zip_member_date(adm_bytes, "cad_adm_cart_pj.csv"),
        "cvm_registro_fundo_classe": zip_member_date(reg_bytes, "registro_fundo.csv"),
        "cvm_cad_intermed": zip_member_date(int_bytes, "cad_intermed.csv"),
        "cvm_cad_fi_hist": zip_member_date(hist_bytes, "cad_fi_hist_gestor.csv"),
    }
    for source_id, value in as_of.items():
        run.sources[source_id] = SourceStatus(source_id, "ok", value.isoformat(), 1)
    source_sha = {
        "cvm_cad_adm_cart": adm_artifact.sha256,
        "cvm_cad_intermed": int_artifact.sha256,
    }

    managers = parse_managers(adm_bytes)
    intermediaries = parse_intermediaries(int_bytes)
    admin_stats, registry_anomalies = administrator_stats(reg_bytes)
    drafts, curated_gaps = collect_entities(
        managers, intermediaries, {c for c, s in admin_stats.items() if s.active_funds}, curated
    )
    manager_cnpjs = sorted(c for c, d in drafts.items() if "gestora" in d.kinds)
    progress("classes de fundos do universo")
    classes = parse_universe_classes(reg_bytes, manager_cnpjs, cancelled_since=run.window_start)
    counts = manager_fund_counts(classes)

    progress("IF.data (Banco Central)")
    institutions, bank_values, ifdata_period = _ifdata(run)
    individual = {row["cod_inst"]: row for row in institutions if not row["is_conglomerate"]}

    names = {cnpj: (d.trade_name or d.legal_name) for cnpj, d in drafts.items()}
    memberships = resolve_groups(names, curated, institutions)
    suggestions = name_suggestions(memberships, names)

    progress("Informe Diário (36 meses)")
    curated_managers = {c for c in curated_owner if c in set(manager_cnpjs)}
    series = build_series(_inf_diario_months(run, months), classes, curated_managers)
    series.daily = trim_daily(
        series.daily, min_nav_brl=DAILY_MIN_NAV_BRL, recent_days=DAILY_RECENT_DAYS
    )
    latest_month = series.manager_monthly["month"].max() if series.manager_monthly.height else None
    latest_nav = (
        {
            cnpj: nav
            for cnpj, nav in series.manager_monthly.filter(pl.col("month") == latest_month)
            .select("manager_cnpj", "nav_end_brl")
            .iter_rows()
        }
        if latest_month
        else {}
    )

    progress("CDA, Perfil Mensal e Lâmina")
    selected = sorted(c.class_cnpj for c in classes if c.is_selected)
    holdings: list[dict[str, Any]] = []
    for period, artifact in _newest_monthly(run, "cvm_cda", CDA_URL, ".zip", 3)[0]:
        for row in fund_docs.cda_summary(run.read(artifact), selected, period):
            holdings.append({**row, "raw_sha256": artifact.sha256})
    profiles: list[dict[str, Any]] = []
    for _period, artifact in _newest_monthly(run, "cvm_perfil_mensal", PERFIL_URL, ".csv", 3)[0]:
        for row in fund_docs.perfil_rows(run.read(artifact), selected):
            profiles.append({**row, "raw_sha256": artifact.sha256})
    laminas: list[dict[str, Any]] = []
    for _period, artifact in _newest_monthly(run, "cvm_lamina", LAMINA_URL, ".zip", 1)[0]:
        for row in fund_docs.lamina_rows(run.read(artifact), selected):
            laminas.append({**row, "raw_sha256": artifact.sha256})

    progress("histórico de gestores (cad_fi_hist)")
    events, last_event = manager_events(hist_bytes, manager_cnpjs, since=run.window_start)
    run.sources["cvm_cad_fi_hist"].note = f"último evento no arquivo: {last_event}"
    for event in events:
        event["raw_sha256"] = hist_artifact.sha256

    progress("benchmarks (SGS)")
    benchmarks = _benchmarks(run)

    centres: dict[str, tuple[str | None, str | None]] = {
        cnpj: centre_of(d.state, d.city, d.street, d.district) for cnpj, d in drafts.items()
    }
    to_geocode = {cnpj for cnpj, (centre, _) in centres.items() if centre in MAPPED_CENTRES} | (
        curated_owner.keys() & drafts.keys()
    )
    progress(f"geocodificação por prédio ({len(to_geocode)} entidades)")
    geocodes = _geocode_buildings(run, drafts, to_geocode, geocode_buildings)

    radar_since = current - timedelta(days=RADAR_DAYS)
    entity_rows: list[dict[str, Any]] = []
    for cnpj in sorted(drafts):
        draft = drafts[cnpj]
        stats = counts.get(cnpj, {})
        admin = admin_stats.get(cnpj)
        kind = _primary_kind(draft.kinds, int(stats.get("active_classes", 0)))
        side = curated_side.get(cnpj) or ("buy_side" if kind == "gestora" else "sell_side")
        if cnpj in curated_owner:
            tier = "curated"
        elif (
            "gestora" in draft.kinds
            and draft.registration_date
            and draft.registration_date >= radar_since
        ):
            tier = "radar"
        else:
            tier = "universe"
        centre, basis = centres[cnpj]
        key = building_key(draft.street, draft.city, draft.state, draft.complement)
        geo = geocodes.get(key) if key and cnpj in to_geocode else None
        latitude = geo.latitude if geo else None
        longitude = geo.longitude if geo else None
        r8, r9 = h3_cells(latitude, longitude)
        membership = memberships[cnpj]
        institution = individual.get(cnpj[:8])
        entity_rows.append(
            {
                "cnpj": cnpj,
                "cnpj_root": cnpj[:8],
                "legal_name": draft.legal_name,
                "trade_name": draft.trade_name or "",
                "kinds": ";".join(sorted(draft.kinds)),
                "primary_kind": kind,
                "side": side,
                "coverage_tier": tier,
                "curated_account_key": curated_owner.get(cnpj, ""),
                "registration_category": draft.registration_category or "",
                "registration_date": draft.registration_date,
                "street": draft.street or "",
                "complement": draft.complement or "",
                "district": draft.district or "",
                "city": draft.city or "",
                "state": draft.state or "",
                "postal_code": draft.postal_code or "",
                "centre": centre or "",
                "centre_basis": basis or "",
                "building_key": key or "",
                "latitude": latitude,
                "longitude": longitude,
                "geocode_precision": geo.precision if geo else "none",
                "geocode_is_exact": bool(geo and geo.is_exact),
                "geocode_status": geo.status
                if geo
                else ("not_in_scope" if cnpj not in to_geocode else "no_building_number"),
                "h3_r8": r8 or "",
                "h3_r9": r9 or "",
                "phone_official": draft.phone or "",
                "website_official": draft.website or "",
                "group_key": membership.group_key,
                "group_name": membership.group_name,
                "group_basis": membership.basis,
                "ifdata_cod_inst": institution["cod_inst"] if institution else "",
                "ifdata_conglomerate": institution["prudential_conglomerate"]
                if institution
                else "",
                "active_classes": int(stats.get("active_classes", 0)),
                "selected_classes": int(stats.get("selected_classes", 0)),
                "nav_registry_non_fic_brl": round(stats.get("nav_registry_non_fic_brl", 0.0), 2)
                or None,
                "nav_daily_report_brl": latest_nav.get(cnpj),
                "nav_daily_report_month": latest_month if cnpj in latest_nav else None,
                "funds_administered": admin.active_funds if admin else 0,
                "nav_administered_brl": round(admin.nav_brl, 2) if admin else None,
                "source_id": draft.source_id,
                "raw_sha256": source_sha[draft.source_id],
                "as_of_date": as_of[draft.source_id],
            }
        )

    groups: dict[str, dict[str, Any]] = {}
    for membership in memberships.values():
        group = groups.setdefault(
            membership.group_key,
            {
                "group_key": membership.group_key,
                "group_name": membership.group_name,
                "basis": membership.basis,
                "members": 0,
            },
        )
        group["members"] += 1
    membership_rows = [
        asdict(m) for m in sorted(memberships.values(), key=lambda m: (m.group_key, m.cnpj))
    ]

    curated_rows = [
        {
            "account_key": a.account_key,
            "display_name": a.display_name,
            "wave": a.wave,
            "side": a.side,
            "segment": a.segment,
            "rationale": a.rationale,
            "primary_cnpj": a.primary_cnpj,
            "entities": len(a.entities),
            "approval_status": "pending_human_review"
            if any(e.approval_status == "pending_human_review" for e in a.entities)
            else "approved",
        }
        for a in curated
    ]
    curated_entity_rows = [
        {
            "account_key": a.account_key,
            "cnpj": e.cnpj,
            "relation": e.relation,
            "business_unit": e.business_unit or "",
            "approval_status": e.approval_status,
            "relation_evidence": e.relation_evidence,
            "found_in_registry": e.cnpj in drafts,
        }
        for a in curated
        for e in a.entities
    ]
    class_rows = [
        {
            **{k: v for k, v in asdict(c).items()},
            "is_active": c.is_active,
            "is_selected": c.is_selected,
            "curated_account_key": curated_owner.get(c.manager_cnpj, ""),
        }
        for c in classes
    ]
    building_rows = []
    tenants: Counter[str] = Counter(
        row["building_key"]
        for row in entity_rows
        if row["building_key"] and row["latitude"] is not None
    )
    for key, result in sorted(geocodes.items()):
        r8, r9 = h3_cells(result.latitude, result.longitude)
        building_rows.append(
            {
                "building_key": key,
                "tenants": tenants.get(key, 0),
                "latitude": result.latitude,
                "longitude": result.longitude,
                "precision": result.precision,
                "is_exact": result.is_exact,
                "status": result.status,
                "display_name": result.display_name or "",
                "h3_r8": r8 or "",
                "h3_r9": r9 or "",
                "provider": result.provider,
                "attribution": result.attribution,
                "fetched_at": result.fetched_at or "",
                "raw_sha256": result.raw_sha256 or "",
            }
        )

    out = paths.out_dir
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "entities.csv", entity_rows)
    _write_csv(out / "economic_groups.csv", sorted(groups.values(), key=lambda g: g["group_key"]))
    _write_csv(out / "group_memberships.csv", membership_rows)
    _write_csv(out / "curated_accounts.csv", curated_rows)
    _write_csv(out / "curated_account_entities.csv", curated_entity_rows)
    _write_csv(out / "buildings.csv", building_rows)
    _write_csv(out / "fund_events.csv", events)
    _write_csv(out / "fund_holdings.csv", holdings)
    _write_csv(out / "fund_profiles.csv", profiles)
    _write_csv(out / "fund_laminas.csv", laminas)
    _write_csv(out / "bank_institutions.csv", institutions)
    _write_csv(out / "benchmarks.csv", benchmarks)
    _parquet(pl.DataFrame(class_rows, infer_schema_length=None), out / "fund_classes.parquet")
    _parquet(series.daily, out / "fund_daily_curated.parquet")
    _parquet(series.monthly, out / "fund_monthly.parquet")
    _parquet(series.manager_monthly, out / "manager_monthly.parquet")
    _parquet(pl.DataFrame(bank_values, infer_schema_length=None), out / "bank_financials.parquet")
    _write_csv(paths.review_dir / "group_suggestions.csv", suggestions)
    manifest = [
        {
            "source_id": a.source_id,
            "url": a.url,
            "raw_sha256": a.sha256,
            "fetched_at": a.fetched_at,
            "http_status": a.http_status,
            "size_bytes": a.size_bytes,
        }
        for a in sorted(run.used.values(), key=lambda item: (item.source_id, item.url, item.sha256))
    ]
    _write_csv(out / "source_manifest.csv", manifest)

    summary = summarize(
        entity_rows,
        classes,
        series,
        holdings,
        profiles,
        laminas,
        events,
        institutions,
        bank_values,
        benchmarks,
        building_rows,
        suggestions,
        curated,
        curated_gaps,
    )
    sizes = {p.name: p.stat().st_size for p in sorted(out.iterdir()) if p.is_file()}
    report = {
        "version": UNIVERSE_VERSION,
        "run_at": run_at,
        "today": current.isoformat(),
        "window": {"start": run.window_start.isoformat(), "months": series.months},
        "ifdata_period": ifdata_period,
        "sources": [asdict(s) for s in sorted(run.sources.values(), key=lambda s: s.source_id)],
        "anomalies": {
            "registry_fund_nav_above_cap": registry_anomalies,
            "daily_nav_above_cap": series.anomalies,
        },
        "curated_gaps": curated_gaps,
        "snapshot_bytes": sizes,
        "snapshot_total_bytes": sum(sizes.values()),
        **summary,
    }
    (out / "quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    logger.info("universe_complete", entities=len(entity_rows), classes=len(classes))
    return report


def summarize(
    entities: list[dict[str, Any]],
    classes: list[UniverseClass],
    series: Any,
    holdings: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
    laminas: list[dict[str, Any]],
    events: list[dict[str, Any]],
    institutions: list[dict[str, Any]],
    bank_values: list[dict[str, Any]],
    benchmarks: list[dict[str, Any]],
    buildings: list[dict[str, Any]],
    suggestions: list[dict[str, Any]],
    curated: Sequence[CuratedAccount],
    curated_gaps: list[str],
) -> dict[str, Any]:
    by_kind: Counter[str] = Counter()
    for row in entities:
        for kind in row["kinds"].split(";"):
            by_kind[kind] += 1
    centre_rows: dict[str, Counter[str]] = defaultdict(Counter)
    for row in entities:
        centre_rows[row["centre"] or "fora do universo"][row["primary_kind"]] += 1
    precision = Counter(row["precision"] for row in buildings)
    return {
        "counts": {
            "entities": len(entities),
            "by_kind": dict(sorted(by_kind.items())),
            "by_primary_kind": dict(sorted(Counter(r["primary_kind"] for r in entities).items())),
            "by_side": dict(sorted(Counter(r["side"] for r in entities).items())),
            "by_tier": dict(sorted(Counter(r["coverage_tier"] for r in entities).items())),
            "by_centre": {k: dict(sorted(v.items())) for k, v in sorted(centre_rows.items())},
            "managers_with_active_classes": sum(
                1 for r in entities if "gestora" in r["kinds"] and r["active_classes"]
            ),
            "groups": len({r["group_key"] for r in entities}),
            "entities_by_group_basis": dict(
                sorted(Counter(r["group_basis"] for r in entities).items())
            ),
            "group_suggestions_pending": len(suggestions),
            "curated_accounts": len(curated),
            "curated_entities": sum(len(a.entities) for a in curated),
            "curated_gaps": len(curated_gaps),
            "classes": len(classes),
            "classes_active": sum(c.is_active for c in classes),
            "classes_selected": sum(c.is_selected for c in classes),
            "daily_rows_curated": series.daily.height,
            "daily_series_curated": series.daily.select("class_cnpj", "subclass_id").unique().height
            if series.daily.height
            else 0,
            "monthly_rows": series.monthly.height,
            "monthly_series": series.monthly.select("class_cnpj", "subclass_id").unique().height
            if series.monthly.height
            else 0,
            "manager_month_rows": series.manager_monthly.height,
            "inf_diario_rows_read": series.rows_read,
            "holdings_rows": len(holdings),
            "profile_rows": len(profiles),
            "lamina_rows": len(laminas),
            "manager_events": len(events),
            "ifdata_institutions": len(institutions),
            "ifdata_values": len(bank_values),
            "benchmark_points": len(benchmarks),
            "buildings": len(buildings),
            "buildings_by_precision": dict(sorted(precision.items())),
            "entities_geocoded": sum(1 for r in entities if r["latitude"] is not None),
        }
    }


def reconcile_counts(raw_dir: Path) -> dict[str, Any]:
    """Independent recount from the raw zips (used by the reconciliation test)."""
    cache = RawCache(raw_dir)

    def latest(source_id: str) -> bytes:
        entries = [e for e in cache.entries() if e.source_id == source_id]
        return cache.read_bytes(max(entries, key=lambda e: e.fetched_at))

    managers = 0
    for row in zip_csv_rows(latest("cvm_cad_adm_cart"), "cad_adm_cart_pj.csv"):
        if (
            row["SIT"].strip().upper() == "EM FUNCIONAMENTO NORMAL"
            and "Gestor" in (row["CATEG_REG"] or "")
            and in_universe(row["UF"], row["MUN"])
        ):
            managers += 1
    intermediaries: set[str] = set()
    by_type: Counter[str] = Counter()
    for row in zip_csv_rows(latest("cvm_cad_intermed"), "cad_intermed.csv"):
        if "FUNCIONAMENTO NORMAL" in row["SIT"].upper() and in_universe(row["UF"], row["MUN"]):
            intermediaries.add(row["CNPJ"])
            by_type[row["TP_PARTIC"].strip()] += 1
    return {"managers": managers, "intermediaries": len(intermediaries), "by_type": dict(by_type)}
