# Prompt 3 — Relatório de enriquecimento e qualidade

Execução: 2026-10-30T04:58:52+00:00  
Data de referência dos fundos: 2026-10-27  
Versão: prompt3-v1

> Retornos são variações de cota dos fundos (líquidas de taxas, para o cotista). Não representam receita nem lucro da gestora.

## Freshness das fontes

| Fonte | Status | Dados de | Idade (dias) | Limite | Artefatos | Detalhe |
|---|---|---|---:|---:|---:|---|
| Cadastro de Administradores de Carteira | fresh | 2026-10-29 | 1 | 7 | 1 |  |
| Registro de Fundos, Classes e Subclasses (RCVM 175) | fresh | 2026-10-29 | 1 | 7 | 1 |  |
| Informe Diário de Fundos de Investimento | fresh | 2026-10-27 | 3 | 7 | 13 |  |
| IF.data — cadastro de instituições (Olinda) | unavailable | — | — | 200 | 0 | 202609: HTTP 500 after retries; 202606: HTTP 500 after retries; 202603: HTTP 500 after retries |
| Nominatim geocoding | fresh | 2026-10-30 | 0 | 365 | 22 | 13/22 endereços com precisão de porta |

## Cobertura por conta

| Conta | CNPJ principal | Entidades | Endereço oficial | Geo exato | Classes ativas | c/ Informe | Retorno 12m comparável | PL (não-FIC) | Captação líq. 12m | Conflitos abertos |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| SPX Capital | 12.330.774/0001-60 | 3/3 | sim | address | 236 | 210 | 88% | R$ 33.185 mi | R$ -13.744 mi | 2 |
| Verde Asset Management | 19.749.539/0001-76 | 2/2 | sim | address | 125 | 117 | 96% | R$ 12.036 mi | R$ -2.241 mi | 0 |
| Kapitalo Investimentos | 11.180.009/0001-48 | 3/3 | sim | address | 112 | 111 | 84% | R$ 36.992 mi | R$ -1.012 mi | 0 |
| Ibiúna Investimentos | 11.918.575/0001-04 | 4/4 | sim | street | 82 | 81 | 78% | R$ 13.130 mi | R$ -1.493 mi | 0 |
| Kinea Investimentos | 08.604.187/0001-44 | 2/2 | sim | street | 371 | 306 | 84% | R$ 118.374 mi | R$ -4.774 mi | 0 |
| Pátria Investimentos | 12.461.756/0001-17 | 6/6 | sim | none | 139 | 25 | 84% | R$ 3.078 mi | R$ 766 mi | 0 |
| Vinci Compass | 11.077.576/0001-73 | 14/14 | sim | street | 396 | 280 | 89% | R$ 31.656 mi | R$ -770 mi | 2 |
| Constellation Asset Management | 06.182.127/0001-55 | 1/1 | sim | address | 45 | 45 | 96% | R$ 998 mi | R$ -378 mi | 1 |
| Jive Investments | 12.600.032/0001-07 | 4/4 | sim | address | 144 | 50 | 73% | R$ 11.353 mi | R$ -972 mi | 2 |
| Portofino Gestão de Recursos | 17.590.181/0001-56 | 3/3 | sim | street | 167 | 149 | 73% | R$ 12.853 mi | R$ 127 mi | 0 |
| BTG Pactual | 09.631.542/0001-37 | 5/5 | sim | address | 2458 | 2134 | 86% | R$ 488.284 mi | R$ 16.057 mi | 0 |
| Itaú BBA | 60.701.190/0001-04 | 1/1 | sim | none | 0 | 0 | — | — | — | 2 |

## Lacunas por conta

- **SPX Capital**: classes ativas sem Informe Diário atualizado (FII: 10, FIP: 16).
- **Verde Asset Management**: classes ativas sem Informe Diário atualizado (FIDC: 6, FII: 2).
- **Kapitalo Investimentos**: classes ativas sem Informe Diário atualizado (FIP: 1).
- **Ibiúna Investimentos**: classes ativas sem Informe Diário atualizado (FIP: 1); geocodificação da sede não exata (matched_approximate, precisão street).
- **Kinea Investimentos**: classes ativas sem Informe Diário atualizado (FIAGRO: 3, FIDC: 3, FII: 26, FIP: 33); geocodificação da sede não exata (matched_approximate, precisão street).
- **Pátria Investimentos**: classes ativas sem Informe Diário atualizado (FIAGRO: 2, FIDC: 9, FII: 47, FIP: 56); geocodificação da sede não exata (rejected_wrong_locality, precisão none).
- **Vinci Compass**: classes ativas sem Informe Diário atualizado (FIAGRO: 8, FIDC: 27, FIF: 1, FII: 18, FIP: 62); geocodificação da sede não exata (matched_approximate, precisão street).
- **Constellation Asset Management**: nenhuma lacuna crítica nas fontes deste prompt.
- **Jive Investments**: classes ativas sem Informe Diário atualizado (FIAGRO: 2, FIDC: 51, FIF: 2, FII: 32, FIP: 7).
- **Portofino Gestão de Recursos**: classes ativas sem Informe Diário atualizado (FIDC: 11, FIF: 2, FII: 5); geocodificação da sede não exata (matched_approximate, precisão street).
- **BTG Pactual**: dados prudenciais do banco dependem do IF.data (BCB) — indisponível nesta execução; mesas/áreas e decisores do banco exigem validação comercial; classes ativas sem Informe Diário atualizado (FIAGRO: 21, FIDC: 88, FIF: 12, FII: 45, FIIM: 35, FIP: 123).
- **Itaú BBA**: dados prudenciais do banco dependem do IF.data (BCB) — indisponível nesta execução; mesas/áreas e decisores do banco exigem validação comercial; nenhuma classe de fundo ativa mapeada às entidades da conta; geocodificação da sede não exata (no_match, precisão none).

## Regras aplicadas

- Fundos ligados a contas apenas por igualdade exata de CNPJ do gestor (registro_fundo.CPF_CNPJ_Gestor) contra o registro curado; sem similaridade de nome.
- Retorno calculado por classe/subclasse, em BRL, somente com observação inicial até 7 dias antes do início da janela, sem lacunas > 10 dias e série atualizada até 5 dias da data de referência; caso contrário o campo fica nulo com o motivo.
- Variação diária que se afasta mais de 25 p.p. da mediana do mesmo dia na mesma classificação CVM é tratada como suspeita de evento de cota (amortização, grupamento) e torna a janela não comparável; choques de mercado amplos continuam contando como retorno.
- Data de referência = último dia reportado por pelo menos 50% das séries do dia mais completo, para não ancorar a janela num dia com poucas classes publicadas.
- Captação líquida 12m só é somada quando a janela de 12m da série está completa.
- PL agregado exclui classes FIC/CIC para reduzir dupla contagem e usa o nível de classe quando existe; ainda pode haver dupla contagem master-feeder.
- Endereços geocodificados são apenas os registrados na CVM; 'address' só quando o número da porta retornado coincide. Excel não confirmado não é geocodificado.
- E-mails individuais são descartados; apenas caixas institucionais/funcionais são mantidas.
- Diretores coletados apenas para a função de gestão de carteiras (Res. CVM 21) das entidades principais; compliance, risco e PLD não são coletados.
- Fontes sandbox/fictícias (ex.: ANBIMA sandbox) são bloqueadas no cache e no fetcher.

## Revisão humana

- Fila de conflitos: `data/review/conflicts.csv` (9 pendentes de 14).
- Registro de identidade: `data/reference/identity_registry.yaml` (todas as entidades em `pending_human_review`).
- Para resolver, preencha `resolution_status`, `resolved_by`, `resolved_at` e `resolution_note`; a próxima execução preserva a decisão.
