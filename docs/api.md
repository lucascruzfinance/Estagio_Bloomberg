# API — referência gerada a partir do banco

Gerado por `scripts/document_api.py` contra o banco carregado; os exemplos são respostas reais truncadas. OpenAPI interativo em `/docs` (ambientes não produtivos).

## Como subir

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\uvicorn.exe networking_intel.api.app:create_app --factory --port 8000
```

## Convenções

- Somente leitura (`SET TRANSACTION READ ONLY`), timeout de consulta e de conexão.
- Erros `application/problem+json` (RFC 7807) com `request_id`; entrada inválida nunca é ecoada.
- `X-Request-ID` aceito (8-64 caracteres seguros) ou gerado; logs JSON sem query string nem IP.
- `ETag` + `Cache-Control: no-cache`: o cliente sempre revalida, então nova carga aparece na hora.
- Rate limit local por cliente (padrão 600/min) com `Retry-After`; `/health`, `/ready`, `/metrics` isentos.
- CORS restrito às origens configuradas e ao método GET; hosts confiáveis explícitos.

## Endpoints e exemplos reais

### Metadados e convenções

`GET /api/v1/meta` → 200

```json
{
  "api_version": "1.0.0",
  "data_mode": "live",
  "data_note": "Dados carregados pelo pipeline; atualize com o enriquecimento e a carga.",
  "model_version": "opportunity-v1.0.0",
  "score_as_of_date": "2026-10-27",
  "score_run_loaded_at": "2026-10-30T04:04:17.454307-03:00",
  "fund_reference_date": "2026-10-27",
  "disclaimer": "Apoio à preparação de contas: não é probabilidade de compra nem recomendação automática. Fit, timing e confiança são saídas separadas.",
  "limitations": [
    "Não é probabilidade de compra: não existe variável-alvo histórica de oportunidades ou conversões; pesos são premissas especialistas editáveis e versionadas.",
    "Fit usa proxies regulatórios (classes, estratégias, PL); headcount, sistemas atuais e contratos vigentes com Bloomberg ou concorrentes não foram observados.",
    "… +6 itens"
  ],
  "conventions": {
    "money": "BRL (reais), sem escala.",
    "returns": "Fração decimal (0.05 = 5%); retorno do fundo, não lucro da gestora.",
    "scores": "0-100; point=null quando não há evidência; lower/upper = faixa dos ausentes.",
    "dates": "ISO 8601; timestamps com fuso.",
    "null": "Não observado — nunca equivale a zero.",
    "coordinates": "WGS84 [longitude, latitude]; is_exact só com número de porta conferido."
  },
  "attributions": [
    "Fundos, gestores e endereços: CVM — Portal de Dados Abertos.",
    "Geocodificação: © OpenStreetMap contributors (ODbL), via Nominatim."
  ]
}
```

### Busca canônica

`GET /api/v1/search?q=kapitalo` → 200

```json
[
  {
    "account_id": "org-kapitalo",
    "canonical_name": "Kapitalo Investimentos",
    "institution_type": "gestora independente",
    "matched": "Kapitalo",
    "match_kind": "exact",
    "alias_kind": "raw_name"
  }
]
```

### Contas (ranking por prioridade)

`GET /api/v1/accounts?page_size=2` → 200

```json
{
  "data": [
    {
      "account_id": "org-btg-pactual",
      "canonical_name": "BTG Pactual",
      "legal_name": "BANCO BTG PACTUAL S/A",
      "cnpj": "30306294000145",
      "institution_type": "banco",
      "analysis_unit": "mesa/área",
      "strategy_profile": "banco universal, asset e investment banking",
      "headquarters": {
        "address": "AV BRIGADEIRO FARIA LIMA, 3477, 14º ANDAR, ITAIM BIBI, SÃO PAULO/SP, CEP 04538-133",
        "city": "SÃO PAULO",
        "state": "SP",
        "latitude": -23.5863292,
        "longitude": -46.6817127,
        "precision": "address",
        "is_exact": true
      },
      "best_unit_key": "org-btg-pactual:wealth-family-office",
      "best_rank": 1,
      "tier": "Prioridade agora",
      "priority": {
        "point": 78.39,
        "lower": 71.16,
        "upper": 83.16,
        "coverage": null
      },
      "fit": {
        "point": 90.48,
        "lower": 90.48,
        "upper": 90.48,
        "coverage": 1.0
      },
      "timing": {
        "point": 60.25,
        "lower": 42.18,
        "upper": 72.18,
        "coverage": 0.7
      },
      "confidence": 80.96,
      "units_scored": 7,
      "nav_brl_non_fic": 488283864303.59894,
      "net_flow_12m_brl": 16057332729.079992,
      "open_conflicts": 0
    },
    {
      "account_id": "org-portofino",
      "canonical_name": "Portofino Gestão de Recursos",
      "legal_name": "PORTOFINO GESTÃO DE RECURSOS LTDA.",
      "cnpj": "17590181000156",
      "institution_type": "multi-family office",
      "analysis_unit": "organização",
      "strategy_profile": "wealth e gestão patrimonial",
      "headquarters": {
        "address": "RUA LEOPOLDO COUTO MAGALHAES JUNIOR, 758, CJ 111 E 112, ITAIM BIBI, SÃO PAULO/SP, CEP 04542-000",
        "city": "SÃO PAULO",
        "state": "SP",
        "latitude": -23.5892049,
        "longitude": -46.6839228,
        "precision": "street",
        "is_exact": false
      },
      "best_unit_key": "org-portofino",
      "best_rank": 3,
      "tier": "Prioridade agora",
      "priority": {
        "point": 66.62,
        "lower": 59.45,
        "upper": 71.45,
        "coverage": null
      },
      "fit": {
        "point": 71.18,
        "lower": 71.18,
        "upper": 71.18,
        "coverage": 1.0
      },
      "timing": {
        "point": 59.78,
        "lower": 41.85,
        "upper": 71.85,
        "coverage": 0.7
      },
      "confidence": 82.68,
      "units_scored": 1,
      "nav_brl_non_fic": 12852623626.930004,
      "net_flow_12m_brl": 126984319.26999997,
      "open_conflicts": 0
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 12,
    "sort": "priority",
    "order": "desc"
  }
}
```

### Ranking explicável

`GET /api/v1/scores?page_size=2` → 200

```json
{
  "data": [
    {
      "rank": 1,
      "unit_key": "org-btg-pactual:wealth-family-office",
      "unit_name": "BTG Pactual — Wealth & Family Office",
      "account_id": "org-btg-pactual",
      "canonical_name": "BTG Pactual",
      "institution_type": "banco",
      "analysis_unit": "mesa/área",
      "evidence_mode": "observed",
      "tier": "Prioridade agora",
      "priority": {
        "point": 78.39,
        "lower": 71.16,
        "upper": 83.16,
        "coverage": null
      },
      "fit": {
        "point": 90.48,
        "lower": 90.48,
        "upper": 90.48,
        "coverage": 1.0
      },
      "fit_assumption_share": 0.0,
      "timing": {
        "point": 60.25,
        "lower": 42.18,
        "upper": 72.18,
        "coverage": 0.7
      },
      "confidence": 80.96,
      "top_positive": [
        "Lançamento de produtos: 35 fundos abertos constituídos em 12 meses (mais 95 exclusivos, não pontuados). Ex.: ACCESS XP DEBÊNTURES INCENTIVADAS CDI FIF EM COT…",
        "Complexidade e intensidade de dados do workflow: Intensidade média de dados 0,87 em 473 estratégias próprias (abertas não-FIC).",
        "… +1 itens"
      ],
      "top_negative": [
        "Expansão: Nenhuma nova entidade regulada pela CVM em 24 meses."
      ],
      "missing_factors": [
        "hiring",
        "m_and_a",
        "… +1 itens"
      ]
    },
    {
      "rank": 2,
      "unit_key": "org-btg-pactual:asset-management",
      "unit_name": "BTG Pactual — Asset Management",
      "account_id": "org-btg-pactual",
      "canonical_name": "BTG Pactual",
      "institution_type": "banco",
      "analysis_unit": "mesa/área",
      "evidence_mode": "observed",
      "tier": "Prioridade agora",
      "priority": {
        "point": 70.45,
        "lower": 62.25,
        "upper": 74.25,
        "coverage": null
      },
      "fit": {
        "point": 71.88,
        "lower": 71.88,
        "upper": 71.88,
        "coverage": 1.0
      },
      "fit_assumption_share": 0.0,
      "timing": {
        "point": 68.31,
        "lower": 47.81,
        "upper": 77.81,
        "coverage": 0.7
      },
      "confidence": 80.36,
      "top_positive": [
        "Lançamento de produtos: 80 fundos abertos constituídos em 12 meses (mais 22 exclusivos, não pontuados). Ex.: AGRO GM FUNDO DE INVESTIMENTO NAS CADEIAS PRODUT…",
        "Amplitude de ativos: 10 famílias de estratégia: Agro (FIAGRO): 20, Ações: 37, Cambial: 3, Crédito estruturado (FIDC): 71, Imobiliário: 77, Multimercado: 85, …",
        "… +1 itens"
      ],
      "top_negative": [
        "Expansão: Nenhuma nova entidade regulada pela CVM em 24 meses."
      ],
      "missing_factors": [
        "hiring",
        "m_and_a",
        "… +1 itens"
      ]
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 22,
    "sort": "rank",
    "order": "asc"
  }
}
```

### Explicação de uma unidade

`GET /api/v1/scores/org-verde-asset/explanation` → 200

```json
{
  "score": {
    "rank": 7,
    "unit_key": "org-verde-asset",
    "unit_name": "Verde Asset Management",
    "account_id": "org-verde-asset",
    "canonical_name": "Verde Asset Management",
    "institution_type": "gestora independente",
    "analysis_unit": "organização",
    "evidence_mode": "observed",
    "tier": "Desenvolver relacionamento",
    "priority": {
      "point": 53.42,
      "lower": 48.84,
      "upper": 60.84,
      "coverage": null
    },
    "fit": {
      "point": 63.56,
      "lower": 63.56,
      "upper": 63.56,
      "coverage": 1.0
    },
    "fit_assumption_share": 0.0,
    "timing": {
      "point": 38.21,
      "lower": 26.75,
      "upper": 56.75,
      "coverage": 0.7
    },
    "confidence": 86.11,
    "top_positive": [
      "Amplitude de ativos: 6 famílias de estratégia: Ações: 7, Crédito estruturado (FIDC): 4, Imobiliário: 1, Multimercado: 15, Previdência: 14, Renda fixa: 1.",
      "Atuação internacional: 28,6% das estratégias próprias com mandato 100% exterior ou classificação exterior."
    ],
    "top_negative": [
      "Necessidade de dados/API: 42 classes/subclasses não-FIC com cota diária (proxy de volume de dados operacionais).",
      "Captação/resgates: Captação líquida de R$ -2,2 bi (-15,7% do PL inicial; cobertura 100,0% do PL)."
    ],
    "missing_factors": [
      "hiring",
      "m_and_a",
      "… +1 itens"
    ]
  },
  "model_version": "opportunity-v1.0.0",
  "as_of_date": "2026-10-27",
  "factors": [
    {
      "key": "workflow_complexity",
      "group": "fit",
      "label": "Complexidade e intensidade de dados do workflow",
      "weight": 0.3,
      "value": 0.6496598639455786,
      "status": "observed",
      "contribution_points": 19.48979591836736,
      "explanation": "Intensidade média de dados 0,75 em 42 estratégias próprias (abertas não-FIC).",
      "evidence": [
        "CVM — Registro de Fundos/Classes; 42 estratégias próprias (abertas não-FIC) de 125 classes ativas (Ações: 7, Crédito estruturado (FIDC): 4, Imobiliário: 1, M…"
      ],
      "raw": {
        "basis": "abertas não-FIC",
        "data_intensity": 0.754761904761905
      }
    },
    {
      "key": "asset_breadth",
      "group": "fit",
      "label": "Amplitude de ativos",
      "weight": 0.2,
      "value": 0.7142857142857143,
      "status": "observed",
      "contribution_points": 14.285714285714286,
      "explanation": "6 famílias de estratégia: Ações: 7, Crédito estruturado (FIDC): 4, Imobiliário: 1, Multimercado: 15, Previdência: 14, Renda fixa: 1.",
      "evidence": [
        "CVM — Registro de Fundos/Classes; 42 estratégias próprias (abertas não-FIC) de 125 classes ativas (Ações: 7, Crédito estruturado (FIDC): 4, Imobiliário: 1, M…"
      ],
      "raw": {
        "families": {
          "Ações": 7,
          "Renda fixa": 1,
          "Imobiliário": 1,
          "Multimercado": 15,
          "Previdência": 14,
          "Crédito estruturado (FIDC)": 4
        }
      }
    },
    "… +10 itens"
  ],
  "reasons": [
    {
      "code": "FIT_ASSET_BREADTH_HIGH",
      "polarity": "+",
      "group": "fit",
      "factor": "asset_breadth",
      "text": "Amplitude de ativos: 6 famílias de estratégia: Ações: 7, Crédito estruturado (FIDC): 4, Imobiliário: 1, Multimercado: 15, Previdência: 14, Renda fixa: 1.",
      "points": 14.285714285714286
    },
    {
      "code": "FIT_INTERNATIONAL_HIGH",
      "polarity": "+",
      "group": "fit",
      "factor": "international",
      "text": "Atuação internacional: 28,6% das estratégias próprias com mandato 100% exterior ou classificação exterior.",
      "points": 14.285714285714285
    },
    "… +5 itens"
  ],
  "confidence_components": {
    "identity": 0.6,
    "conflicts": 1.0,
    "freshness": 1.0,
    "comparability": 0.9572649572649573,
    "evidence_coverage": 0.85
  },
  "products": [
    {
      "product_code": "TERMINAL",
      "product_name": "Bloomberg Terminal",
      "workflow": "Research, monitoramento de mercado, notícias e analytics multiativos",
      "rationale": "Macro/multimercado opera juros, câmbio e derivativos com risco multiativo. Crédito estruturado exige precificação independente e dados de referência. Alocaçã…",
      "basis": "evidence_rule",
      "fit_status": "candidate"
    },
    {
      "product_code": "PORT",
      "product_name": "PORT",
      "workflow": "Risco, atribuição de performance e análise de carteira",
      "rationale": "Macro/multimercado opera juros, câmbio e derivativos com risco multiativo.",
      "basis": "evidence_rule",
      "fit_status": "candidate"
    },
    "… +5 itens"
  ],
  "limitations": [
    "Não é probabilidade de compra: não existe variável-alvo histórica de oportunidades ou conversões; pesos são premissas especialistas editáveis e versionadas.",
    "Fit usa proxies regulatórios (classes, estratégias, PL); headcount, sistemas atuais e contratos vigentes com Bloomberg ou concorrentes não foram observados.",
    "… +6 itens"
  ],
  "sanity_checks": []
}
```

### Mesas de um banco

`GET /api/v1/business-units?account_id=org-itau-bba` → 200

```json
[
  {
    "unit_key": "org-itau-bba:enterprise-data",
    "account_id": "org-itau-bba",
    "name": "Market Data / Tecnologia",
    "mapping_status": "pending",
    "score": {
      "rank": 16,
      "unit_key": "org-itau-bba:enterprise-data",
      "unit_name": "Itaú BBA — Market Data / Tecnologia",
      "account_id": "org-itau-bba",
      "canonical_name": "Itaú BBA",
      "institution_type": "banco",
      "analysis_unit": "mesa/área",
      "evidence_mode": "assumption",
      "tier": "Fit alto — timing desconhecido",
      "priority": {
        "point": null,
        "lower": 46.2,
        "upper": 86.2,
        "coverage": null
      },
      "fit": {
        "point": 77.0,
        "lower": 77.0,
        "upper": 77.0,
        "coverage": 1.0
      },
      "fit_assumption_share": 1.0,
      "timing": {
        "point": null,
        "lower": 0.0,
        "upper": 100.0,
        "coverage": 0.0
      },
      "confidence": 26.25,
      "top_positive": [],
      "top_negative": [],
      "missing_factors": [
        "product_launches",
        "net_flows",
        "… +5 itens"
      ]
    }
  },
  {
    "unit_key": "org-itau-bba:investment-banking-e-mercados",
    "account_id": "org-itau-bba",
    "name": "Investment Banking e Mercados",
    "mapping_status": "source_stated",
    "score": {
      "rank": 17,
      "unit_key": "org-itau-bba:investment-banking-e-mercados",
      "unit_name": "Itaú BBA — Investment Banking e Mercados",
      "account_id": "org-itau-bba",
      "canonical_name": "Itaú BBA",
      "institution_type": "banco",
      "analysis_unit": "mesa/área",
      "evidence_mode": "assumption",
      "tier": "Fit alto — timing desconhecido",
      "priority": {
        "point": null,
        "lower": 41.1,
        "upper": 81.1,
        "coverage": null
      },
      "fit": {
        "point": 68.5,
        "lower": 68.5,
        "upper": 68.5,
        "coverage": 1.0
      },
      "fit_assumption_share": 1.0,
      "timing": {
        "point": null,
        "lower": 0.0,
        "upper": 100.0,
        "coverage": 0.0
      },
      "confidence": 26.25,
      "top_positive": [],
      "top_negative": [],
      "missing_factors": [
        "product_launches",
        "net_flows",
        "… +5 itens"
      ]
    }
  },
  "… +3 itens"
]
```

### Fundos com métricas

`GET /api/v1/funds?account_id=org-verde-asset&with_metrics=true&page_size=1` → 200

```json
{
  "data": [
    {
      "class_cnpj": "07455507000189",
      "subclass_id": "",
      "fund_cnpj": "07455507000189",
      "name": "VERDE MASTER FUNDO DE INVESTIMENTO FINANCEIRO MULTIMERCADO RESPONSABILIDADE LIMITADA",
      "fund_name": "VERDE MASTER FUNDO DE INVESTIMENTO FINANCEIRO MULTIMERCADO RESPONSABILIDADE LIMITADA",
      "account_id": "org-verde-asset",
      "manager_cnpj": "19749539000176",
      "unit_key": null,
      "class_type": "Classes de Cotas de Fundos FIF",
      "classification": "Multimercado",
      "anbima_classification": "Multimercados Macro",
      "benchmark": "DI de um dia",
      "is_active": true,
      "is_exclusive": false,
      "is_fund_of_funds": false,
      "allows_full_offshore": false,
      "constitution_date": "2006-02-20",
      "metrics": {
        "reference_date": "2026-10-27",
        "currency": "BRL",
        "latest_nav_brl": 5718358873.23,
        "latest_investors": 27,
        "return_1m": -0.01379279,
        "return_1m_status": "ok",
        "return_3m": 0.01787183,
        "return_3m_status": "ok",
        "return_6m": 0.02106818,
        "return_6m_status": "ok",
        "return_12m": 0.12809677,
        "return_12m_status": "ok",
        "return_ytd": 0.10478325,
        "return_ytd_status": "ok",
        "net_flow_12m_brl": -1038360738.63,
        "net_flow_status": "ok",
        "volatility_12m": 0.08087312,
        "max_drawdown_12m": -0.05491957
      }
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 1,
    "total": 117,
    "sort": "nav",
    "order": "desc"
  }
}
```

### Mapa (GeoJSON)

`GET /api/v1/map/offices?bbox=-46.75,-23.65,-46.6,-23.5` → 200

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [
          -46.6824811,
          -23.5951591
        ]
      },
      "properties": {
        "office_key": "b06f92981d54fe27cac279ef1bff3daad832f7a737f7e45db079dc4b892d773b",
        "account_id": "org-btg-pactual",
        "canonical_name": "BTG Pactual",
        "institution_type": "banco",
        "legal_name": "BTG PACTUAL GESTÃO E CONSULTORIA DE INVESTIMENTOS LTDA",
        "entity_cnpj": "12695840000103",
        "relation": "affiliate_manager",
        "address": "RUA ELVIRA FERRAZ, 68, 10 E 11º ANDARES, VILA OLÍMPIA, SÃO PAULO/SP, CEP 04552-040",
        "city": "SÃO PAULO",
        "state": "SP",
        "phone_official": "+551130899393",
        "precision": "street",
        "is_exact": false,
        "tier": "Prioridade agora",
        "priority_point": 78.39,
        "fit_point": 90.48,
        "timing_point": 60.25,
        "confidence": 80.96,
        "nav_brl_non_fic": 488283864303.59894,
        "net_flow_12m_brl": 16057332729.079992
      }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [
          -46.6817127,
          -23.5863292
        ]
      },
      "properties": {
        "office_key": "d3cb49b05478999492368ecdb8184769efa4562871aa0cf0e039ac383ccfa97e",
        "account_id": "org-btg-pactual",
        "canonical_name": "BTG Pactual",
        "institution_type": "banco",
        "legal_name": "BTG PACTUAL GESTORA DE RECURSOS LTDA",
        "entity_cnpj": "09631542000137",
        "relation": "primary_manager",
        "address": "AV BRIGADEIRO FARIA LIMA, 3477, 14º ANDAR, ITAIM BIBI, SÃO PAULO/SP, CEP 04538-133",
        "city": "SÃO PAULO",
        "state": "SP",
        "phone_official": "+551133832000",
        "precision": "address",
        "is_exact": true,
        "tier": "Prioridade agora",
        "priority_point": 78.39,
        "fit_point": 90.48,
        "timing_point": 60.25,
        "confidence": 80.96,
        "nav_brl_non_fic": 488283864303.59894,
        "net_flow_12m_brl": 16057332729.079992
      }
    },
    "… +33 itens"
  ],
  "meta": {
    "count": 35,
    "without_location": 18,
    "attribution": "Geocodificação: © OpenStreetMap contributors (ODbL), via Nominatim. Fundos, gestores e endereços: CVM — Portal de Dados Abertos.",
    "precision_note": "Pontos com is_exact=false são aproximados (rua ou bairro) e devem ser exibidos como tal."
  }
}
```

### Densidade (heatmap)

`GET /api/v1/map/density?cell_m=2000` → 200

```json
{
  "cell_m": 2000,
  "cells": [
    {
      "longitude": -46.68242738,
      "latitude": -23.588453848650246,
      "offices": 15,
      "accounts": [
        "org-btg-pactual",
        "org-portofino",
        "… +3 itens"
      ]
    },
    {
      "longitude": -46.68918611428572,
      "latitude": -23.5731232085353,
      "offices": 7,
      "accounts": [
        "org-jive",
        "org-vinci-compass"
      ]
    },
    "… +6 itens"
  ],
  "attribution": "Geocodificação: © OpenStreetMap contributors (ODbL), via Nominatim.",
  "note": "Densidade de escritórios de prospects (inclui pontos aproximados); não representa performance."
}
```

### Sinais de timing

`GET /api/v1/signals?account_id=org-kinea&page_size=2` → 200

```json
{
  "data": [
    {
      "account_id": "org-kinea",
      "unit_key": "org-kinea",
      "signal_type": "expansion",
      "label": "Expansão",
      "observed_at": "2026-10-26T21:00:00-03:00",
      "expires_at": "2027-10-26T21:00:00-03:00",
      "value": 0.0,
      "status": "observed",
      "explanation": "Nenhuma nova entidade regulada pela CVM em 24 meses.",
      "evidence": [
        "CVM — Cadastro de Administradores de Carteira; data de registro das entidades"
      ],
      "source": {
        "source_type": "cvm_cad_adm_cart",
        "url": "https://dados.cvm.gov.br/dados/ADM_CART/CAD/DADOS/cad_adm_cart.zip",
        "collected_at": "2026-10-30T01:02:35.618412-03:00",
        "as_of_date": "2026-10-27",
        "sha256": "f5a8b6e1c51cf2c0570a0d6f95d8a802546b0fbeb7c1e010fb6eeeaa40d45387"
      }
    },
    {
      "account_id": "org-kinea",
      "unit_key": "org-kinea",
      "signal_type": "net_flows",
      "label": "Captação/resgates",
      "observed_at": "2026-10-26T21:00:00-03:00",
      "expires_at": "2027-10-26T21:00:00-03:00",
      "value": 0.4005542145550828,
      "status": "observed",
      "explanation": "Captação líquida de R$ -4,8 bi (-4,0% do PL inicial; cobertura 97,3% do PL).",
      "evidence": [
        "CVM — Informe Diário; CAPTC_DIA - RESG_DIA em 12 meses"
      ],
      "source": {
        "source_type": "cvm_inf_diario",
        "url": "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_202610.zip",
        "collected_at": "2026-10-30T01:03:17.649417-03:00",
        "as_of_date": "2026-10-27",
        "sha256": "21737b9f9faa6875bc23cd7c24bb198ce17ca72b2ccf48e127bfc644df4cf45d"
      }
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 4,
    "sort": "observed_at",
    "order": "desc"
  }
}
```

### Qualidade de dados

`GET /api/v1/data-quality` → 200

```json
{
  "report_version": "prompt3-v1",
  "run_at": "2026-10-30T01:58:52-03:00",
  "fund_reference_date": "2026-10-27",
  "freshness": [
    {
      "source_id": "cvm_cad_adm_cart",
      "title": "Cadastro de Administradores de Carteira",
      "status": "fresh",
      "data_as_of": "2026-10-29",
      "fetched_at": "2026-10-30T04:02:35.618412Z",
      "age_days": 1,
      "max_age_days": 7,
      "detail": ""
    },
    {
      "source_id": "cvm_registro_fundo_classe",
      "title": "Registro de Fundos, Classes e Subclasses (RCVM 175)",
      "status": "fresh",
      "data_as_of": "2026-10-29",
      "fetched_at": "2026-10-30T04:02:36.505272Z",
      "age_days": 1,
      "max_age_days": 7,
      "detail": ""
    },
    "… +3 itens"
  ],
  "accounts": [
    {
      "account_id": "org-spx-capital",
      "canonical_name": "SPX Capital",
      "entities_found": 3,
      "entities_registered": 3,
      "official_address": true,
      "geocode_precision": "address",
      "active_classes": 236,
      "classes_with_daily_report": 210,
      "comparable_12m_share": 0.8779342723004695,
      "open_conflicts": 2,
      "gaps": [
        "classes ativas sem Informe Diário atualizado (FII: 10, FIP: 16)"
      ]
    },
    {
      "account_id": "org-verde-asset",
      "canonical_name": "Verde Asset Management",
      "entities_found": 2,
      "entities_registered": 2,
      "official_address": true,
      "geocode_precision": "address",
      "active_classes": 125,
      "classes_with_daily_report": 117,
      "comparable_12m_share": 0.9572649572649573,
      "open_conflicts": 0,
      "gaps": [
        "classes ativas sem Informe Diário atualizado (FIDC: 6, FII: 2)"
      ]
    },
    "… +10 itens"
  ],
  "rules": [
    "Fundos ligados a contas apenas por igualdade exata de CNPJ do gestor (registro_fundo.CPF_CNPJ_Gestor) contra o registro curado; sem similaridade de nome.",
    "Retorno calculado por classe/subclasse, em BRL, somente com observação inicial até 7 dias antes do início da janela, sem lacunas > 10 dias e série atualizada…",
    "… +8 itens"
  ],
  "conflicts_by_status": {
    "no_longer_detected": 5,
    "pending_review": 9
  },
  "database": {
    "organizations": 12,
    "legal_entities": 48,
    "regulatory_offices": 48,
    "located_offices": 44,
    "exact_offices": 30,
    "fund_classes": 6293,
    "active_fund_classes": 4275,
    "fund_metric_rows": 3648,
    "latest_observation": "2026-10-27",
    "signals": 48,
    "last_load": "2026-10-30T04:04:53.894174-03:00"
  }
}
```

### Fila de conflitos

`GET /api/v1/data-quality/conflicts?page_size=2` → 200

```json
{
  "data": [
    {
      "conflict_id": "c1278be36a7af280",
      "account_id": "org-itau-bba",
      "entity_cnpj": "60701190000104",
      "field": "address_raw",
      "rule": "address_not_in_official_registry",
      "severity": "medium",
      "workbook_value": "Av. Brigadeiro Faria Lima, 3500, Itaim Bibi, São Paulo/SP, CEP 04538-132",
      "source_value": "PC ALFREDO E.S. ARANHA, 100, T.O.SETUBAL, PRQ. JABAQUARA, SÃO PAULO/SP, CEP 04344-902",
      "detected_at": "2026-10-30T01:02:35-03:00",
      "resolution_status": "pending_review",
      "resolution_note": null
    },
    {
      "conflict_id": "d6471ca897d50c0c",
      "account_id": "org-itau-bba",
      "entity_cnpj": "60701190000104",
      "field": "phone_public",
      "rule": "phone_not_in_official_registry",
      "severity": "medium",
      "workbook_value": "+55 (11) 3631-2000",
      "source_value": "+551150199986",
      "detected_at": "2026-10-30T01:02:35-03:00",
      "resolution_status": "pending_review",
      "resolution_note": null
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 14,
    "sort": "severity",
    "order": "asc"
  }
}
```

## Planos de consulta (EXPLAIN ANALYZE no banco carregado)

Com poucas linhas o PostgreSQL pode preferir varredura sequencial; os testes de integração confirmam com `enable_seqscan=off` que cada consulta consegue usar seu índice.

### Mapa: escritórios no bbox (GiST)

```sql
SELECT office_key FROM offices WHERE location IS NOT NULL AND location && ST_MakeEnvelope(-46.8,-23.7,-46.5,-23.4,4326)
```

```text
Seq Scan on offices (actual time=0.030..0.094 rows=35 loops=1)
  Filter: ((location IS NOT NULL) AND (location && '0103000020E6100000010000000500000066666666666647C03333333333B337C066666666666647C066666666666637C000000000004047C066666666666637C000000000004047C03333333333B337C066666666666647C03333333333B337C0'::geometry))
  Rows Removed by Filter: 27
  Buffers: shared hit=12
Planning:
  Buffers: shared hit=128
Planning Time: 12.170 ms
Execution Time: 0.317 ms
```

### Ranking: última rodada ordenada por rank

```sql
SELECT unit_key FROM opportunity_scores WHERE score_run_id = (SELECT id FROM score_runs ORDER BY loaded_at DESC, id LIMIT 1) ORDER BY rank LIMIT 50
```

```text
Limit (actual time=0.081..0.083 rows=22 loops=1)
  Buffers: shared hit=14
  InitPlan 1 (returns $0)
    ->  Limit (actual time=0.036..0.036 rows=1 loops=1)
          Buffers: shared hit=7
          ->  Sort (actual time=0.036..0.036 rows=1 loops=1)
                Sort Key: score_runs.loaded_at DESC, score_runs.id
                Sort Method: quicksort  Memory: 25kB
                Buffers: shared hit=7
                ->  Seq Scan on score_runs (actual time=0.010..0.011 rows=1 loops=1)
                      Buffers: shared hit=1
  ->  Sort (actual time=0.080..0.081 rows=22 loops=1)
        Sort Key: opportunity_scores.rank
        Sort Method: quicksort  Memory: 26kB
        Buffers: shared hit=14
        ->  Seq Scan on opportunity_scores (actual time=0.052..0.064 rows=22 loops=1)
              Filter: (score_run_id = $0)
              Buffers: shared hit=11
Planning:
  Buffers: shared hit=162
Planning Time: 8.343 ms
Execution Time: 0.108 ms
```

### Série diária de uma classe

```sql
SELECT observation_date, quota_value FROM fund_observations WHERE fund_id = (SELECT id FROM funds WHERE cnpj IS NOT NULL ORDER BY cnpj LIMIT 1) AND subclass_id = '' ORDER BY observation_date
```

```text
Index Scan using ix_fund_observation_date on fund_observations (actual time=0.898..0.898 rows=0 loops=1)
  Index Cond: ((fund_id = $0) AND ((subclass_id)::text = ''::text))
  Buffers: shared hit=1 read=5
  InitPlan 1 (returns $0)
    ->  Limit (actual time=0.047..0.047 rows=1 loops=1)
          Buffers: shared hit=1 read=2
          ->  Index Scan using ix_fund_cnpj on funds (actual time=0.046..0.046 rows=1 loops=1)
                Buffers: shared hit=1 read=2
Planning:
  Buffers: shared hit=161 read=6
Planning Time: 18.685 ms
Execution Time: 0.922 ms
```

### Fundos ativos de uma conta

```sql
SELECT f.cnpj FROM funds f JOIN organizations o ON o.id = f.organization_id WHERE o.account_id = 'org-verde-asset' AND f.is_active
```

```text
Nested Loop (actual time=0.055..0.308 rows=125 loops=1)
  Buffers: shared hit=91
  ->  Seq Scan on organizations o (actual time=0.018..0.025 rows=1 loops=1)
        Filter: ((account_id)::text = 'org-verde-asset'::text)
        Rows Removed by Filter: 11
        Buffers: shared hit=5
  ->  Bitmap Heap Scan on funds f (actual time=0.033..0.270 rows=125 loops=1)
        Recheck Cond: ((o.id = organization_id) AND is_active)
        Heap Blocks: exact=84
        Buffers: shared hit=86
        ->  Bitmap Index Scan on ix_fund_org_active (actual time=0.021..0.021 rows=125 loops=1)
              Index Cond: ((organization_id = o.id) AND (is_active = true))
              Buffers: shared hit=2
Planning:
  Buffers: shared hit=118
Planning Time: 6.800 ms
Execution Time: 0.354 ms
```
