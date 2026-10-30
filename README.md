# Prospecção de contas: sales intelligence explicável

## Como abrir o app (passo a passo)

1. Abra o **PowerShell** e entre na pasta do projeto:

   ```powershell
   cd C:\Users\Lucas\Desktop\Estagio_Bloomberg
   ```

2. Suba o app com um único comando (ele liga o banco sozinho se estiver desligado):

   ```powershell
   .\.venv\Scripts\python.exe scripts\demo.py
   ```

3. Espere aparecer a linha **`[demo] pronto: abra http://127.0.0.1:4173`** (cerca de 2 minutos).
4. Abra no navegador: **http://127.0.0.1:4173**
5. **Deixe a janela do PowerShell aberta** enquanto usa o app. Para encerrar, volte a ela e aperte `Ctrl+C`.

Deu erro? Veja a tabela [Se algo der errado](#se-algo-der-errado) logo abaixo.

---

Ferramenta para o time de vendas da Bloomberg no Brasil decidir **quem visitar, em qual área e com qual conversa**. Ela separa **fit** (o workflow depende de dados?), **timing** (há uma mudança recente que abre conversa?) e **confiança** (quanto disso tem fonte recente), com fonte e data em cada número. Não é previsão de compra.

> **Novo no projeto? Leia o [GUIA.md](GUIA.md)**: o que é, como funciona, critérios, pontuação, fontes, bibliotecas, números para citar e roteiro para os avaliadores.

O que tem dentro:

- **Contas curadas e pontuadas** (telas 1 a 5): 12 contas-piloto (gestoras, family office e mesas de BTG e Itaú BBA) com score explicável, mais 24 contas da onda 2 mapeadas por CNPJ, pendentes de revisão humana.
- **Universo SP/RJ** (tela 6): 1.447 gestoras, bancos, corretoras e administradores ativos na CVM em São Paulo, Rio de Janeiro e Osasco, com grupo econômico, centro financeiro, PL e captação mês a mês de 36 meses.

---

## Detalhes da execução

O `demo.py` carrega o banco a partir dos arquivos versionados (sem internet), compila o dashboard e sobe a API (porta 8000) e o dashboard (porta 4173). O selo **DEMO** no topo indica a base congelada (dados públicos de outubro/2026).

### Se algo der errado

| Mensagem | O que fazer |
|---|---|
| `porta(s) 8000, 4173 já em uso` | Já existe um app aberto. Feche a outra janela do PowerShell (`Ctrl+C`) ou rode `.\.venv\Scripts\python.exe scripts\demo.py --api-port 8010 --web-port 4180` e abra http://127.0.0.1:4180 |
| `não foi possível conectar em localhost:5433` | O banco não ligou sozinho. Confira com `C:\Users\Lucas\tools\pgsql16\pgsql\bin\pg_ctl.exe -D C:\Users\Lucas\tools\pgdata16 status`; se estiver parado, troque `status` por `start` |
| `password authentication failed` | O `.env` foi trocado. **Nunca** copie o `.env.example` por cima do `.env` desta máquina; ele guarda a senha local |
| `npm não encontrado` | Instale o Node.js 20+ e abra um PowerShell novo |
| A página abre mas o mapa fica sem fundo | Sem internet o mapa perde só o fundo; os pontos continuam |

Para verificar tudo sem abrir o navegador: `.\.venv\Scripts\python.exe scripts\demo.py --check` (sobe, testa cada camada e encerra).

### Primeira instalação em outra máquina

Pré-requisitos: Python 3.11, Node.js 20+ e PostgreSQL 16 com PostGIS (portátil ou `docker compose up --build -d db migrate`).

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements\dev.lock
if (-not (Test-Path .env)) { Copy-Item .env.example .env }   # depois ajuste porta e senha do banco no .env
.\.venv\Scripts\python.exe scripts\demo.py
```

---

## Como navegar

| Tecla | Tela | Para quê |
|---|---|---|
| `1` | **Prioridade** | Ranking das 22 unidades pontuadas (bancos por mesa). O ponto é o observado; a faixa cinza é o quanto pode mudar com o que falta |
| `2` | **Mapa** | Escritórios do piloto. Ponto cheio = endereço exato; anel = aproximado |
| `3` | **Comparador** | Até 5 unidades lado a lado |
| `4` | **Qualidade dos dados** | Atualização das fontes e fila de revisão humana |
| `5` | **Conta 360** | Preparação de reunião: fatores, fundos, contatos institucionais, workflows hipotéticos |
| `6` | **Universo SP/RJ** | Território completo com filtros (buy/sell side, curada/radar/universo, tipo, centro). Clique numa linha para ver PL e captação mês a mês, maiores fundos e fonte |
| `/` | **Busca** | Conta, alias ou CNPJ |

Roteiros de 90 segundos e de 5 minutos: [docs/demo_script.md](docs/demo_script.md).

---

## Como funciona, em uma página

1. **Dados públicos** (CVM, Banco Central, OpenStreetMap) são baixados com cache imutável em `data/raw/` (fora do git).
2. **Pipelines em Python** cruzam tudo por **CNPJ exato**; nome parecido só vira sugestão para revisão. O resultado vai para `data/enriched/`, `data/scored/` e `data/universe/`, que são versionados e alimentam a demo offline.
3. **PostgreSQL + PostGIS** guarda os dados com proveniência; a **API FastAPI** é somente leitura.
4. O **dashboard em React** mostra tudo, sempre com fonte e data.

Detalhes, critérios e pesos: [GUIA.md](GUIA.md).

## Documentação

| Documento | Conteúdo |
|---|---|
| [GUIA.md](GUIA.md) | **Comece aqui**: projeto, critérios, pontuação, fontes, bibliotecas, perguntas prováveis |
| [docs/demo_script.md](docs/demo_script.md) | Roteiro da apresentação e plano B |
| [docs/universe.md](docs/universe.md) | Universo SP/RJ: centros, maiores grupos, sell side, administradores, radar |
| [docs/curated_wave2.md](docs/curated_wave2.md) | As 24 contas da onda 2, com CNPJs e evidência |
| [docs/data_sources.md](docs/data_sources.md) | Catálogo de fontes com status verificado |
| [docs/delivery_report.md](docs/delivery_report.md) | O que foi validado e o que falta |
| [docs/architecture.md](docs/architecture.md) | Arquitetura e decisões |
| [docs/opportunity_model_report.md](docs/opportunity_model_report.md) | Modelo de pontuação, sensibilidade e limitações |
| [docs/validation_report.md](docs/validation_report.md) | Validação independente por amostragem |
| [docs/security_review.md](docs/security_review.md) | Segurança e LGPD |
| [prompts_codex.md](prompts_codex.md) | Revisão crítica e plano dos próximos passos |

---

## Para desenvolvedores

### Atualizar os dados (online, com cache)

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m networking_intel.etl.cli               # 12 contas da planilha tratada
.\.venv\Scripts\python.exe -m networking_intel.enrichment.cli        # CVM, BCB, Nominatim
.\.venv\Scripts\python.exe -m networking_intel.scoring.cli           # fit, timing, confiança
.\.venv\Scripts\python.exe -m networking_intel.etl.load_enriched     # carga no banco
.\.venv\Scripts\python.exe -m networking_intel.universe.cli          # universo SP/RJ (~1 min com cache)
.\.venv\Scripts\python.exe -m networking_intel.etl.load_universe     # carga do universo
```

`--offline` usa só o cache bruto; `--skip-geocode` pula o Nominatim.

### Modo desenvolvimento

```powershell
$env:PYTHONPATH='src'; .\.venv\Scripts\uvicorn.exe networking_intel.api.app:create_app --factory --port 8000
cd frontend; npm run dev        # http://localhost:5173 (em outro PowerShell)
```

API documentada em http://localhost:8000/docs.

### Testes

```powershell
.\.venv\Scripts\ruff.exe check src scripts tests migrations
.\.venv\Scripts\mypy.exe src scripts tests
$env:TEST_DATABASE_URL = (Select-String -Path .env -Pattern '^TEST_DATABASE_URL=(.*)').Matches.Groups[1].Value
.\.venv\Scripts\python.exe -m pytest -q          # 128 testes, inclui integração com PostGIS
cd frontend; npm run lint; npm run typecheck; npm test; npm run test:e2e
```
