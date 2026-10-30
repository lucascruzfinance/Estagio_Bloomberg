"""Per-unit raw features built from the Prompt 3 curated outputs.

Each feature keeps the evidence that produced it. A feature is ``None`` when the
data needed to observe it does not exist — never a silent zero.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import polars as pl

from networking_intel.scoring.config import DeskSpec, ScoringConfig

CVM_SOURCES = ("cvm_cad_adm_cart", "cvm_registro_fundo_classe", "cvm_inf_diario")
MANUAL_SIGNAL_TYPES = ("hiring", "m_and_a", "operational_change")


def desk_unit_key(account_id: str, desk_key: str) -> str:
    """Same key format as the Prompt 2 business units (e.g. org-x:asset-management)."""
    return f"{account_id}:{desk_key.replace('_', '-')}"


@dataclass(frozen=True)
class ManualSignal:
    signal_id: str
    account_id: str
    unit_key: str
    signal_type: str
    observed_at: date
    description: str
    strength: int
    source_url: str
    source_publisher: str


@dataclass
class UnitFeatures:
    unit_key: str
    account_id: str
    unit_name: str
    canonical_name: str
    institution_type: str
    analysis_unit: str
    desk_key: str | None
    evidence_mode: str  # observed | assumption
    reference_date: date
    priors: dict[str, float] = field(default_factory=dict)
    desk_products: tuple[str, ...] = ()
    manager_cnpjs: tuple[str, ...] = ()
    active_classes: int = 0
    strategy_classes: int = 0
    strategy_basis: str = ""
    families: dict[str, int] = field(default_factory=dict)
    data_intensity: float | None = None
    offshore_share: float | None = None
    daily_share_classes: int | None = None
    nav_non_fic: float | None = None
    launches: int | None = None
    launches_exclusive: int | None = None
    launch_examples: list[str] = field(default_factory=list)
    net_flow_ratio: float | None = None
    net_flow_brl: float | None = None
    net_flow_coverage: float | None = None
    new_entities: int | None = None
    new_entity_names: list[str] = field(default_factory=list)
    performance_excess: float | None = None
    performance_coverage: float | None = None
    manual_signals: dict[str, list[ManualSignal]] = field(default_factory=dict)
    identity_found: bool = False
    identity_found_active: bool = False
    identity_pending: bool = True
    open_conflicts: int = 0
    comparable_share: float | None = None
    freshness_share: float = 0.0
    duplicate_classes_removed: int = 0

    @property
    def dominant_family(self) -> str | None:
        if not self.families:
            return None
        return max(sorted(self.families), key=lambda name: self.families[name])


def strategy_family(class_type: str | None, classification: str | None, anbima: str | None) -> str:
    kind = (class_type or "").upper()
    cls = classification or ""
    anb = anbima or ""
    if "FIDC" in kind:
        return "Crédito estruturado (FIDC)"
    if "FIP" in kind:
        return "Private equity (FIP)"
    if "FIAGRO" in kind:
        return "Agro (FIAGRO)"
    if "FII" in kind:
        return "Imobiliário"
    if anb.startswith("Previdência"):
        return "Previdência"
    for token, family in (
        ("Multimercado", "Multimercado"),
        ("Ações", "Ações"),
        ("Renda Fixa", "Renda fixa"),
        ("Cambial", "Cambial"),
    ):
        if token in cls or token in anb:
            return family
    return "Outros"


@dataclass(frozen=True)
class CuratedInputs:
    pilot: pl.DataFrame
    classes: pl.DataFrame
    metrics: pl.DataFrame
    entities: pl.DataFrame
    quality: dict[str, Any]
    signals: list[ManualSignal]
    paths: tuple[Path, ...]


def _read_csv(path: Path) -> pl.DataFrame:
    return pl.read_csv(path, infer_schema_length=0, encoding="utf8-lossy")


def load_signals(path: Path) -> list[ManualSignal]:
    if not path.exists():
        return []
    signals = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["signal_type"] not in MANUAL_SIGNAL_TYPES:
                raise ValueError(f"unknown signal_type {row['signal_type']} in {path}")
            if not row["source_url"].startswith("http"):
                raise ValueError(f"signal {row['signal_id']} has no source URL")
            signals.append(
                ManualSignal(
                    signal_id=row["signal_id"],
                    account_id=row["account_id"],
                    unit_key=row["unit_key"],
                    signal_type=row["signal_type"],
                    observed_at=date.fromisoformat(row["observed_at"]),
                    description=row["description"],
                    strength=int(row["strength"] or 1),
                    source_url=row["source_url"],
                    source_publisher=row["source_publisher"],
                )
            )
    return signals


def load_inputs(root: Path) -> CuratedInputs:
    paths = (
        root / "data/staging/pilot_accounts.csv",
        root / "data/enriched/fund_classes.csv",
        root / "data/enriched/fund_metrics.csv",
        root / "data/enriched/legal_entities.csv",
        root / "data/enriched/quality_report.json",
        root / "data/reference/commercial_signals.csv",
    )
    return CuratedInputs(
        pilot=_read_csv(paths[0]),
        classes=_read_csv(paths[1]),
        metrics=_read_csv(paths[2]),
        entities=_read_csv(paths[3]),
        quality=json.loads(paths[4].read_text(encoding="utf-8")),
        signals=load_signals(paths[5]),
        paths=paths,
    )


def _primary_rows(metrics: pl.DataFrame) -> pl.DataFrame:
    """One row set per class: the class-level row if present, else its subclasses."""
    has_class_row = (
        metrics.filter(pl.col("subclass_id").fill_null("") == "")
        .select("class_cnpj")
        .unique(maintain_order=True)
        .with_columns(pl.lit(True).alias("_has_class_row"))
    )
    joined = metrics.join(has_class_row, on="class_cnpj", how="left")
    return joined.filter(
        pl.col("_has_class_row").is_null() | (pl.col("subclass_id").fill_null("") == "")
    ).drop("_has_class_row")


def prepare_metrics(metrics: pl.DataFrame) -> pl.DataFrame:
    """Typed, deduplicated share-class metrics with peer-relative 12m excess return."""
    typed = (
        metrics.with_columns(
            pl.col("subclass_id").fill_null(""),
            pl.col("latest_nav_brl").cast(pl.Float64, strict=False),
            pl.col("net_flow_12m_brl").cast(pl.Float64, strict=False),
            pl.col("return_12m").cast(pl.Float64, strict=False),
            (pl.col("is_fund_of_funds") == "True").alias("is_fic"),
            (pl.col("status_reference_ok") == "True").alias("reference_ok"),
        )
        .unique(subset=["class_cnpj", "subclass_id"], keep="first", maintain_order=True)
        .filter(pl.col("reference_ok"))
    )
    return _primary_rows(typed).sort(["class_cnpj", "subclass_id"])


def _peer_excess(rows: pl.DataFrame, classes: pl.DataFrame) -> pl.DataFrame:
    peer = classes.select(
        "class_cnpj", pl.col("classification").fill_null("Sem classificação").alias("peer")
    ).unique(subset=["class_cnpj"], keep="first", maintain_order=True)
    comparable = rows.join(peer, on="class_cnpj", how="left").filter(
        (pl.col("return_12m_status") == "ok") & ~pl.col("is_fic")
    )
    return comparable.with_columns(
        (pl.col("return_12m") - pl.col("return_12m").median().over("peer")).alias("excess")
    )


def _window_start(reference: date, days: int) -> date:
    return reference - timedelta(days=days)


def _quality_by_account(quality: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["account_id"]: row for row in quality["accounts"]}


def _freshness_share(quality: dict[str, Any], include_bank: bool) -> float:
    status = {item["source_id"]: item["status"] for item in quality["freshness"]}
    wanted = [*CVM_SOURCES, *(("bcb_ifdata_cadastro",) if include_bank else ())]
    return float(sum(status.get(source) == "fresh" for source in wanted) / len(wanted))


def _fund_features(
    unit: UnitFeatures,
    inputs: CuratedInputs,
    rows: pl.DataFrame,
    excess: pl.DataFrame,
    config: ScoringConfig,
) -> None:
    cnpjs = list(unit.manager_cnpjs)
    classes_all = inputs.classes.filter(
        pl.col("manager_cnpj").is_in(cnpjs) & (pl.col("is_active") == "True")
    ).sort(["class_cnpj", "fund_cnpj"])
    classes = classes_all.unique(subset=["class_cnpj"], keep="first", maintain_order=True)
    unit.duplicate_classes_removed = classes_all.height - classes.height
    unit.active_classes = classes.height
    if classes.height:
        # Structure is measured on the manager's own strategies: open, non-FIC classes.
        # Exclusive wrappers and fund-of-funds would otherwise inflate breadth and complexity.
        is_open = (pl.col("is_exclusive") != "True") & (pl.col("is_fund_of_funds") != "True")
        strategies = classes.filter(is_open)
        unit.strategy_basis = "abertas não-FIC"
        if not strategies.height:
            strategies = classes.filter(pl.col("is_fund_of_funds") != "True")
            unit.strategy_basis = "não-FIC (sem classes abertas)"
        if not strategies.height:
            strategies, unit.strategy_basis = classes, "todas as classes ativas"
        unit.strategy_classes = strategies.height
        family = [
            strategy_family(
                r["class_type"] or r["fund_type"], r["classification"], r["anbima_classification"]
            )
            for r in strategies.iter_rows(named=True)
        ]
        unit.families = dict(Counter(family))
        intensity = config.family_data_intensity
        unit.data_intensity = sum(intensity.get(f, intensity["Outros"]) for f in family) / len(
            family
        )
        offshore = [
            r["allows_full_offshore"] == "True" or "Exterior" in (r["anbima_classification"] or "")
            for r in strategies.iter_rows(named=True)
        ]
        unit.offshore_share = sum(offshore) / len(offshore)
        rules = config.evidence_rules
        launch_start = _window_start(unit.reference_date, rules.launch_window_days)
        new_funds = classes_all.unique(
            subset=["fund_cnpj"], keep="first", maintain_order=True
        ).filter(
            pl.col("fund_constitution_date").is_not_null()
            & (pl.col("fund_constitution_date").str.to_date() > launch_start)
            & (pl.col("fund_constitution_date").str.to_date() <= unit.reference_date)
        )
        open_funds = new_funds.filter(pl.col("is_exclusive") != "True")
        unit.launches = open_funds.height
        unit.launches_exclusive = new_funds.height - open_funds.height
        unit.launch_examples = sorted(open_funds["fund_name"].to_list())[:5]

    unit_rows = rows.filter(pl.col("manager_cnpj").is_in(cnpjs))
    non_fic = unit_rows.filter(~pl.col("is_fic"))
    unit.daily_share_classes = non_fic.height if classes.height else None
    nav_total = float(non_fic["latest_nav_brl"].fill_null(0).sum())
    unit.nav_non_fic = float(nav_total) if non_fic.height else None
    if unit_rows.height:
        unit.comparable_share = (
            unit_rows.filter(pl.col("return_12m_status") == "ok").height / unit_rows.height
        )
    if nav_total:
        with_flows = non_fic.filter(pl.col("net_flow_status") == "ok")
        unit.net_flow_coverage = float(with_flows["latest_nav_brl"].fill_null(0).sum()) / nav_total
        if with_flows.height:
            flow = float(with_flows["net_flow_12m_brl"].sum())
            nav = float(with_flows["latest_nav_brl"].fill_null(0).sum())
            unit.net_flow_brl = flow
            # Ratio over the starting NAV proxy (end NAV minus flow) keeps the sign meaningful.
            base = nav - flow
            unit.net_flow_ratio = flow / base if base > 0 else None
        perf = excess.filter(pl.col("manager_cnpj").is_in(cnpjs))
        perf_nav = float(perf["latest_nav_brl"].fill_null(0).sum())
        unit.performance_coverage = perf_nav / nav_total
        if perf_nav > 0:
            weighted = float((perf["excess"] * perf["latest_nav_brl"].fill_null(0)).sum())
            unit.performance_excess = weighted / perf_nav


def _entity_features(unit: UnitFeatures, inputs: CuratedInputs, config: ScoringConfig) -> None:
    entities = inputs.entities.filter(pl.col("account_id") == unit.account_id)
    if unit.manager_cnpjs:
        scoped = entities.filter(pl.col("cnpj").is_in(list(unit.manager_cnpjs)))
    else:
        scoped = entities.filter(pl.col("relation") == "bank_entity")
    start = _window_start(unit.reference_date, config.evidence_rules.expansion_window_days)
    if unit.evidence_mode == "observed":
        recent = scoped.filter(
            pl.col("cvm_registration_date").is_not_null()
            & (pl.col("cvm_registration_date").str.to_date() > start)
        )
        unit.new_entities = recent.height
        unit.new_entity_names = sorted(recent["legal_name"].to_list())
    primary = scoped.filter(pl.col("relation").is_in(["primary_manager", "bank_entity"]))
    reference = primary if primary.height else scoped
    unit.identity_found = bool(reference.height)
    unit.identity_found_active = bool(reference.height) and all(
        status == "EM FUNCIONAMENTO NORMAL" for status in reference["cvm_status"].to_list()
    )
    unit.identity_pending = any(s != "approved" for s in reference["approval_status"].to_list())


def _manual(unit: UnitFeatures, signals: list[ManualSignal], config: ScoringConfig) -> None:
    start = _window_start(unit.reference_date, config.evidence_rules.manual_signal_validity_days)
    for signal in signals:
        if signal.account_id != unit.account_id:
            continue
        if signal.unit_key and signal.unit_key != (unit.desk_key or ""):
            continue
        if not start < signal.observed_at <= unit.reference_date:
            continue
        unit.manual_signals.setdefault(signal.signal_type, []).append(signal)


def build_units(inputs: CuratedInputs, config: ScoringConfig) -> list[UnitFeatures]:
    reference_date = date.fromisoformat(str(inputs.quality["fund_reference_date"]))
    rows = prepare_metrics(inputs.metrics)
    excess = _peer_excess(rows, inputs.classes)
    quality = _quality_by_account(inputs.quality)
    units: list[UnitFeatures] = []
    for pilot in inputs.pilot.iter_rows(named=True):
        account_id = pilot["account_id"]
        is_bank = account_id in config.bank_desks
        account_entities = inputs.entities.filter(
            (pl.col("account_id") == account_id) & (pl.col("relation") != "bank_entity")
        )
        desks: list[DeskSpec | None] = list(config.bank_desks[account_id]) if is_bank else [None]
        for desk in desks:
            observed = desk is None or bool(desk.entity_cnpjs)
            unit = UnitFeatures(
                unit_key=account_id if desk is None else desk_unit_key(account_id, desk.key),
                account_id=account_id,
                unit_name=pilot["canonical_name"]
                if desk is None
                else f"{pilot['canonical_name']} — {desk.name}",
                canonical_name=pilot["canonical_name"],
                institution_type=pilot["institution_type"],
                analysis_unit=pilot["analysis_unit"],
                desk_key=None if desk is None else desk.key,
                evidence_mode="observed" if observed else "assumption",
                reference_date=reference_date,
                priors=dict(desk.priors) if desk and not desk.entity_cnpjs else {},
                desk_products=desk.products if desk else (),
                manager_cnpjs=(
                    tuple(desk.entity_cnpjs)
                    if desk is not None
                    else tuple(account_entities["cnpj"].to_list())
                ),
                open_conflicts=int(quality.get(account_id, {}).get("open_conflicts", 0)),
                freshness_share=_freshness_share(inputs.quality, include_bank=is_bank),
            )
            if observed:
                _fund_features(unit, inputs, rows, excess, config)
            _entity_features(unit, inputs, config)
            _manual(unit, inputs.signals, config)
            units.append(unit)
    return units
