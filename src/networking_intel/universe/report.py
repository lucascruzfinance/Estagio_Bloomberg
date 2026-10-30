"""Markdown reports generated from the universe snapshot (numbers never typed by hand)."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import polars as pl

from networking_intel.enrichment.identity import format_cnpj
from networking_intel.enrichment.sources import SOURCES
from networking_intel.universe.geo import MAPPED_CENTRES
from networking_intel.universe.pipeline import DAILY_MIN_NAV_BRL, DAILY_RECENT_DAYS, RADAR_DAYS

KIND_LABELS = {
    "gestora": "Gestora",
    "banco_multiplo": "Banco múltiplo",
    "banco_investimento": "Banco de investimento",
    "caixa_economica": "Caixa econômica",
    "corretora": "Corretora",
    "distribuidora": "Distribuidora",
    "administrador_fiduciario": "Administrador fiduciário",
    "custodiante": "Custodiante",
    "escriturador": "Escriturador",
    "infraestrutura_mercado": "Infraestrutura de mercado",
    "outro": "Outro",
}
TIER_LABELS = {"curated": "curada", "radar": "radar", "universe": "universo"}


def brl(value: float | None, unit: str = "bi") -> str:
    if value is None:
        return "—"
    divisor = {"bi": 1e9, "mi": 1e6}[unit]
    text = f"{value / divisor:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text} {unit}"


def integer(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def br_date(value: Any) -> str:
    if not value:
        return "—"
    text = str(value)[:10]
    return f"{text[8:10]}/{text[5:7]}/{text[:4]}" if len(text) == 10 else text


def period_label(value: str | None) -> str:
    return f"{value[4:6]}/{value[:4]}" if value and len(value) == 6 else (value or "—")


def _load(root: Path) -> dict[str, Any]:
    base = root / "data/universe"
    quality = json.loads((base / "quality_report.json").read_text(encoding="utf-8"))
    entities = pl.read_csv(base / "entities.csv", infer_schema_length=0)
    curated = pl.read_csv(base / "curated_accounts.csv", infer_schema_length=0)
    curated_entities = pl.read_csv(base / "curated_account_entities.csv", infer_schema_length=0)
    manager_monthly = pl.read_parquet(base / "manager_monthly.parquet")
    banks = pl.read_parquet(base / "bank_financials.parquet")
    institutions = pl.read_csv(base / "bank_institutions.csv", infer_schema_length=0)
    return {
        "quality": quality,
        "entities": entities,
        "curated": curated,
        "curated_entities": curated_entities,
        "manager_monthly": manager_monthly,
        "banks": banks,
        "institutions": institutions,
    }


def _float(value: str | None) -> float | None:
    return float(value) if value not in (None, "") else None


def _bank_assets(data: dict[str, Any]) -> tuple[dict[str, float], str | None]:
    banks: pl.DataFrame = data["banks"]
    if banks.is_empty():
        return {}, None
    assets = banks.filter((pl.col("report") == "1") & (pl.col("metric") == "Ativo Total"))
    latest = assets["period"].max()
    rows = assets.filter(pl.col("period") == latest).select("cod_inst", "value").iter_rows()
    return {cod: float(value) for cod, value in rows if value is not None}, str(latest)


def universe_markdown(data: dict[str, Any]) -> str:
    quality = data["quality"]
    counts = quality["counts"]
    entities: pl.DataFrame = data["entities"]
    rows = entities.to_dicts()
    window = quality["window"]
    lines = [
        "# Universo de território: São Paulo e Rio de Janeiro",
        "",
        f"Gerado por `python -m networking_intel.universe.cli` em {br_date(quality['run_at'])} "
        f"({quality['version']}). Todas as contagens abaixo vêm do snapshot em `data/universe/`.",
        "",
        "O universo reúne **toda** gestora ativa (cadastro de administradores de carteira da CVM), "
        "todo intermediário ativo (cadastro de intermediários da CVM: bancos, corretoras, "
        "distribuidoras, custodiantes, escrituradores, infraestrutura de mercado) e todo "
        "administrador fiduciário com fundos ativos, com sede nos municípios de São Paulo, Rio de "
        "Janeiro e Osasco. O vínculo é sempre por CNPJ exato; nome parecido só gera sugestão para "
        "revisão humana.",
        "",
        "Três camadas de cobertura:",
        "",
        f"- **curada**: as 12 contas do piloto e as 24 da onda 2 ({counts['curated_entities']} "
        "CNPJs), com vínculos pendentes de revisão humana;",
        f"- **radar**: gestoras registradas na CVM há no máximo {RADAR_DAYS // 365} anos "
        "(casas novas, que montam mesa e contratam ferramentas);",
        "- **universo**: todas as demais, automáticas.",
        "",
        "## Panorama",
        "",
        "| Medida | Valor |",
        "|---|---:|",
        f"| Entidades no universo | {integer(counts['entities'])} |",
        f"| Gestoras com classes ativas | {integer(counts['managers_with_active_classes'])} |",
        f"| Buy side / sell side | {integer(counts['by_side'].get('buy_side', 0))} / "
        f"{integer(counts['by_side'].get('sell_side', 0))} |",
        f"| Camada curada / radar / universo | {integer(counts['by_tier'].get('curated', 0))} / "
        f"{integer(counts['by_tier'].get('radar', 0))} / {integer(counts['by_tier'].get('universe', 0))} |",
        f"| Grupos econômicos | {integer(counts['groups'])} |",
        f"| Classes de fundos das gestoras do universo | {integer(counts['classes'])} "
        f"({integer(counts['classes_selected'])} abertas, não exclusivas e não FIC) |",
        f"| Instituições do IF.data em SP/RJ | {integer(counts['ifdata_institutions'])} "
        f"(período {period_label(quality['ifdata_period'])}) |",
        f"| Prédios geocodificados | {integer(counts['buildings'])} "
        f"({integer(counts['buildings_by_precision'].get('address', 0))} com número de porta conferido) |",
        "",
        "### Por tipo (uma entidade pode ter mais de um papel)",
        "",
        "| Tipo | Entidades |",
        "|---|---:|",
    ]
    for kind, value in sorted(counts["by_kind"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {KIND_LABELS.get(kind, kind)} | {integer(value)} |")

    lines += [
        "",
        "### Por centro financeiro",
        "",
        "| Centro | Gestoras | Sell side | Total | Geocodificadas |",
        "|---|---:|---:|---:|---:|",
    ]
    by_centre: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        centre = row["centre"] or "Fora de SP/RJ (conta curada)"
        by_centre[centre]["total"] += 1
        by_centre[centre]["buy" if row["side"] == "buy_side" else "sell"] += 1
        by_centre[centre]["geo"] += row["latitude"] not in (None, "")
    order = [*MAPPED_CENTRES, *sorted(set(by_centre) - set(MAPPED_CENTRES))]
    for centre in order:
        if centre in by_centre:
            c = by_centre[centre]
            lines.append(
                f"| {centre} | {integer(c['buy'])} | {integer(c['sell'])} | {integer(c['total'])} | {integer(c['geo'])} |"
            )

    monthly: pl.DataFrame = data["manager_monthly"]
    latest_month = monthly["month"].max()
    nav = {
        cnpj: value
        for cnpj, value in monthly.filter(pl.col("month") == latest_month)
        .select("manager_cnpj", "nav_end_brl")
        .iter_rows()
    }
    flows_12m = (
        monthly.filter(pl.col("month") > pl.lit(latest_month) - pl.duration(days=365))
        .group_by("manager_cnpj")
        .agg((pl.col("inflow_brl") - pl.col("outflow_brl")).sum().alias("net"))
    )
    net = dict(flows_12m.iter_rows())
    group_nav: dict[str, float] = defaultdict(float)
    group_net: dict[str, float] = defaultdict(float)
    group_meta: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row["cnpj"] in nav and nav[row["cnpj"]] is not None:
            key = row["group_key"]
            group_nav[key] += nav[row["cnpj"]]
            group_net[key] += net.get(row["cnpj"]) or 0.0
            meta = group_meta.setdefault(
                key, {"name": row["group_name"], "centres": Counter(), "tier": set()}
            )
            meta["centres"][row["centre"] or "—"] += 1
            meta["tier"].add(row["coverage_tier"])
    lines += [
        "",
        f"## 40 maiores grupos gestores por PL (Informe Diário, {br_date(latest_month)})",
        "",
        "PL somado das classes não FIC de cada gestora, com um valor por classe e dia "
        "(classe ou soma das subclasses). Inclui fundos exclusivos; não é AUM oficial do grupo. "
        "Captação líquida dos últimos 12 meses no mesmo recorte.",
        "",
        "| # | Grupo | Centro principal | Camada | PL | Captação líquida 12m |",
        "|---:|---|---|---|---:|---:|",
    ]
    for index, (key, value) in enumerate(
        sorted(group_nav.items(), key=lambda kv: -kv[1])[:40], start=1
    ):
        meta = group_meta[key]
        tier = (
            "curada"
            if "curated" in meta["tier"]
            else ("radar" if "radar" in meta["tier"] else "universo")
        )
        lines.append(
            f"| {index} | {meta['name']} | {meta['centres'].most_common(1)[0][0]} | {tier} | "
            f"{brl(value)} | {brl(group_net[key])} |"
        )

    assets, assets_period = _bank_assets(data)
    institutions = {r["cod_inst"]: r for r in data["institutions"].to_dicts()}
    if assets:
        lines += [
            "",
            f"## Sell side: 20 maiores conglomerados prudenciais com sede em SP/RJ (IF.data, {period_label(assets_period)})",
            "",
            "| # | Conglomerado | Sede | Ativo total |",
            "|---:|---|---|---:|",
        ]
        conglomerates = [
            (c, v)
            for c, v in assets.items()
            if institutions.get(c, {}).get("is_conglomerate") in ("True", "true")
        ]
        for index, (cod, value) in enumerate(
            sorted(conglomerates, key=lambda kv: -kv[1])[:20], start=1
        ):
            inst = institutions[cod]
            name = str(inst["name"]).removesuffix(" - PRUDENCIAL")
            lines.append(f"| {index} | {name} | {inst['city']}/{inst['state']} | {brl(value)} |")

    admins = sorted(
        (r for r in rows if int(r["funds_administered"] or 0) > 0),
        key=lambda r: -int(r["funds_administered"]),
    )[:15]
    lines += [
        "",
        "## Administradores fiduciários do universo (fundos ativos no registro da CVM)",
        "",
        "Administrar fundos exige precificação diária, dados de referência e cadastro de ativos: "
        "é a ponte com dados corporativos (Data License, BVAL) para Banks and Brokers. "
        "PL do registro sem os fundos com valor implausível.",
        "",
        "| # | Administrador | Centro | Fundos ativos | PL administrado |",
        "|---:|---|---|---:|---:|",
    ]
    for index, row in enumerate(admins, start=1):
        lines.append(
            f"| {index} | {row['legal_name']} | {row['centre'] or '—'} | "
            f"{integer(int(row['funds_administered']))} | {brl(_float(row['nav_administered_brl']))} |"
        )

    radar = sorted(
        (r for r in rows if r["coverage_tier"] == "radar"),
        key=lambda r: r["registration_date"] or "",
        reverse=True,
    )
    radar_centres = Counter(r["centre"] or "—" for r in radar)
    lines += [
        "",
        f"## Radar: {integer(len(radar))} gestoras registradas nos últimos {RADAR_DAYS // 365} anos",
        "",
        "Por centro: "
        + "; ".join(f"{c} {integer(n)}" for c, n in radar_centres.most_common())
        + ".",
        "",
        "| Registro CVM | Gestora | Centro | Classes ativas |",
        "|---|---|---|---:|",
    ]
    for row in [r for r in radar if r["centre"] in MAPPED_CENTRES][:30]:
        lines.append(
            f"| {br_date(row['registration_date'])} | {row['legal_name']} | {row['centre']} | "
            f"{integer(int(row['active_classes']))} |"
        )

    lines += [
        "",
        "## Séries de fundos",
        "",
        f"- Janela do Informe Diário: {period_label(window['months'][0])} a "
        f"{period_label(window['months'][-1])} ({len(window['months'])} arquivos mensais).",
        f"- Mensal: {integer(counts['monthly_series'])} séries (classe/subclasse) abertas, não "
        f"exclusivas e não FIC, {integer(counts['monthly_rows'])} linhas.",
        f"- Diária: {integer(counts['daily_series_curated'])} séries das contas curadas com PL ≥ "
        f"{brl(DAILY_MIN_NAV_BRL, 'mi')} no último informe e informe nos últimos "
        f"{DAILY_RECENT_DAYS} dias, {integer(counts['daily_rows_curated'])} linhas. Com o cache "
        "bruto, o pipeline gera a diária de qualquer classe.",
        f"- Por gestora: {integer(counts['manager_month_rows'])} linhas (gestora, mês).",
        f"- Composição (CDA): {integer(counts['holdings_rows'])} linhas; Perfil Mensal: "
        f"{integer(counts['profile_rows'])}; Lâmina: {integer(counts['lamina_rows'])} (só fundos com lâmina).",
        f"- Histórico de gestores (cad_fi_hist): {integer(counts['manager_events'])} eventos desde "
        f"{br_date(window['start'])}.",
        "",
        "Arquivos anteriores à adaptação à RCVM 175 informam por fundo; a classe única de um "
        "fundo adaptado mantém o CNPJ do fundo, e é assim que as séries se emendam.",
        "",
        "## Qualidade e revisão",
        "",
        f"- Sugestões de grupo por marca pendentes de revisão: {integer(counts['group_suggestions_pending'])} "
        "(`data/review/group_suggestions.csv`; nunca aplicadas automaticamente).",
        f"- CNPJs curados ausentes dos cadastros: {integer(counts['curated_gaps'])}.",
        f"- Fundos com PL implausível no registro (excluídos das somas): "
        f"{integer(len(quality['anomalies']['registry_fund_nav_above_cap']))}; séries diárias "
        f"acima do limite: {integer(len(quality['anomalies']['daily_nav_above_cap']))}.",
        f"- Entidades com coordenada: {integer(counts['entities_geocoded'])}; prédios por "
        "precisão: "
        + ", ".join(f"{k} {integer(v)}" for k, v in counts["buildings_by_precision"].items())
        + ".",
        f"- Snapshot versionado: {quality['snapshot_total_bytes'] / 1e6:,.1f} MB.".replace(
            ".", ",", 1
        ),
        "",
    ]
    return "\n".join(lines)


def wave2_markdown(data: dict[str, Any]) -> str:
    entities = {r["cnpj"]: r for r in data["entities"].to_dicts()}
    curated = [r for r in data["curated"].to_dicts() if r["wave"] == "wave2"]
    members: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in data["curated_entities"].to_dicts():
        members[row["account_key"]].append(row)
    monthly: pl.DataFrame = data["manager_monthly"]
    latest_month = monthly["month"].max()
    nav = dict(
        monthly.filter(pl.col("month") == latest_month)
        .select("manager_cnpj", "nav_end_brl")
        .iter_rows()
    )
    assets, assets_period = _bank_assets(data)
    lines = [
        "# Onda 2 de contas curadas",
        "",
        "Proposta em `prompts_codex.md` (seção 5) e registrada em "
        "`data/reference/curated_wave2.yaml`. Cada CNPJ foi conferido nos cadastros da CVM; "
        "**todos os vínculos estão pendentes de revisão humana**. Números gerados do snapshot "
        "do universo.",
        "",
        "Critérios: presença nos centros financeiros (prioridade Faria Lima), relevância por PL e "
        "número de fundos abertos, diversidade de estratégia e de tipo de instituição, presença na "
        "planilha de networking e evidência pública disponível.",
        "",
        "| Conta | Lado | Segmento | Centro | PL gestão (Informe Diário) | Classes ativas / abertas | Fundos administrados | Ativo do conglomerado (IF.data) |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for account in curated:
        rows = [
            entities[m["cnpj"]] for m in members[account["account_key"]] if m["cnpj"] in entities
        ]
        centres = Counter(r["centre"] or "—" for r in rows)
        account_nav = sum(nav.get(r["cnpj"]) or 0.0 for r in rows) or None
        active = sum(int(r["active_classes"] or 0) for r in rows)
        selected = sum(int(r["selected_classes"] or 0) for r in rows)
        administered = sum(int(r["funds_administered"] or 0) for r in rows)
        conglomerates = {r["ifdata_conglomerate"] for r in rows if r["ifdata_conglomerate"]}
        bank_assets = [assets[c] for c in conglomerates if c in assets]
        lines.append(
            f"| {account['display_name']} | {'buy side' if account['side'] == 'buy_side' else 'sell side'} | "
            f"{account['segment']} | {centres.most_common(1)[0][0]} | {brl(account_nav)} | "
            f"{integer(active)} / {integer(selected)} | {integer(administered)} | "
            f"{brl(max(bank_assets)) if bank_assets else '—'} |"
        )
    lines += [
        "",
        f"PL de gestão: classes não FIC no Informe Diário de {br_date(latest_month)}. Ativo do "
        f"conglomerado: IF.data {period_label(assets_period)}.",
        "",
        "## Entidades e evidência",
        "",
    ]
    for account in curated:
        lines += [f"### {account['display_name']}", "", account["rationale"], ""]
        for member in members[account["account_key"]]:
            row = entities.get(member["cnpj"], {})
            lines.append(
                f"- `{format_cnpj(member['cnpj'])}` {row.get('legal_name', '—')} — "
                f"{member['relation']}; {row.get('centre') or '—'}; {member['relation_evidence']}"
            )
        lines.append("")
    lines += [
        "## Alternativas se alguma conta não passar na revisão",
        "",
        "Atmos, Squadra, Kadima, AZ Quest, Perfin, Augme, Genial Institucional (Faria Lima 3400), "
        "ABC Brasil, Daycoval.",
        "",
    ]
    return "\n".join(lines)


SOURCE_NOTES: dict[str, tuple[str, str, str, str]] = {
    # source_id: (frequência, defasagem típica, campos usados, uso)
    "cvm_cad_adm_cart": (
        "diária",
        "1 dia",
        "CNPJ, razão social, categoria, endereço, telefone, site, data de registro, diretores de gestão",
        "universo buy side, radar, contas",
    ),
    "cvm_cad_intermed": (
        "diária",
        "1 dia",
        "CNPJ, tipo de participante, endereço, controle acionário",
        "universo sell side",
    ),
    "cvm_registro_fundo_classe": (
        "diária",
        "1 dia",
        "gestor, administrador, custodiante, classe, condomínio, exclusividade, FIC, PL do registro",
        "classes, administradores",
    ),
    "cvm_cad_fi_hist": (
        "diária",
        "1 dia",
        "mandatos de gestor por fundo (início e fim)",
        "eventos de transferência",
    ),
    "cvm_inf_diario": (
        "diária, arquivo mensal",
        "1 a 2 dias úteis",
        "cota, PL, captação, resgate, cotistas",
        "séries diária e mensal, gestoras",
    ),
    "cvm_cda": (
        "mensal",
        "1 a 2 meses (posições confidenciais até 90 dias)",
        "posição por ativo e PL",
        "composição da carteira",
    ),
    "cvm_perfil_mensal": (
        "mensal",
        "1 mês",
        "cotistas por tipo, VaR, estresse, nocional de derivativos, liquidez",
        "perfil do fundo",
    ),
    "cvm_lamina": (
        "mensal",
        "1 mês",
        "taxas, limites, risco, benchmark",
        "lâmina (fundos de varejo)",
    ),
    "bcb_ifdata_cadastro": (
        "trimestral",
        "3 a 4 meses",
        "instituição, conglomerado prudencial, segmento, sede",
        "grupos de bancos e sell side",
    ),
    "bcb_ifdata_valores": (
        "trimestral",
        "3 a 4 meses",
        "resumo (ativo, TVM, crédito, captações, PL, lucro) e DRE selecionada",
        "porte e mix dos bancos",
    ),
    "bcb_sgs": (
        "diária (CDI, PTAX), mensal (IPCA)",
        "1 dia",
        "CDI (12), IPCA (433), PTAX venda (1)",
        "benchmarks",
    ),
    "osm_nominatim": ("sob demanda", "—", "coordenada e tipo do resultado", "mapa por prédio"),
}


def data_sources_markdown(data: dict[str, Any]) -> str:
    quality = data["quality"]
    status = {s["source_id"]: s for s in quality["sources"]}
    lines = [
        "# Catálogo de fontes",
        "",
        f"Status verificado na execução de {br_date(quality['run_at'])} do pipeline do universo. "
        "Todas as fontes são públicas; o conteúdo bruto fica em `data/raw/` (fora do git), "
        "imutável e endereçado por SHA-256, com manifesto.",
        "",
        "| Fonte | Publicador | Licença / termos | Frequência | Defasagem | Campos usados | Uso | Status | Dados até |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for source_id, (frequency, lag, fields, use) in SOURCE_NOTES.items():
        spec = SOURCES[source_id]
        state = status.get(source_id, {})
        lines.append(
            f"| [{spec.title}]({spec.base_url}) | {spec.publisher} | {spec.licence} | {frequency} | "
            f"{lag} | {fields} | {use} | {state.get('status', 'não executada')} | "
            f"{period_label(state['data_as_of']) if state.get('data_as_of') and len(str(state['data_as_of'])) == 6 else br_date(state.get('data_as_of'))} |"
        )
    lines += [
        "",
        "## Observações da última execução",
        "",
    ]
    for source in quality["sources"]:
        if source.get("note"):
            lines.append(f"- `{source['source_id']}`: {source['note']}")
    lines += [
        "",
        "## Fontes avaliadas e não usadas",
        "",
        "| Fonte | Motivo |",
        "|---|---|",
        "| BCB SGS 7 (Ibovespa) | Série encerrada em 2019; ações são comparadas com a mediana dos pares. |",
        "| API pública de vagas da Gupy | Respondeu HTTP 404 em 30/10/2026; vagas entram só por curadoria manual com URL e data. |",
        "| ANBIMA (sandbox) | Dados fictícios: bloqueados no cache e no fetcher. |",
        "| LinkedIn autenticado | Vedado (termos de uso e LGPD). |",
        "| CVM FRE (companhias abertas) | Disponível; headcount dos bancos listados fica como extensão opcional. |",
        "",
        f"Regra de plausibilidade: fundo com PL acima de R$ 300 bi no registro é anomalia "
        f"(hoje {len(quality['anomalies']['registry_fund_nav_above_cap'])} fundos, cada um com "
        "cerca de R$ 16,7 trilhões, data de PL 14/08/2025) e não entra em somas.",
        "",
    ]
    return "\n".join(lines)


def write_reports(root: Path) -> None:
    data = _load(root)
    (root / "docs/universe.md").write_text(universe_markdown(data), encoding="utf-8")
    (root / "docs/curated_wave2.md").write_text(wave2_markdown(data), encoding="utf-8")
    (root / "docs/data_sources.md").write_text(data_sources_markdown(data), encoding="utf-8")
