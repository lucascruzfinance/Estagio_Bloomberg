"""Manager history from the pre-RCVM 175 fund register (cad_fi_hist_gestor).

A fund that starts with a manager right after another manager's mandate ended is a
transfer; a fund whose first manager is this one is a start. The file stops being
updated after the RCVM 175 migration, so the report states its last event date.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from typing import Any

from networking_intel.enrichment.cvm import _parse_date, zip_csv_rows
from networking_intel.enrichment.identity import digits

# A new mandate within this many days of the previous one ending counts as a transfer.
TRANSFER_GAP_DAYS = 31


def manager_events(
    content: bytes, manager_cnpjs: Iterable[str], *, since: date
) -> tuple[list[dict[str, Any]], date | None]:
    wanted = set(manager_cnpjs)
    mandates: dict[str, list[tuple[str, date | None, date | None, str]]] = defaultdict(list)
    last_event: date | None = None
    for row in zip_csv_rows(content, "cad_fi_hist_gestor.csv"):
        start = _parse_date(row["DT_INI_GESTOR"])
        end = _parse_date(row["DT_FIM_GESTOR"])
        for value in (start, end):
            if value and (last_event is None or value > last_event):
                last_event = value
        mandates[digits(row["CNPJ_FUNDO"])].append(
            (
                digits(row["CPF_CNPJ_GESTOR"] or ""),
                start,
                end,
                " ".join((row["GESTOR"] or "").split()),
            )
        )
    events: list[dict[str, Any]] = []
    for fund, items in mandates.items():
        items.sort(key=lambda m: m[1] or date.min)
        for index, (manager, start, end, _name) in enumerate(items):
            previous = items[index - 1] if index else None
            following = items[index + 1] if index + 1 < len(items) else None
            if manager in wanted and start and start >= since:
                transfer = (
                    previous is not None
                    and previous[0] != manager
                    and previous[2] is not None
                    and abs((start - previous[2]).days) <= TRANSFER_GAP_DAYS
                )
                events.append(
                    {
                        "fund_cnpj": fund,
                        "manager_cnpj": manager,
                        "event_type": "transfer_in" if transfer else "mandate_start",
                        "event_date": start,
                        "counterparty_cnpj": previous[0] if transfer and previous else None,
                        "counterparty_name": previous[3] if transfer and previous else None,
                    }
                )
            if manager in wanted and end and end >= since:
                transfer = (
                    following is not None
                    and following[0] != manager
                    and following[1] is not None
                    and abs((following[1] - end).days) <= TRANSFER_GAP_DAYS
                )
                events.append(
                    {
                        "fund_cnpj": fund,
                        "manager_cnpj": manager,
                        "event_type": "transfer_out" if transfer else "mandate_end",
                        "event_date": end,
                        "counterparty_cnpj": following[0] if transfer and following else None,
                        "counterparty_name": following[3] if transfer and following else None,
                    }
                )
    events.sort(key=lambda e: (e["manager_cnpj"], e["event_date"], e["fund_cnpj"], e["event_type"]))
    return events, last_event
