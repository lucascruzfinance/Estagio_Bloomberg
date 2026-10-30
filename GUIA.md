# Guia do projeto: o que é, como funciona e como apresentar

Guia de estudo para a apresentação. Números conferidos na base de 30/10/2026 (dados públicos até 28/10/2026 nos fundos, 06/2026 no IF.data). Se a base for recarregada, confira os números na tela antes de citá-los.

## 1. Em 30 segundos

> "Preparar uma conta hoje significa juntar CVM, site, LinkedIn e planilha, e cada vendedor prioriza de um jeito. Construí uma ferramenta que mapeia **todo o território de São Paulo e Rio** (1.447 gestoras, bancos, corretoras e administradores, com CNPJ, prédio, PL e captação mês a mês) e **prioriza as contas de forma explicável**: separo **fit** (o workflow depende de dados?), **timing** (há uma mudança recente que abre conversa?) e **confiança** (quanto disso tem fonte recente). Cada número tem fonte e data. Não prevejo quem compra: reduzo o tempo de preparação e deixo explícito por que uma conta entra na fila."

## 2. O problema e a proposta

- **Problema comercial**: o território é grande, os dados estão espalhados e a prioridade depende da intuição de cada vendedor. Preparar uma reunião leva horas.
- **Hipótese corrigida**: "fundo que performa bem compra Terminal" não está demonstrado (viés de sobrevivência, retorno do fundo não é lucro da gestora, sem dado de conversão). Por isso performance pesa no máximo 10% do timing.
- **Proposta**: priorização explicável com três leituras separadas (fit, timing, confiança), faixa de incerteza onde falta dado e fonte em todo número. Para bancos, a unidade de análise é a **mesa/área**, não o banco inteiro.

## 3. Como o app funciona (telas)

Abra com `python scripts/demo.py` e acesse http://127.0.0.1:4173 (ou `npm run dev` em `frontend/` → http://localhost:5173 com a API em :8000).

| Tecla | Tela | O que mostrar |
|---|---|---|
| `1` | **Prioridade** | Ranking das 22 unidades (10 gestoras + 12 mesas de BTG e Itaú BBA). A barra mostra o ponto (dados observados) e a faixa cinza (quanto pode mudar com o que falta). |
| `5` | **Conta 360** | Preparação de reunião: fatores com peso e evidência, fundos e gráfico de cota, contatos institucionais da CVM, diretor de gestão registrado, workflows hipotéticos. |
| `2` | **Mapa** | Escritórios do piloto; ponto cheio = endereço exato (número da porta conferido), anel = aproximado. |
| `3` | **Comparador** | Até 5 unidades lado a lado; avisa quando mistura dado observado com premissa. |
| `4` | **Qualidade** | Atualização das fontes, cobertura e fila de revisão humana (conflitos entre planilha e CVM). |
| `6` | **Universo SP/RJ** | O território inteiro com filtros por lado (buy/sell side), camada (curada, radar, universo), tipo e centro financeiro. Ao clicar: PL e captação mês a mês de 36 meses, maiores fundos com retorno 12m, endereço, grupo e fonte. |

## 4. De onde vêm os dados e como são puxados

Só fontes públicas e legais. Tudo é baixado por um *fetcher* com cache bruto imutável (`data/raw/`, endereçado por SHA-256, com manifesto), limite de requisições e novas tentativas limitadas. A demo roda **offline** a partir de um snapshot versionado.

| Fonte | O que usamos |
|---|---|
| CVM, cadastro de administradores de carteira | gestoras: CNPJ, endereço, telefone, site, data de registro, diretor de gestão |
| CVM, cadastro de intermediários | bancos, corretoras, distribuidoras, custodiantes (sell side) |
| CVM, registro de fundos/classes (RCVM 175) | gestor, administrador, custodiante, classe, exclusivo, FIC, PL |
| CVM, Informe Diário (37 arquivos mensais) | cota, PL, captação, resgate, cotistas: base de retorno e fluxo |
| CVM, CDA, Perfil Mensal, Lâmina | composição da carteira (derivativos, exterior, crédito, ações), tipo de cotista, VaR, taxas |
| CVM, histórico cadastral | transferências de fundos entre gestoras |
| Banco Central, IF.data | porte e balanço dos conglomerados (ativo, TVM, crédito, captações, lucro, DRE) e o mapa CNPJ → conglomerado |
| Banco Central, SGS | CDI, IPCA, PTAX |
| OpenStreetMap (Nominatim) | coordenadas por prédio, com precisão declarada |

Regras que dão credibilidade (vale citar):

- **Vínculo só por CNPJ exato.** Nome parecido nunca cria vínculo; vira sugestão para revisão humana (`data/review/group_suggestions.csv`).
- **Grupo econômico**: registro curado (pendente de revisão) > conglomerado prudencial do Banco Central > raiz do CNPJ.
- **Dado ausente não vira zero**: aparece como faixa.
- **Anomalias são tratadas**: 3 fundos com PL de R$ 16,7 trilhões no registro (erro de unidade) ficam fora das somas; linhas diárias repetidas da CVM são deduplicadas.
- **Endereço exato só com número da porta conferido.**
- **LGPD**: só contato institucional e diretor registrado na CVM; nada de LinkedIn autenticado nem e-mail pessoal.

## 5. Critérios do universo e das contas

- **Universo**: toda gestora e todo intermediário ativo na CVM com sede nos municípios de São Paulo, Rio de Janeiro e Osasco (onde fica o Bradesco).
- **Centros financeiros**: Faria Lima, JK/Vila Olímpia, Cidade Jardim/Jardins, Paulista, Berrini/Chucri Zaidan, Centro (SP), Leblon/Ipanema, Botafogo, Centro (RJ) e Barra. A classificação usa a avenida primeiro e o bairro como reserva.
- **Camadas**:
  - **curada**: 12 contas do piloto + 24 da onda 2, com 102 CNPJs ao todo;
  - **radar**: gestoras registradas há até 2 anos; inclui re-registros, como o da Sicredi Asset;
  - **universo**: todas as demais, automáticas.
- **Onda 2 (24 contas)**: escolhidas por centro (prioridade Faria Lima), PL e fundos abertos, diversidade de estratégia (macro, crédito, ações, quant, global) e de tipo de instituição.
  - Buy side: Itaú Asset, XP, Santander Asset, Safra, UBS, BNP, Absolute, Genoa, Legacy, Capitânia, Vinland, Quadra, Guepardo, Giant Steps, Opportunity, ARX, Dynamo e Truxt.
  - Sell side: Banco Santander, Bradesco BBI, Banco Safra, XP Investimentos, BR Partners e BNY Mellon.
  - Detalhes em `docs/curated_wave2.md`.
- **Classes "selecionadas"**: abertas, não exclusivas e não FIC, ou seja, os veículos públicos com carteira própria. O PL da gestora soma as classes não FIC, incluindo as exclusivas, para não contar duas vezes.

## 6. Como funciona a pontuação (`opportunity-v1.0.0`)

**Fit estrutural** (o workflow da instituição depende de dados e ferramentas?):

| Fator | Peso | Ideia |
|---|---:|---|
| Complexidade do workflow | 30% | Estratégias intensivas em dados (macro, derivativos, crédito, ações) |
| Amplitude de ativos | 20% | Número de famílias de estratégia |
| Atuação internacional | 15% | Classes que podem investir 100% no exterior |
| Necessidade de dados/API | 15% | Volume de fundos e dados a precificar e integrar |
| Potencial de usuários | 20% | Porte (PL, número de veículos) |

**Timing comercial** (há uma razão para ligar agora?):

| Fator | Peso | Ideia |
|---|---:|---|
| Lançamento de fundos | 25% | Fundos abertos não exclusivos lançados em 12 meses |
| Captação líquida | 20% | Fluxo de 12 meses em % do PL |
| Expansão | 15% | Novas entidades e escritórios |
| Contratações | 15% | Sinal curado com fonte |
| M&A | 10% | Sinal curado com fonte |
| Mudança operacional | 5% | Sinal curado com fonte |
| Performance | 10% (máximo) | Retorno contra os pares, peso propositalmente baixo |

**Prioridade** = 60% fit + 40% timing, quando há cobertura de timing de pelo menos 40%. Sem isso, a unidade aparece como "fit alto ou baixo, timing desconhecido".

**Confiança** (0 a 100) é separada e **nunca** altera fit ou timing. É composta de:

- cobertura de evidência (35%);
- identidade revisada (20%);
- atualização das fontes (15%);
- conflitos (15%);
- comparabilidade (15%).

**Faixas**: o ponto usa só fatores observados. O limite inferior e o superior mostram o que aconteceria se cada fator ausente valesse 0 ou 1.

**Bancos por mesa**:
- Asset e Wealth são observados (fundos na CVM).
- Sales & Trading, Research, Risco e Market Data são **premissas editáveis**, rotuladas como tal.

**Robustez**:
- 1.000 sorteios de pesos (Dirichlet) com Spearman médio de 0,95;
- testes de sanidade (3 de 4 passam; a falha é documentada: a SPX é macro global, mas a CVM não vê fundos offshore);
- calibração só com pelo menos 50 resultados reais de CRM, dos quais pelo menos 10 positivos (regra no código).

**Ranking atual (topo)**:
- BTG Wealth (78): lidera por escala de plataforma, e eu digo isso;
- BTG Asset (70), Portofino (67), Kinea (60);
- no fim, Constellation (18): timing ruim por resgates, não fit ruim.

## 7. Números para citar

- **Universo**:
  - **1.447 entidades**: 1.228 buy side e 219 sell side;
  - **1.007 gestoras** com fundos ativos;
  - **30.710 classes** de fundos;
  - **1.331 grupos** econômicos.
- **Centros**:
  - Faria Lima: **362 entidades**, das quais 305 buy side;
  - JK/Vila Olímpia: **505**;
  - Leblon/Ipanema: **137**.
- **Radar**: **174 gestoras** registradas nos últimos 2 anos (39 na Faria Lima, 68 na JK).
- **Maiores grupos gestores por PL** (Informe Diário, 10/2026):
  - BB Gestão: R$ 2,0 tri;
  - Itaú Asset: R$ 1,28 tri, com captação 12m de −R$ 19,9 bi;
  - Bradesco: R$ 1,0 tri;
  - BTG: R$ 487 bi, com captação 12m de **+R$ 60 bi**.
- **Sell side** (IF.data 06/2026, ativo total):
  - Itaú: R$ 2,85 tri;
  - Bradesco: R$ 2,0 tri;
  - Santander: R$ 1,3 tri;
  - BTG: R$ 858 bi.
- **Administradores fiduciários** (fundos ativos):
  - BTG DTVM: 7.081;
  - Itaú: 3.257;
  - BEM/Bradesco: 2.609;
  - Intrag: 2.360;
  - BNY Mellon: 1.778.

## 8. Como isso ajuda a Bloomberg a vender mais

**Leandro Pena (Brazil Buy-Side)**:
- **Quem visitar**: a tela Universo filtrada por Faria Lima e buy side, ordenada por PL ou por captação, mostra o território. O **radar** lista casas novas, que montam mesa e precisam de Terminal, dados e execução.
- **Com qual conversa**:
  - estratégia e composição apontam o workflow: macro e derivativos (curvas, FX, opções), crédito (precificação e dados de crédito), ações (research e screening), quant (dados em volume e API);
  - a captação diz o momento: gestora captando contrata, gestora sob resgate corta custo.
- **Execução**: gestoras com muitos fundos abertos e derivativos são candidatas naturais a ferramentas de ordens e execução. É a sua experiência em Electronic Trading.

**Yasmin La Manna (Banks and Brokers)**:
- **A resposta não é "vender um Terminal ao banco"**: é encontrar a área e o problema.
  - IF.data mostra o porte e o balanço (TVM, crédito, captações), que são evidência para tesouraria/ALM e sales & trading.
  - **Administradores fiduciários** precificam milhares de fundos todo dia, o que aponta para dados de referência e precificação (Data License, BVAL). Isso conversa com a experiência dela em Enterprise Data.
  - Corretoras e distribuidoras apontam para execução, distribuição e research.

**Para o time**:
- menos horas de preparação por conta;
- prioridade com critério explícito e auditável;
- fila de revisão humana em vez de dado errado;
- base pronta para receber o CRM e calibrar com resultados reais.

## 9. Tecnologias e bibliotecas

| Camada | Tecnologia | Por quê |
|---|---|---|
| Dados | Python 3.11, **Polars**, PyArrow (Parquet), httpx + tenacity, openpyxl, **h3** (hexágonos geográficos), pydantic | Processar 20 milhões de linhas do Informe Diário em ~1 min; validação estrita |
| Banco | **PostgreSQL 16 + PostGIS**, SQLAlchemy 2, Alembic (3 migrações), carga por COPY | Dados geográficos, integridade (CNPJ válido, regras de precisão), cargas idempotentes |
| API | **FastAPI**, pydantic, structlog, Prometheus | API somente leitura, documentada (OpenAPI em /docs), erros RFC 7807, rate limit, ETag, CSP |
| Front-end | **React 19 + TypeScript + Vite**, TanStack Query, **ECharts**, **MapLibre** | Painel denso no estilo terminal financeiro, sem copiar a identidade da Bloomberg |
| Qualidade | pytest, ruff, mypy --strict, Vitest, Playwright + axe, pip-audit, npm audit | Testes unitários, de integração e ponta a ponta; acessibilidade; dependências auditadas |

## 10. Limitações (dizer em voz alta)

1. Os pesos são premissas especialistas: ainda não há dado de conversão para calibrar.
2. A CVM não vê fundos offshore (por isso a SPX parece menor do que é).
3. As mesas de banco no ranking v1 ainda são premissas. O IF.data já está carregado para dar evidência a elas (próximo passo).
4. Os vínculos entre entidades e todas as 36 contas curadas aguardam revisão humana.
5. A geocodificação cobre 869 entidades em 544 prédios (254 com porta conferida); o resto ficou para a próxima execução online.
6. PL somado por gestora inclui fundos exclusivos e não é o AUM oficial.

## 11. O que ficou para depois (plano dos Prompts 9 a 11)

Executado agora:

- **Prompt 8 completo**: universo, sell side, novas fontes, migração, carga, testes e documentos.
- **Do Prompt 10**: a tela Universo com PL e captação mês a mês.
- **Do Prompt 11**: README e este guia.

Ficou planejado em `prompts_codex.md`:

- **Prompt 9**: modelo v2 sobre o universo inteiro; matriz mês a mês de retornos contra o CDI; drawdown; percentil entre pares; segmentos e personas.
- **Prompt 10**: telas Fundo 360, Sell side, Radar, Segmentos, e mapa por prédio com rota de visita.
- **Prompt 11**: CI, reorganização de testes e documentos, e checagem automática dos números citados.

## 12. Perguntas prováveis

| Pergunta | Resposta curta |
|---|---|
| Isso prevê quem vai comprar? | Não. Prioriza e explica. Sem histórico de oportunidades não há modelo preditivo honesto; a calibração está pronta para quando houver CRM. |
| Por que o BTG Wealth está em primeiro? | Escala de plataforma e lançamentos. O modelo v2 normaliza pelo porte para medir sofisticação, não só tamanho. |
| De onde vêm os telefones e endereços? | Cadastros da CVM, com data e link; o mapa diz a precisão de cada ponto. |
| Como sei que os números estão certos? | Um script independente recalcula scores, retornos, séries e coordenadas a partir dos arquivos brutos e compara com a API (`docs/validation_report.md`); as contagens do universo são reconciliadas com os cadastros em teste automatizado. |
| E a LGPD? | Só dado institucional e diretor registrado na CVM, para planejamento de conta. Nada de LinkedIn autenticado. |
| Quanto custa manter? | Fontes públicas e gratuitas; o universo inteiro roda em cerca de 1 minuto com cache; a carga no banco leva cerca de 1 minuto. |
