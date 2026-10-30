# Validação independente por amostragem

Gerado em 2026-10-30 16:29 UTC por `scripts/validate_sample.py` contra `http://127.0.0.1:8000` (semente 20261030).

O script não importa o pipeline: recalcula com a biblioteca padrão a partir dos zips brutos da CVM no cache imutável, dos pesos do YAML e das respostas brutas do Nominatim.

| Verificação | Situação | Itens | Observação |
|---|---|---:|---|
| Contagens: contas, unidades e entidades | ok | 3 | 12 contas, 22 unidades, 48 entidades |
| Scores recalculados a partir dos fatores e dos pesos do YAML | ok | 155 | 22 unidades, maior desvio 0.0049 pontos (API arredonda em 2 casas) |
| Retorno 12m, PL e captação recalculados dos zips brutos da CVM | ok | 24 | 8 classes sorteadas entre 1193; maior desvio de retorno 4.62e-09 |
| Série do gráfico de cota igual aos dados brutos | ok | 32 | 8 séries comparadas ponto a ponto nas pontas e na contagem |
| Fontes: hash do arquivo bruto e domínio oficial | ok | 96 | 1 arquivo(s) bruto(s) conferido(s) por SHA-256 |
| Datas de referência coerentes | ok | 7 | referência 2026-10-27, hoje 2026-10-30 |
| Coordenadas: dentro da UF e iguais à resposta bruta do Nominatim | ok | 118 | 44 escritórios; atribuição: Geocodificação: © OpenStreetMap contributors (ODbL), via Nominatim. Fundos, gestores e endereços: CVM — Portal de Dados Abertos. |
| Cada fator com valor tem evidência citada | ok | 158 |  |

## Falhas

Nenhuma.

## O que esta validação não cobre

- Se os pesos e as premissas do modelo são economicamente corretos (exige resultados comerciais reais; ver docs/pilot_metrics.md).
- Se o vínculo entre entidades e grupos econômicos está certo (fila de revisão humana).
- Dados que as fontes públicas não publicam (headcount, contratos vigentes).
