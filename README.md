# Prospecção de contas: sales intelligence explicável

MVP que prioriza 12 contas-piloto (gestoras, family office e mesas de dois bancos) para o time de vendas, separando **fit**, **timing** e **confiança dos dados**, com fonte e data para cada número. Não é previsão de compra.

## Demo em um comando

Pré-requisitos: Python 3.11, Node.js 20+ e um PostgreSQL 16 com PostGIS acessível (Docker ou o pacote portátil descrito abaixo).

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements\dev.lock
Copy-Item .env.example .env        # ajuste DATABASE_URL e a senha
.\.venv\Scripts\python.exe scripts\demo.py
```

Abra http://127.0.0.1:4173. O comando cria o banco se faltar, migra, faz o seed determinístico das 12 contas a partir dos arquivos versionados (sem rede), compila o dashboard e sobe API e dashboard em **modo DEMO** (selo no topo; base congelada de 27/10/2026). `--check` verifica todas as camadas e encerra; `--database-url` aponta para outro banco.

Sem internet tudo funciona; só o mapa perde o fundo (os escritórios continuam posicionados, com aviso).

### Banco de dados

Com Docker:

```powershell
docker compose up --build -d db migrate
```

Sem Docker nem administrador (Windows): PostgreSQL 16 portátil (binários da EnterpriseDB) + bundle PostGIS (OSGeo) extraídos em `C:\Users\Lucas\tools\pgsql16`, cluster em `C:\Users\Lucas\tools\pgdata16`, porta 5433, só localhost:

```powershell
C:\Users\Lucas\tools\pgsql16\pgsql\bin\pg_ctl.exe -D C:\Users\Lucas\tools\pgdata16 -l C:\Users\Lucas\tools\pgdata16\server.log start
```

## Documentação

| Documento                                                                                                            | Conteúdo                                                                            |
| -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `docs/demo_script.md`                                                                                              | Roteiro de 90 s e de 5 min, plano B e perguntas prováveis                           |
| `docs/architecture.md`                                                                                             | Diagrama e decisões de trade-off                                                    |
| `docs/delivery_report.md`                                                                                          | O que foi validado tecnicamente, o que falta validar economicamente e comercialmente |
| `docs/pilot_metrics.md`                                                                                            | Métricas do piloto (definições, sem resultados inventados)                        |
| `docs/validation_report.md`                                                                                        | Validação independente por amostragem (gerada por script)                          |
| `docs/security_review.md`                                                                                          | Segurança, dependências, logs e LGPD                                               |
| `docs/data_audit.md`, `docs/enrichment_quality_report.md`, `docs/opportunity_model_report.md`, `docs/api.md` | Relatórios dos prompts 1, 3, 4 e 5                                                  |

## Pipeline completo (atualizar os dados)

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m networking_intel.etl.cli               # 12 contas da planilha tratada
.\.venv\Scripts\python.exe -m networking_intel.enrichment.cli        # CVM, BCB, Nominatim (online, com cache)
.\.venv\Scripts\python.exe -m networking_intel.scoring.cli           # fit, timing, confiança
.\.venv\Scripts\python.exe -m networking_intel.etl.load_enriched     # carga idempotente no banco
.\.venv\Scripts\uvicorn.exe networking_intel.api.app:create_app --factory --port 8000 --no-server-header
```

- Enriquecimento: `--offline` usa só o cache bruto `data/raw/` (fora do git); `--skip-geocode` pula o Nominatim.
- Revisão humana: `data/review/conflicts.csv` e `data/reference/identity_registry.yaml`.
- Modelo: pesos e premissas em `config/scoring/opportunity_v1.yaml` (mude `model_version` a cada alteração); sinais curados com fonte em `data/reference/commercial_signals.csv`.
- API: OpenAPI em http://localhost:8000/docs; `/health`, `/ready`, `/metrics`.

Dashboard em modo desenvolvimento (API em `:8000`):

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173; teclas 1–5 trocam de tela, / busca
```

## Testes e validação

```powershell
.\.venv\Scripts\ruff.exe check src scripts tests migrations
.\.venv\Scripts\mypy.exe src scripts tests
$env:TEST_DATABASE_URL = (Select-String -Path .env -Pattern '^TEST_DATABASE_URL=(.*)').Matches.Groups[1].Value
.\.venv\Scripts\python.exe -m pytest -q                      # unitários + integração com PostGIS
.\.venv\Scripts\python.exe scripts\validate_sample.py        # validação independente (API em :8000)

cd frontend
npm run lint; npm run typecheck; npm test                   # oxlint, tsc, Vitest
npm run test:e2e                                             # Playwright 1366×768 e 1440×900, axe, offline
```
