"""Share-class return and flow metrics from CVM Informe Diário quotas.

These are *fund* returns (quota variation, net of fees) for investors. They are
not the asset manager's revenue or profit and must never be presented as such.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

import polars as pl

METRIC_VERSION = "returns-v1"
CURRENCY = "BRL"  # CVM Informe Diário reports quota and NAV in reais.
MAX_START_LAG_DAYS = 7
MAX_GAP_DAYS = 10
MAX_STALENESS_DAYS = 5
# A one-day quota move that departs from the same-day median of its peer group
# (CVM classification) by more than this is treated as a suspected quota event
# (amortisation, split/grouping, restructuring) rather than performance. Peer
# relative so that genuine market-wide shocks are kept as performance.
MAX_EXCESS_DAILY_MOVE = 0.25
SERIES_KEYS = ["class_cnpj", "subclass_id"]

WINDOWS: dict[str, int] = {"1m": 30, "3m": 91, "6m": 182, "12m": 365}


@dataclass
class ShareClassMetrics:
    class_cnpj: str
    subclass_id: str
    reference_date: date
    first_date: date | None
    last_date: date | None
    observations: int
    currency: str = CURRENCY
    metric_version: str = METRIC_VERSION
    latest_nav_brl: float | None = None
    latest_investors: int | None = None
    returns: dict[str, float | None] = field(default_factory=dict)
    return_status: dict[str, str] = field(default_factory=dict)
    net_flow_12m_brl: float | None = None
    net_flow_status: str = "not_computed"
    volatility_12m: float | None = None
    max_drawdown_12m: float | None = None
    series_flags: list[str] = field(default_factory=list)

    def as_row(self) -> dict[str, Any]:
        row = asdict(self)
        for key in ("returns", "return_status"):
            row.pop(key)
        for window in [*WINDOWS, "ytd"]:
            row[f"return_{window}"] = self.returns.get(window)
            row[f"return_{window}_status"] = self.return_status.get(window)
        row["series_flags"] = " | ".join(self.series_flags)
        return row


def _window_return(
    dates: list[date],
    quotas: list[float],
    quota_events: list[bool],
    start_target: date,
    end_index: int,
) -> tuple[float | None, str]:
    start_index = None
    for index, current in enumerate(dates):
        if current <= start_target:
            start_index = index
        else:
            break
    if start_index is None:
        return None, "insufficient_history"
    if (start_target - dates[start_index]).days > MAX_START_LAG_DAYS:
        return None, "start_observation_too_old"
    for previous, current in zip(
        dates[start_index:end_index], dates[start_index + 1 : end_index + 1], strict=True
    ):
        if (current - previous).days > MAX_GAP_DAYS:
            return None, "gap_in_series"
    if any(quota_events[start_index + 1 : end_index + 1]):
        return None, "quota_event_suspected"
    return quotas[end_index] / quotas[start_index] - 1.0, "ok"


def share_class_metrics(
    frame: pl.DataFrame, class_cnpj: str, subclass_id: str, reference_date: date
) -> ShareClassMetrics:
    series = frame.filter(
        (pl.col("class_cnpj") == class_cnpj) & (pl.col("subclass_id") == subclass_id)
    ).sort("date")
    metrics = ShareClassMetrics(
        class_cnpj=class_cnpj,
        subclass_id=subclass_id,
        reference_date=reference_date,
        first_date=None,
        last_date=None,
        observations=series.height,
    )
    duplicates = series.group_by("date").agg(pl.col("quota").n_unique().alias("n"))
    if duplicates.filter(pl.col("n") > 1).height:
        metrics.series_flags.append("conflicting_duplicate_dates")
    series = series.unique(subset=["date"], keep="last").sort("date")
    valid = series.filter(pl.col("quota").is_not_null() & (pl.col("quota") > 0))
    if valid.height < series.height:
        metrics.series_flags.append("non_positive_or_missing_quota_dropped")
    if valid.is_empty():
        metrics.return_status = {window: "no_valid_quota" for window in [*WINDOWS, "ytd"]}
        return metrics

    dates: list[date] = valid["date"].to_list()
    quotas: list[float] = valid["quota"].to_list()
    if "quota_event" in valid.columns:
        quota_events: list[bool] = valid["quota_event"].fill_null(False).to_list()
    else:
        moves = (valid["quota"] / valid["quota"].shift(1) - 1.0).abs()
        quota_events = (moves > MAX_EXCESS_DAILY_MOVE).fill_null(False).to_list()
    metrics.first_date, metrics.last_date = dates[0], dates[-1]
    last_row = valid.row(-1, named=True)
    metrics.latest_nav_brl = last_row["nav_brl"]
    metrics.latest_investors = last_row["investors"]

    if "conflicting_duplicate_dates" in metrics.series_flags:
        metrics.return_status = {w: "conflicting_duplicate_dates" for w in [*WINDOWS, "ytd"]}
        return metrics
    if (reference_date - dates[-1]).days > MAX_STALENESS_DAYS:
        metrics.series_flags.append("stale_series")
        metrics.return_status = {window: "stale_series" for window in [*WINDOWS, "ytd"]}
        return metrics

    end_index = len(dates) - 1
    targets = {window: reference_date - timedelta(days=days) for window, days in WINDOWS.items()}
    targets["ytd"] = date(reference_date.year - 1, 12, 31)
    for window, start_target in targets.items():
        value, status = _window_return(dates, quotas, quota_events, start_target, end_index)
        metrics.returns[window] = value
        metrics.return_status[window] = status

    if metrics.return_status["12m"] == "ok":
        start = targets["12m"]
        window_frame = series.filter(pl.col("date") > start)
        metrics.net_flow_12m_brl = float(
            (
                window_frame["inflow_brl"].fill_null(0) - window_frame["outflow_brl"].fill_null(0)
            ).sum()
        )
        metrics.net_flow_status = "ok"
        window_quotas = valid.filter(pl.col("date") >= dates[_index_on_or_before(dates, start)])
        log_returns = window_quotas["quota"].log().diff().drop_nulls()
        if log_returns.len() > 20:
            std = log_returns.std()
            metrics.volatility_12m = std * math.sqrt(252) if isinstance(std, float) else None
        running_peak = window_quotas["quota"].cum_max()
        drawdown = (window_quotas["quota"] / running_peak - 1.0).min()
        metrics.max_drawdown_12m = float(drawdown) if isinstance(drawdown, float) else None
    else:
        metrics.net_flow_status = "requires_full_12m_window"
    return metrics


def _index_on_or_before(dates: list[date], target: date) -> int:
    index = 0
    for position, current in enumerate(dates):
        if current <= target:
            index = position
    return index


def flag_quota_events(
    frame: pl.DataFrame, peer_groups: dict[str, str] | None = None
) -> pl.DataFrame:
    """Mark daily moves that are idiosyncratic versus same-day peers."""
    valid = (
        frame.filter(pl.col("quota").is_not_null() & (pl.col("quota") > 0))
        .unique(subset=[*SERIES_KEYS, "date"], keep="last")
        .sort([*SERIES_KEYS, "date"])
        .with_columns(
            (pl.col("quota") / pl.col("quota").shift(1).over(SERIES_KEYS) - 1.0).alias("move"),
            pl.col("class_cnpj")
            .replace_strict(peer_groups or {}, default="all", return_dtype=pl.Utf8)
            .alias("peer_group"),
        )
        .with_columns(pl.col("move").median().over(["date", "peer_group"]).alias("peer_median"))
        .with_columns(
            ((pl.col("move") - pl.col("peer_median")).abs() > MAX_EXCESS_DAILY_MOVE)
            .fill_null(False)
            .alias("quota_event")
        )
        .select(*SERIES_KEYS, "date", "quota_event")
    )
    return frame.join(valid, on=[*SERIES_KEYS, "date"], how="left")


def broad_reference_date(frame: pl.DataFrame, min_share: float = 0.5) -> date | None:
    """Latest date reported by at least `min_share` of the busiest day's series."""
    counts = frame.group_by("date").agg(pl.len().alias("n")).sort("date")
    if counts.is_empty():
        return None
    threshold = counts["n"].max() * min_share  # type: ignore[operator]
    eligible = counts.filter(pl.col("n") >= threshold)
    return eligible["date"].max()  # type: ignore[return-value]


def compute_all(
    frame: pl.DataFrame, reference_date: date, peer_groups: dict[str, str] | None = None
) -> list[ShareClassMetrics]:
    flagged = flag_quota_events(frame, peer_groups)
    partitions = flagged.partition_by(SERIES_KEYS, as_dict=True)
    return [
        share_class_metrics(partitions[key], str(key[0]), str(key[1]), reference_date)
        for key in sorted(partitions, key=lambda item: (str(item[0]), str(item[1])))
    ]
