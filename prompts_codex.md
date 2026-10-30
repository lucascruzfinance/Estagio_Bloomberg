# Bloomberg Sales Intelligence — revisão crítica (v2) e 4 prompts finais

Data de referência: 30/10/2026
Workspace: `C:\Users\Lucas\Desktop\Estagio_Bloomberg`
Versão anterior deste arquivo (7 prompts, todos executados): histórico do git, commit `7e87630`.

Este arquivo tem duas partes. As seções 1 a 8 são a análise: o objetivo, o que foi construído, o que está fraco, o que foi verificado como possível e as decisões para a versão final. A seção 9 traz os **4 prompts** (numerados 8 a 11, continuando os 7 anteriores) que levam o projeto ao estado final. Execute um prompt por vez e só avance quando os critérios de aceite passarem.

---

## 1. Objetivo e para quem

Apresentação de estágio para o time de vendas da Bloomberg no Brasil. O produto responde a uma pergunta comercial: **quais instituições (e, nos bancos, quais áreas) têm mais chance de precisar de um Terminal ou de dados Bloomberg agora, por quê, e como abordar**, com fonte para cada número.

A proposta defensável continua a mesma da v1: **priorização comercial explicável**, não previsão de compra. Três leituras separadas: *fit* (o workflow depende de dados?), *timing* (há mudança recente que abre conversa?) e *confiança* (quanto disso está apoiado em fonte recente). Sem dados de conversão do CRM, qualquer "probabilidade de compra" seria inventada.

### O que cada avaliador vai procurar

| Avaliador | Experiência | Pergunta que o produto precisa responder na frente dele |
|---|---|---|
| **Leandro Pena** — Sales Team Leader, Brazil Buy-Side | Electronic Trading Solutions (México e América Central), RM/AM Sell-Side (Argentina e Uruguai), Financial Product Analytics & Sales | "Quais gestoras da Faria Lima eu visito este mês, com qual conversa? Quem acabou de abrir, quem está captando, quem lançou fundos, que estratégia exige quais dados e ferramentas de execução?" |
| **Yasmin La Manna** — Sales Team Leader, Banks and Brokers | Enterprise Data Sales LatAm (real time, static, pricing, APIs); RM/AM Banks and Brokers (tesouraria, TI, sales, ALM, brokerage, crédito, risco, research); Financial Products Analytics | "Em quais bancos, corretoras e administradores há um problema de dados (tempo real, referência, precificação, API, risco) e em qual área? Qual produto e qual evidência?" |

Para os dois, o diferencial não é a quantidade de logos: é **reduzir o tempo de preparação de uma conta**, mostrar evidência verificável e ser honesto sobre o que é hipótese.

---

## 2. O que foi construído (prompts 1 a 7)

| Camada | Estado em 30/10/2026 |
|---|---|
| Base de origem | Planilha `Networking_estagio_v2.xlsx` auditada (30 abas; 211 instituições na base consolidada). Piloto de **12 contas**: SPX, Verde, Kapitalo, Ibiuna, Kinea, Pátria, Vinci, Constellation, Jive, Portofino, BTG Pactual e Itaú BBA. |
| Enriquecimento | CVM (cadastro de administradores de carteira, registro de fundos/classes, Informe Diário), Nominatim (geocodificação com cache), BCB IF.data registrado como indisponível (HTTP 500 na coleta). Cache bruto imutável com SHA-256; vínculo por CNPJ exato; 48 entidades legais; 6.385 classes no registro; série diária de **3.529 classes** (917 mil linhas, 01/10/2025 a 28/10/2026); métricas 1m/3m/6m/YTD/12m, volatilidade, drawdown e captação 12m. |
| Modelo | `opportunity-v1.0.0`: fit, timing e confiança; faixas para dado ausente; bancos pontuados por mesa (22 unidades = 10 gestoras + 12 mesas); sensibilidade (Spearman 0,95 em 1.000 sorteios); sanidade 3/4; trava de calibração (≥ 50 resultados, ≥ 10 positivos). |
| Backend | PostgreSQL 16 + PostGIS portátil, Alembic, FastAPI somente leitura com problemas RFC 7807, ETag, rate limit, CSP, logs estruturados sem variáveis locais, `/health`, `/ready`, `/metrics`. |
| Frontend | React 19 + Vite + TypeScript, ECharts, MapLibre; 5 telas (Ranking, Conta 360, Mapa, Comparador, Qualidade); selo DEMO; atalhos de teclado. |
| QA | pytest 118, Vitest 25, Playwright 26 em dev e 26 em produção (com axe), validação independente 8/8 blocos, instalação do zero aprovada, seed determinístico (`34f15cd40d894faa`). |
| Demo | `python scripts/demo.py` sobe tudo offline a partir de arquivos versionados. |

A base técnica é boa: proveniência, determinismo, testes e honestidade metodológica estão acima do esperado para um MVP. O problema da v1 é **escopo e profundidade analítica**, não qualidade de engenharia.

---

## 3. Diagnóstico crítico

### 3.1 Produto e cobertura

| Problema | Evidência | Consequência |
|---|---|---|
| Universo pequeno demais para um território de vendas | 12 contas e 22 unidades; a CVM tem **1.494 gestores ativos**, 1.059 em SP e 224 no RJ; 850 entidades (573 grupos) nos centros financeiros mapeados | Um líder de vendas vê "uma lista de 22", não o território. A pergunta "quem mais eu deveria visitar?" fica sem resposta. |
| Sell side quase ausente | Só BTG e Itaú BBA, com as mesas pontuadas por **premissa** | A avaliadora de Banks and Brokers vê hipóteses, não evidência. Ficaram de fora corretoras (57 ativas na CVM), distribuidoras (104), bancos com carteira de investimento (78), bancos de investimento (13), custodiantes (156) e administradores fiduciários (129). |
| Nenhum radar de novas casas | **119 gestoras** registradas na CVM nos últimos 24 meses estão nos centros financeiros de SP/RJ (ex.: Amoreiras Capital, Ártico Capital, Algarve Infra na Faria Lima) | É o sinal mais acionável para Buy-Side: casa nova monta mesa e contrata ferramentas. Hoje não aparece. |
| Nenhuma visão "quem é cliente / onde expandir" | Não existe campo de status comercial | Não dá para separar *new logo* de expansão de assentos; a calibração nunca começa. |

### 3.2 Dados

| Problema | Evidência | Correção |
|---|---|---|
| IF.data tratado como fora do ar | Em 30/10/2026 `IfDataCadastro` respondeu 200 para 202606, 202603, 202512 e 202509 (≈ 2,3 MB cada) e `IfDataValores` também (testado com 202503). O trimestre 202609 responde **200 com lista vazia**: o código atual (`try_ifdata`) aceitaria esse período como "ok" sem dados | Tratar resposta vazia como período indisponível e recuar; buscar valores (ativo total, TVM, carteira de crédito, captações, PL, resultado) por conglomerado prudencial. |
| Série curta | Informe Diário só desde 01/10/2025 (13 meses) | Sem ano a ano, sem mês a mês de 3 anos, sem rolling 12m. Ampliar para 36 meses (≈ 11,6 MB por mês zipado; cache fora do git). |
| Sem composição de carteira nem perfil | CDA, Perfil Mensal e Lâmina não são lidos (disponíveis até 09/2026) | "Intensidade de dados" é inferida do nome da classificação. A CDA mostra derivativos, ativos no exterior, crédito privado e número de ativos: medida direta de necessidade de dados e precificação. |
| Sem benchmark | Retorno sem CDI; a série SGS 7 (Ibovespa) parou em 2019 | CDI (SGS 12), IPCA (433), PTAX (1) funcionam. Para ações, usar mediana dos pares ou fonte pública da B3 com termos verificados; proxy só com rótulo. |
| Sem histórico cadastral | `cad_fi_hist` não é lido | Perde-se troca de gestor, transferência de fundos e lançamentos com data: sinais de timing com fonte. |
| Agrupamento econômico frágil fora do piloto | O script de universo agrupa por primeiro token do nome; já foram encontrados falsos positivos (Santander↔H.I.G., Sul América↔Bank of America, Morgan Stanley↔J.P. Morgan) e corrigidos | No produto, grupo econômico precisa de raiz de CNPJ + conglomerado do IF.data + registro curado; heurística de nome só como sugestão na fila de revisão. |
| Anomalias no registro da CVM | 3 fundos com PL de ≈ R$ 16,7 **trilhões** cada (unidade errada no registro) | Regra de plausibilidade (PL de um fundo > R$ 300 bi é excluído e listado), já aplicada em `scripts/expansion_universe.py`. |
| 30% do timing vazio | `data/reference/commercial_signals.csv` sem linhas; vagas: a API pública da Gupy respondeu 404 em 30/10/2026 | Faixas largas em todos os timings. Sinais automáticos da CVM cobrem parte; vagas e notícias entram curadas, com URL, data e trecho curto. |

### 3.3 Modelo

- **BTG Wealth em 1º lugar mede escala de plataforma, não sofisticação** (35 fundos lançados em 12 meses). Lançamentos precisam ser normalizados por porte e excluir feeders, FIC de distribuição e exclusivos.
- **Mesas de banco por premissa**: com IF.data (TVM, derivativos, câmbio, crédito, captação) e o número de fundos administrados, várias mesas passam a ter evidência observada.
- **Performance com peso baixo** está certo e deve continuar assim, mas o produto precisa *mostrar* retorno vs CDI, captação e drawdown para a conversa, mesmo que pese pouco no score.
- **"O que as contas atrativas têm em comum"** só pode ser respondido de forma descritiva (perfis e segmentos), porque não há variável de resultado. É preciso dizer isso na tela e no roteiro.

### 3.4 Análise de fundos (pedido explícito)

Hoje a Conta 360 mostra um gráfico de cota de um fundo. Faltam: captação diária, semanal e mensal; retornos mês a mês (matriz ano × mês) e ano a ano; últimos 5 e 20 dias úteis; % do CDI; drawdown com duração e recuperação; volatilidade e Sharpe; percentil entre pares; PL e cotistas ao longo do tempo; decomposição da variação do PL em captação e rendimento; composição da carteira. No nível da gestora: PL por estratégia, captação mensal de 36 meses, lançamentos e encerramentos, base de cotistas.

### 3.5 Frontend

- Não existe página de **fundo**, de **gestora** (fora das 12 contas), de **universo**, de **sell side**, de **radar** nem de **segmentos**.
- O mapa mostra só os escritórios do piloto. Falta densidade (hexágonos H3), agrupamento **por prédio** ("Faria Lima 3477: 9 contas", uma visita cobre várias) e roteiro de visitas.
- A tabela é própria e não virtualizada: não escala para 1.000+ linhas.
- 7 avisos de Fast Refresh e componentes grandes; sem orçamento de bundle por rota.

### 3.6 Repositório e entrega

- Testes e relatórios nomeados por prompt (`test_prompt3_*.py`, "relatórios dos prompts 1, 3, 4 e 5"): faz sentido para quem construiu, não para quem lê.
- `AGENTS.md` é citado nos prompts antigos e não existe.
- Sem CI; Docker nunca validado nesta máquina.
- O pack do `.git` ocupa ≈ 114 MB, muito acima da soma dos arquivos versionados (o maior é `fund_daily.parquet`, 14 MB): investigar objetos inalcançáveis antes de crescer os dados versionados.
- README bom para subir a demo, mas não explica o que é, por que, critérios, fontes, como navegar e como ler cada tela.
- Mudanças locais não commitadas (README, docs, `scripts/demo.py`) e arquivos novos desta análise.

---

## 4. Fontes verificadas em 30/10/2026

| Fonte | Status | Uso proposto |
|---|---|---|
| CVM `INTERMED/CAD` (`cad_intermed.zip`, 0,3 MB) | 200; 507 intermediários ativos (373 em SP, 58 no RJ) | Universo sell side: bancos, corretoras, distribuidoras, custodiantes, escrituradores |
| CVM `FI/CAD` (`registro_fundo_classe.zip`, `cad_fi_hist.zip` 18,7 MB) | 200; 34.488 fundos ativos; 129 administradores | Administradores fiduciários (BTG 7.081 fundos, Itaú 3.257, BEM/Bradesco 2.609, Intrag 2.360, BNY Mellon 1.778…): demanda de precificação e dados de referência. Histórico: troca de gestor e lançamentos |
| CVM `FI/DOC/INF_DIARIO` (mensal ≈ 11,6 MB; anual em `HIST/`) | 200 | 36 meses de cota, PL, captação, resgate e cotistas |
| CVM `FI/DOC/CDA` (até 202609, ≈ 15,5 MB/mês) | 200 | Composição: derivativos, exterior, crédito privado, número de ativos |
| CVM `FI/DOC/PERFIL_MENSAL` (até 202609, ≈ 14,4 MB/mês) | 200 | Cotistas por tipo, VaR e cenários de estresse informados |
| CVM `FI/DOC/LAMINA` (até 202609) | 200 | Taxas, público-alvo, política de investimento |
| CVM `CIA_ABERTA/DOC/FRE` (2023–2026) | 200 | Headcount e estrutura de bancos listados (opcional) |
| BCB IF.data (Olinda) `IfDataCadastro` e `IfDataValores` | 200 (202509 a 202606); 202609 vazio | Porte e composição do balanço por conglomerado; evidência para mesas |
| BCB SGS 12 (CDI), 433 (IPCA), 1 (PTAX) | 200 | Benchmarks e % do CDI |
| BCB SGS 7 (Ibovespa) | encerrada em 2019 | Não usar |
| Gupy (API pública de vagas) | 404 | Vagas só curadas manualmente, com URL e data |
| LinkedIn autenticado | não usar | Vedado |

---

## 5. Universo de expansão (resultado de `scripts/expansion_universe.py`)

Detalhe em `docs/universe.md` e `data/universe/` (gerados por `python -m networking_intel.universe.cli`).

| Centro | Grupos com fundos ativos | PL somado (registro CVM) |
|---|---:|---:|
| Faria Lima | 148 | R$ 2.631,6 bi |
| Centro (RJ) | 20 | R$ 2.561,3 bi |
| Juscelino Kubitschek / Vila Olímpia | 226 | R$ 1.841,2 bi |
| Paulista | 20 | R$ 1.158,5 bi |
| Leblon / Ipanema (RJ) | 91 | R$ 550,0 bi |
| Botafogo (RJ) | 12 | R$ 459,7 bi |
| Cidade Jardim / Jardins | 28 | R$ 228,5 bi |
| Barra / São Conrado (RJ) | 18 | R$ 82,4 bi |
| Berrini / Chucri Zaidan | 10 | R$ 81,9 bi |

PL do registro inclui FIC e exclusivos (há dupla contagem): serve para ordenar, não para reportar AUM. 86 dos 573 grupos casam com a planilha de networking (todas as 12 contas do piloto estão entre eles).

### Três camadas de cobertura

1. **Universo** (automático, CNPJ exato, sem curadoria): todas as gestoras e intermediários ativos nos centros de SP e RJ, com métricas da CVM e do BCB. Centenas de entidades.
2. **Radar de novas casas** (automático): gestoras registradas nos últimos 24 meses nos centros (119 hoje).
3. **Contas curadas** (identidade revisada por humano, sinais curados, notas da planilha): as 12 do piloto + a **onda 2** abaixo.

### Onda 2 proposta (24 contas, sujeita a aprovação)

Critérios: presença nos centros financeiros (prioridade Faria Lima), relevância pelo PL e número de fundos abertos, diversidade de estratégia (macro, ações, crédito, quant, global, alternativos) e de tipo (gestora independente, braço de banco, global), presença na planilha de networking, e evidência pública disponível.

| Grupo | Local (CVM) | Por quê |
|---|---|---|
| Itaú Asset Management | Faria Lima | Maior gestora do país; multiativo; separa buy side do Itaú BBA já no piloto |
| XP Asset Management | JK / Vila Olímpia | Plataforma multiestratégia com FII, FIDC e ações |
| Santander Asset Management | JK / Vila Olímpia | Braço de banco global |
| Safra Asset | Paulista | Família de fundos grande; banco próprio |
| UBS BB / UBS Asset | Faria Lima | Global com joint venture local |
| BNP Paribas Asset Management Brasil | JK / Vila Olímpia | Global, renda fixa e multimercado |
| Absolute Investimentos | JK / Vila Olímpia | Macro e crédito, PL alto entre independentes |
| Genoa Capital | JK / Vila Olímpia | Macro independente |
| Legacy Capital | Faria Lima | Macro independente |
| Capitânia | Faria Lima | Crédito privado e FII (precificação de crédito) |
| Vinland Capital | JK / Vila Olímpia | Crédito e macro |
| Quadra Capital | JK / Vila Olímpia | Crédito estruturado e FIDC |
| Guepardo Investimentos | Faria Lima | Ações fundamentalista |
| Giant Steps Capital | Faria Lima | Quant (dados em volume, API) |
| Opportunity | Leblon (RJ) | Ações e macro, casa tradicional |
| ARX Investimentos | Leblon (RJ) | Multiestratégia |
| Dynamo | Leblon (RJ) | Ações long only |
| Truxt Investimentos | Leblon (RJ) | Macro |
| Banco Santander (Brasil) | JK | Banco por mesa: tesouraria, S&T, câmbio, research, risco |
| Bradesco BBI / Bradesco CTVM | Osasco / JK | Banco de investimento e corretora |
| Banco Safra | Paulista | Tesouraria e câmbio |
| XP Investimentos CCTVM | Botafogo (RJ) | Corretora: execução, distribuição, research |
| BR Partners | Faria Lima 3732 | Banco de investimento boutique |
| BNY Mellon DTVM | Centro (RJ) | Administrador e custodiante: precificação e dados de referência (Data License, BVAL) |

Alternativas se alguma não passar na revisão: Atmos, Squadra, Kadima, AZ Quest, Perfin, Augme, Genial Institucional (Faria Lima 3400), ABC Brasil, Daycoval.

---

## 6. Decisões para a versão final

1. **Duas profundidades no mesmo produto.** Universo largo e automático com CNPJ exato; contas curadas profundas com revisão humana. Toda tela diz em qual camada a entidade está.
2. **Modelo `opportunity-v2`**: mesmas três saídas; novas variáveis com evidência (CDA, Perfil Mensal, IF.data, histórico cadastral, idade da casa); normalização por porte; mesas de banco com evidência observada onde houver; administradores e corretoras com fit próprio (dados de referência, precificação, execução).
3. **Personas e segmentos descritivos** ("o que as contas atrativas têm em comum") com a ressalva explícita de que descrevem o *score*, não a compra.
4. **Análise de fundo e de gestora no nível que um vendedor de Terminal usa**: retorno vs CDI e pares, captação em várias granularidades, drawdown, mês a mês, ano a ano, últimos dias.
5. **Mapa para planejar visitas**: prédio, hexágono, roteiro.
6. **Status comercial importável** (cliente, ex-cliente, oportunidade aberta, nunca contatado) por CSV, vazio na demo; a calibração só começa com dados reais.
7. **Nada inventado.** Proxies e premissas sempre rotulados; sem dado de cliente fictício.

---

## 7. Skills e bibliotecas

### Instaladas nesta análise (Claude Code e Codex, escopo global)

| Skill | Origem | Uso |
|---|---|---|
| `statistical-analysis`, `data-visualization` | anthropics/knowledge-work-plugins | Estatística descritiva, outliers, testes; escolha e desenho de gráficos |
| `account-tiering`, `account-research`, `expansion-whitespace`, `competitive-intelligence` | anthropics/knowledge-work-plugins | Estrutura de tiering ICP × sinais, pesquisa de conta, whitespace por produto, concorrentes (Refinitiv/LSEG, FactSet, S&P, Quantum, Economatica) |
| `kpi-dashboard-design` | wshobson/agents | Hierarquia de KPIs e layout de painéis |
| `vercel-react-best-practices`, `web-design-guidelines` | vercel-labs/agent-skills | Desempenho React e revisão de interface |

Já disponíveis e relevantes: `frontend-design`, `frontend-design-excellence`, `backend-production-excellence`, `data-ml-excellence`, `senior-finance-analyst`, `risk-metrics-calculation`, `data-quality-frameworks`, `data-storytelling`, `postgresql-table-design`, `sql-optimization-patterns`, `fastapi-templates`, `security-best-practices`, `cybersecurity-defensive-review`, `general-code-review`, `playwright`.

### Bibliotecas

- Adicionadas: `h3` 4.5.0 (Python, locks regenerados com pip-compile, pip-audit limpo); `@tanstack/react-virtual` 3.14.20 e `h3-js` 4.5.0 (versões exatas com mais de duas semanas; npm audit limpo).
- Já presentes e suficientes: polars, pyarrow, duckdb, numpy, scipy, statsmodels, scikit-learn, pandera, plotly; ECharts, MapLibre, TanStack Query.
- Rejeitadas: `bizdays` (puxa pandas-market-calendars e exchange-calendars; os dias úteis vêm das próprias séries CVM/BCB) e `python-bcb` (o SGS é um JSON simples, coberto pelo fetcher com cache que já existe).

---

## 8. Regras globais (valem para os 4 prompts)

1. Nenhum dado inventado. Ausente fica nulo e aparece como ausente; proxy e premissa sempre rotulados. Sandbox nunca entra como real.
2. Fontes públicas e legais apenas. Respeitar termos de uso e `robots.txt`; rate limit; cache bruto imutável com SHA-256 e manifesto; retries limitados. Nada de LinkedIn autenticado nem contorno de bloqueio.
3. Dados pessoais mínimos (LGPD): só contato institucional e diretores registrados na CVM. Sem e-mail ou telefone pessoal.
4. Vínculo entre entidades só por CNPJ exato ou registro curado aprovado; similaridade de nome só gera sugestão na fila de revisão.
5. Retorno de fundo não é lucro da gestora. Score não é probabilidade de compra. Segmento descreve o score, não causa.
6. Não sobrescrever o `.env` (porta 5433 e senha local); copiar o exemplo só se o arquivo não existir. Nunca imprimir nem versionar segredos.
7. Não alterar a planilha original. Não criar PPT, PDF ou vídeo sem pedido. Não fazer commit nem push sem pedido explícito.
8. A demo continua funcionando **offline** a partir de arquivos versionados; o snapshot versionado deve ficar abaixo de ~60 MB (agregados para o universo, séries diárias só para as contas curadas e fundos selecionados).
9. Ambiente: Windows 11, PowerShell, Python 3.11 em `.venv`, Node 20+, PostgreSQL 16 + PostGIS portátil em `C:\Users\Lucas\tools\pgsql16` (porta 5433).
10. Identidade visual inspirada em terminais financeiros, sem copiar logo, fontes proprietárias ou telas da Bloomberg. Nomes de produtos Bloomberg aparecem só como hipótese de workflow.
11. Formatação pt-BR (vírgula decimal, R$, datas dd/mm/aaaa); unidades explícitas; data de referência e fonte em todo número exibido.
12. Antes de mudar, rodar a suíte existente como linha de base; ao final, rodar tudo de novo e relatar números reais.

---

## 9. Os 4 prompts

### Prompt 8 (1/4) — Correções e fundação v2: universo SP/RJ, sell side e novas fontes

```text
Você está no repositório C:\Users\Lucas\Desktop\Estagio_Bloomberg (Windows, PowerShell). Leia integralmente prompts_codex.md (seções 1 a 8 valem como contexto e regras), README.md, docs/architecture.md, docs/delivery_report.md, docs/expansion_universe.md, data/reference/expansion_candidates.csv, scripts/expansion_universe.py, data/reference/identity_registry.yaml, migrations/ e src/networking_intel/enrichment/. Use as skills data-ml-excellence, backend-production-excellence, postgresql-table-design, data-quality-frameworks, senior-finance-analyst e security-best-practices.

Objetivo: transformar o piloto de 12 contas em uma base de território (SP com foco Faria Lima, e RJ) com buy side e sell side, CNPJ exato e novas fontes públicas, sem perder a demo offline.

Antes de tudo: rode ruff, mypy, pytest (com TEST_DATABASE_URL do .env) e os testes do frontend como linha de base e registre os números.

Tarefas:
1. IF.data: corrija try_ifdata para tratar resposta 200 com "value" vazio como período indisponível e recuar até o último trimestre com dados (hoje 202606). Colete IfDataCadastro e IfDataValores (relatórios de resumo, ativo, passivo/captações, carteira de crédito e resultado) para conglomerados prudenciais com sede em SP/RJ; ligue ao CNPJ pela raiz de 8 dígitos (CnpjInstituicaoLider). Teste com fixtures, incluindo o caso vazio.
2. Novos conectores (cache bruto imutável, manifesto, retries limitados, testes com fixtures):
   - CVM INTERMED/CAD (cad_intermed e cad_intermed_resp: só dados institucionais);
   - CVM FI/CAD cad_fi_hist (troca de gestor e de administrador, datas de registro e cancelamento);
   - CVM Informe Diário de 36 meses (mensais recentes + anuais de HIST quando necessário), filtrado às classes do universo;
   - CVM CDA, Perfil Mensal e Lâmina dos 3 meses mais recentes, filtrados às classes do universo;
   - BCB SGS 12 (CDI), 433 (IPCA) e 1 (PTAX). A SGS 7 (Ibovespa) parou em 2019: não use. Para ações, o benchmark será a mediana dos pares; se usar fonte da B3, verifique os termos e rotule.
   - Vagas e notícias: sem raspagem automática de portais com termos restritivos (a API pública da Gupy respondeu 404). Amplie data/reference/commercial_signals.csv com modelo para curadoria manual (URL, data, trecho de até 25 palavras, tipo de sinal, quem revisou).
3. Mova a lógica de scripts/expansion_universe.py para um pacote testado (networking_intel.universe) e mantenha o script como CLI fina. Universo = gestoras ativas (cad_adm_cart, categoria Gestor) + intermediários ativos (bancos, corretoras, distribuidoras, custodiantes, escrituradores) + administradores fiduciários (a partir do registro de fundos: número de fundos e PL administrados) + conglomerados do IF.data, nos centros: Faria Lima; JK/Vila Olímpia; Cidade Jardim/Jardins; Paulista; Berrini/Chucri Zaidan; Leblon/Ipanema; Botafogo; Centro RJ; Barra/São Conrado. Preserve as correções já feitas: limite de plausibilidade de PL por fundo (> R$ 300 bi é anomalia listada, não somada), exclusões de colisão de nomes, casamento com a planilha exigindo a chave do grupo.
4. Grupo econômico: raiz de CNPJ + conglomerado do IF.data + data/reference/group_registry.yaml curado (grupos com raízes diferentes, ex.: Itaú Unibanco, Itaú Asset, Intrag, Kinea). A heurística por nome só gera sugestões em data/review/group_suggestions.csv.
5. Prédio e geografia: chave de prédio normalizada (logradouro + número) para agrupar inquilinos; geocodifique por prédio único (não por entidade), com cache, 1 req/s e atribuição OSM; precisão explícita; nunca marcar aproximado como exato. Gere o índice H3 (resoluções 8 e 9) para cada ponto.
6. Camadas: universe (automática), radar (gestoras registradas há ≤ 24 meses) e curated (12 do piloto + onda 2 da seção 5 de prompts_codex.md). Para a onda 2, gere docs/curated_wave2.md com a evidência de cada conta (CNPJs, local, PL, fundos, tipo, por que entra) e marque todos os vínculos como pending_human_review. Se uma conta proposta não se sustentar nos dados, troque por uma alternativa da lista e explique.
7. Migração Alembic 0003: universe_entities (CNPJ, raiz, tipo, grupo, centro, prédio, ponto PostGIS, H3, datas de registro, situação, camada), group_memberships (evidência e status de aprovação), bank_financials (formato longo: conglomerado, trimestre, conta, valor, fonte), fund_holdings_summary (por classe e mês), fund_profile_monthly, benchmarks (série, data, valor), fund_daily como tabela (PK classe+subclasse+data, índice BRIN na data), crm_status (vazia, para importação futura). Constraints e índices para os filtros da API.
8. Carga idempotente e determinística; snapshot da demo atualizado dentro do limite de tamanho da seção 8 (agregados mensais para o universo, diário para contas curadas). Atualize o fingerprint do demo.py e as contagens esperadas no --check.
9. Qualidade: estenda o quality report com cobertura por camada e tipo, freshness por fonte, anomalias excluídas, sugestões de grupo pendentes e prédios sem coordenada.
10. Documentação: docs/data_sources.md (catálogo: URL, termos, frequência, defasagem, campos usados, status verificado e data) e docs/universe.md (substitui docs/expansion_universe.md, com números gerados pelo código).

Critérios de aceite:
- contagens por tipo e por centro reconciliadas com os arquivos brutos (teste automatizado);
- nenhum vínculo automático por similaridade de nome; toda linha nova tem fonte e data;
- IF.data com período declarado e teste do caso vazio;
- carga duas vezes não duplica; seed determinístico; demo --check passa offline;
- ruff, mypy --strict, pytest (unitário + integração) e testes do frontend passam; pip-audit limpo;
- relatório final com números reais, o que ficou pendente de revisão humana e o tamanho do snapshot.

Não faça ainda: modelo v2, novas telas ou README final.
```

### Prompt 9 (2/4) — Análise de fundos, gestoras, bancos e mercado; modelo opportunity-v2 e segmentos

```text
Leia prompts_codex.md, docs/data_sources.md, docs/universe.md, docs/curated_wave2.md, config/scoring/opportunity_v1.yaml, src/networking_intel/scoring/ e o estado do banco após o Prompt 8. Use senior-finance-analyst, risk-metrics-calculation, statistical-analysis, data-ml-excellence, account-tiering, expansion-whitespace, competitive-intelligence e backend-production-excellence.

Objetivo: dar ao vendedor a análise de cada fundo, gestora, banco e administrador no nível de uma preparação de reunião, e reconstruir o modelo de prioridade sobre o universo inteiro, sem alegar probabilidade de compra.

Tarefas:
1. Analytics de fundo (por classe e subclasse; regras de comparabilidade da v1 preservadas: defasagem, lacunas, cota parada, eventos de cota relativos aos pares):
   - retornos 1d, 5d, MTD, 1m, 3m, 6m, YTD, 12m, 24m, 36m e desde o início da série; matriz ano × mês e retorno anual; últimos 5 e 20 dias úteis;
   - excesso sobre o CDI e % do CDI (convenção brasileira, só quando fizer sentido para a classe); volatilidade anualizada (252), Sharpe e Sortino vs CDI, máximo drawdown com data de pico, vale, duração e recuperação, série underwater, rolling 12m, % de meses acima do CDI;
   - captação líquida diária, semanal e mensal, em R$ e em % do PL inicial; aceleração (4 semanas vs média de 52, em z-score); cotistas ao longo do tempo; decomposição da variação do PL em captação líquida e efeito de rendimento;
   - percentil e quartil entre pares (classificação CVM/ANBIMA, mínimo de 10 pares, senão "pares insuficientes");
   - composição (CDA): % derivativos, % exterior, % crédito privado, número de ativos, concentração dos 10 maiores; perfil (cotistas por tipo, VaR informado).
2. Analytics de gestora: PL sem dupla contagem (FIC e master deduplicados, regra documentada), PL por estratégia, captação mensal de 36 meses, lançamentos e encerramentos por mês (excluindo exclusivos e feeders), idade da casa, diretores registrados (CVM), concentração no maior fundo, base de cotistas, uso de derivativos e exterior.
3. Sell side: bancos (IF.data: ativo, TVM, derivativos quando disponível, crédito, captações, PL, resultado, crescimento trimestral e anual, ranking); administradores (fundos e PL administrados, crescimento, participação); corretoras e distribuidoras (cadastro, conglomerado, porte do IF.data quando houver). Mapeie evidência para mesas: tesouraria/ALM, sales & trading, câmbio, crédito, research, risco/compliance, market data/TI, administração e custódia.
4. Contexto de mercado: captação líquida da indústria por categoria e mês (36 meses), para dizer onde o dinheiro está entrando ou saindo. Leia como contexto e hipótese, não como causa.
5. Sinais de timing v2, cada um com data, fonte, evidência e meia-vida: gestora nova (≤ 24 meses), lançamentos normalizados por porte, aceleração de captação, resgates relevantes e drawdown (negativos), transferência de fundos para a gestora (cad_fi_hist), novos diretores (diferença entre snapshots do cadastro), mudança de endereço; bancos: crescimento de TVM e captações; curados: vagas que citam ferramentas de dados, M&A, notícias (só com URL).
6. Modelo opportunity-v2 (config/scoring/opportunity_v2.yaml, versão nova, v1 preservada para comparação): mesmas três saídas e faixas para ausência; variáveis novas com evidência (composição, perfil, IF.data, administração, idade, sinais); normalização por porte para que escala de plataforma não domine; fit próprio para administradores (precificação e dados de referência), corretoras (execução e distribuição) e mesas de banco com evidência observada quando houver (premissa só onde faltar, rotulada). Mapeie workflows plausíveis por persona como hipótese: macro (juros, câmbio, derivativos), crédito (precificação e dados de crédito), ações (research e screening), quant (dados em volume e API), wealth/family office (portfólio multiativo), bancos (tempo real, dados de referência, risco, execução), administradores (precificação, dados de referência). Pontue todo o universo; as contas curadas recebem também os sinais curados.
7. Validação do modelo: sensibilidade (OAT e Dirichlet), checagens de sanidade atualizadas e documentadas (ex.: macro multiestratégia com exterior acima de gestora só de FIDC; BTG Wealth não lidera só por número de lançamentos), comparação v1 × v2 com o motivo de cada mudança de posição relevante. Trava de calibração mantida; crie data/reference/crm_outcomes_template.csv (status comercial, new logo ou expansão, data, fonte) sem nenhuma linha fictícia.
8. Segmentos: variáveis padronizadas, agrupamento (k-means ou mistura gaussiana com escolha do número de grupos por silhueta/BIC e estabilidade por bootstrap), 4 a 7 personas nomeadas pelo centroide; comparação quartil superior × inferior do score com diferenças de mediana e intervalo por bootstrap. Texto obrigatório: descreve o score, não a decisão de compra.
9. API (mesmos padrões de segurança, ETag, paginação e OpenAPI documentado): /universe (filtros por tipo, camada, centro, persona, faixa de score, busca; ordenação), /radar, /managers/{cnpj}, /managers/{cnpj}/funds, /funds/{cnpj}/analytics (granularidade dia|semana|mês e janela), /funds/{cnpj}/peers, /banks/{cnpj}/financials, /administrators, /segments, /market/flows, /benchmarks, /map/buildings, /map/hex?res=. Orçamento local: p95 < 300 ms com índices ou visões materializadas; regenere o schema TypeScript do frontend.
10. Relatórios: docs/methodology.md (todas as fórmulas, convenções e regras de exclusão), docs/opportunity_model_v2_report.md, docs/segments_report.md e docs/market_context.md, com números gerados pelo código.

Critérios de aceite:
- fórmulas conferidas contra fixtures calculadas à mão (composição de retornos mensais = retorno acumulado; % do CDI; drawdown; captação semanal = soma das diárias);
- sem look-ahead; determinismo; nenhum par com N < 10 exibido como percentil;
- scripts/validate_sample.py estendido recalcula, a partir dos arquivos brutos, retornos mensais, captação, drawdown e % do CDI de fundos sorteados e bate com a API;
- toda variável do score cita evidência; toda premissa está rotulada;
- suíte completa e pip-audit passam.

Não faça ainda as telas novas.
```

### Prompt 10 (3/4) — Frontend v2: universo, radar, gestora, fundo, sell side, segmentos e mapa de visitas

```text
Leia prompts_codex.md, a OpenAPI e docs/methodology.md após o Prompt 9, e o código em frontend/. Use frontend-design, frontend-design-excellence, kpi-dashboard-design, data-visualization, vercel-react-best-practices, web-design-guidelines e playwright.

Objetivo: um dashboard denso e profissional, inspirado em terminais financeiros (sem copiar a identidade da Bloomberg), em que cada avaliador faça a sua jornada em menos de 3 minutos e cada número tenha fonte e data.

Telas (atalhos de teclado 1–9 e 0; barra de comando busca entidade, fundo ou CNPJ):
1. Ranking — o atual, com filtros de camada, tipo e persona e faixa de incerteza.
2. Universo — tabela virtualizada (@tanstack/react-virtual) para 1.000+ linhas; presets de colunas "Buy-Side" e "Banks & Brokers"; filtros na URL; exportar CSV do recorte.
3. Radar — linha do tempo de sinais de 7, 30 e 90 dias (gestoras novas, lançamentos, aceleração de captação, resgates, transferências, sinais curados), cada um com fonte.
4. Gestora 360 — KPIs (PL, captação 12m, fundos, lançamentos, idade); PL por estratégia (treemap); captação mensal de 36 meses (barras + acumulado); tabela de fundos com sparkline e retorno vs CDI; diretores registrados; escritórios; explicação do score; workflows hipotéticos.
5. Fundo 360 — cota vs CDI e mediana dos pares com seletor 5d/1m/3m/6m/YTD/12m/24m/36m/máx; matriz ano × mês de retornos com total anual (heatmap legível em daltonismo); barras anuais vs CDI; underwater; rolling 12m de retorno e volatilidade; captação diária/semanal/mensal com acumulado; cotistas; últimos 10 dias úteis em tabela; faixa de percentil entre pares; composição da carteira; avisos de qualidade da série.
6. Sell side — bancos com KPIs do IF.data e mesas com evidência (observado × premissa); ranking de administradores por fundos e PL administrados; corretoras e distribuidoras; workflows por área.
7. Segmentos — cartões de persona, perfil do centroide, dispersão fit × timing por persona com faixas, comparação quartil superior × inferior.
8. Mapa — alternância SP/RJ; hexágonos H3 de densidade; prédios com lista de inquilinos (ex.: "Faria Lima 3477"); filtros por camada, persona e score; roteiro de visita (selecionar contas, agrupar por prédio e ordenar por proximidade, com distância estimada); aviso quando o basemap estiver offline. Densidade não sugere causalidade.
9. Comparador — contas e também até 5 fundos com curvas normalizadas e métricas lado a lado.
0. Qualidade — freshness das novas fontes, cobertura por camada, filas de revisão (grupos, conflitos, prédios sem coordenada).

Requisitos:
- ECharts carregado sob demanda; uma paleta única com verde/vermelho só para variação; nota de fonte e data em todo gráfico; tooltips com unidade; pt-BR.
- Estados de carregamento, vazio, erro, dado vencido, premissa e pares insuficientes.
- Divisão por rota e orçamento de bundle documentado; nenhuma lista longa sem virtualização; zero avisos novos do linter e resolver os 7 avisos de Fast Refresh existentes.
- Acessibilidade (axe sem violações sérias), navegação por teclado e contraste AA; funciona em 1366×768, 1440×900 e 1920×1080 sem overflow nem texto cortado.
- Selo DEMO em modo demo; nenhum dado de exemplo inventado.

Testes:
- Vitest para matemática de exibição (matriz mensal, agregação semanal, formatação) e componentes, com fixtures capturadas da API real (MSW);
- Playwright: jornada Buy-Side (Radar → gestora nova → Gestora 360 → Fundo 360 → comparar 3 fundos → roteiro no mapa) e jornada Banks & Brokers (Sell side → administrador → banco → mesa → explicação), filtros sincronizados com a URL, offline, axe, capturas de tela de referência nas três resoluções.

Critérios de aceite: lint, typecheck, Vitest e Playwright passam em dev e no build de produção com CSP; nenhum erro de console; as duas jornadas cabem em 3 minutos cada.
```

### Prompt 11 (4/4) — Integração final, organização do repositório, README completo e roteiro

```text
Leia prompts_codex.md e todo o repositório após o Prompt 10. Use general-code-review, cybersecurity-defensive-review, security-best-practices, backend-production-excellence, data-storytelling e playwright.

Objetivo: deixar o projeto final, organizado e explicável para quem nunca o viu, com a narrativa honesta para a banca.

Tarefas:
1. QA completo: ruff, mypy --strict, pytest unitário e de integração, Vitest, Playwright (dev e produção), pip-audit, npm audit, validação independente por amostragem estendida, seed determinístico em dois bancos novos, instalação do zero a partir de uma cópia limpa. Corrija o que falhar.
2. Revisão de segurança e LGPD atualizada para as novas fontes (termos de uso, rate limits, dados pessoais, logs, CORS, CSP, dependências).
3. Organização do repositório:
   - testes por domínio (tests/unit/<domínio>, tests/integration/), não por número de prompt;
   - docs com índice (docs/README.md), registros de decisão curtos (docs/adr/) e nomes por assunto; mover relatórios antigos dos prompts para docs/history/ com uma linha explicando cada um;
   - scripts consolidados (demo, check_all que roda todas as verificações, validate_sample, document_api, universe) e CLIs com --help;
   - AGENTS.md com as regras globais da seção 8 de prompts_codex.md e os comandos de verificação;
   - workflow de CI (.github/workflows) com lint, tipos, testes unitários, integração com serviço PostGIS e frontend (só criar o arquivo; não fazer push);
   - Docker: validar se possível; se não, declarar como não validado;
   - investigar por que o pack do .git ocupa ≈ 114 MB (objetos inalcançáveis?) e relatar; não reescrever histórico sem pedido.
4. Verificação de números nos documentos: script que confere cada número citado no README, no roteiro e no relatório de entrega contra a API (falha se divergir). Nenhum número escrito à mão sem essa checagem.
5. README completo, nesta ordem: o que é e para quem; o problema comercial; o que o produto faz e o que não faz; demo em um comando (incluindo PostgreSQL portátil e o aviso do .env); como navegar (tela a tela, atalhos, as duas jornadas dos avaliadores, com capturas de tela); dados e fontes (tabela com data de referência); metodologia (fit, timing, confiança, faixas, normalização, segmentos; link para docs/methodology.md); universo e critérios de seleção (SP com foco Faria Lima, RJ, camadas, onda 2); principais resultados com números reais; limitações; arquitetura (diagrama); estrutura de pastas; pipeline completo para atualizar os dados; testes e validação; segurança e LGPD; próximos passos (piloto, CRM, calibração); glossário (fit, timing, confiança, % do CDI, drawdown, FIC, master, administrador, mesa).
6. Roteiro da apresentação atualizado (docs/demo_script.md): 90 segundos, 5 minutos e 10 minutos; um caminho para cada avaliador; perguntas prováveis com respostas curtas; plano B offline. Atualize docs/delivery_report.md (validação técnica, qualidade econômica do score e aprovação comercial, separadas) e docs/pilot_metrics.md.
7. Revisão final de UI com web-design-guidelines e capturas em docs/screenshots/.

Critérios de aceite:
- uma pessoa nova sobe a demo seguindo só o README;
- check_all passa do início ao fim;
- todo insight exibido é rastreável à fonte e data;
- limitações e revisões humanas pendentes estão no README, no roteiro e no relatório de entrega;
- nenhum commit ou push sem pedido; relatório final lista o que mudou, os números finais e o que depende da Bloomberg (revisão das contas, dados de CRM, piloto).
```

---

## 10. Se o tempo apertar

Ordem de corte, do que sai primeiro: CI e Docker → comparador de fundos → segmentos → Perfil Mensal e Lâmina → roteiro no mapa. Não cortar: IF.data e sell side, radar de novas gestoras, Fundo 360 com captação e retornos mensais, universo, README e roteiro.

## 11. Fontes de pesquisa

- CVM Dados Abertos: https://dados.cvm.gov.br/ (FI/CAD, FI/DOC/INF_DIARIO, CDA, PERFIL_MENSAL, LAMINA, INTERMED/CAD, CIA_ABERTA/DOC/FRE)
- Banco Central, IF.data (Olinda): https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/
- Banco Central, SGS: https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados
- OpenStreetMap Nominatim, política de uso: https://operations.osmfoundation.org/policies/nominatim/
- H3: https://h3geo.org/
- Bloomberg Terminal: https://www.bloomberg.com/professional/solution/bloomberg-terminal/
- ANPD, legítimo interesse: https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_hipoteses_legais_tratamento_de_dados_pessoais_legitimo_interesse
- Leandro Pena: https://br.linkedin.com/in/leandro-pena-332478112
- Yasmin La Manna: https://br.linkedin.com/in/yasmin-la-manna-m-pilatti-160a3b97/pt
- Skills: https://skills.sh/
