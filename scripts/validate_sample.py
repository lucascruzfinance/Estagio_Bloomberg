"""Independent sample validation of what the API serves.

Deliberately re-implements every calculation with the standard library only
(csv, zipfile, json, hashlib) instead of importing the pipeline, so a bug in
the pipeline cannot validate itself. Reads the raw CVM files from the immutable
cache, the weights straight from the YAML, and the raw Nominatim responses.

    python scripts/validate_sample.py [--api http://127.0.0.1:8000] [--seed 20261030]

Writes docs/validation_report.md and exits 1 if any check fails.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
BBOX = {  # generous metro boxes per UF
    "SP": (-47.2, -24.1, -46.2, -23.2),
    "RJ": (-43.8, -23.1, -43.0, -22.7),
    "PE": (-35.1, -8.25, -34.8, -7.9),
}


@dataclass
class Check:
    name: str
    checked: int = 0
    failures: list[str] = field(default_factory=list)
    note: str = ""
    skipped: bool = False

    @property
    def status(self) -> str:
        if self.skipped:
            return "pulado"
        return "ok" if not self.failures else "FALHA"


class Api:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")

    def get(self, path: str, **params: Any) -> Any:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self.base}{path}{'?' + query if query else ''}"
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest() -> list[dict[str, str]]:
    with (ROOT / "data/enriched/source_manifest.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        return list(csv.DictReader(handle))


def raw_path(source_id: str, sha: str, suffix: str) -> Path:
    return RAW / source_id / f"{sha}{suffix}"


# ------------------------------------------------------------------ checks


def check_counts(api: Api, config: dict[str, Any]) -> Check:
    check = Check("Contagens: contas, unidades e entidades")
    with (ROOT / "data/staging/pilot_accounts.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        pilot = list(csv.DictReader(handle))
    registry = yaml.safe_load(
        (ROOT / "data/reference/identity_registry.yaml").read_text(encoding="utf-8")
    )
    accounts = api.get("/api/v1/accounts", page_size=200)
    scores = api.get("/api/v1/scores", page_size=200)
    banks = set(config["bank_desks"])
    expected_units = sum(1 for p in pilot if p["account_id"] not in banks) + sum(
        len(d) for d in config["bank_desks"].values()
    )
    expected_entities = sum(len(a["entities"]) for a in registry["accounts"].values())
    served_entities = sum(
        len(api.get(f"/api/v1/accounts/{p['account_id']}")["legal_entities"]) for p in pilot
    )
    for label, expected, served in (
        ("contas", len(pilot), accounts["meta"]["total"]),
        ("unidades pontuadas", expected_units, scores["meta"]["total"]),
        ("entidades legais", expected_entities, served_entities),
    ):
        check.checked += 1
        if expected != served:
            check.failures.append(f"{label}: esperado {expected}, API {served}")
    check.note = f"{len(pilot)} contas, {expected_units} unidades, {expected_entities} entidades"
    return check


def _aggregate(
    factors: list[dict[str, Any]], weights: dict[str, float]
) -> tuple[float | None, float, float, float]:
    total = sum(weights.values())
    available = [f for f in factors if f["value"] is not None]
    have = sum(weights[f["key"]] for f in available)
    weighted = sum(weights[f["key"]] * f["value"] for f in available)
    point = 100 * weighted / have if have else None
    return point, 100 * weighted / total, 100 * (weighted + total - have) / total, have / total


def check_scores(api: Api, config: dict[str, Any]) -> Check:
    check = Check("Scores recalculados a partir dos fatores e dos pesos do YAML")
    fit_w = {k: v["weight"] for k, v in config["fit"].items()}
    timing_w = {k: v["weight"] for k, v in config["timing"].items()}
    pf, pt = config["priority_index"]["fit"], config["priority_index"]["timing"]
    min_timing = config["tiers"]["min_timing_coverage"]
    worst = 0.0
    rows = api.get("/api/v1/scores", page_size=200)["data"]
    for row in rows:
        explanation = api.get(
            f"/api/v1/scores/{urllib.parse.quote(row['unit_key'], safe=':')}/explanation"
        )
        factors = explanation["factors"]
        fit = _aggregate([f for f in factors if f["group"] == "fit"], fit_w)
        timing = _aggregate([f for f in factors if f["group"] == "timing"], timing_w)
        priority = (
            pf * fit[0] + pt * timing[0]
            if fit[0] is not None and timing[0] is not None and timing[3] >= min_timing
            else None
        )
        pairs = [
            ("fit", fit[0], row["fit"]["point"]),
            ("fit.min", fit[1], row["fit"]["lower"]),
            ("fit.max", fit[2], row["fit"]["upper"]),
            ("timing", timing[0], row["timing"]["point"]),
            ("timing.min", timing[1], row["timing"]["lower"]),
            ("timing.max", timing[2], row["timing"]["upper"]),
            ("prioridade", priority, row["priority"]["point"]),
        ]
        for label, mine, served in pairs:
            check.checked += 1
            if (mine is None) != (served is None):
                check.failures.append(
                    f"{row['unit_key']} {label}: recalculado {mine}, API {served}"
                )
            elif mine is not None and served is not None:
                worst = max(worst, abs(mine - served))
                if abs(mine - served) > 0.006:
                    check.failures.append(f"{row['unit_key']} {label}: {mine:.4f} vs {served:.4f}")
    ranked = [r for r in rows if r["priority"]["point"] is not None]
    points = [r["priority"]["point"] for r in sorted(ranked, key=lambda r: r["rank"])]
    check.checked += 1
    if points != sorted(points, reverse=True):
        check.failures.append("ordem do ranking não segue a prioridade")
    check.note = f"{len(rows)} unidades, maior desvio {worst:.4f} pontos (API arredonda em 2 casas)"
    return check


def _raw_daily(class_cnpj: str, subclass: str) -> dict[date, dict[str, float]]:
    """Daily rows for one share class straight from the raw monthly zips."""
    files = sorted(
        (row for row in manifest() if row["source_id"] == "cvm_inf_diario"),
        key=lambda row: (row["url"], row["fetched_at"]),
    )
    series: dict[date, dict[str, float]] = {}
    formatted = (
        f"{class_cnpj[:2]}.{class_cnpj[2:5]}.{class_cnpj[5:8]}/{class_cnpj[8:12]}-{class_cnpj[12:]}"
    )
    for row in files:
        path = raw_path("cvm_inf_diario", row["raw_sha256"], ".zip")
        with zipfile.ZipFile(path) as archive:
            member = next(n for n in archive.namelist() if n.endswith(".csv"))
            text = archive.read(member).decode("latin-1")
        for record in csv.DictReader(io.StringIO(text), delimiter=";"):
            if record["CNPJ_FUNDO_CLASSE"] not in (formatted, class_cnpj):
                continue
            if (record.get("ID_SUBCLASSE") or "") != subclass:
                continue
            day = date.fromisoformat(record["DT_COMPTC"])
            series[day] = {  # later files (revisions) overwrite earlier ones
                "quota": float(record["VL_QUOTA"]),
                "nav": float(record["VL_PATRIM_LIQ"]),
                "flow": float(record["CAPTC_DIA"] or 0) - float(record["RESG_DIA"] or 0),
            }
    return series


def check_fund_returns(api: Api, rng: random.Random) -> tuple[Check, Check]:
    returns = Check("Retorno 12m, PL e captação recalculados dos zips brutos da CVM")
    chart = Check("Série do gráfico de cota igual aos dados brutos")
    if not (RAW / "cvm_inf_diario").exists():
        for c in (returns, chart):
            c.skipped, c.note = True, "cache bruto data/raw ausente (rode o enriquecimento)"
        return returns, chart
    candidates: list[dict[str, Any]] = []
    for account in api.get("/api/v1/accounts", page_size=200)["data"]:
        funds = api.get(
            "/api/v1/funds", account_id=account["account_id"], with_metrics="true", page_size=200
        )["data"]
        candidates += [
            f for f in funds if f["metrics"] and f["metrics"]["return_12m_status"] == "ok"
        ]
    sample = rng.sample(candidates, k=min(8, len(candidates)))
    worst = 0.0
    for fund in sample:
        metrics = fund["metrics"]
        reference = date.fromisoformat(metrics["reference_date"])
        series = _raw_daily(fund["class_cnpj"], fund["subclass_id"])
        days = sorted(d for d in series if series[d]["quota"] > 0)
        end = max(d for d in days if d <= reference)
        start = max(d for d in days if d <= reference - timedelta(days=365))
        mine = series[end]["quota"] / series[start]["quota"] - 1
        flow = sum(
            series[d]["flow"] for d in days if reference - timedelta(days=365) < d <= reference
        )
        for label, a, b, tol in (
            ("retorno 12m", mine, metrics["return_12m"], 1e-8),
            ("PL", series[end]["nav"], metrics["latest_nav_brl"], 0.01),
            ("captação 12m", flow, metrics["net_flow_12m_brl"], 0.05),
        ):
            returns.checked += 1
            worst = max(worst, abs(a - b)) if label == "retorno 12m" else worst
            if abs(a - b) > tol:
                returns.failures.append(
                    f"{fund['class_cnpj']}/{fund['subclass_id'] or 'classe'} {label}: {a} vs {b}"
                )
        performance = api.get(
            f"/api/v1/funds/{fund['class_cnpj']}/performance", subclass_id=fund["subclass_id"]
        )
        points = performance["points"]
        chart.checked += 4
        if len(points) != len(days):
            chart.failures.append(
                f"{fund['class_cnpj']}: {len(points)} pontos vs {len(days)} no bruto"
            )
        if abs(points[0]["quota"] - series[days[0]]["quota"]) > 1e-9:
            chart.failures.append(f"{fund['class_cnpj']}: primeira cota diverge")
        if abs(points[-1]["quota"] - series[days[-1]]["quota"]) > 1e-9:
            chart.failures.append(f"{fund['class_cnpj']}: última cota diverge")
        if abs(points[0]["quota_index"] - 100) > 1e-9:
            chart.failures.append(f"{fund['class_cnpj']}: índice não começa em 100")
    returns.note = f"{len(sample)} classes sorteadas entre {len(candidates)}; maior desvio de retorno {worst:.2e}"
    chart.note = f"{len(sample)} séries comparadas ponto a ponto nas pontas e na contagem"
    return returns, chart


def check_sources(api: Api) -> Check:
    check = Check("Fontes: hash do arquivo bruto e domínio oficial")
    if not RAW.exists():
        check.skipped, check.note = True, "cache bruto data/raw ausente"
        return check
    with (ROOT / "data/staging/pilot_accounts.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        ids = [row["account_id"] for row in csv.DictReader(handle)]
    seen: set[str] = set()
    for account_id in ids:
        detail = api.get(f"/api/v1/accounts/{account_id}")
        for entity in detail["legal_entities"]:
            source = entity["source"]
            check.checked += 1
            if urllib.parse.urlparse(source["url"]).hostname != "dados.cvm.gov.br":
                check.failures.append(f"{entity['cnpj']}: domínio {source['url']}")
            sha = source["sha256"]
            if sha in seen:
                continue
            seen.add(sha)
            path = raw_path(source["source_type"], sha, ".zip")
            if not path.exists() or sha256(path) != sha:
                check.failures.append(
                    f"{entity['cnpj']}: arquivo bruto {sha[:12]} ausente ou alterado"
                )
        for signal in detail["signals"]:
            check.checked += 1
            if not signal["source"]["url"] and not signal["evidence"]:
                check.failures.append(f"{account_id} sinal {signal['signal_type']} sem fonte")
    check.note = f"{len(seen)} arquivo(s) bruto(s) conferido(s) por SHA-256"
    return check


def check_dates(api: Api) -> Check:
    check = Check("Datas de referência coerentes")
    meta = api.get("/api/v1/meta")
    quality = api.get("/api/v1/data-quality")
    today = datetime.now(UTC).date()
    check.checked += 3
    if meta["score_as_of_date"] != meta["fund_reference_date"]:
        check.failures.append(
            f"score {meta['score_as_of_date']} vs fundos {meta['fund_reference_date']}"
        )
    daily = next(f for f in quality["freshness"] if f["source_id"] == "cvm_inf_diario")
    if daily["data_as_of"] != meta["fund_reference_date"]:
        check.failures.append(
            f"informe {daily['data_as_of']} vs referência {meta['fund_reference_date']}"
        )
    if date.fromisoformat(meta["fund_reference_date"]) > today:
        check.failures.append("data de referência no futuro")
    for item in quality["freshness"]:
        if item["data_as_of"]:
            check.checked += 1
            if date.fromisoformat(item["data_as_of"]) > today:
                check.failures.append(f"{item['source_id']} com data futura")
    check.note = f"referência {meta['fund_reference_date']}, hoje {today.isoformat()}"
    return check


def check_coordinates(api: Api) -> Check:
    check = Check("Coordenadas: dentro da UF e iguais à resposta bruta do Nominatim")
    with (ROOT / "data/enriched/legal_entities.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        entities = {row["cnpj"]: row for row in csv.DictReader(handle)}
    collection = api.get("/api/v1/map/offices")
    for feature in collection["features"]:
        props = feature["properties"]
        lon, lat = feature["geometry"]["coordinates"]
        check.checked += 1
        box = BBOX.get(props["state"] or "")
        if box is None or not (box[0] <= lon <= box[2] and box[1] <= lat <= box[3]):
            check.failures.append(
                f"{props['canonical_name']} fora da UF {props['state']}: {lon},{lat}"
            )
        entity = entities.get(props["entity_cnpj"] or "")
        sha = entity["geocode_raw_sha256"] if entity else ""
        path = raw_path("osm_nominatim", sha, ".json") if sha else None
        if path and path.exists():
            hit = json.loads(path.read_text(encoding="utf-8"))
            check.checked += 1
            if (
                not hit
                or abs(float(hit[0]["lon"]) - lon) > 1e-6
                or abs(float(hit[0]["lat"]) - lat) > 1e-6
            ):
                check.failures.append(
                    f"{props['canonical_name']}: coordenada diverge da resposta bruta"
                )
            if props["is_exact"]:
                check.checked += 1
                number = str(hit[0].get("address", {}).get("house_number", ""))
                if not number or number.replace(".", "") not in props["address"].replace(".", ""):
                    check.failures.append(
                        f"{props['canonical_name']}: exato sem número de porta conferido"
                    )
    check.note = f"{collection['meta']['count']} escritórios; atribuição: {collection['meta']['attribution']}"
    return check


def check_traceability(api: Api) -> Check:
    check = Check("Cada fator com valor tem evidência citada")
    for row in api.get("/api/v1/scores", page_size=200)["data"]:
        explanation = api.get(
            f"/api/v1/scores/{urllib.parse.quote(row['unit_key'], safe=':')}/explanation"
        )
        for factor in explanation["factors"]:
            if factor["value"] is None:
                continue
            check.checked += 1
            if not factor["evidence"]:
                check.failures.append(f"{row['unit_key']}.{factor['key']} sem evidência")
    return check


def render(checks: list[Check], api: str, seed: int) -> str:
    lines = [
        "# Validação independente por amostragem",
        "",
        f"Gerado em {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} por `scripts/validate_sample.py` "
        f"contra `{api}` (semente {seed}).",
        "",
        "O script não importa o pipeline: recalcula com a biblioteca padrão a partir dos zips "
        "brutos da CVM no cache imutável, dos pesos do YAML e das respostas brutas do Nominatim.",
        "",
        "| Verificação | Situação | Itens | Observação |",
        "|---|---|---:|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.checked} | {check.note} |")
    failures = [f"- **{c.name}**: {failure}" for c in checks for failure in c.failures]
    lines += ["", "## Falhas", "", *(failures or ["Nenhuma."]), ""]
    lines += [
        "## O que esta validação não cobre",
        "",
        "- Se os pesos e as premissas do modelo são economicamente corretos (exige resultados "
        "comerciais reais; ver docs/pilot_metrics.md).",
        "- Se o vínculo entre entidades e grupos econômicos está certo (fila de revisão humana).",
        "- Dados que as fontes públicas não publicam (headcount, contratos vigentes).",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--seed", type=int, default=20261030)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/validation_report.md")
    args = parser.parse_args()
    api = Api(args.api)
    rng = random.Random(args.seed)
    config = yaml.safe_load(
        (ROOT / "config/scoring/opportunity_v1.yaml").read_text(encoding="utf-8")
    )
    checks = [check_counts(api, config), check_scores(api, config)]
    checks += list(check_fund_returns(api, rng))
    checks += [
        check_sources(api),
        check_dates(api),
        check_coordinates(api),
        check_traceability(api),
    ]
    args.output.write_text(render(checks, args.api, args.seed), encoding="utf-8")
    for check in checks:
        print(f"{check.status:7} {check.checked:5}  {check.name}  {check.note}")
        for failure in check.failures[:5]:
            print(f"          - {failure}")
    return 0 if all(c.status != "FALHA" for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
