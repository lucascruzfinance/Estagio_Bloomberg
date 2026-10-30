"""Informe Diário series for the universe: daily (curated), monthly (selected), manager.

Three outputs from one pass over the monthly files:
- daily rows for the selected classes of curated accounts (versioned, drives Fundo 360);
- month-level rows per class/subclass for every selected class of the universe;
- manager-month aggregates over all non-FIC classes (exclusive mandates included),
  with one NAV per class and day: the class-level row when it exists, otherwise the
  sum of its subclasses (avoids double counting classes reported both ways).
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import polars as pl

from networking_intel.enrichment.cache import RawArtifact
from networking_intel.enrichment.cvm import INF_DIARIO_SCHEMA
from networking_intel.universe.registries import MAX_PLAUSIBLE_FUND_NAV, UniverseClass

DAILY_COLUMNS = (
    "class_cnpj",
    "subclass_id",
    "date",
    "quota",
    "nav_brl",
    "inflow_brl",
    "outflow_brl",
    "investors",
    "raw_sha256",
)


@dataclass
class SeriesOutput:
    daily: pl.DataFrame
    monthly: pl.DataFrame
    manager_monthly: pl.DataFrame
    months: list[str] = field(default_factory=list)
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    rows_read: int = 0


def month_start(period: str) -> date:
    return date(int(period[:4]), int(period[4:]), 1)


# Files before the RCVM 175 migration report per fund (CNPJ_FUNDO, TP_FUNDO) and have
# no subclass; the single class of an adapted fund keeps the fund CNPJ.
LEGACY_COLUMNS = {"CNPJ_FUNDO": "CNPJ_FUNDO_CLASSE", "TP_FUNDO": "TP_FUNDO_CLASSE"}


def read_month(content: bytes) -> pl.DataFrame:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        member = next(name for name in archive.namelist() if name.endswith(".csv"))
        raw = archive.read(member)
    header = raw.split(b"\n", 1)[0].decode("latin-1").strip().split(";")
    overrides = {
        column: dtype
        for column, dtype in INF_DIARIO_SCHEMA.items()
        if column in {LEGACY_COLUMNS.get(h, h) for h in header}
    }
    legacy = {old: new for old, new in LEGACY_COLUMNS.items() if old in header}
    overrides.update({old: INF_DIARIO_SCHEMA[new] for old, new in legacy.items()})
    frame = pl.read_csv(
        raw, separator=";", encoding="utf8-lossy", schema_overrides=overrides
    ).rename(legacy)
    if "ID_SUBCLASSE" not in frame.columns:
        frame = frame.with_columns(pl.lit(None, dtype=pl.Utf8).alias("ID_SUBCLASSE"))
    return frame.select(
        pl.col("CNPJ_FUNDO_CLASSE").str.replace_all(r"\D", "").alias("class_cnpj"),
        pl.col("ID_SUBCLASSE").fill_null("").alias("subclass_id"),
        pl.col("DT_COMPTC").str.to_date("%Y-%m-%d").alias("date"),
        pl.col("VL_QUOTA").alias("quota"),
        pl.col("VL_PATRIM_LIQ").alias("nav_brl"),
        pl.col("CAPTC_DIA").alias("inflow_brl"),
        pl.col("RESG_DIA").alias("outflow_brl"),
        pl.col("NR_COTST").alias("investors"),
    )


def class_frame(classes: Iterable[UniverseClass], curated_managers: set[str]) -> pl.DataFrame:
    rows = [
        (
            c.class_cnpj,
            c.manager_cnpj,
            c.is_fic is True,
            c.is_selected,
            c.is_selected and c.manager_cnpj in curated_managers,
        )
        for c in classes
    ]
    return pl.DataFrame(
        rows,
        schema={
            "class_cnpj": pl.Utf8,
            "manager_cnpj": pl.Utf8,
            "is_fic": pl.Boolean,
            "is_selected": pl.Boolean,
            "is_curated_daily": pl.Boolean,
        },
        orient="row",
    )


def _monthly(frame: pl.DataFrame, month: date) -> pl.DataFrame:
    ordered = frame.sort(["class_cnpj", "subclass_id", "date"])
    return (
        ordered.group_by(["class_cnpj", "subclass_id"], maintain_order=True)
        .agg(
            pl.col("date").min().alias("first_date"),
            pl.col("date").max().alias("last_date"),
            pl.col("quota").first().alias("quota_first"),
            pl.col("quota").last().alias("quota_end"),
            pl.col("nav_brl").last().alias("nav_end_brl"),
            pl.col("investors").last().alias("investors_end"),
            pl.col("inflow_brl").sum().alias("inflow_brl"),
            pl.col("outflow_brl").sum().alias("outflow_brl"),
            pl.len().alias("days_reported"),
            pl.col("raw_sha256").first(),
        )
        .with_columns(pl.lit(month).alias("month"))
    )


def _manager_monthly(frame: pl.DataFrame, month: date, raw_sha256: str) -> pl.DataFrame:
    keys = ["class_cnpj", "date"]
    class_rows = frame.filter(pl.col("subclass_id") == "")
    subclass_rows = (
        frame.filter(pl.col("subclass_id") != "")
        .join(class_rows.select(keys), on=keys, how="anti")
        .group_by(["manager_cnpj", *keys])
        .agg(
            pl.col("nav_brl").sum(),
            pl.col("inflow_brl").sum(),
            pl.col("outflow_brl").sum(),
            pl.col("investors").sum(),
        )
    )
    columns = ["manager_cnpj", *keys, "nav_brl", "inflow_brl", "outflow_brl", "investors"]
    per_class_day = pl.concat([class_rows.select(columns), subclass_rows.select(columns)])
    per_class = (
        per_class_day.sort(["class_cnpj", "date"])
        .group_by(["manager_cnpj", "class_cnpj"], maintain_order=True)
        .agg(
            pl.col("nav_brl").last().alias("nav_end_brl"),
            pl.col("investors").last().alias("investors_end"),
            pl.col("inflow_brl").sum(),
            pl.col("outflow_brl").sum(),
        )
    )
    return (
        per_class.group_by("manager_cnpj")
        .agg(
            pl.col("nav_end_brl").sum(),
            pl.col("inflow_brl").sum(),
            pl.col("outflow_brl").sum(),
            pl.col("investors_end").sum(),
            pl.len().alias("classes_reporting"),
        )
        .with_columns(pl.lit(month).alias("month"), pl.lit(raw_sha256).alias("raw_sha256"))
    )


def trim_daily(daily: pl.DataFrame, *, min_nav_brl: float, recent_days: int) -> pl.DataFrame:
    """Keep series that are alive and material: last NAV above a floor, reported recently.

    Keeps the versioned snapshot small; every selected class still has monthly rows.
    """
    if daily.is_empty():
        return daily
    newest = daily["date"].max()
    keys = ["class_cnpj", "subclass_id"]
    alive = (
        daily.sort("date")
        .group_by(keys)
        .agg(pl.col("nav_brl").last(), pl.col("date").last())
        .filter(
            (pl.col("nav_brl") >= min_nav_brl)
            & (pl.col("date") >= pl.lit(newest) - pl.duration(days=recent_days))
        )
        .select(keys)
    )
    return daily.join(alive, on=keys, how="semi").sort([*keys, "date"])


def build_series(
    months: Iterable[tuple[str, RawArtifact, bytes]],
    classes: Iterable[UniverseClass],
    curated_managers: set[str],
) -> SeriesOutput:
    meta = class_frame(classes, curated_managers)
    daily: list[pl.DataFrame] = []
    monthly: list[pl.DataFrame] = []
    managers: list[pl.DataFrame] = []
    output = SeriesOutput(pl.DataFrame(), pl.DataFrame(), pl.DataFrame())
    for period, artifact, content in months:
        frame = read_month(content)
        output.rows_read += frame.height
        # The CVM file occasionally repeats a (class, subclass, day) row; keep the last one so
        # flows are not counted twice.
        frame = (
            frame.join(meta, on="class_cnpj", how="inner")
            .unique(subset=["class_cnpj", "subclass_id", "date"], keep="last", maintain_order=True)
            .with_columns(pl.lit(artifact.sha256).alias("raw_sha256"))
        )
        implausible = frame.filter(pl.col("nav_brl") > MAX_PLAUSIBLE_FUND_NAV)
        if implausible.height:
            for cnpj, rows in implausible.group_by("class_cnpj").len().iter_rows():
                output.anomalies.append({"period": period, "class_cnpj": cnpj, "rows": rows})
            frame = frame.filter(
                pl.col("nav_brl").is_null() | (pl.col("nav_brl") <= MAX_PLAUSIBLE_FUND_NAV)
            )
        month = month_start(period)
        daily.append(frame.filter(pl.col("is_curated_daily")).select(DAILY_COLUMNS))
        monthly.append(_monthly(frame.filter(pl.col("is_selected")), month))
        managers.append(_manager_monthly(frame.filter(~pl.col("is_fic")), month, artifact.sha256))
        output.months.append(period)
    if daily:
        output.daily = pl.concat(daily).sort(["class_cnpj", "subclass_id", "date"])
        output.monthly = pl.concat(monthly).sort(["class_cnpj", "subclass_id", "month"])
        output.manager_monthly = pl.concat(managers).sort(["manager_cnpj", "month"])
    return output
