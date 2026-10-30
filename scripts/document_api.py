"""Generate docs/api.md from the live database: endpoint examples and query plans.

Examples are real responses (truncated), so they always match the loaded data.
Usage: PYTHONPATH=src python scripts/document_api.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from networking_intel.api.app import create_app
from networking_intel.config import Settings, get_settings

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES: tuple[tuple[str, str, dict[str, Any]], ...] = (
    ("Metadados e convenções", "/api/v1/meta", {}),
    ("Busca canônica", "/api/v1/search", {"q": "kapitalo"}),
    ("Contas (ranking por prioridade)", "/api/v1/accounts", {"page_size": 2}),
    ("Ranking explicável", "/api/v1/scores", {"page_size": 2}),
    ("Explicação de uma unidade", "/api/v1/scores/org-verde-asset/explanation", {}),
    ("Mesas de um banco", "/api/v1/business-units", {"account_id": "org-itau-bba"}),
    (
        "Fundos com métricas",
        "/api/v1/funds",
        {"account_id": "org-verde-asset", "with_metrics": "true", "page_size": 1},
    ),
    ("Mapa (GeoJSON)", "/api/v1/map/offices", {"bbox": "-46.75,-23.65,-46.6,-23.5"}),
    ("Densidade (heatmap)", "/api/v1/map/density", {"cell_m": 2000}),
    ("Sinais de timing", "/api/v1/signals", {"account_id": "org-kinea", "page_size": 2}),
    ("Qualidade de dados", "/api/v1/data-quality", {}),
    ("Fila de conflitos", "/api/v1/data-quality/conflicts", {"page_size": 2}),
)
PLANS = (
    (
        "Mapa: escritórios no bbox (GiST)",
        "SELECT office_key FROM offices WHERE location IS NOT NULL "
        "AND location && ST_MakeEnvelope(-46.8,-23.7,-46.5,-23.4,4326)",
    ),
    (
        "Ranking: última rodada ordenada por rank",
        "SELECT unit_key FROM opportunity_scores WHERE score_run_id = "
        "(SELECT id FROM score_runs ORDER BY loaded_at DESC, id LIMIT 1) ORDER BY rank LIMIT 50",
    ),
    (
        "Série diária de uma classe",
        "SELECT observation_date, quota_value FROM fund_observations WHERE fund_id = "
        "(SELECT id FROM funds WHERE cnpj IS NOT NULL ORDER BY cnpj LIMIT 1) AND subclass_id = '' "
        "ORDER BY observation_date",
    ),
    (
        "Fundos ativos de uma conta",
        "SELECT f.cnpj FROM funds f JOIN organizations o ON o.id = f.organization_id "
        "WHERE o.account_id = 'org-verde-asset' AND f.is_active",
    ),
)


def _truncate(value: Any, items: int = 2, depth: int = 0) -> Any:
    if isinstance(value, list):
        head = [_truncate(v, items, depth + 1) for v in value[:items]]
        return head + ([f"… +{len(value) - items} itens"] if len(value) > items else [])
    if isinstance(value, dict):
        return {k: _truncate(v, items, depth + 1) for k, v in value.items()}
    if isinstance(value, str) and len(value) > 160:
        return value[:157] + "…"
    return value


def main() -> int:
    base = get_settings()
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        database_url=base.database_url,
        api_trusted_hosts="testserver",
        log_level="WARNING",
    )
    lines = [
        "# API — referência gerada a partir do banco",
        "",
        "Gerado por `scripts/document_api.py` contra o banco carregado; os exemplos são "
        "respostas reais truncadas. OpenAPI interativo em `/docs` (ambientes não produtivos).",
        "",
        "## Como subir",
        "",
        "```powershell",
        "$env:PYTHONPATH='src'",
        ".\\.venv\\Scripts\\uvicorn.exe networking_intel.api.app:create_app --factory --port 8000",
        "```",
        "",
        "## Convenções",
        "",
        "- Somente leitura (`SET TRANSACTION READ ONLY`), timeout de consulta e de conexão.",
        "- Erros `application/problem+json` (RFC 7807) com `request_id`; entrada inválida nunca é ecoada.",
        "- `X-Request-ID` aceito (8-64 caracteres seguros) ou gerado; logs JSON sem query string nem IP.",
        "- `ETag` + `Cache-Control: no-cache`: o cliente sempre revalida, então nova carga aparece na hora.",
        "- Rate limit local por cliente (padrão 600/min) com `Retry-After`; `/health`, `/ready`, `/metrics` isentos.",
        "- CORS restrito às origens configuradas e ao método GET; hosts confiáveis explícitos.",
        "",
    ]
    with TestClient(create_app(settings)) as client:
        lines += ["## Endpoints e exemplos reais", ""]
        for title, path, params in EXAMPLES:
            response = client.get(path, params=params)
            query = "&".join(f"{k}={v}" for k, v in params.items())
            lines += [
                f"### {title}",
                "",
                f"`GET {path}{'?' + query if query else ''}` → {response.status_code}",
                "",
                "```json",
                json.dumps(_truncate(response.json()), ensure_ascii=False, indent=2, default=str),
                "```",
                "",
            ]
    engine = create_engine(base.database_url)
    lines += [
        "## Planos de consulta (EXPLAIN ANALYZE no banco carregado)",
        "",
        "Com poucas linhas o PostgreSQL pode preferir varredura sequencial; os testes de "
        "integração confirmam com `enable_seqscan=off` que cada consulta consegue usar seu índice.",
        "",
    ]
    with engine.connect() as connection:
        for title, sql in PLANS:
            plan = (
                connection.execute(text("EXPLAIN (ANALYZE, BUFFERS, COSTS OFF) " + sql))
                .scalars()
                .all()
            )
            lines += [f"### {title}", "", "```sql", sql, "```", "", "```text", *plan, "```", ""]
    engine.dispose()
    (ROOT / "docs/api.md").write_text("\n".join(lines), encoding="utf-8")
    print("docs/api.md written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
