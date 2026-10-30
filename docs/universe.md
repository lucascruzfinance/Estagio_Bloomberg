# Universo de território: São Paulo e Rio de Janeiro

Gerado por `python -m networking_intel.universe.cli` em 30/10/2026 (universe-v1.0.0). Todas as contagens abaixo vêm do snapshot em `data/universe/`.

O universo reúne **toda** gestora ativa (cadastro de administradores de carteira da CVM), todo intermediário ativo (cadastro de intermediários da CVM: bancos, corretoras, distribuidoras, custodiantes, escrituradores, infraestrutura de mercado) e todo administrador fiduciário com fundos ativos, com sede nos municípios de São Paulo, Rio de Janeiro e Osasco. O vínculo é sempre por CNPJ exato; nome parecido só gera sugestão para revisão humana.

Três camadas de cobertura:

- **curada**: as 12 contas do piloto e as 24 da onda 2 (102 CNPJs), com vínculos pendentes de revisão humana;
- **radar**: gestoras registradas na CVM há no máximo 2 anos (casas novas, que montam mesa e contratam ferramentas);
- **universo**: todas as demais, automáticas.

## Panorama

| Medida | Valor |
|---|---:|
| Entidades no universo | 1.447 |
| Gestoras com classes ativas | 1.007 |
| Buy side / sell side | 1.228 / 219 |
| Camada curada / radar / universo | 102 / 174 / 1.171 |
| Grupos econômicos | 1.331 |
| Classes de fundos das gestoras do universo | 30.710 (5.226 abertas, não exclusivas e não FIC) |
| Instituições do IF.data em SP/RJ | 1.274 (período 06/2026) |
| Prédios geocodificados | 544 (254 com número de porta conferido) |

### Por tipo (uma entidade pode ter mais de um papel)

| Tipo | Entidades |
|---|---:|
| Gestora | 1.240 |
| Custodiante | 135 |
| Administrador fiduciário | 122 |
| Distribuidora | 84 |
| Escriturador | 68 |
| Banco múltiplo | 62 |
| Corretora | 49 |
| Banco de investimento | 10 |
| Infraestrutura de mercado | 9 |

### Por centro financeiro

| Centro | Gestoras | Sell side | Total | Geocodificadas |
|---|---:|---:|---:|---:|
| Faria Lima | 305 | 57 | 362 | 298 |
| JK / Vila Olímpia | 443 | 62 | 505 | 233 |
| Cidade Jardim / Jardins | 96 | 7 | 103 | 71 |
| Paulista | 39 | 30 | 69 | 66 |
| Berrini / Chucri Zaidan | 43 | 13 | 56 | 33 |
| Centro (SP) | 3 | 3 | 6 | 4 |
| Leblon / Ipanema (RJ) | 134 | 3 | 137 | 96 |
| Botafogo (RJ) | 21 | 9 | 30 | 15 |
| Centro (RJ) | 25 | 10 | 35 | 25 |
| Barra / São Conrado (RJ) | 29 | 6 | 35 | 26 |
| Osasco | 0 | 6 | 6 | 1 |
| Fora de SP/RJ (conta curada) | 1 | 0 | 1 | 1 |
| Outros bairros (RJ) | 7 | 0 | 7 | 0 |
| Outros bairros (SP) | 82 | 13 | 95 | 0 |

## 40 maiores grupos gestores por PL (Informe Diário, 01/10/2026)

PL somado das classes não FIC de cada gestora, com um valor por classe e dia (classe ou soma das subclasses). Inclui fundos exclusivos; não é AUM oficial do grupo. Captação líquida dos últimos 12 meses no mesmo recorte.

| # | Grupo | Centro principal | Camada | PL | Captação líquida 12m |
|---:|---|---|---|---:|---:|
| 1 | BB GESTÃO DE RECURSOS DTVM SA | Centro (RJ) | universo | R$ 2.021,4 bi | R$ 14,4 bi |
| 2 | Itaú Asset Management | Faria Lima | curada | R$ 1.277,9 bi | R$ -19,9 bi |
| 3 | Bradesco BBI | Osasco | curada | R$ 1.004,1 bi | R$ 20,2 bi |
| 4 | CAIXA DTVM | Paulista | universo | R$ 670,0 bi | R$ 31,7 bi |
| 5 | BTG Pactual | Botafogo (RJ) | curada | R$ 487,1 bi | R$ 60,1 bi |
| 6 | Santander Asset Management | JK / Vila Olímpia | curada | R$ 379,6 bi | R$ -19,0 bi |
| 7 | Sicredi Asset Management Ltda. | JK / Vila Olímpia | radar | R$ 203,3 bi | R$ 20,9 bi |
| 8 | XP Asset Management | JK / Vila Olímpia | curada | R$ 161,6 bi | R$ 9,1 bi |
| 9 | Opportunity | Leblon / Ipanema (RJ) | curada | R$ 159,8 bi | R$ 1,2 bi |
| 10 | Kinea Investimentos | JK / Vila Olímpia | curada | R$ 118,4 bi | R$ -2,3 bi |
| 11 | Safra Asset Management | Paulista | curada | R$ 106,8 bi | R$ 14,9 bi |
| 12 | ICATU VANGUARDA GESTÃO DE RECURSOS LTDA | Outros bairros (RJ) | universo | R$ 76,9 bi | R$ 10,7 bi |
| 13 | BNP Paribas Asset Management Brasil | JK / Vila Olímpia | curada | R$ 73,5 bi | R$ 2,8 bi |
| 14 | Banco Safra | Paulista | curada | R$ 73,3 bi | R$ -1,9 bi |
| 15 | UBS Asset Management Brasil | Faria Lima | curada | R$ 61,4 bi | R$ -0,1 bi |
| 16 | Banco Santander (Brasil) | Berrini / Chucri Zaidan | curada | R$ 57,3 bi | R$ 5,8 bi |
| 17 | Franklin Templeton Brasil Ltda. | JK / Vila Olímpia | universo | R$ 53,1 bi | R$ -0,4 bi |
| 18 | Absolute Investimentos | JK / Vila Olímpia | curada | R$ 52,4 bi | R$ -18,7 bi |
| 19 | ARX Investimentos | Leblon / Ipanema (RJ) | curada | R$ 47,5 bi | R$ -4,5 bi |
| 20 | SUL AMÉRICA INVESTIMENTOS GESTORA DE RECURSOS S.A. | JK / Vila Olímpia | universo | R$ 47,0 bi | R$ 2,7 bi |
| 21 | BW GESTÃO DE INVESTIMENTOS LTDA. | Faria Lima | universo | R$ 44,9 bi | R$ 10,8 bi |
| 22 | BCO CLASSICO S.A. | Leblon / Ipanema (RJ) | universo | R$ 39,6 bi | R$ 0,2 bi |
| 23 | SUESTE CAPITAL | JK / Vila Olímpia | universo | R$ 38,6 bi | R$ 0,0 bi |
| 24 | MAPFRE INVESTIMENTOS | Berrini / Chucri Zaidan | universo | R$ 35,0 bi | R$ 9,2 bi |
| 25 | Sul América Gestão de Investimentos S.A. | JK / Vila Olímpia | radar | R$ 33,4 bi | R$ -2,4 bi |
| 26 | SPX Capital | Faria Lima | curada | R$ 33,2 bi | R$ -11,5 bi |
| 27 | OLIVEIRA TRUST SERVICER S/A | Barra / São Conrado (RJ) | universo | R$ 32,2 bi | R$ 11,7 bi |
| 28 | Kapitalo Investimentos | Faria Lima | curada | R$ 32,1 bi | R$ 0,2 bi |
| 29 | Vinci Compass | Faria Lima | curada | R$ 31,5 bi | R$ 1,1 bi |
| 30 | PORTO ASSET | Faria Lima | universo | R$ 24,3 bi | R$ -3,2 bi |
| 31 | WHG CAPITAL | Cidade Jardim / Jardins | universo | R$ 23,9 bi | R$ -0,3 bi |
| 32 | BRADESCO | Faria Lima | universo | R$ 23,0 bi | R$ -2,0 bi |
| 33 | REGIA CAPITAL LTDA | Leblon / Ipanema (RJ) | universo | R$ 22,9 bi | R$ 7,1 bi |
| 34 | SPARTA FUNDOS DE INVESTIMENTO | JK / Vila Olímpia | universo | R$ 22,1 bi | R$ 3,2 bi |
| 35 | LETO ASSET MANAGEMENT LTDA | Leblon / Ipanema (RJ) | universo | R$ 22,0 bi | R$ 1,5 bi |
| 36 | Dynamo | Leblon / Ipanema (RJ) | curada | R$ 20,8 bi | R$ -3,3 bi |
| 37 | MAG INVESTIMENTOS | Centro (RJ) | universo | R$ 20,4 bi | R$ 2,7 bi |
| 38 | Genoa Capital | JK / Vila Olímpia | curada | R$ 20,3 bi | R$ -2,1 bi |
| 39 | Vinland Capital | JK / Vila Olímpia | curada | R$ 19,9 bi | R$ -3,7 bi |
| 40 | G5 ADMINISTRADORA DE RECURSOS LTDA. | Faria Lima | universo | R$ 19,6 bi | R$ 2,0 bi |

## Sell side: 20 maiores conglomerados prudenciais com sede em SP/RJ (IF.data, 06/2026)

| # | Conglomerado | Sede | Ativo total |
|---:|---|---|---:|
| 1 | ITAU | São Paulo/SP | R$ 2.846,4 bi |
| 2 | BRADESCO | Osasco/SP | R$ 2.015,2 bi |
| 3 | SANTANDER | São Paulo/SP | R$ 1.314,9 bi |
| 4 | BNDES | Rio de Janeiro/RJ | R$ 1.058,0 bi |
| 5 | BTG PACTUAL | Rio de Janeiro/RJ | R$ 858,4 bi |
| 6 | NU PAGAMENTOS | São Paulo/SP | R$ 363,3 bi |
| 7 | XP | Rio de Janeiro/RJ | R$ 305,3 bi |
| 8 | SAFRA | São Paulo/SP | R$ 273,6 bi |
| 9 | BANCO C6 | São Paulo/SP | R$ 170,6 bi |
| 10 | CITIBANK | São Paulo/SP | R$ 169,1 bi |
| 11 | VOTORANTIM | São Paulo/SP | R$ 154,3 bi |
| 12 | MERCADO PAGO IP | Osasco/SP | R$ 125,0 bi |
| 13 | CIELO IP | Barueri/SP | R$ 115,1 bi |
| 14 | BCO DAYCOVAL S.A | São Paulo/SP | R$ 107,7 bi |
| 15 | JP MORGAN CHASE | São Paulo/SP | R$ 102,1 bi |
| 16 | PAGSEGURO | São Paulo/SP | R$ 77,1 bi |
| 17 | ABC-BRASIL | São Paulo/SP | R$ 69,6 bi |
| 18 | VOLKSWAGEN | São Paulo/SP | R$ 60,9 bi |
| 19 | BCO RABOBANK INTL BRASIL S.A. | São Paulo/SP | R$ 54,7 bi |
| 20 | STONE IP | São Paulo/SP | R$ 54,1 bi |

## Administradores fiduciários do universo (fundos ativos no registro da CVM)

Administrar fundos exige precificação diária, dados de referência e cadastro de ativos: é a ponte com dados corporativos (Data License, BVAL) para Banks and Brokers. PL do registro sem os fundos com valor implausível.

| # | Administrador | Centro | Fundos ativos | PL administrado |
|---:|---|---|---:|---:|
| 1 | BTG PACTUAL SERVIÇOS FINANCEIROS S/A DTVM | Botafogo (RJ) | 7.081 | R$ 1.198,6 bi |
| 2 | ITAU UNIBANCO S.A. | Outros bairros (SP) | 3.257 | R$ 1.710,0 bi |
| 3 | BEM - DISTRIBUIDORA DE TITULOS E VALORES MOBILIARIOS LTDA. | Osasco | 2.609 | R$ 671,2 bi |
| 4 | INTRAG DTVM LTDA. | Faria Lima | 2.360 | R$ 820,6 bi |
| 5 | BNY MELLON SERVICOS FINANCEIROS DTVM S.A. | Centro (RJ) | 1.778 | R$ 487,5 bi |
| 6 | BANCO BRADESCO S.A. | Osasco | 1.769 | R$ 1.280,0 bi |
| 7 | BB GESTAO DE RECURSOS DTVM S.A | Centro (RJ) | 1.370 | R$ 3.159,1 bi |
| 8 | BANCO DAYCOVAL S.A. | Paulista | 1.064 | R$ 91,3 bi |
| 9 | SANTANDER DISTRIBUIDORA DE TÍTULOS E VALORES MOBILIÁRIOS S.A. | Berrini / Chucri Zaidan | 1.018 | R$ 552,8 bi |
| 10 | XP INVESTIMENTOS CCTVM S.A. | Botafogo (RJ) | 1.003 | R$ 93,6 bi |
| 11 | SAFRA ASSET CORRETORA DE TÍTULOS E VALORES MOBILIÁRIOS S.A. | Paulista | 983 | R$ 203,0 bi |
| 12 | QI CORRETORA DE TÍTULOS E VALORES MOBILIÁRIOS S.A. | Cidade Jardim / Jardins | 955 | R$ 98,2 bi |
| 13 | UBS (BRASIL) CORRETORA DE VALORES S.A | JK / Vila Olímpia | 744 | R$ 118,3 bi |
| 14 | S3 CACEIS BRASIL DISTRIBUIDORA DE TITULOS E VALORES MOBILIARIOS S.A | Berrini / Chucri Zaidan | 587 | R$ 118,1 bi |
| 15 | VORTX DISTRIBUIDORA DE TITULOS E VALORES MOBILIARIOS LTDA. | Faria Lima | 520 | R$ 39,6 bi |

## Radar: 174 gestoras registradas nos últimos 2 anos

Por centro: JK / Vila Olímpia 68; Faria Lima 39; Cidade Jardim / Jardins 14; Outros bairros (SP) 14; Leblon / Ipanema (RJ) 12; Berrini / Chucri Zaidan 10; Barra / São Conrado (RJ) 6; Paulista 4; Botafogo (RJ) 3; Centro (RJ) 3; Outros bairros (RJ) 1.

| Registro CVM | Gestora | Centro | Classes ativas |
|---|---|---|---:|
| 27/10/2026 | Geia Capital Gestão de Investimentos e Consultoria Ltda. | Berrini / Chucri Zaidan | 0 |
| 26/10/2026 | Ártico Capital Asset Management Ltda. | Faria Lima | 0 |
| 26/10/2026 | Strada LVNT Gestão de Recursos Ltda. | JK / Vila Olímpia | 0 |
| 22/10/2026 | Metric Gestão de Recursos Ltda. | JK / Vila Olímpia | 0 |
| 13/10/2026 | Tess Capital Gestora de Recursos Ltda. | Berrini / Chucri Zaidan | 0 |
| 09/10/2026 | Decade Asset Management Ltda. | Cidade Jardim / Jardins | 0 |
| 08/10/2026 | Morano Gestora de Recursos Ltda. | JK / Vila Olímpia | 0 |
| 30/09/2026 | VISLO CAPITAL LTDA. | JK / Vila Olímpia | 0 |
| 29/09/2026 | Ferox Capital Ltda. | JK / Vila Olímpia | 0 |
| 18/09/2026 | Árvore Capital Ltda. | Cidade Jardim / Jardins | 0 |
| 11/09/2026 | Pin Factory Investimentos Ltda. | Leblon / Ipanema (RJ) | 0 |
| 10/09/2026 | RJDI Real Estate Gestora de Recursos Ltda. | Botafogo (RJ) | 0 |
| 08/09/2026 | MLP (Brasil) Ltda. | Faria Lima | 0 |
| 03/09/2026 | Alpe Asset Gestão de Recursos Ltda. | Berrini / Chucri Zaidan | 0 |
| 02/09/2026 | WHG Portfolio Solutions Ltda. | Cidade Jardim / Jardins | 0 |
| 18/08/2026 | Glaux Capital Gestora de Recursos Ltda. | JK / Vila Olímpia | 0 |
| 18/08/2026 | Mata Investimentos Ltda. | Leblon / Ipanema (RJ) | 0 |
| 12/08/2026 | Aliança Partners Gestora de Recursos Ltda. | Faria Lima | 13 |
| 10/08/2026 | Simetrio Capital Gestão de Recursos Ltda. | Faria Lima | 0 |
| 10/08/2026 | Natsu Capital Gestora de Recursos Ltda. | Cidade Jardim / Jardins | 0 |
| 31/07/2026 | Kanoa Capital Ltda. | Faria Lima | 0 |
| 31/07/2026 | Amoreiras Capital Ltda. | Faria Lima | 0 |
| 24/07/2026 | Alinea Capital Ltda. | Cidade Jardim / Jardins | 0 |
| 22/07/2026 | Fulwood Capital Partners Gestora de Recursos Ltda. | JK / Vila Olímpia | 0 |
| 22/07/2026 | G5 Gestão de Recursos de Crédito Ltda. | Faria Lima | 0 |
| 06/07/2026 | G5 Partners Consultoria e Participações Ltda. | Faria Lima | 0 |
| 02/07/2026 | RBR Crédito Gestora de Recursos Ltda. | JK / Vila Olímpia | 1 |
| 02/07/2026 | Sol Tempus Capital Ltda. | Berrini / Chucri Zaidan | 0 |
| 01/07/2026 | Torino Gestora de Recursos Ltda. | JK / Vila Olímpia | 0 |
| 29/06/2026 | Vera Cruz Capital Management Ltda. | Cidade Jardim / Jardins | 0 |

## Séries de fundos

- Janela do Informe Diário: 10/2023 a 10/2026 (37 arquivos mensais).
- Mensal: 5.240 séries (classe/subclasse) abertas, não exclusivas e não FIC, 163.177 linhas.
- Diária: 1.571 séries das contas curadas com PL ≥ R$ 50,0 mi no último informe e informe nos últimos 45 dias, 1.036.609 linhas. Com o cache bruto, o pipeline gera a diária de qualquer classe.
- Por gestora: 25.009 linhas gestora × mês.
- Composição (CDA): 15.346 linhas; Perfil Mensal: 15.300; Lâmina: 354 (só fundos com lâmina).
- Histórico de gestores (cad_fi_hist): 22.580 eventos desde 01/10/2023.

Arquivos anteriores à adaptação à RCVM 175 informam por fundo; a classe única de um fundo adaptado mantém o CNPJ do fundo, e é assim que as séries se emendam.

## Qualidade e revisão

- Sugestões de grupo por marca pendentes de revisão: 122 (`data/review/group_suggestions.csv`; nunca aplicadas automaticamente).
- CNPJs curados ausentes dos cadastros: 0.
- Fundos com PL implausível no registro (excluídos das somas): 3; séries diárias acima do limite: 0.
- Entidades com coordenada: 869; prédios por precisão: address 254, none 175, street 112, unknown 3.
- Snapshot versionado: 35,3 MB.
