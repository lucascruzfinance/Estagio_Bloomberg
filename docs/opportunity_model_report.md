# Prompt 4 — Modelo explicável de oportunidade comercial

Modelo `opportunity-v1.0.0` · dados até 2026-10-27 · config SHA-256 `2b0ed4728f8c…`

> Apoio à preparação de contas. Não é probabilidade de compra nem recomendação automática de abordagem. Fit, timing e confiança são saídas separadas; a confiança nunca altera fit ou timing.

## Ranking do piloto

Pontos de 0 a 100. `ponto` usa só fatores com evidência; `mín-máx` mostra o intervalo se cada fator ausente valesse 0 ou 1. `~` = pontuação por premissa.

| # | Unidade | Faixa | Prioridade (mín-máx) | Fit (mín-máx) | Timing (mín-máx) | Cobertura timing | Confiança | Rank p05-p95 |
|---:|---|---|---|---|---|---:|---:|---|
| 1 | BTG Pactual — Wealth & Family Office | Prioridade agora | 78 (71-83) | 90 (90-90) | 60 (42-72) | 70% | 81 | 1-1 |
| 2 | BTG Pactual — Asset Management | Prioridade agora | 70 (62-74) | 72 (72-72) | 68 (48-78) | 70% | 80 | 2-3 |
| 3 | Portofino Gestão de Recursos | Prioridade agora | 67 (59-71) | 71 (71-71) | 60 (42-72) | 70% | 83 | 2-4 |
| 4 | Kinea Investimentos | Prioridade agora | 60 (53-65) | 63 (63-63) | 54 (38-68) | 70% | 84 | 3-7 |
| 5 | Kapitalo Investimentos | Desenvolver relacionamento | 58 (53-65) | 70 (70-70) | 40 (28-58) | 70% | 84 | 4-7 |
| 6 | Vinci Compass | Desenvolver relacionamento | 57 (52-64) | 64 (64-64) | 47 (33-63) | 70% | 79 | 5-7 |
| 7 | Verde Asset Management | Desenvolver relacionamento | 53 (49-61) | 64 (64-64) | 38 (27-57) | 70% | 86 | 4-9 |
| 8 | SPX Capital | Monitorar | 50 (45-57) | 53 (53-53) | 45 (32-62) | 70% | 79 | 7-11 |
| 9 | Jive Investments | Monitorar | 48 (43-55) | 53 (53-53) | 40 (28-58) | 70% | 77 | 7-11 |
| 10 | Ibiúna Investimentos | Monitorar | 47 (42-54) | 48 (48-48) | 45 (31-61) | 70% | 83 | 8-11 |
| 11 | Pátria Investimentos | Oportunidade tática | 45 (39-51) | 39 (39-39) | 55 (39-69) | 70% | 84 | 7-11 |
| 12 | Constellation Asset Management | Monitorar | 18 (18-30) | 30 (30-30) | 0 (0-30) | 70% | 83 | 12-12 |
| 13 | BTG Pactual — Sales & Trading e Tesouraria ~ | Fit alto — timing desconhecido | — (53-93) | 89 (89-89) | — (0-100) | 0% | 29 | fit 1-2 |
| 14 | Itaú BBA — Sales & Trading e Tesouraria ~ | Fit alto — timing desconhecido | — (53-93) | 89 (89-89) | — (0-100) | 0% | 26 | fit 2-3 |
| 15 | BTG Pactual — Market Data / Tecnologia ~ | Fit alto — timing desconhecido | — (46-86) | 77 (77-77) | — (0-100) | 0% | 29 | fit 4-6 |
| 16 | Itaú BBA — Market Data / Tecnologia ~ | Fit alto — timing desconhecido | — (46-86) | 77 (77-77) | — (0-100) | 0% | 26 | fit 5-7 |
| 17 | Itaú BBA — Investment Banking e Mercados ~ | Fit alto — timing desconhecido | — (41-81) | 68 (68-68) | — (0-100) | 0% | 26 | fit 8-11 |
| 18 | BTG Pactual — Risco e Compliance ~ | Fit alto — timing desconhecido | — (41-81) | 68 (68-68) | — (0-100) | 0% | 29 | fit 7-12 |
| 19 | Itaú BBA — Risco e Compliance ~ | Fit alto — timing desconhecido | — (41-81) | 68 (68-68) | — (0-100) | 0% | 26 | fit 8-13 |
| 20 | BTG Pactual — Research ~ | Fit alto — timing desconhecido | — (36-76) | 60 (60-60) | — (0-100) | 0% | 29 | fit 13-16 |
| 21 | Itaú BBA — Research ~ | Fit alto — timing desconhecido | — (36-76) | 60 (60-60) | — (0-100) | 0% | 26 | fit 14-17 |
| 22 | BTG Pactual — Investment Banking (ECM/DCM/M&A) ~ | Fit baixo — timing desconhecido | — (34-74) | 56 (56-56) | — (0-100) | 0% | 29 | fit 13-19 |

## Por que cada unidade está onde está

### BTG Pactual — Wealth & Family Office

Faixa **Prioridade agora** · fit 90 · timing 60 · confiança 81

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.82 | 24.6 | observed | Intensidade média de dados 0,87 em 473 estratégias próprias (abertas não-FIC). |
| fit: Amplitude de ativos | 0.86 | 17.1 | observed | 7 famílias de estratégia: Ações: 110, Crédito estruturado (FIDC): 4, Imobiliário: 3, Multimercado: 272, Previdência: 7, Private equity (FIP): 4, Renda fixa: 73. |
| fit: Atuação internacional | 1.00 | 15.0 | observed | 67,7% das estratégias próprias com mandato 100% exterior ou classificação exterior. |
| fit: Necessidade de dados/API | 0.98 | 14.8 | proxy | 1384 classes/subclasses não-FIC com cota diária (proxy de volume de dados operacionais). |
| fit: Potencial de usuários | 0.95 | 18.9 | proxy | PL não-FIC de R$ 203,5 bi como proxy de equipe (headcount não coletado). |
| timing: Lançamento de produtos | 1.00 | 35.7 | observed | 35 fundos abertos constituídos em 12 meses (mais 95 exclusivos, não pontuados). Ex.: ACCESS XP DEBÊNTURES INCENTIVADAS CDI FIF EM COTAS DE FUNDOS INCENTIVADOS DE INVEST EM INFRA RF; AMB ISENTO CDI FUNDO INCENTIVADO DE INVESTIMENTO FINANCEIRO EM INFRAESTRUTURA RENDA FIXA; ARAUCÁRIA TERCEIRO FUNDO DE INVESTIMENTO FINANCEIRO EM AÇÕES. |
| timing: Captação/resgates | 0.48 | 13.7 | observed | Captação líquida de R$ -1,6 bi (-0,9% do PL inicial; cobertura 90,5% do PL). |
| timing: Expansão | 0.00 | 0.0 | observed | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | 0.76 | 10.9 | observed | Excesso de retorno 12m ponderado por PL de 5,2% vs pares (peso limitado; retorno do fundo, não lucro da gestora). |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, PORT, BQuant, EMSX, BVAL, Data License, BQL (Bloomberg Query Language), AIM.

### BTG Pactual — Asset Management

Faixa **Prioridade agora** · fit 72 · timing 68 · confiança 80

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.51 | 15.3 | observed | Intensidade média de dados 0,66 em 505 estratégias próprias (abertas não-FIC). |
| fit: Amplitude de ativos | 1.00 | 20.0 | observed | 10 famílias de estratégia: Agro (FIAGRO): 20, Ações: 37, Cambial: 3, Crédito estruturado (FIDC): 71, Imobiliário: 77, Multimercado: 85, Outros: 1, Previdência: 30, Private equity (FIP): 105, Renda fixa: 76. |
| fit: Atuação internacional | 0.41 | 6.1 | observed | 12,3% das estratégias próprias com mandato 100% exterior ou classificação exterior. |
| fit: Necessidade de dados/API | 0.71 | 10.6 | proxy | 347 classes/subclasses não-FIC com cota diária (proxy de volume de dados operacionais). |
| fit: Potencial de usuários | 0.99 | 19.9 | proxy | PL não-FIC de R$ 284,8 bi como proxy de equipe (headcount não coletado). |
| timing: Lançamento de produtos | 1.00 | 35.7 | observed | 80 fundos abertos constituídos em 12 meses (mais 22 exclusivos, não pontuados). Ex.: AGRO GM FUNDO DE INVESTIMENTO NAS CADEIAS PRODUTIVAS DO AGRONEGÓCIO RESPONSABILIDADE LIMITADA; AGRO PARANÁ FRIVATTI INDUSTRIAL FI EM DIREITOS CREDITÓRIOS RESPONSABILIDADE LIMITADA; ALIANÇA FUNDO DE INVESTIMENTO EM DIREITOS CREDITÓRIOS. |
| timing: Captação/resgates | 0.69 | 19.8 | observed | Captação líquida de R$ 17,7 bi (7,7% do PL inicial; cobertura 86,5% do PL). |
| timing: Expansão | 0.00 | 0.0 | observed | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | 0.90 | 12.8 | observed | Excesso de retorno 12m ponderado por PL de 7,9% vs pares (peso limitado; retorno do fundo, não lucro da gestora). |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, BVAL, Data License, BQL (Bloomberg Query Language), PORT, BQuant, EMSX.

### Portofino Gestão de Recursos

Faixa **Prioridade agora** · fit 71 · timing 60 · confiança 83

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.84 | 25.3 | observed | Intensidade média de dados 0,89 em 54 estratégias próprias (abertas não-FIC). |
| fit: Amplitude de ativos | 0.57 | 11.4 | observed | 5 famílias de estratégia: Ações: 3, Crédito estruturado (FIDC): 1, Imobiliário: 5, Multimercado: 41, Renda fixa: 4. |
| fit: Atuação internacional | 1.00 | 15.0 | observed | 72,2% das estratégias próprias com mandato 100% exterior ou classificação exterior. |
| fit: Necessidade de dados/API | 0.54 | 8.0 | proxy | 147 classes/subclasses não-FIC com cota diária (proxy de volume de dados operacionais). |
| fit: Potencial de usuários | 0.57 | 11.4 | proxy | PL não-FIC de R$ 12,9 bi como proxy de equipe (headcount não coletado). |
| timing: Lançamento de produtos | 0.67 | 23.9 | observed | 9 fundos abertos constituídos em 12 meses (mais 18 exclusivos, não pontuados). Ex.: LATERES 95 FUNDO DE INVESTIMENTO FINANCEIRO MULTIMERCADO; SPECIALE 180 FEEDER FIF MULTIMERCADO CRÉDITO PRIVADO RESPONSABILIDADE LIMITADA; SPECIALE APM FUNDO DE INVESTIMENTO FINANCEIRO MULTIMERCADO CREDITO PRIVADO RESP LIMITADA. |
| timing: Captação/resgates | 0.53 | 15.2 | observed | Captação líquida de R$ 0,1 bi (1,2% do PL inicial; cobertura 82,5% do PL). |
| timing: Expansão | 0.50 | 10.7 | observed | 1 nova(s) entidade(s) CVM em 24 meses: Portofino Internacional Gestão de Recursos Ltda.. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | 0.70 | 10.0 | observed | Excesso de retorno 12m ponderado por PL de 4,0% vs pares (peso limitado; retorno do fundo, não lucro da gestora). |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, PORT, BQuant, EMSX, BVAL, Data License, AIM.

### Kinea Investimentos

Faixa **Prioridade agora** · fit 63 · timing 54 · confiança 84

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.42 | 12.5 | observed | Intensidade média de dados 0,59 em 135 estratégias próprias (abertas não-FIC). |
| fit: Amplitude de ativos | 1.00 | 20.0 | observed | 8 famílias de estratégia: Agro (FIAGRO): 3, Ações: 1, Crédito estruturado (FIDC): 1, Imobiliário: 25, Multimercado: 20, Previdência: 17, Private equity (FIP): 31, Renda fixa: 37. |
| fit: Atuação internacional | 0.20 | 3.0 | observed | 5,9% das estratégias próprias com mandato 100% exterior ou classificação exterior. |
| fit: Necessidade de dados/API | 0.69 | 10.3 | proxy | 313 classes/subclasses não-FIC com cota diária (proxy de volume de dados operacionais). |
| fit: Potencial de usuários | 0.87 | 17.5 | proxy | PL não-FIC de R$ 118,4 bi como proxy de equipe (headcount não coletado). |
| timing: Lançamento de produtos | 0.89 | 31.7 | observed | 20 fundos abertos constituídos em 12 meses (mais 20 exclusivos, não pontuados). Ex.: KINEA ATACAMA FUNDO DE INVESTIMENTO FINANCEIRO RENDA FIXA LONGO PRAZO RESP LIMITADA; KINEA CDI ABSOLUTO FUNDO DE INVESTIMENTO FINANCEIRO RENDA FIXA LP RESP LIMITADA; KINEA CRÉDITO ESTRUTURADO PREV FIF MULTIMERCADO CRÉDITO PRIVADO RESP LIMITADA. |
| timing: Captação/resgates | 0.40 | 11.4 | observed | Captação líquida de R$ -4,8 bi (-4,0% do PL inicial; cobertura 97,3% do PL). |
| timing: Expansão | 0.00 | 0.0 | observed | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | 0.76 | 10.9 | observed | Excesso de retorno 12m ponderado por PL de 5,2% vs pares (peso limitado; retorno do fundo, não lucro da gestora). |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, BVAL, Data License, BQL (Bloomberg Query Language).

### Kapitalo Investimentos

Faixa **Desenvolver relacionamento** · fit 70 · timing 40 · confiança 84

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.90 | 27.0 | observed | Intensidade média de dados 0,93 em 38 estratégias próprias (abertas não-FIC). |
| fit: Amplitude de ativos | 0.57 | 11.4 | observed | 5 famílias de estratégia: Ações: 2, Multimercado: 31, Previdência: 3, Private equity (FIP): 1, Renda fixa: 1. |
| fit: Atuação internacional | 0.88 | 13.2 | observed | 26,3% das estratégias próprias com mandato 100% exterior ou classificação exterior. |
| fit: Necessidade de dados/API | 0.30 | 4.5 | proxy | 45 classes/subclasses não-FIC com cota diária (proxy de volume de dados operacionais). |
| fit: Potencial de usuários | 0.71 | 14.3 | proxy | PL não-FIC de R$ 37,0 bi como proxy de equipe (headcount não coletado). |
| timing: Lançamento de produtos | 0.67 | 23.9 | observed | 9 fundos abertos constituídos em 12 meses (mais 0 exclusivos, não pontuados). Ex.: KAPITALO ALOCAÇÃO GLOBAL 60 FUNDO DE INVESTIMENTO FINANCEIRO MULTIMERCADO; KAPITALO INFRA CDI LOW DURATION FIC DE FUNDOS INCENTIVADOS-INFRA RF; KAPITALO INFRA CDI LOW DURATION MASTER FI INCENTIVADO INFRA RENDA FIXA. |
| timing: Captação/resgates | 0.43 | 12.3 | observed | Captação líquida de R$ -1,0 bi (-2,8% do PL inicial; cobertura 96,5% do PL). |
| timing: Expansão | 0.00 | 0.0 | observed | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | 0.28 | 4.0 | observed | Excesso de retorno 12m ponderado por PL de -4,4% vs pares (peso limitado; retorno do fundo, não lucro da gestora). |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, PORT, BQuant, EMSX, BQL (Bloomberg Query Language), AIM.

### Vinci Compass

Faixa **Desenvolver relacionamento** · fit 64 · timing 47 · confiança 79

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.56 | 16.7 | observed | Intensidade média de dados 0,69 em 185 estratégias próprias (abertas não-FIC). |
| fit: Amplitude de ativos | 1.00 | 20.0 | observed | 8 famílias de estratégia: Agro (FIAGRO): 7, Ações: 20, Crédito estruturado (FIDC): 20, Imobiliário: 18, Multimercado: 38, Previdência: 6, Private equity (FIP): 60, Renda fixa: 16. |
| fit: Atuação internacional | 0.29 | 4.3 | observed | 8,6% das estratégias próprias com mandato 100% exterior ou classificação exterior. |
| fit: Necessidade de dados/API | 0.63 | 9.4 | proxy | 234 classes/subclasses não-FIC com cota diária (proxy de volume de dados operacionais). |
| fit: Potencial de usuários | 0.69 | 13.8 | proxy | PL não-FIC de R$ 31,7 bi como proxy de equipe (headcount não coletado). |
| timing: Lançamento de produtos | 0.70 | 24.9 | observed | 10 fundos abertos constituídos em 12 meses (mais 19 exclusivos, não pontuados). Ex.: FBB FIA DIVIDENDOS FIF - CLASSE DE INVESTIMENTO EM AÇÕES - RESPONSABILIDADE LIMITADA; MONACO FIF - CLASSE DE INVESTIMENTO EM AÇÕES - RESPONSABILIDADE LIMITADA; MSV3 FUNDO DE INVESTIMENTO EM DIREITOS CREDITÓRIOS RECEBÍVEIS COMERCIAIS RESPONSABILIDADE LIMITADA. |
| timing: Captação/resgates | 0.44 | 12.5 | observed | Captação líquida de R$ -0,8 bi (-2,5% do PL inicial; cobertura 93,1% do PL). |
| timing: Expansão | 0.00 | 0.0 | observed | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | 0.65 | 9.2 | observed | Excesso de retorno 12m ponderado por PL de 2,9% vs pares (peso limitado; retorno do fundo, não lucro da gestora). |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, BVAL, Data License, BQL (Bloomberg Query Language).

### Verde Asset Management

Faixa **Desenvolver relacionamento** · fit 64 · timing 38 · confiança 86

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.65 | 19.5 | observed | Intensidade média de dados 0,75 em 42 estratégias próprias (abertas não-FIC). |
| fit: Amplitude de ativos | 0.71 | 14.3 | observed | 6 famílias de estratégia: Ações: 7, Crédito estruturado (FIDC): 4, Imobiliário: 1, Multimercado: 15, Previdência: 14, Renda fixa: 1. |
| fit: Atuação internacional | 0.95 | 14.3 | observed | 28,6% das estratégias próprias com mandato 100% exterior ou classificação exterior. |
| fit: Necessidade de dados/API | 0.29 | 4.3 | proxy | 42 classes/subclasses não-FIC com cota diária (proxy de volume de dados operacionais). |
| fit: Potencial de usuários | 0.56 | 11.2 | proxy | PL não-FIC de R$ 12,0 bi como proxy de equipe (headcount não coletado). |
| timing: Lançamento de produtos | 0.47 | 16.7 | observed | 4 fundos abertos constituídos em 12 meses (mais 2 exclusivos, não pontuados). Ex.: ATLANTIC C7 FUNDO DE INVESTIMENTO EM COTAS DE FUNDOS DE INVESTIMENTO FINANCEIRO - AÇÕES RESP LTDA; VERDE AM BETA 60 II FIF CIC EM AÇÕES RESP LIMITADA; VERDE AM MUNDI A AÇÕES GLOBAIS FUNDO DE INVESTIMENTO FINANCEIRO CIC DE AÇÕES RESP LIMITADA. |
| timing: Captação/resgates | 0.11 | 3.1 | observed | Captação líquida de R$ -2,2 bi (-15,7% do PL inicial; cobertura 100,0% do PL). |
| timing: Expansão | 0.50 | 10.7 | observed | 1 nova(s) entidade(s) CVM em 24 meses: VERDE ASSET AGRO E IMOBILIÁRIO LTDA. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | 0.54 | 7.7 | observed | Excesso de retorno 12m ponderado por PL de 0,8% vs pares (peso limitado; retorno do fundo, não lucro da gestora). |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, PORT, BQuant, EMSX, BVAL, Data License, AIM.

### SPX Capital

Faixa **Monitorar** · fit 53 · timing 45 · confiança 79

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.49 | 14.8 | observed | Intensidade média de dados 0,65 em 59 estratégias próprias (abertas não-FIC). |
| fit: Amplitude de ativos | 0.71 | 14.3 | observed | 6 famílias de estratégia: Ações: 3, Imobiliário: 10, Multimercado: 15, Previdência: 9, Private equity (FIP): 15, Renda fixa: 7. |
| fit: Atuação internacional | 0.40 | 5.9 | observed | 11,9% das estratégias próprias com mandato 100% exterior ou classificação exterior. |
| fit: Necessidade de dados/API | 0.29 | 4.3 | proxy | 42 classes/subclasses não-FIC com cota diária (proxy de volume de dados operacionais). |
| fit: Potencial de usuários | 0.70 | 14.0 | proxy | PL não-FIC de R$ 33,2 bi como proxy de equipe (headcount não coletado). |
| timing: Lançamento de produtos | 0.87 | 31.2 | observed | 19 fundos abertos constituídos em 12 meses (mais 2 exclusivos, não pontuados). Ex.: SPX CRÉDITO OPPORTUNA I PREVIDENCIÁRIO FIF MULTIMERCADO CRÉDITO PRIVADO RESP LIMITADA; SPX FALCON 2 ADVISORY FIF DA CLASSE DE INVESTIMENTO EM COTAS EM AÇÕES RESP LIMITADA; SPX FALCON 2 CARPA FIF CIC EM AÇÕES RESP LIMITADA. |
| timing: Captação/resgates | 0.00 | 0.0 | observed | Captação líquida de R$ -13,7 bi (-30,7% do PL inicial; cobertura 93,4% do PL). |
| timing: Expansão | 0.00 | 0.0 | observed | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | 1.00 | 14.3 | observed | Excesso de retorno 12m ponderado por PL de 10,1% vs pares (peso limitado; retorno do fundo, não lucro da gestora). |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, PORT, BQuant, EMSX, BQL (Bloomberg Query Language).

### Jive Investments

Faixa **Monitorar** · fit 53 · timing 40 · confiança 77

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.52 | 15.5 | observed | Intensidade média de dados 0,66 em 110 estratégias próprias (abertas não-FIC). |
| fit: Amplitude de ativos | 1.00 | 20.0 | observed | 9 famílias de estratégia: Agro (FIAGRO): 1, Ações: 1, Crédito estruturado (FIDC): 44, Imobiliário: 31, Multimercado: 19, Outros: 1, Previdência: 2, Private equity (FIP): 6, Renda fixa: 5. |
| fit: Atuação internacional | 0.18 | 2.7 | observed | 5,5% das estratégias próprias com mandato 100% exterior ou classificação exterior. |
| fit: Necessidade de dados/API | 0.24 | 3.6 | proxy | 33 classes/subclasses não-FIC com cota diária (proxy de volume de dados operacionais). |
| fit: Potencial de usuários | 0.55 | 11.0 | proxy | PL não-FIC de R$ 11,4 bi como proxy de equipe (headcount não coletado). |
| timing: Lançamento de produtos | 0.90 | 32.1 | observed | 21 fundos abertos constituídos em 12 meses (mais 3 exclusivos, não pontuados). Ex.: BELVEDERE FUNDO DE INVESTIMENTO IMOBILIÁRIO - RESPONSABILIDADE LIMITADA; CLASSE I DO BOSSANOVA LIQUIDEZ DE INVESTIMENTO RENDA FIXA CRÉDITO PRIVADORESPONSABILIDADE LIMITADA; DIFAL FUNDO DE INVESTIMENTO EM DIREITOS CREDITÓRIOS - RESPONSABILIDADE LIMITADA. |
| timing: Captação/resgates | 0.26 | 7.5 | observed | Captação líquida de R$ -1,0 bi (-9,6% do PL inicial; cobertura 81,0% do PL). |
| timing: Expansão | 0.00 | 0.0 | observed | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | 0.00 | 0.0 | observed | Excesso de retorno 12m ponderado por PL de -11,0% vs pares (peso limitado; retorno do fundo, não lucro da gestora). |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, BVAL, Data License, BQL (Bloomberg Query Language).

### Ibiúna Investimentos

Faixa **Monitorar** · fit 48 · timing 45 · confiança 83

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.61 | 18.2 | observed | Intensidade média de dados 0,72 em 29 estratégias próprias (abertas não-FIC). |
| fit: Amplitude de ativos | 0.43 | 8.6 | observed | 4 famílias de estratégia: Ações: 6, Multimercado: 8, Previdência: 8, Renda fixa: 7. |
| fit: Atuação internacional | 0.34 | 5.2 | observed | 10,3% das estratégias próprias com mandato 100% exterior ou classificação exterior. |
| fit: Necessidade de dados/API | 0.33 | 4.9 | proxy | 52 classes/subclasses não-FIC com cota diária (proxy de volume de dados operacionais). |
| fit: Potencial de usuários | 0.57 | 11.4 | proxy | PL não-FIC de R$ 13,1 bi como proxy de equipe (headcount não coletado). |
| timing: Lançamento de produtos | 0.64 | 22.9 | observed | 8 fundos abertos constituídos em 12 meses (mais 3 exclusivos, não pontuados). Ex.: IBIUNA CREDIT INFRA II FIF - CI RF INCENTIVADO DE INVESTIMENTO EM INFRA - RESP LIMITADA; IBIUNA CREDIT IPCA+ FIF - CI RF INCENTIVADO DE INVESTIMENTO EM INFRAESTRUTURA - RESP LIMITADA; IBIUNA EQUITIES A FIF - CLASSE DE INVESTIMENTO EM COTAS AÇÕES - RESPONSABILIDADE LIMITADA. |
| timing: Captação/resgates | 0.22 | 6.3 | observed | Captação líquida de R$ -1,5 bi (-11,1% do PL inicial; cobertura 90,6% do PL). |
| timing: Expansão | 0.50 | 10.7 | observed | 1 nova(s) entidade(s) CVM em 24 meses: IBIUNA PREVIDÊNCIA GESTÃO DE RECURSOS LTDA.. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | 0.35 | 4.9 | observed | Excesso de retorno 12m ponderado por PL de -3,1% vs pares (peso limitado; retorno do fundo, não lucro da gestora). |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, PORT, BQuant, EMSX.

### Pátria Investimentos

Faixa **Oportunidade tática** · fit 39 · timing 55 · confiança 84

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.32 | 9.6 | observed | Intensidade média de dados 0,52 em 117 estratégias próprias (abertas não-FIC). |
| fit: Amplitude de ativos | 1.00 | 20.0 | observed | 8 famílias de estratégia: Agro (FIAGRO): 2, Ações: 1, Crédito estruturado (FIDC): 8, Imobiliário: 45, Multimercado: 8, Previdência: 1, Private equity (FIP): 51, Renda fixa: 1. |
| fit: Atuação internacional | 0.09 | 1.3 | observed | 2,6% das estratégias próprias com mandato 100% exterior ou classificação exterior. |
| fit: Necessidade de dados/API | 0.04 | 0.5 | proxy | 12 classes/subclasses não-FIC com cota diária (proxy de volume de dados operacionais). |
| fit: Potencial de usuários | 0.37 | 7.5 | proxy | PL não-FIC de R$ 3,1 bi como proxy de equipe (headcount não coletado). |
| timing: Lançamento de produtos | 0.64 | 22.9 | observed | 8 fundos abertos constituídos em 12 meses (mais 1 exclusivos, não pontuados). Ex.: CTA III FUNDO DE INVESTIMENTO IMOBILIÁRIO - RESPONSABILIDADE LIMITADA; CTA IV FUNDO DE INVESTIMENTO IMOBILIÁRIO - RESPONSABILIDADE LIMITADA; FUNDO DE INVESTIMENTO IMOBILIÁRIO PATRIA CRÉDITO MULTIESTRATÉGIA CDI - RESPONSABILIDADE LIMITADA. |
| timing: Captação/resgates | 1.00 | 28.6 | observed | Captação líquida de R$ 0,8 bi (34,3% do PL inicial; cobertura 97,4% do PL). |
| timing: Expansão | 0.00 | 0.0 | observed | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | 0.27 | 3.9 | observed | Excesso de retorno 12m ponderado por PL de -4,6% vs pares (peso limitado; retorno do fundo, não lucro da gestora). |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, BVAL, Data License, BQL (Bloomberg Query Language).

### Constellation Asset Management

Faixa **Monitorar** · fit 30 · timing 0 · confiança 83

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.62 | 18.7 | observed | Intensidade média de dados 0,74 em 11 estratégias próprias (abertas não-FIC). |
| fit: Amplitude de ativos | 0.29 | 5.7 | observed | 3 famílias de estratégia: Ações: 7, Multimercado: 1, Previdência: 3. |
| fit: Atuação internacional | 0.00 | 0.0 | observed | 0,0% das estratégias próprias com mandato 100% exterior ou classificação exterior. |
| fit: Necessidade de dados/API | 0.11 | 1.6 | proxy | 17 classes/subclasses não-FIC com cota diária (proxy de volume de dados operacionais). |
| fit: Potencial de usuários | 0.22 | 4.4 | proxy | PL não-FIC de R$ 1,0 bi como proxy de equipe (headcount não coletado). |
| timing: Lançamento de produtos | 0.00 | 0.0 | observed | 0 fundos abertos constituídos em 12 meses (mais 1 exclusivos, não pontuados). Ex.: —. |
| timing: Captação/resgates | 0.00 | 0.0 | observed | Captação líquida de R$ -0,4 bi (-28,1% do PL inicial; cobertura 97,0% do PL). |
| timing: Expansão | 0.00 | 0.0 | observed | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | 0.00 | 0.0 | observed | Excesso de retorno 12m ponderado por PL de -11,9% vs pares (peso limitado; retorno do fundo, não lucro da gestora). |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, BQL (Bloomberg Query Language), PORT.

### BTG Pactual — Sales & Trading e Tesouraria

Faixa **Fit alto — timing desconhecido** · fit 89 · timing — · confiança 29

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.90 | 27.0 | assumption | Premissa editável para a mesa (0,90); sem evidência pública coletada. |
| fit: Amplitude de ativos | 0.90 | 18.0 | assumption | Premissa editável para a mesa (0,90); sem evidência pública coletada. |
| fit: Atuação internacional | 0.80 | 12.0 | assumption | Premissa editável para a mesa (0,80); sem evidência pública coletada. |
| fit: Necessidade de dados/API | 0.90 | 13.5 | assumption | Premissa editável para a mesa (0,90); sem evidência pública coletada. |
| fit: Potencial de usuários | 0.90 | 18.0 | assumption | Premissa editável para a mesa (0,90); sem evidência pública coletada. |
| timing: Lançamento de produtos | — | — | missing | Sem fundos mapeados a esta unidade; lançamentos não observáveis. |
| timing: Captação/resgates | — | — | missing | Cobertura de séries completas insuficiente para medir fluxos. |
| timing: Expansão | — | — | missing | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | — | — | missing | Retornos comparáveis cobrem pouco do PL; performance não avaliada. |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, B-PIPE, FXGO, EMSX, Data License.

### Itaú BBA — Sales & Trading e Tesouraria

Faixa **Fit alto — timing desconhecido** · fit 89 · timing — · confiança 26

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.90 | 27.0 | assumption | Premissa editável para a mesa (0,90); sem evidência pública coletada. |
| fit: Amplitude de ativos | 0.90 | 18.0 | assumption | Premissa editável para a mesa (0,90); sem evidência pública coletada. |
| fit: Atuação internacional | 0.80 | 12.0 | assumption | Premissa editável para a mesa (0,80); sem evidência pública coletada. |
| fit: Necessidade de dados/API | 0.90 | 13.5 | assumption | Premissa editável para a mesa (0,90); sem evidência pública coletada. |
| fit: Potencial de usuários | 0.90 | 18.0 | assumption | Premissa editável para a mesa (0,90); sem evidência pública coletada. |
| timing: Lançamento de produtos | — | — | missing | Sem fundos mapeados a esta unidade; lançamentos não observáveis. |
| timing: Captação/resgates | — | — | missing | Cobertura de séries completas insuficiente para medir fluxos. |
| timing: Expansão | — | — | missing | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | — | — | missing | Retornos comparáveis cobrem pouco do PL; performance não avaliada. |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, B-PIPE, FXGO, EMSX, Data License.

### BTG Pactual — Market Data / Tecnologia

Faixa **Fit alto — timing desconhecido** · fit 77 · timing — · confiança 29

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.70 | 21.0 | assumption | Premissa editável para a mesa (0,70); sem evidência pública coletada. |
| fit: Amplitude de ativos | 0.90 | 18.0 | assumption | Premissa editável para a mesa (0,90); sem evidência pública coletada. |
| fit: Atuação internacional | 0.60 | 9.0 | assumption | Premissa editável para a mesa (0,60); sem evidência pública coletada. |
| fit: Necessidade de dados/API | 1.00 | 15.0 | assumption | Premissa editável para a mesa (1,00); sem evidência pública coletada. |
| fit: Potencial de usuários | 0.70 | 14.0 | assumption | Premissa editável para a mesa (0,70); sem evidência pública coletada. |
| timing: Lançamento de produtos | — | — | missing | Sem fundos mapeados a esta unidade; lançamentos não observáveis. |
| timing: Captação/resgates | — | — | missing | Cobertura de séries completas insuficiente para medir fluxos. |
| timing: Expansão | — | — | missing | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | — | — | missing | Retornos comparáveis cobrem pouco do PL; performance não avaliada. |

Workflows/produtos a explorar (hipótese): Data License, B-PIPE, Enterprise Access Point.

### Itaú BBA — Market Data / Tecnologia

Faixa **Fit alto — timing desconhecido** · fit 77 · timing — · confiança 26

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.70 | 21.0 | assumption | Premissa editável para a mesa (0,70); sem evidência pública coletada. |
| fit: Amplitude de ativos | 0.90 | 18.0 | assumption | Premissa editável para a mesa (0,90); sem evidência pública coletada. |
| fit: Atuação internacional | 0.60 | 9.0 | assumption | Premissa editável para a mesa (0,60); sem evidência pública coletada. |
| fit: Necessidade de dados/API | 1.00 | 15.0 | assumption | Premissa editável para a mesa (1,00); sem evidência pública coletada. |
| fit: Potencial de usuários | 0.70 | 14.0 | assumption | Premissa editável para a mesa (0,70); sem evidência pública coletada. |
| timing: Lançamento de produtos | — | — | missing | Sem fundos mapeados a esta unidade; lançamentos não observáveis. |
| timing: Captação/resgates | — | — | missing | Cobertura de séries completas insuficiente para medir fluxos. |
| timing: Expansão | — | — | missing | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | — | — | missing | Retornos comparáveis cobrem pouco do PL; performance não avaliada. |

Workflows/produtos a explorar (hipótese): Data License, B-PIPE, Enterprise Access Point.

### Itaú BBA — Investment Banking e Mercados

Faixa **Fit alto — timing desconhecido** · fit 68 · timing — · confiança 26

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.70 | 21.0 | assumption | Premissa editável para a mesa (0,70); sem evidência pública coletada. |
| fit: Amplitude de ativos | 0.70 | 14.0 | assumption | Premissa editável para a mesa (0,70); sem evidência pública coletada. |
| fit: Atuação internacional | 0.70 | 10.5 | assumption | Premissa editável para a mesa (0,70); sem evidência pública coletada. |
| fit: Necessidade de dados/API | 0.60 | 9.0 | assumption | Premissa editável para a mesa (0,60); sem evidência pública coletada. |
| fit: Potencial de usuários | 0.70 | 14.0 | assumption | Premissa editável para a mesa (0,70); sem evidência pública coletada. |
| timing: Lançamento de produtos | — | — | missing | Sem fundos mapeados a esta unidade; lançamentos não observáveis. |
| timing: Captação/resgates | — | — | missing | Cobertura de séries completas insuficiente para medir fluxos. |
| timing: Expansão | — | — | missing | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | — | — | missing | Retornos comparáveis cobrem pouco do PL; performance não avaliada. |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, BQL (Bloomberg Query Language).

### BTG Pactual — Risco e Compliance

Faixa **Fit alto — timing desconhecido** · fit 68 · timing — · confiança 29

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.70 | 21.0 | assumption | Premissa editável para a mesa (0,70); sem evidência pública coletada. |
| fit: Amplitude de ativos | 0.80 | 16.0 | assumption | Premissa editável para a mesa (0,80); sem evidência pública coletada. |
| fit: Atuação internacional | 0.60 | 9.0 | assumption | Premissa editável para a mesa (0,60); sem evidência pública coletada. |
| fit: Necessidade de dados/API | 0.80 | 12.0 | assumption | Premissa editável para a mesa (0,80); sem evidência pública coletada. |
| fit: Potencial de usuários | 0.50 | 10.0 | assumption | Premissa editável para a mesa (0,50); sem evidência pública coletada. |
| timing: Lançamento de produtos | — | — | missing | Sem fundos mapeados a esta unidade; lançamentos não observáveis. |
| timing: Captação/resgates | — | — | missing | Cobertura de séries completas insuficiente para medir fluxos. |
| timing: Expansão | — | — | missing | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | — | — | missing | Retornos comparáveis cobrem pouco do PL; performance não avaliada. |

Workflows/produtos a explorar (hipótese): MARS, BVAL, Data License, Soluções de compliance.

### Itaú BBA — Risco e Compliance

Faixa **Fit alto — timing desconhecido** · fit 68 · timing — · confiança 26

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.70 | 21.0 | assumption | Premissa editável para a mesa (0,70); sem evidência pública coletada. |
| fit: Amplitude de ativos | 0.80 | 16.0 | assumption | Premissa editável para a mesa (0,80); sem evidência pública coletada. |
| fit: Atuação internacional | 0.60 | 9.0 | assumption | Premissa editável para a mesa (0,60); sem evidência pública coletada. |
| fit: Necessidade de dados/API | 0.80 | 12.0 | assumption | Premissa editável para a mesa (0,80); sem evidência pública coletada. |
| fit: Potencial de usuários | 0.50 | 10.0 | assumption | Premissa editável para a mesa (0,50); sem evidência pública coletada. |
| timing: Lançamento de produtos | — | — | missing | Sem fundos mapeados a esta unidade; lançamentos não observáveis. |
| timing: Captação/resgates | — | — | missing | Cobertura de séries completas insuficiente para medir fluxos. |
| timing: Expansão | — | — | missing | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | — | — | missing | Retornos comparáveis cobrem pouco do PL; performance não avaliada. |

Workflows/produtos a explorar (hipótese): MARS, BVAL, Data License, Soluções de compliance.

### BTG Pactual — Research

Faixa **Fit alto — timing desconhecido** · fit 60 · timing — · confiança 29

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.60 | 18.0 | assumption | Premissa editável para a mesa (0,60); sem evidência pública coletada. |
| fit: Amplitude de ativos | 0.70 | 14.0 | assumption | Premissa editável para a mesa (0,70); sem evidência pública coletada. |
| fit: Atuação internacional | 0.50 | 7.5 | assumption | Premissa editável para a mesa (0,50); sem evidência pública coletada. |
| fit: Necessidade de dados/API | 0.60 | 9.0 | assumption | Premissa editável para a mesa (0,60); sem evidência pública coletada. |
| fit: Potencial de usuários | 0.60 | 12.0 | assumption | Premissa editável para a mesa (0,60); sem evidência pública coletada. |
| timing: Lançamento de produtos | — | — | missing | Sem fundos mapeados a esta unidade; lançamentos não observáveis. |
| timing: Captação/resgates | — | — | missing | Cobertura de séries completas insuficiente para medir fluxos. |
| timing: Expansão | — | — | missing | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | — | — | missing | Retornos comparáveis cobrem pouco do PL; performance não avaliada. |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, BQuant, Data License.

### Itaú BBA — Research

Faixa **Fit alto — timing desconhecido** · fit 60 · timing — · confiança 26

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.60 | 18.0 | assumption | Premissa editável para a mesa (0,60); sem evidência pública coletada. |
| fit: Amplitude de ativos | 0.70 | 14.0 | assumption | Premissa editável para a mesa (0,70); sem evidência pública coletada. |
| fit: Atuação internacional | 0.50 | 7.5 | assumption | Premissa editável para a mesa (0,50); sem evidência pública coletada. |
| fit: Necessidade de dados/API | 0.60 | 9.0 | assumption | Premissa editável para a mesa (0,60); sem evidência pública coletada. |
| fit: Potencial de usuários | 0.60 | 12.0 | assumption | Premissa editável para a mesa (0,60); sem evidência pública coletada. |
| timing: Lançamento de produtos | — | — | missing | Sem fundos mapeados a esta unidade; lançamentos não observáveis. |
| timing: Captação/resgates | — | — | missing | Cobertura de séries completas insuficiente para medir fluxos. |
| timing: Expansão | — | — | missing | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | — | — | missing | Retornos comparáveis cobrem pouco do PL; performance não avaliada. |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, BQuant, Data License.

### BTG Pactual — Investment Banking (ECM/DCM/M&A)

Faixa **Fit baixo — timing desconhecido** · fit 56 · timing — · confiança 29

| Fator | Valor 0-1 | Pontos | Status | Explicação |
|---|---:|---:|---|---|
| fit: Complexidade e intensidade de dados do workflow | 0.60 | 18.0 | assumption | Premissa editável para a mesa (0,60); sem evidência pública coletada. |
| fit: Amplitude de ativos | 0.50 | 10.0 | assumption | Premissa editável para a mesa (0,50); sem evidência pública coletada. |
| fit: Atuação internacional | 0.70 | 10.5 | assumption | Premissa editável para a mesa (0,70); sem evidência pública coletada. |
| fit: Necessidade de dados/API | 0.40 | 6.0 | assumption | Premissa editável para a mesa (0,40); sem evidência pública coletada. |
| fit: Potencial de usuários | 0.60 | 12.0 | assumption | Premissa editável para a mesa (0,60); sem evidência pública coletada. |
| timing: Lançamento de produtos | — | — | missing | Sem fundos mapeados a esta unidade; lançamentos não observáveis. |
| timing: Captação/resgates | — | — | missing | Cobertura de séries completas insuficiente para medir fluxos. |
| timing: Expansão | — | — | missing | Nenhuma nova entidade regulada pela CVM em 24 meses. |
| timing: Contratações | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: M&A | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Mudanças operacionais | — | — | missing | Sem sinal curado com fonte; ausência de registro não é evidência de ausência. |
| timing: Performance relativa | — | — | missing | Retornos comparáveis cobrem pouco do PL; performance não avaliada. |

Workflows/produtos a explorar (hipótese): Bloomberg Terminal, BQL (Bloomberg Query Language).

## Sensibilidade dos pesos

- 1000 sorteios Dirichlet em torno dos pesos-base (concentração 20): Spearman médio 0.95, p05 0.87 contra o ranking-base de prioridade.
- Variação de ±50% em cada peso isolado (renormalizado): maior deslocamento de posição por unidade na coluna `max_rank_shift_oat_50pct` de `data/scored/sensitivity.csv`.

## Checagens contra rankings absurdos

Falhas são investigadas e documentadas; pesos não são ajustados para forçar o resultado esperado.

| Esperado maior | Esperado menor | Saída | Valores | Status | Racional | Fatores da falha |
|---|---|---|---|---|---|---|
| org-btg-pactual:asset-management | org-constellation | fit | 72 vs 30 | pass | Plataforma multiestratégia de grande porte vs boutique de ações de estratégia única. | — |
| org-kinea | org-constellation | fit | 63 vs 30 | pass | Gestora multiproduto com alternativos vs boutique de ações. | — |
| org-itau-bba:sales-trading-treasury | org-itau-bba:investment-banking-e-mercados | fit | 89 vs 68 | pass | Mesa de trading usa dados em tempo real e execução de forma mais intensa que banking. | — |
| org-spx-capital | org-portofino | fit | 53 vs 71 | fail | Macro multiestratégia global vs multi-family office. | Complexidade e intensidade de dados do workflow (+10.5 pts para o esperado menor); Atuação internacional (+9.1 pts para o esperado menor) |

## Pesos (editáveis em `config/scoring/opportunity_v1.yaml`)

| Grupo | Fator | Peso | Definição |
|---|---|---:|---|
| fit | Complexidade e intensidade de dados do workflow | 30% | Intensidade média de dados das estratégias próprias (classes abertas, não-FIC), pela tabela family_data_intensity. |
| fit | Amplitude de ativos | 20% | Número de famílias de estratégia distintas entre as estratégias próprias (abertas, não-FIC). |
| fit | Atuação internacional | 15% | Parcela das estratégias próprias que podem aplicar 100% no exterior ou são classificadas como exterior. |
| fit | Necessidade de dados/API | 15% | Classes/subclasses não-FIC com cota diária a precificar, controlar e reportar (proxy). |
| fit | Potencial de usuários | 20% | Escala do PL não-FIC como proxy de equipe de gestão, risco e research (headcount não coletado). |
| timing | Lançamento de produtos | 25% | Fundos abertos (não exclusivos) constituídos nos últimos 12 meses (data de constituição CVM); exclusivos são reportados à parte. |
| timing | Captação/resgates | 20% | Captação líquida 12m sobre o PL das classes com série completa. |
| timing | Expansão | 15% | Novas entidades reguladas pela CVM no grupo nos últimos 24 meses. |
| timing | Contratações | 15% | Sinais curados de contratação com fonte (data/reference/commercial_signals.csv). |
| timing | M&A | 10% | Sinais curados de fusões, aquisições ou parcerias com fonte. |
| timing | Mudanças operacionais | 5% | Sinais curados de troca de sistemas, administrador, custodiante ou regulação. |
| timing | Performance relativa | 10% | Excesso de retorno 12m ponderado por PL contra a mediana da mesma classificação CVM. |

Índice de prioridade = 60% fit + 40% timing, calculado só quando a cobertura de timing ≥ 40%.

## Limitações

- Não é probabilidade de compra: não existe variável-alvo histórica de oportunidades ou conversões; pesos são premissas especialistas editáveis e versionadas.
- Fit usa proxies regulatórios (classes, estratégias, PL); headcount, sistemas atuais e contratos vigentes com Bloomberg ou concorrentes não foram observados.
- 30% do peso de timing (contratações, M&A, mudanças operacionais) depende de sinais curados com fonte em data/reference/commercial_signals.csv, hoje vazio; o intervalo [mín, máx] mostra o efeito dessa lacuna.
- Mesas de bancos sem entidade CVM própria são pontuadas por premissa (marcadas '~'); servem para estruturar a conversa por área, não para comparar com gestoras observadas.
- Performance é retorno de fundos para o cotista, relativo aos pares da mesma classificação CVM dentro do piloto, com peso máximo de 10%; não é lucro da gestora.
- A CVM só enxerga veículos domiciliados no Brasil: fundos offshore (ex.: veículos globais de gestoras macro) não entram em amplitude, atuação internacional nem escala, o que subestima o fit de gestoras com operação global relevante fora do país.
- Em plataformas de wealth/family office, veículos de famílias não exclusivos ainda contam como estratégias; ali o fit mede escala da plataforma, não sofisticação de gestão.
- Ranking é um apoio à preparação de contas; a decisão de abordagem é do vendedor.
