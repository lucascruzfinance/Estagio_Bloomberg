# Onda 2 de contas curadas

Proposta em `prompts_codex.md` (seção 5) e registrada em `data/reference/curated_wave2.yaml`. Cada CNPJ foi conferido nos cadastros da CVM; **todos os vínculos estão pendentes de revisão humana**. Números gerados do snapshot do universo.

Critérios: presença nos centros financeiros (prioridade Faria Lima), relevância por PL e número de fundos abertos, diversidade de estratégia e de tipo de instituição, presença na planilha de networking e evidência pública disponível.

| Conta | Lado | Segmento | Centro | PL gestão (Informe Diário) | Classes ativas / abertas | Fundos administrados | Ativo do conglomerado (IF.data) |
|---|---|---|---|---:|---:|---:|---:|
| Itaú Asset Management | buy side | Asset de banco (multiativo) | Faria Lima | R$ 1.277,9 bi | 3.488 / 505 | 0 | — |
| XP Asset Management | buy side | Plataforma multiestratégia (FI, FII, FIDC) | JK / Vila Olímpia | R$ 161,6 bi | 803 / 181 | 0 | — |
| Santander Asset Management | buy side | Asset de banco global | JK / Vila Olímpia | R$ 379,6 bi | 573 / 125 | 0 | — |
| Safra Asset Management | buy side | Asset de banco (família de fundos) | Paulista | R$ 106,8 bi | 662 / 79 | 983 | R$ 273,6 bi |
| UBS Asset Management Brasil | buy side | Asset global | Faria Lima | R$ 61,4 bi | 686 / 64 | 744 | R$ 15,6 bi |
| BNP Paribas Asset Management Brasil | buy side | Asset global | JK / Vila Olímpia | R$ 73,5 bi | 166 / 50 | 0 | — |
| Absolute Investimentos | buy side | Macro e crédito independente | JK / Vila Olímpia | R$ 52,4 bi | 185 / 63 | 0 | — |
| Genoa Capital | buy side | Macro independente | JK / Vila Olímpia | R$ 20,3 bi | 81 / 17 | 0 | — |
| Legacy Capital | buy side | Macro independente | Faria Lima | R$ 15,4 bi | 107 / 31 | 0 | — |
| Capitânia | buy side | Crédito privado, FII e alternativos | Faria Lima | R$ 9,0 bi | 103 / 28 | 0 | — |
| Vinland Capital | buy side | Crédito e macro | JK / Vila Olímpia | R$ 19,9 bi | 114 / 39 | 0 | — |
| Quadra Capital | buy side | Crédito estruturado e FIDC | JK / Vila Olímpia | R$ 3,3 bi | 35 / 0 | 0 | — |
| Guepardo Investimentos | buy side | Ações fundamentalista | Faria Lima | R$ 6,1 bi | 28 / 8 | 0 | — |
| Giant Steps Capital | buy side | Quant | Faria Lima | R$ 0,5 bi | 28 / 7 | 0 | — |
| Opportunity | buy side | Ações e macro (RJ) | Leblon / Ipanema (RJ) | R$ 159,8 bi | 83 / 28 | 0 | — |
| ARX Investimentos | buy side | Multiestratégia (RJ) | Leblon / Ipanema (RJ) | R$ 47,5 bi | 96 / 42 | 0 | — |
| Dynamo | buy side | Ações long only (RJ) | Leblon / Ipanema (RJ) | R$ 20,8 bi | 15 / 11 | 15 | — |
| Truxt Investimentos | buy side | Macro (RJ) | Leblon / Ipanema (RJ) | R$ 2,5 bi | 71 / 20 | 0 | — |
| Banco Santander (Brasil) | sell side | Banco múltiplo por mesa | JK / Vila Olímpia | R$ 57,3 bi | 513 / 18 | 1.018 | R$ 1.314,9 bi |
| Bradesco BBI | sell side | Banco de investimento e corretora | Osasco | R$ 1.004,1 bi | 1.998 / 297 | 1.769 | R$ 2.015,2 bi |
| Banco Safra | sell side | Banco múltiplo por mesa | Paulista | R$ 73,3 bi | 167 / 32 | 58 | R$ 273,6 bi |
| XP Investimentos (corretora e banco) | sell side | Corretora e banco | Botafogo (RJ) | — | 0 / 0 | 1.236 | R$ 305,3 bi |
| BR Partners | sell side | Banco de investimento boutique | Faria Lima | R$ 0,7 bi | 1 / 0 | 0 | R$ 18,2 bi |
| BNY Mellon (administração e custódia) | sell side | Administrador fiduciário e custodiante | Centro (RJ) | — | 0 / 0 | 1.778 | R$ 1,1 bi |

PL de gestão: classes não FIC no Informe Diário de 01/10/2026. Ativo do conglomerado: IF.data 06/2026.

## Entidades e evidência

### Itaú Asset Management

Uma das maiores gestoras do país pelo PL no registro da CVM; separa o buy side do Itaú BBA, que segue no piloto como banco por mesa.

- `40.430.971/0001-96` ITAU UNIBANCO ASSET MANAGEMENT LTDA. — primary_manager; Faria Lima; Itaú Unibanco Asset Management Ltda., Av. Brig. Faria Lima 3500 (cad_adm_cart).

### XP Asset Management

Família de gestoras do grupo XP na JK; ações, macro, crédito, imobiliário e alocação.

- `16.789.525/0001-98` XP VISTA ASSET MANAGEMENT LTDA. — primary_manager; JK / Vila Olímpia; XP Vista Asset Management Ltda., Av. Pres. Juscelino Kubitschek (cad_adm_cart).
- `37.918.829/0001-88` XP ALLOCATION ASSET MANAGEMENT LTDA. — affiliate_manager; JK / Vila Olímpia; XP Allocation Asset Management Ltda., mesmo logradouro (JK).
- `07.625.200/0001-89` XP GESTÃO DE RECURSOS LTDA — affiliate_manager; JK / Vila Olímpia; XP Gestão de Recursos Ltda., mesmo logradouro (JK).
- `15.289.957/0001-77` XP ADVISORY GESTAO DE RECURSOS LTDA — affiliate_manager; JK / Vila Olímpia; XP Advisory Gestão de Recursos Ltda., mesmo logradouro (JK).

### Santander Asset Management

Braço de gestão de banco global na JK; conta separada do Banco Santander (sell side).

- `10.231.177/0001-52` SANTANDER BRASIL GESTÃO DE RECURSOS LTDA — primary_manager; JK / Vila Olímpia; Santander Brasil Gestão de Recursos Ltda., Av. Pres. Juscelino Kubitschek (cad_adm_cart).

### Safra Asset Management

Família de fundos grande na Paulista; gestora e administradora no mesmo CNPJ.

- `65.913.436/0001-17` SAFRA ASSET CORRETORA DE TÍTULOS E VALORES MOBILIÁRIOS S.A. — primary_manager; Paulista; Safra Asset Corretora de Títulos e Valores Mobiliários S.A., Av. Paulista 2100 (cad_adm_cart, gestor e administrador).

### UBS Asset Management Brasil

Gestora global na Faria Lima; a corretora do grupo é administradora fiduciária.

- `11.519.438/0001-05` UBS BRASIL ADMINISTRADORA DE VALORES MOBILIÁRIOS LTDA. — primary_manager; Faria Lima; UBS Brasil Administradora de Valores Mobiliários Ltda., Av. Brig. Faria Lima 4440 (cad_adm_cart, gestor).
- `61.809.182/0001-30` UBS (BRASIL) CORRETORA DE VALORES S.A — affiliate_manager; JK / Vila Olímpia; UBS (Brasil) Corretora de Valores S.A., administradora fiduciária (cad_adm_cart); confirmar se pertence à mesma conta.

### BNP Paribas Asset Management Brasil

Gestora global de renda fixa e multimercado na JK.

- `02.562.663/0001-25` BNP PARIBAS ASSET MANAGEMENT BRASIL LTDA — primary_manager; JK / Vila Olímpia; BNP Paribas Asset Management Brasil Ltda., Av. Pres. Juscelino Kubitschek (cad_adm_cart).

### Absolute Investimentos

PL elevado entre as gestoras independentes no registro da CVM; macro e crédito privado.

- `17.285.755/0001-82` ABSOLUTE GESTAO DE INVESTIMENTOS LTDA — primary_manager; JK / Vila Olímpia; Absolute Gestão de Investimentos Ltda., Rua Iguatemi 151 (cad_adm_cart).
- `47.243.769/0001-02` ABSOLUTE CRÉDITO GESTÃO DE INVESTIMENTOS LTDA. — affiliate_manager; JK / Vila Olímpia; Absolute Crédito Gestão de Investimentos Ltda., mesmo prédio (Rua Iguatemi 151).
- `14.351.454/0001-11` ABSOLUTE DHAMA GESTÃO DE INVESTIMENTOS LTDA — affiliate_manager; JK / Vila Olímpia; Absolute Dhama Gestão de Investimentos Ltda., mesmo prédio (Rua Iguatemi 151).

### Genoa Capital

Gestora macro independente na JK.

- `34.276.448/0001-54` GENOA CAPITAL GESTORA DE RECURSOS LTDA — primary_manager; JK / Vila Olímpia; Genoa Capital Gestora de Recursos Ltda., Av. Juscelino Kubitschek 1600 (cad_adm_cart).

### Legacy Capital

Gestora macro independente na Faria Lima.

- `28.674.641/0001-40` LEGACY CAPITAL GESTORA DE RECURSOS LTDA. — primary_manager; Faria Lima; Legacy Capital Gestora de Recursos Ltda., Av. Brig. Faria Lima 4221 (cad_adm_cart).

### Capitânia

Crédito privado e imobiliário na Faria Lima; precificação de crédito é workflow central.

- `41.793.345/0001-27` CAPITANIA CAPITAL S.A. — primary_manager; Faria Lima; Capitania Capital S.A., Av. Brig. Faria Lima (cad_adm_cart).
- `04.274.010/0001-76` CAPITÂNIA INVEST S/A — affiliate_manager; Faria Lima; Capitânia Invest S/A, Av. Brig. Faria Lima (cad_adm_cart).
- `41.475.648/0001-00` CAPITÂNIA ALTERNATIVES S/A — affiliate_manager; Faria Lima; Capitânia Alternatives S/A, Av. Brig. Faria Lima, Torre Norte, 3º andar.
- `41.777.833/0001-40` CAPITANIA PREV S.A. — affiliate_manager; Faria Lima; Capitania Prev S.A., mesmo endereço (Torre Norte, 3º andar).
- `30.949.716/0001-09` CAPITÂNIA HBC CONSULTORIA E GESTÃO S.A. — affiliate_manager; Faria Lima; Capitânia HBC Consultoria e Gestão S.A., Av. Brig. Faria Lima 1485.
- `66.266.698/0001-08` Capitânia Special Situations Ltda. — affiliate_manager; Faria Lima; Capitânia Special Situations Ltda., Av. Brig. Faria Lima.

### Vinland Capital

Crédito privado e macro; três entidades com a mesma marca no Itaim.

- `07.341.777/0001-69` VINLAND CAPITAL MANAGEMENT GESTORA DE RECURSOS LTDA. — primary_manager; JK / Vila Olímpia; Vinland Capital Management Gestora de Recursos Ltda., Rua Amauri 255 (cad_adm_cart).
- `28.541.110/0001-80` VINLAND CAPITAL MANAGEMENT II GESTORA DE RECURSOS LTDA — affiliate_manager; JK / Vila Olímpia; Vinland Capital Management II Gestora de Recursos Ltda., Rua Amauri 255.
- `31.846.872/0001-07` VINLAND CAPITAL MANAGEMENT CRÉDITO PRIVADO GESTORA DE RECURSOS LTDA. — affiliate_manager; JK / Vila Olímpia; Vinland Capital Management Crédito Privado Gestora de Recursos Ltda., Rua Jerônimo da Veiga 45.

### Quadra Capital

Crédito estruturado com FIDC; precificação e dados de crédito.

- `17.707.098/0001-14` QUADRA GESTÃO DE RECURSOS S.A. — primary_manager; JK / Vila Olímpia; Quadra Gestão de Recursos S.A., Rua Joaquim Floriano 940 (cad_adm_cart).

### Guepardo Investimentos

Ações long only na Faria Lima; research e screening.

- `07.078.144/0001-00` GUEPARDO INVESTIMENTOS LTDA — primary_manager; Faria Lima; Guepardo Investimentos Ltda., Av. Brig. Faria Lima 3015 (cad_adm_cart).

### Giant Steps Capital

Gestora quantitativa na Faria Lima; dados em volume e API.

- `17.021.922/0001-88` GIANT STEPS CAPITAL INVESTIMENTOS — primary_manager; Faria Lima; Giant Steps Capital Investimentos, Av. Brig. Faria Lima 4300 (cad_adm_cart).

### Opportunity

Casa tradicional do Leblon com ações, macro e private equity.

- `01.608.570/0001-21` OPPORTUNITY GESTORA DE RECURSOS LTDA — primary_manager; Leblon / Ipanema (RJ); Opportunity Gestora de Recursos Ltda., Rua Visconde de Pirajá 351 (cad_adm_cart).
- `05.395.883/0001-08` OPPORTUNITY ASSET ADMINISTRADORA DE RECURSOS DE TERCEIROS LTDA — affiliate_manager; Leblon / Ipanema (RJ); Opportunity Asset Administradora de Recursos de Terceiros Ltda., Rua Visconde de Pirajá.
- `09.647.907/0001-11` OPPORTUNITY GESTÃO DE INVESTIMENTOS E RECURSOS LTDA — affiliate_manager; Leblon / Ipanema (RJ); Opportunity Gestão de Investimentos e Recursos Ltda., Rua Visconde de Pirajá.
- `33.857.830/0001-99` OPPORTUNITY HDF ADMINISTRADORA DE RECURSOS LTDA. — affiliate_manager; Leblon / Ipanema (RJ); Opportunity HDF Administradora de Recursos Ltda., Rua Visconde de Pirajá 351.
- `03.151.030/0001-97` OPPORTUNITY PRIVATE EQUITY GESTORA DE RECURSOS LTDA — affiliate_manager; Leblon / Ipanema (RJ); Opportunity Private Equity Gestora de Recursos Ltda., Rua Visconde de Pirajá 351.

### ARX Investimentos

Multiestratégia no Leblon.

- `04.408.128/0001-40` ARX INVESTIMENTOS LTDA — primary_manager; Leblon / Ipanema (RJ); ARX Investimentos Ltda., Av. Borges de Medeiros 633 (cad_adm_cart).

### Dynamo

Ações long only no Leblon; research fundamentalista.

- `72.116.353/0001-62` DYNAMO ADMINISTRAÇÃO DE RECURSOS LTDA — primary_manager; Leblon / Ipanema (RJ); Dynamo Administração de Recursos Ltda., Av. Ataulfo de Paiva (cad_adm_cart).
- `07.880.927/0001-02` DYNAMO INTERNACIONAL GESTÃO DE RECURSOS LTDA. — affiliate_manager; Leblon / Ipanema (RJ); Dynamo Internacional Gestão de Recursos Ltda., mesmo logradouro.
- `03.215.562/0001-40` DYNAMO V. C . ADMINISTRADORA DE RECURSOS LTDA — affiliate_manager; Leblon / Ipanema (RJ); Dynamo V.C. Administradora de Recursos Ltda., mesmo logradouro.

### Truxt Investimentos

Macro no Leblon.

- `23.890.968/0001-36` TRUXT INVESTIMENTOS LTDA. — primary_manager; Leblon / Ipanema (RJ); Truxt Investimentos Ltda., Av. Ataulfo de Paiva 153 (cad_adm_cart).

### Banco Santander (Brasil)

Banco global na JK; tesouraria, sales & trading, câmbio, research e risco; corretoras do grupo.

- `90.400.888/0001-42` BANCO SANTANDER (BRASIL) S.A. — bank_entity; JK / Vila Olímpia; Banco Santander (Brasil) S.A., Av. Pres. Juscelino Kubitschek (cad_intermed); líder do conglomerado prudencial no IF.data.
- `51.014.223/0001-49` SANTANDER INSTITUCIONAL CORRETORA DE CÂMBIO VALORES MOBILIÁRIOS S.A. — bank_entity; JK / Vila Olímpia; Santander Institucional Corretora de Câmbio e Valores Mobiliários, Av. Pres. Juscelino Kubitschek (cad_intermed).
- `29.162.769/0001-98` SANTANDER CORRETORA DE TÍTULOS E VALORES MOBILIARIOS S/A — bank_entity; Centro (SP); Santander Corretora de Títulos e Valores Mobiliários S/A, Rua Boa Vista 263 (cad_intermed).
- `03.502.968/0001-04` SANTANDER DISTRIBUIDORA DE TÍTULOS E VALORES MOBILIÁRIOS S.A. — bank_entity; Berrini / Chucri Zaidan; Santander Distribuidora de Títulos e Valores Mobiliários S.A. (cad_intermed).

### Bradesco BBI

Banco de investimento do Bradesco (Osasco) e corretora do grupo na JK.

- `06.271.464/0001-19` BANCO BRADESCO BBI S.A. — bank_entity; Osasco; Banco Bradesco BBI S.A., Núcleo Cidade de Deus, Osasco (cad_intermed); conglomerado Bradesco no IF.data.
- `61.855.045/0001-32` BRADESCO S/A CTVM — bank_entity; JK / Vila Olímpia; Bradesco S/A CTVM, Av. Pres. Juscelino Kubitschek (cad_intermed).
- `60.746.948/0001-12` BANCO BRADESCO S.A. — bank_entity; Osasco; Banco Bradesco S.A., Núcleo Cidade de Deus, Osasco (cad_intermed); líder do conglomerado.

### Banco Safra

Tesouraria e câmbio na Paulista; conta separada da Safra Asset.

- `58.160.789/0001-28` BANCO SAFRA S/A — bank_entity; Paulista; Banco Safra S/A, Av. Paulista 2100 (cad_intermed); líder do conglomerado prudencial no IF.data.
- `03.017.677/0001-20` BANCO J. SAFRA S.A. — bank_entity; Paulista; Banco J. Safra S.A., Av. Paulista 2150 (cad_intermed); mesmo conglomerado no IF.data.
- `01.638.542/0001-57` SAFRA DISTRIBUIDORA DE TÍTULOS E VALORES MOBILIÁRIOS LTDA. — bank_entity; Paulista; Safra Distribuidora de Títulos e Valores Mobiliários Ltda., Av. Paulista 2100 (cad_intermed).

### XP Investimentos (corretora e banco)

Corretora e banco com sede em Botafogo; execução, distribuição e research.

- `02.332.886/0001-04` XP INVESTIMENTOS CCTVM S.A. — bank_entity; Botafogo (RJ); XP Investimentos CCTVM S.A., Praia de Botafogo 501 (cad_intermed).
- `33.264.668/0001-03` BANCO XP S.A. — bank_entity; Botafogo (RJ); Banco XP S.A., Praia de Botafogo 501 (cad_intermed); líder do conglomerado prudencial XP no IF.data.
- `05.389.174/0001-01` XP SERVIÇOS FINANCEIROS DTVM Ltda. — bank_entity; Botafogo (RJ); XP Serviços Financeiros DTVM Ltda., Praia de Botafogo 501 (cad_intermed).
- `44.475.245/0001-40` XP DISTRIBUIDORA DE TÍTULOS E VALORES MOBILIÁRIOS LTDA. — bank_entity; Botafogo (RJ); XP Distribuidora de Títulos e Valores Mobiliários Ltda., Praia de Botafogo 501 (cad_intermed).

### BR Partners

Banco de investimento independente na Faria Lima 3732.

- `13.220.493/0001-17` BR PARTNERS BANCO DE INVESTIMENTO S.A. — bank_entity; Faria Lima; BR Partners Banco de Investimento S.A., Av. Brig. Faria Lima 3732 (cad_intermed); conglomerado próprio no IF.data.

### BNY Mellon (administração e custódia)

Administrador fiduciário e custodiante de milhares de fundos; precificação e dados de referência.

- `02.201.501/0001-61` BNY MELLON SERVICOS FINANCEIROS DTVM S.A. — bank_entity; Centro (RJ); BNY Mellon Serviços Financeiros DTVM S.A., Av. República do Chile 330 (cad_intermed); administrador no registro de fundos.
- `42.272.526/0001-70` BNY MELLON BANCO S.A. — bank_entity; Centro (RJ); BNY Mellon Banco S.A., Av. República do Chile 330 (cad_intermed); líder do conglomerado no IF.data.

## Alternativas se alguma conta não passar na revisão

Atmos, Squadra, Kadima, AZ Quest, Perfin, Augme, Genial Institucional (Faria Lima 3400), ABC Brasil, Daycoval.
