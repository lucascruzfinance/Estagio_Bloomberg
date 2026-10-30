"""Monthly fund documents: portfolio composition (CDA), monthly profile and Lâmina.

Each parser keeps only the classes it is given and returns plain rows; categories
and shares are descriptive inputs for Prompt 9, not scores.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

import polars as pl
from unidecode import unidecode

CVM_ENCODING = "latin-1"
CDA_CATEGORIES = (
    "public_bonds_repo",
    "fund_quotas",
    "equities",
    "private_credit",
    "derivatives",
    "foreign",
    "cash",
    "other",
    "confidential",
)
# Rows that hold a position (cash, payables and receivables are not positions).
POSITION_CATEGORIES = frozenset(CDA_CATEGORIES) - {"cash", "other"}


def _ascii(value: str | None) -> str:
    return unidecode(value or "").lower().strip()


def cda_category(block: str, application: str | None) -> str:
    """Map a CDA block and TP_APLIC to a coarse category.

    Blocks: 1 public bonds and repo, 2 fund quotas, 3 swaps, 4 listed securities and
    derivatives, 5 bank deposits, 6 private credit, 7 offshore, 8 everything else.
    """
    text = _ascii(application)
    if block == "CONFID":
        return "confidential"
    if block == "3" or any(k in text for k in ("mercado futuro", "opcoes", "a termo", "swap")):
        return "derivatives"
    if block == "1" or "titulos publicos" in text or "compromissadas" in text:
        return "public_bonds_repo"
    if block == "2" or "cotas de fundos" in text:
        return "fund_quotas"
    if block == "7" or "exterior" in text:
        return "foreign"
    if block in {"5", "6"} or any(
        k in text
        for k in ("debentures", "credito privado", "agronegocio", "outros valores mobiliarios")
    ):
        return "private_credit"
    if any(k in text for k in ("acoes", "depository receipt", "recibo de deposito")):
        return "equities"
    if "disponibilidades" in text:
        return "cash"
    return "other"


def _read(content: bytes, *, quoted: bool = False) -> pl.DataFrame:
    return pl.read_csv(
        io.StringIO(content.decode(CVM_ENCODING)),
        separator=";",
        infer_schema_length=0,
        quote_char='"' if quoted else None,
        truncate_ragged_lines=True,
    )


def _cnpj(column: str) -> pl.Expr:
    return pl.col(column).str.replace_all(r"\D", "")


def _number(column: str) -> pl.Expr:
    return pl.col(column).str.replace(",", ".").cast(pl.Float64, strict=False)


def cda_summary(content: bytes, class_cnpjs: Iterable[str], period: str) -> list[dict[str, Any]]:
    """Composition of one monthly CDA zip, one row per class."""
    wanted = list(set(class_cnpjs))
    archive = zipfile.ZipFile(io.BytesIO(content))
    names = archive.namelist()
    nav_member = next(n for n in names if n.startswith("cda_fi_PL_"))
    nav = (
        _read(archive.read(nav_member))
        .with_columns(_cnpj("CNPJ_FUNDO_CLASSE").alias("class_cnpj"), _number("VL_PATRIM_LIQ"))
        .filter(pl.col("class_cnpj").is_in(wanted))
        .group_by("class_cnpj")
        .agg(pl.col("VL_PATRIM_LIQ").max().alias("nav_brl"), pl.col("DT_COMPTC").max())
    )
    frames = []
    for name in names:
        match = re.match(r"cda_fi_(BLC_(\d)|CONFID)_", name)
        if not match:
            continue
        block = match.group(2) or "CONFID"
        frame = _read(archive.read(name)).with_columns(
            _cnpj("CNPJ_FUNDO_CLASSE").alias("class_cnpj")
        )
        frame = frame.filter(pl.col("class_cnpj").is_in(wanted))
        if frame.is_empty():
            continue
        frames.append(
            frame.select(
                "class_cnpj",
                pl.lit(block).alias("block"),
                pl.col("TP_APLIC").alias("application"),
                _number("VL_MERC_POS_FINAL").fill_null(0.0).alias("value"),
            )
        )
    if not frames:
        return []
    positions = pl.concat(frames)
    categories = [
        cda_category(b, a) for b, a in positions.select("block", "application").iter_rows()
    ]
    positions = positions.with_columns(pl.Series("category", categories))
    rows: list[dict[str, Any]] = []
    navs = {cnpj: (value, day) for cnpj, value, day in nav.iter_rows()}
    for (cnpj,), group in positions.group_by(["class_cnpj"], maintain_order=True):
        nav_brl, as_of = navs.get(str(cnpj), (None, None))
        by_category: dict[str, float] = defaultdict(float)
        derivative_rows = 0
        held: list[float] = []
        for category, value in group.select("category", "value").iter_rows():
            by_category[category] += value
            derivative_rows += category == "derivatives"
            if category in POSITION_CATEGORIES:
                held.append(abs(value))
        row: dict[str, Any] = {
            "class_cnpj": cnpj,
            "period": period,
            "as_of_date": as_of,
            "nav_brl": nav_brl,
            "positions": len(held),
            "derivative_positions": derivative_rows,
            "top10_share": (sum(sorted(held, reverse=True)[:10]) / nav_brl) if nav_brl else None,
        }
        for category in CDA_CATEGORIES:
            row[f"pct_{category}"] = (by_category[category] / nav_brl) if nav_brl else None
        rows.append(row)
    return sorted(rows, key=lambda r: r["class_cnpj"])


INVESTOR_GROUPS = {
    "retail": ("PF_VAREJO", "PJ_NAO_FINANC_VAREJO"),
    "private_banking": ("PF_PB", "PJ_NAO_FINANC_PB"),
    "institutional": (
        "BANCO",
        "CORRETORA_DISTRIB",
        "PJ_FINANC",
        "EAPC",
        "EFPC",
        "RPPS",
        "SEGUR",
        "CAPITALIZ",
    ),
    "funds": ("FI_CLUBE",),
    "non_resident": ("INVNR",),
    "distributors": ("DISTRIB",),
    "other": ("OUTRO",),
}
NOTIONAL_COLUMNS = tuple(
    f"VL_FATOR_RISCO_NOCIONAL_{side}_{factor}"
    for side in ("LONG", "SHORT")
    for factor in ("IBOVESPA", "JUROS", "CUPOM", "DOLAR", "OUTRO")
)


def perfil_rows(content: bytes, class_cnpjs: Iterable[str]) -> list[dict[str, Any]]:
    """Investor base, reported VaR and stress, derivatives notional and liquidity."""
    frame = _read(content).with_columns(_cnpj("CNPJ_FUNDO_CLASSE").alias("class_cnpj"))
    frame = frame.filter(pl.col("class_cnpj").is_in(list(set(class_cnpjs))))
    rows = []
    for record in frame.iter_rows(named=True):

        def number(column: str, record: dict[str, Any] = record) -> float | None:
            value = record.get(column)
            try:
                return float(str(value).replace(",", ".")) if value not in (None, "") else None
            except ValueError:
                return None

        row: dict[str, Any] = {
            "class_cnpj": record["class_cnpj"],
            "as_of_date": record["DT_COMPTC"],
        }
        investors = 0.0
        for group, suffixes in INVESTOR_GROUPS.items():
            shares = [number(f"PR_PL_COTST_{s}") for s in suffixes]
            known = [s for s in shares if s is not None]
            row[f"pct_nav_{group}"] = sum(known) / 100 if known else None
            investors += sum(number(f"NR_COTST_{s}") or 0 for s in suffixes)
        row["investors"] = int(investors)
        notional = [number(c) for c in NOTIONAL_COLUMNS]
        row["derivatives_notional_brl"] = sum(abs(v) for v in notional if v) or None
        row["var_pct"] = number("PR_VAR_CARTEIRA")
        row["var_model"] = record.get("MOD_VAR") or None
        row["stress_pct"] = number("PR_VARIACAO_DIARIA_COTA_ESTRESSE")
        row["private_credit_pct"] = number("PR_ATIVO_CRED_PRIV")
        row["largest_investor_pct"] = number("PR_PATRIM_LIQ_MAIOR_COTST")
        row["days_to_liquidate_half"] = number("NR_DIA_CINQU_PERC")
        rows.append(row)
    return sorted(rows, key=lambda r: (r["class_cnpj"], r["as_of_date"]))


LAMINA_FIELDS = {
    "NM_FANTASIA": "trade_name",
    "PR_PL_ATIVO_EXTERIOR": "max_foreign_pct",
    "PR_PL_ATIVO_CRED_PRIV": "max_private_credit_pct",
    "PR_PL_ALAVANC": "max_leverage_pct",
    "TAXA_ADM": "admin_fee_pct",
    "TAXA_PERFM": "performance_fee",
    "INVEST_INICIAL_MIN": "min_initial_investment_brl",
    "CLASSE_RISCO_ADMIN": "risk_class",
    "INDICE_REFER": "benchmark",
    "QT_DIA_PAGTO_RESGATE": "redemption_payment_days",
}


def lamina_rows(content: bytes, class_cnpjs: Iterable[str]) -> list[dict[str, Any]]:
    """Latest Lâmina per class/subclass. Free-text fields carry unescaped quotes, so the
    lenient stdlib reader is used instead of polars."""
    wanted = set(class_cnpjs)
    archive = zipfile.ZipFile(io.BytesIO(content))
    member = next(n for n in archive.namelist() if re.fullmatch(r"lamina_fi_\d{6}\.csv", n))
    text = archive.read(member).decode(CVM_ENCODING)
    rows = []
    for record in csv.DictReader(io.StringIO(text), delimiter=";"):
        cnpj = re.sub(r"\D", "", record.get("CNPJ_FUNDO_CLASSE") or "")
        if cnpj not in wanted:
            continue
        row: dict[str, Any] = {
            "class_cnpj": cnpj,
            "subclass_id": (record.get("ID_SUBCLASSE") or "").strip(),
            "as_of_date": record.get("DT_COMPTC"),
        }
        for column, key in LAMINA_FIELDS.items():
            value = (record.get(column) or "").strip()
            row[key] = " ".join(value.split())[:200] or None
        rows.append(row)
    return sorted(rows, key=lambda r: (r["class_cnpj"], r["subclass_id"]))
