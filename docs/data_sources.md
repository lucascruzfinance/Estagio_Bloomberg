# Catálogo de fontes

Status verificado na execução de 30/10/2026 do pipeline do universo. Todas as fontes são públicas; o conteúdo bruto fica em `data/raw/` (fora do git), imutável e endereçado por SHA-256, com manifesto.

| Fonte | Publicador | Licença / termos | Frequência | Defasagem | Campos usados | Uso | Status | Dados até |
|---|---|---|---|---|---|---|---|---|
| [Cadastro de Administradores de Carteira](https://dados.cvm.gov.br/dados/ADM_CART/CAD/DADOS/cad_adm_cart.zip) | CVM | Open Database License (ODbL) — Portal de Dados Abertos da CVM | diária | 1 dia | CNPJ, razão social, categoria, endereço, telefone, site, data de registro, diretores de gestão | universo buy side, radar, contas | ok | 29/10/2026 |
| [Cadastro de Intermediários](https://dados.cvm.gov.br/dados/INTERMED/CAD/DADOS/cad_intermed.zip) | CVM | Open Database License (ODbL) — Portal de Dados Abertos da CVM | diária | 1 dia | CNPJ, tipo de participante, endereço, controle acionário | universo sell side | ok | 30/10/2026 |
| [Registro de Fundos, Classes e Subclasses (RCVM 175)](https://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip) | CVM | Open Database License (ODbL) — Portal de Dados Abertos da CVM | diária | 1 dia | gestor, administrador, custodiante, classe, condomínio, exclusividade, FIC, PL do registro | classes, administradores | ok | 29/10/2026 |
| [Cadastro de Fundos — histórico (pré-RCVM 175)](https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi_hist.zip) | CVM | Open Database License (ODbL) — Portal de Dados Abertos da CVM | diária | 1 dia | mandatos de gestor por fundo (início e fim) | eventos de transferência | ok | 30/10/2026 |
| [Informe Diário de Fundos de Investimento](https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/) | CVM | Open Database License (ODbL) — Portal de Dados Abertos da CVM | diária, arquivo mensal | 1 a 2 dias úteis | cota, PL, captação, resgate, cotistas | séries diária e mensal, gestoras | ok | 10/2026 |
| [Composição e Diversificação das Aplicações (CDA)](https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS/) | CVM | Open Database License (ODbL) — Portal de Dados Abertos da CVM | mensal | 1 a 2 meses (posições confidenciais até 90 dias) | posição por ativo e PL | composição da carteira | ok | 09/2026 |
| [Perfil Mensal de Fundos](https://dados.cvm.gov.br/dados/FI/DOC/PERFIL_MENSAL/DADOS/) | CVM | Open Database License (ODbL) — Portal de Dados Abertos da CVM | mensal | 1 mês | cotistas por tipo, VaR, estresse, nocional de derivativos, liquidez | perfil do fundo | ok | 09/2026 |
| [Lâmina de Informações Essenciais](https://dados.cvm.gov.br/dados/FI/DOC/LAMINA/DADOS/) | CVM | Open Database License (ODbL) — Portal de Dados Abertos da CVM | mensal | 1 mês | taxas, limites, risco, benchmark | lâmina (fundos de varejo) | ok | 09/2026 |
| [IF.data — cadastro de instituições (Olinda)](https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/) | Banco Central do Brasil | Dados abertos do Banco Central do Brasil | trimestral | 3 a 4 meses | instituição, conglomerado prudencial, segmento, sede | grupos de bancos e sell side | ok | 06/2026 |
| [IF.data — valores por relatório (Olinda)](https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/) | Banco Central do Brasil | Dados abertos do Banco Central do Brasil | trimestral | 3 a 4 meses | resumo (ativo, TVM, crédito, captações, PL, lucro) e DRE selecionada | porte e mix dos bancos | ok | 06/2026 |
| [SGS — Sistema Gerenciador de Séries Temporais](https://api.bcb.gov.br/dados/serie/) | Banco Central do Brasil | Dados abertos do Banco Central do Brasil | diária (CDI, PTAX), mensal (IPCA) | 1 dia | CDI (12), IPCA (433), PTAX venda (1) | benchmarks | ok | 29/10/2026 |
| [Nominatim geocoding](https://nominatim.openstreetmap.org/search) | OpenStreetMap Foundation | ODbL 1.0 — dados © colaboradores do OpenStreetMap | sob demanda | — | coordenada e tipo do resultado | mapa por prédio | ok | — |

## Observações da última execução

- `bcb_ifdata_cadastro`: 202609: resposta vazia (período ainda não publicado)
- `bcb_ifdata_valores`: resumo: 202606, 202603, 202512, 202509, 202506; DRE: 202606; 202609: resposta vazia (período ainda não publicado)
- `bcb_sgs`: cdi: 794 pontos até 2026-10-29; ipca: 38 pontos até 2026-09-01; ptax_usd: 795 pontos até 2026-10-30
- `cvm_cad_fi_hist`: último evento no arquivo: 2026-10-29
- `cvm_cda`: 202610: offline and not cached
- `cvm_lamina`: 202610: offline and not cached
- `cvm_perfil_mensal`: 202610: offline and not cached
- `osm_nominatim`: 254/544 prédios com precisão de porta

## Fontes avaliadas e não usadas

| Fonte | Motivo |
|---|---|
| BCB SGS 7 (Ibovespa) | Série encerrada em 2019; ações são comparadas com a mediana dos pares. |
| API pública de vagas da Gupy | Respondeu HTTP 404 em 30/10/2026; vagas entram só por curadoria manual com URL e data. |
| ANBIMA (sandbox) | Dados fictícios: bloqueados no cache e no fetcher. |
| LinkedIn autenticado | Vedado (termos de uso e LGPD). |
| CVM FRE (companhias abertas) | Disponível; headcount dos bancos listados fica como extensão opcional. |

Regra de plausibilidade: fundo com PL acima de R$ 300 bi no registro é anomalia (hoje 3 fundos, cada um com cerca de R$ 16,7 trilhões, data de PL 14/08/2025) e não entra em somas.
