# Relatório de entrega do MVP

Data: 30/10/2026. Base de dados: fontes públicas até 27/10/2026. Modelo: `opportunity-v1.0.0`.

Este relatório separa três perguntas que não podem ser confundidas:

1. **Validação técnica**: o sistema faz corretamente o que diz fazer? → **concluída para o MVP.**
2. **Qualidade econômica do score**: a ordem proposta corresponde a oportunidades reais? → **não validada**; não há dados de resultado.
3. **Aprovação comercial**: o time Bloomberg quer usar e a ferramenta muda a conversa? → **pendente**; depende do piloto.

## 1. Validação técnica

### Suíte de testes (rodada final em 30/10/2026)

| Camada | Ferramenta | Resultado |
|---|---|---|
| Python: estilo e tipos | ruff, ruff format, mypy --strict | aprovado (58 arquivos, mypy em modo estrito) |
| Python: unidade + integração (PostgreSQL 16 + PostGIS reais) | pytest | 118 aprovados, nenhum pulado (integração inclusa) |
| Dependências | pip-audit (projeto e dev), npm audit | sem vulnerabilidades conhecidas |
| Dashboard: estilo e tipos | oxlint, tsc | 0 erros; 7 avisos de Fast Refresh (helpers co-localizados, sem efeito funcional) |
| Dashboard: componentes e jornadas | Vitest + Testing Library + MSW | 25 aprovados |
| Dashboard: ponta a ponta | Playwright em 1366×768 e 1440×900, axe (WCAG 2 A/AA), sem internet | 26 aprovados no servidor de desenvolvimento e 26 no build de produção (com CSP ativa) |
| Subida do zero | cópia limpa do repositório → venv + `pip install` do lock + `npm ci` + `scripts/demo.py --check` em banco novo | aprovado; a primeira tentativa revelou que o `.gitignore` excluía `frontend/src/lib` (corrigido) |
| Determinismo do seed | impressão digital do conteúdo em dois bancos criados do zero e no banco de trabalho | idêntica (`34f15cd40d894faa`) |
| Validação independente por amostragem | `scripts/validate_sample.py` (biblioteca padrão, sem importar o pipeline) | 8 de 8 blocos aprovados, 593 itens conferidos |

### O que a amostragem independente confirma

- Contagens: 12 contas, 22 unidades (10 gestoras + 12 mesas), 48 entidades legais.
- Os 22 scores, recalculados a partir dos fatores e dos pesos do YAML, batem com a API (desvio ≤ 0,005 ponto, arredondamento).
- Retorno 12m, PL e captação de 8 classes sorteadas, refeitos dos zips brutos da CVM, batem com a API (desvio de retorno da ordem de 1e-9).
- As séries do gráfico de cota têm o mesmo número de pontos e as mesmas cotas nas pontas que o arquivo bruto; o índice começa em 100.
- Fontes das entidades apontam para `dados.cvm.gov.br` e o SHA-256 do arquivo bruto confere.
- Coordenadas estão dentro da UF e são idênticas às respostas brutas do Nominatim; "exato" só com número da porta conferido.
- Cada fator com valor (158) cita evidência.

### Defeitos encontrados e corrigidos durante QA (prompts 5 a 7)

| Defeito | Impacto | Correção |
|---|---|---|
| `/ready` sem timeout de conexão travava ~130 s com o banco fora | Health check inútil em orquestrador | `connect_timeout` configurável; teste garante resposta em segundos |
| Tracebacks gravavam variáveis locais nos logs | Possível vazamento de cabeçalhos e credenciais | Renderização sem locals; teste de regressão |
| `migrations/env.py` priorizava a configuração em cache | Teste poderia migrar ou apagar o banco errado | URL explícita do chamador tem prioridade |
| `/data-quality` varria 917 mil linhas e estourava o timeout | Erro 500 intermitente | Consulta trocada por agregado de 3,6 mil linhas (15 ms) |
| Mapa com altura zero e worker do MapLibre ausente | Mapa em branco | Especificidade do CSS e worker empacotado como módulo ES |
| Rolagem da página com o painel aberto, corte de colunas em 1366 | Layout quebrado no notebook da apresentação | Trilhas `minmax(0,1fr)`, painel fluido, rótulos curtos |
| Contraste do selo "fonte indisponível" | Falha WCAG AA | Tom de texto próprio para o status crítico |
| Números no formato americano nas explicações | Inconsistência pt-BR | Formatação brasileira no modelo |
| Explicação dizia "0 fundos" onde não havia fundos mapeados | Sugeria uma observação inexistente | Texto de ausência explícito |
| Rate limit atingido por rajadas legítimas do dashboard | Erro em navegação rápida | Limite local 600/min e nova tentativa automática em 429 |
| Cabeçalho `server: uvicorn` | Exposição de tecnologia | `--no-server-header` |
| `.gitignore` do template Python ignorava qualquer pasta `lib/`, incluindo `frontend/src/lib` | Um clone do repositório não compilaria o dashboard | Regra ancorada na raiz (`/lib/`); confirmado pela instalação do zero |
| Instrução `Copy-Item .env.example .env` do README sobrescrevia um `.env` existente | A senha local do banco foi perdida durante o uso e a API deixou de autenticar | Senha restaurada; README só copia se o arquivo não existir; `demo.py` falha em 5 s com mensagem clara se a conexão for recusada |

### Limitações técnicas conhecidas

- IF.data (Banco Central) respondeu HTTP 500 em todas as tentativas: dados prudenciais dos bancos não entram no score (a interface avisa).
- 18 endereços ficaram sem coordenada confiável; 14 aproximados por rua. Um basemap online é necessário para o fundo do mapa.
- Sem autenticação: uso local apenas (ver `docs/security_review.md`).
- Docker não foi exercitado nesta máquina (sem WSL); o caminho testado é o PostgreSQL portátil. Os arquivos do Docker existem mas não foram validados aqui.

## 2. Qualidade econômica do score (não validada)

O que existe: pesos especialistas versionados, faixas para dados ausentes, sensibilidade aos pesos (Spearman médio 0,95 em 1.000 sorteios) e checagens de sanidade (3 de 4 passam; a falha SPX < Portofino está documentada e explicada pela invisibilidade de fundos offshore na CVM).

O que **não** existe: evidência de que a ordem corresponde a oportunidades reais. Estabilidade interna não é validade externa. Para isso:

- 30% do peso de timing (contratações, M&A, mudanças operacionais) ainda depende de sinais curados com fonte;
- é preciso registrar resultados do piloto e do CRM (definições em `docs/pilot_metrics.md`) e só então calibrar (mínimo de 50 resultados e 10 positivos, regra já no código).

## 3. Aprovação comercial (pendente)

Depende do time Bloomberg. Propostas concretas:

- 30 minutos com cada Sales Team Leader para revisar as 12 contas, as mesas dos bancos e os workflows sugeridos;
- piloto de 4 semanas com 2 vendedores, medindo tempo de preparação, aceitação do ranking, reuniões e conversão contra a linha de base;
- decisão de seguir, ajustar ou parar com os critérios de `docs/pilot_metrics.md`.

## Revisão humana necessária antes de uso real

- Vínculos de afiliadas e entidades bancárias em `data/reference/identity_registry.yaml` (todos marcados `pending_human_review`).
- 9 conflitos pendentes entre planilha e cadastro oficial em `data/review/conflicts.csv`.
- Premissas das 12 mesas de bancos em `config/scoring/opportunity_v1.yaml`.

## 4. Fase 2 (prompts 8 a 11): o que foi entregue em 30/10/2026

Entregue e validado:

- **Universo SP/RJ** (Prompt 8), pacote `networking_intel.universe`:
  - 1.447 entidades (1.228 buy side, 219 sell side), 1.331 grupos econômicos e 30.710 classes de fundos;
  - Informe Diário de 37 meses, CDA, Perfil Mensal, Lâmina e histórico cadastral;
  - IF.data com 1.274 instituições de SP/RJ, período 06/2026. O trimestre ainda não publicado responde vazio e passou a ser tratado como ausente; antes era aceito como "ok";
  - SGS (CDI, IPCA, PTAX);
  - 544 prédios geocodificados, com índice H3.
- **Onda 2**: 24 contas curadas com CNPJ conferido (`docs/curated_wave2.md`), todas pendentes de revisão humana.
- **Banco**: migração 0003 com 18 tabelas e carga idempotente por substituição (1.036.609 linhas diárias, 163.177 mensais, 25.009 por gestora e mês), integrada ao `scripts/demo.py`.
- **API**: `/api/v1/universe`, `/universe/summary` e `/universe/{cnpj}` (PL e captação mês a mês, maiores fundos, fonte).
- **Dashboard**: tela 6, "Universo SP/RJ".
- **Documentos gerados pelo código**: `docs/universe.md`, `docs/curated_wave2.md` e `docs/data_sources.md`; guia de estudo em `GUIA.md`.
- **Testes novos**:
  - unidade: geografia, prédio, IF.data com período vazio, CDA, deduplicação classe/subclasse, precedência de grupos;
  - reconciliação das contagens com os arquivos brutos;
  - integração: carga duas vezes, nenhum vínculo aprovado por nome, nenhum status comercial inventado.

Validação da fase 2: pytest 128 aprovados (unidade + integração com PostGIS), ruff e mypy --strict limpos (76 arquivos), Vitest 25, typecheck do dashboard limpo, `scripts/demo.py --check` aprovado em banco novo com o universo (impressão digital do seed `1a3f3e5739065d00`, substitui a anterior). Snapshot versionado: 52 MB no total (universo 34 MB).

Defeitos de dados encontrados e tratados:

- 3 fundos com PL de R$ 16,7 trilhões no registro (erro de unidade) ficam fora das somas;
- linhas diárias repetidas no arquivo da CVM são deduplicadas;
- o arquivo 202509 do IF.data traz linhas duplicadas;
- os arquivos anteriores à RCVM 175 usam outro layout.

Pendente (planejado em `prompts_codex.md`, não executado por prazo):

- **Prompt 9**:
  - modelo `opportunity-v2` sobre o universo, com normalização por porte e evidência de mesas via IF.data;
  - analytics de fundo (matriz mês a mês contra o CDI, drawdown, percentil entre pares, aceleração de captação);
  - segmentos e personas;
  - endpoints de análise de fundo.
- **Prompt 10**: telas Fundo 360, Sell side, Radar, Segmentos, e mapa por prédio com rota de visita.
- **Prompt 11**: CI, reorganização de testes e documentos por domínio, checagem automática dos números citados, Playwright das novas jornadas.
- **Geocodificação**: completar os prédios restantes numa execução online sem `--offline`.

