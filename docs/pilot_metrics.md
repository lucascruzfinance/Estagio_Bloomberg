# Métricas de validação do piloto

Nenhum resultado abaixo foi medido ainda. Este documento define **o que medir, como, contra qual linha de base e o que contaria como sucesso**, para que o piloto produza evidência em vez de opinião. Onde há valor, ele é o estado técnico atual da base, não um resultado comercial.

## Desenho sugerido

- Duração: 4 semanas, 2 vendedores (1 Buy-Side, 1 Banks and Brokers), 12 contas + mesas.
- Linha de base: semana 0 sem a ferramenta (fluxo atual), medindo o tempo de preparação de 4 contas por vendedor.
- Comparação: semanas 1 a 4 com a ferramenta, em contas diferentes de tamanho parecido.
- Registro: planilha simples por conta (data, vendedor, tempo, campos corrigidos, decisão de abordagem, resultado), depois o CRM.

## Métricas

| Métrica | Definição | Como medir | Linha de base | Situação atual |
|---|---|---|---|---|
| Tempo para preparar uma conta | Minutos do início da pesquisa até o vendedor dizer "estou pronto para a ligação" | Cronômetro pelo próprio vendedor, mesma lista de itens (contato, áreas, produtos, sinais) | Semana 0 | não medido |
| Cobertura de dados | % das contas com: CNPJ principal, endereço oficial, telefone institucional, fundos mapeados, retorno 12m comparável | Calculada pela API (`/api/v1/data-quality`) | — | base técnica: 12/12 com CNPJ e endereço oficial; retorno 12m comparável de 73% a 96% das séries por gestora (sem fundos no Itaú BBA) |
| Taxa de campos verificados | % dos campos exibidos que vieram de fonte primária com data, sobre o total exibido | Contagem por campo na Conta 360 (fonte: `field_provenance` e evidências) | — | cada fator com valor cita evidência (158/158 na validação) |
| Taxa de correção humana | % dos campos que o vendedor precisou corrigir | Fila `data/review/conflicts.csv` + anotação do vendedor | — | 9 conflitos pendentes na revisão inicial |
| Aceitação do ranking | % das unidades em que o vendedor concorda com a faixa (Prioridade agora, Desenvolver, Tática, Monitorar) | Revisão cega: vendedor classifica antes de ver o score; comparar | — | não medido |
| Concordância de ordem | Correlação de Spearman entre a ordem do vendedor e a da ferramenta | Mesma revisão cega | — | não medido (a estabilidade interna aos pesos é 0,95, o que não é validação externa) |
| Reuniões geradas | Reuniões marcadas com contas da lista / contatos feitos | CRM ou planilha do piloto | Taxa histórica do vendedor | não medido |
| Conversão | Oportunidades abertas e ganhas originadas na lista, em 90 dias | CRM | Taxa histórica comparável | não medido |
| Utilidade percebida | Nota de 1 a 5 e um comentário por conta: "o que mudou na conversa" | Formulário curto após cada reunião | — | não medido |

## Critérios de decisão (propostos, a validar com o time)

- Seguir para a fase 2 (mais contas, sinais curados, CRM) se: tempo de preparação cair pelo menos 30% e aceitação do ranking for de pelo menos 60%, sem aumento de correções.
- Rever o modelo se: concordância de ordem abaixo de 0,3 ou mais de 20% de correções em campos de contato.
- Calibrar pesos somente com 50+ resultados e 10+ positivos (regra já codificada em `scoring/calibration.py`).

## Três validações separadas

| Validação | O que prova | Quem aprova | Status |
|---|---|---|---|
| Técnica | O sistema faz o que diz: dados rastreáveis, cálculos corretos, testes, segurança | Analista (eu) + revisão de engenharia | concluída para o MVP (ver `docs/delivery_report.md`) |
| Qualidade econômica do score | Os pesos e fatores ordenam bem as oportunidades reais | Dados de resultado do piloto e do CRM | **não iniciada**: depende das métricas acima |
| Aprovação comercial | O time quer usar e a ferramenta muda a conversa | Sales Team Leaders e vendedores Bloomberg | **pendente**: depende do piloto |
