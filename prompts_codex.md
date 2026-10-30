# Bloomberg Sales Intelligence — análise crítica e prompts de execução

Data de referência: 29/10/2026  
Workspace: `C:\Users\Lucas\Desktop\Estagio_Bloomberg`

## 1. Decisão de produto

O produto não deve prometer “prever quem comprará um Terminal”. A proposta defensável é um **sistema de priorização comercial explicável**, que organiza dados públicos, identifica sinais de necessidade e timing e mostra ao vendedor por que uma conta merece atenção.

### Hipótese que precisa ser corrigida

`Performance recente do fundo -> maior chance de comprar Terminal` é uma hipótese, não um fato. Performance pode ajudar como sinal de crescimento ou capacidade de investimento, mas sofre com:

- dados privados, incompletos ou não comparáveis entre estratégias;
- confusão entre retorno do fundo, lucro da gestora e saúde financeira do grupo;
- survivorship bias, seleção de fundos e janelas diferentes;
- causalidade reversa e variáveis omitidas, como AUM, headcount, novos produtos e complexidade operacional.

O modelo deve separar três resultados:

1. **Fit estrutural:** intensidade de dados, classes de ativos, complexidade do workflow, atuação internacional e potencial de usuários.
2. **Timing comercial:** novos fundos, contratação, expansão, captação/resgates, M&A, novos escritórios, mudanças regulatórias e modernização tecnológica. Performance entra com peso limitado.
3. **Confiança dos dados:** fonte, data, cobertura, qualidade e divergências. Confiança não pode aumentar artificialmente o fit.

Para bancos e brokers, a unidade de análise deve ser **área/mesa**, não o banco inteiro: tesouraria, sales & trading, research, ALM, risco, compliance, brokerage, market data/technology e enterprise data/API.

## 2. O que o Excel permite concluir

O arquivo tem 30 abas. A base consolidada informa 210 instituições, 199 com foco buy-side, 175 com presença em São Paulo e apenas 52 confirmadas por endereço ou presença em SP. Há 117 registros em “Citado — não verificado”. A aba `Progresso`, porém, informa 287 casas únicas e 395 linhas; essa divergência precisa ser resolvida antes de qualquer KPI público.

Outros problemas relevantes:

- a mesma instituição aparece em várias abas e com variações de nome;
- endereço, telefone, e-mail geral e canal de recrutamento não equivalem a contato comercial qualificado;
- algumas observações têm números de AUM e afirmações sem fonte primária adjacente;
- a planilha foi montada para networking/estágio, não para CRM ou sales intelligence;
- não há ainda identificador canônico, CNPJ, coordenadas, data de validade por campo nem trilha de proveniência por observação.

### Piloto recomendado: 12 contas

**Buy-side e alternativos:** SPX Capital, Verde Asset, Kapitalo, Ibiúna, Kinea, Pátria, Vinci Compass, Constellation, Jive Investments e Portofino.  
**Bancos:** BTG Pactual e Itaú BBA, sempre segmentados por área/mesa.

Esse recorte cobre macro/multimercado, equities, alternativos, private equity, crédito/special situations, family office e dois bancos relevantes. XP e BR Partners entram na segunda onda, depois que o modelo de desk-level scoring estiver validado.

## 3. Produto mínimo demonstrável

### Telas

1. **Prioridade comercial:** contas ordenadas por fit e timing, com justificativas e confiança.
2. **Account 360:** instituição, escritórios, pessoas públicas, estratégias, fundos, sinais, gráficos, produto/workflow sugerido e fontes.
3. **Mapa SP/RJ:** pontos e clusters; heatmap representa densidade de prospects, não performance.
4. **Comparador:** 2–5 contas, métricas comparáveis e razões da pontuação.
5. **Qualidade dos dados:** campos faltantes, divergências, fonte, data de coleta e validade.

### Arquitetura recomendada

- Frontend: React + TypeScript + Vite, TanStack Query/Table, ECharts e MapLibre GL.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy e Alembic.
- Banco: PostgreSQL + PostGIS.
- ETL: Python com pandas/Polars; camadas `raw -> staging -> curated`.
- Infra local: Docker Compose; sem cloud obrigatória para o MVP.
- Testes: pytest no backend; Vitest e Playwright no frontend.

### Modelo de dados mínimo

- `organizations`: instituição canônica e tipo.
- `business_units`: área/mesa ou vertical.
- `offices`: endereço, cidade, latitude/longitude e confiança.
- `people`: somente dados profissionais públicos necessários.
- `funds`: CNPJ/código, estratégia, gestor e administrador.
- `fund_observations`: cota, PL, captação, resgate, cotistas e data.
- `commercial_signals`: contratação, lançamento, expansão, M&A e outras mudanças.
- `product_fit`: problema/workflow e produto potencial, sem alegar compra.
- `sources`: URL, publicador, data de coleta, licença/termo e confiança.
- `scores`: versão, fatores, pesos, evidências e resultado.

## 4. Visual Bloomberg-inspired

Não copiar logo, ativos ou a interface do Terminal. Usar uma linguagem visual inspirada em ferramentas financeiras de alta densidade:

- fundo preto/grafite; texto branco/cinza;
- laranja/âmbar para seleção e alertas; verde/vermelho apenas para variações;
- azul `#0062DD` somente como acento secundário de ação, conforme a página atual de Bloomberg Professional;
- fonte aberta: Inter/Arial na interface e IBM Plex Mono ou JetBrains Mono em tabelas;
- barra de comando, filtros compactos, grade densa e painel lateral de detalhes;
- números alinhados, unidades explícitas, pouco espaço desperdiçado e fonte sempre legível.

A página oficial usa `AvenirNextPForBBG` com fallback Helvetica/Arial, corpo `#2D2D32`, azul `#0062DD` e imagens do Terminal com preto e laranja. A fonte proprietária não deve ser redistribuída.

### O que a banca provavelmente avaliará

- **Leandro Pena, Brazil Buy-Side:** o histórico e as publicações públicas recentes enfatizam workflow de investimento, AI/APIs, qualidade dos dados, fontes citadas e confiança. A demonstração deve começar em uma pergunta comercial e terminar em evidências verificáveis, não em um score opaco.
- **Yasmin La Manna, Banks and Brokers:** a experiência em Enterprise Data e relacionamento com bancos indica que a resposta não pode ser “vender um Terminal ao banco”. O sistema deve identificar a área, o problema e a solução potencial: Terminal, dados em tempo real/estáticos, APIs, execução, risco, compliance ou gestão de ordens.

Em ambos os casos, o diferencial não é a quantidade de logos no mapa. É reduzir o tempo de preparação de uma conta e aumentar a qualidade da conversa comercial sem eliminar o julgamento do vendedor.

## 5. Skills

### Já instaladas e suficientes

- `frontend-design` e `frontend-design-excellence` — sistema visual e componentes.
- `backend-production-excellence` — API, arquitetura e observabilidade.
- `data-ml-excellence` — ETL, qualidade e experimentação.
- `senior-finance-analyst` — definição correta de métricas financeiras.
- `security-best-practices` e `cybersecurity-defensive-review` — dados, segredos e superfícies de ataque.
- `playwright` — testes de ponta a ponta.
- `general-code-review` — revisão final.
- `Spreadsheets` e `clean-data-xls` — leitura e saneamento da base de origem.

Não instalar skills adicionais antes da apresentação. Em outra máquina, as opções externas mais defensáveis seriam:

```powershell
npx skills add anthropics/skills@frontend-design -g -y
npx skills add wshobson/agents@fastapi-templates -g -y
npx skills add anthropics/financial-services@clean-data-xls -g -y
```

Evitar skills de data science com baixa adoção ou autoria pouco verificável; o conjunto já instalado cobre melhor o projeto.

## 6. Sete prompts sequenciais para o Codex

Execute um prompt por vez. Cada prompt deve ler os artefatos produzidos pelo anterior e preservar decisões aprovadas. Não avançar se os critérios de aceite falharem.

### Prompt 1 — Auditoria da base, recorte e contrato de dados

```text
Você está no repositório C:\Users\Lucas\Desktop\Estagio_Bloomberg. Leia integralmente prompts_codex.md e AGENTS.md. Use as skills Spreadsheets, clean-data-xls, data-ml-excellence e senior-finance-analyst.

Objetivo: transformar Networking_estagio_v2.xlsx em uma especificação confiável para um MVP de sales intelligence, sem alterar o Excel original.

Tarefas:
1. Audite as abas Base Completa E, Resumo E, Progresso, PE E, Hedge Fund E, Asset E, Family Office E, IB E e Pendências E.
2. Reconcilie 210 instituições versus 287 casas únicas/395 linhas. Explique exatamente a origem da divergência.
3. Crie regras de normalização e deduplicação por nome canônico, CNPJ quando disponível, grupo econômico, vertical e unidade de negócio.
4. Limite o MVP às 12 contas definidas em prompts_codex.md. Não pesquise todas as casas.
5. Para cada campo, defina tipo, unidade, origem, data de referência, possibilidade de nulidade, regra de validação e confiança.
6. Separe fato observado, inferência e dado ausente. Não invente valores.
7. Produza um backlog priorizado de lacunas somente para as 12 contas.

Entregáveis no repositório:
- docs/data_audit.md
- data/contracts/organization_schema.yaml
- data/staging/pilot_accounts.csv
- tests/fixtures/pilot_accounts_expected.csv

Critérios de aceite:
- contagens reconciliadas;
- nenhum registro duplicado sem explicação;
- cada valor do piloto mantém aba, célula/range ou URL de origem;
- dados não confirmados são nulos ou explicitamente marcados, nunca preenchidos por suposição;
- testes de unicidade e campos obrigatórios executados e aprovados.

Ao final, resuma decisões, testes, lacunas e o que exige aprovação humana. Não implemente ainda banco, API ou frontend.
```

### Prompt 2 — Banco de dados e ETL reproduzível

```text
Leia AGENTS.md, prompts_codex.md e todos os entregáveis do Prompt 1. Use backend-production-excellence e data-ml-excellence.

Objetivo: implementar a fundação de dados do MVP em PostgreSQL/PostGIS com ingestão reproduzível e proveniência por campo.

Tarefas:
1. Configure Docker Compose com PostgreSQL 16 + PostGIS e variáveis locais em .env.example, sem segredos reais.
2. Modele organizations, business_units, offices, people, funds, fund_observations, commercial_signals, product_fit, sources e scores.
3. Implemente SQLAlchemy 2, Alembic e constraints de integridade.
4. Crie ETL idempotente raw -> staging -> curated para o CSV do piloto e, opcionalmente, para o Excel original.
5. Grave source_id, collected_at, as_of_date, confidence, verification_status e transformação aplicada.
6. Crie uma tabela de aliases para nomes e grupos econômicos. Um banco deve ter unidades/mesas separadas.
7. Gere seed somente para as 12 contas; não faça enriquecimento amplo.

Critérios de aceite:
- docker compose up inicia banco e migrações;
- executar o ETL duas vezes não duplica dados;
- coordenadas usam PostGIS Point com SRID 4326;
- constraints bloqueiam CNPJ inválido, datas impossíveis e referências órfãs;
- testes de integração e reconciliação passam;
- README contém apenas comandos necessários para subir, migrar, carregar e testar.

Não construa ainda o score comercial nem o frontend.
```

### Prompt 3 — Enriquecimento público, geocodificação e qualidade

```text
Leia AGENTS.md, prompts_codex.md e o estado do repositório após o Prompt 2. Use data-ml-excellence, senior-finance-analyst, playwright quando necessário para páginas públicas e security-best-practices.

Objetivo: enriquecer somente as 12 contas com fontes legais, auditáveis e recentes.

Fontes prioritárias:
- CVM Dados Abertos: cadastro e Informe Diário de fundos;
- Banco Central IF.data para instituições financeiras;
- sites oficiais e documentos regulatórios das instituições;
- ANBIMA apenas se o acesso/licença permitir; sandbox não é dado real;
- geocodificação com política de cache, rate limit e atribuição da fonte cartográfica.

Tarefas:
1. Criar conectores versionados e cache raw imutável.
2. Mapear fundos para gestores e organizações por CNPJ/códigos, sem fuzzy match silencioso.
3. Calcular retornos e fluxos somente quando série, classe, moeda e período forem comparáveis; mostrar cobertura.
4. Geocodificar endereços confirmados e guardar precisão, provedor, data e resultado original.
5. Registrar conflitos e permitir revisão humana.
6. Não raspar LinkedIn autenticado, não coletar dados pessoais desnecessários e não contornar bloqueios.
7. Implementar freshness checks e data quality report.

Critérios de aceite:
- toda observação tem fonte e data;
- dados de sandbox/fictícios nunca entram como reais;
- retorno não é confundido com lucro da gestora;
- nenhum endereço aproximado aparece como exato;
- conectores têm testes com fixtures, retries limitados e logs sem dados sensíveis;
- relatório mostra cobertura e lacunas por conta.
```

### Prompt 4 — Modelo explicável de oportunidade comercial

```text
Leia AGENTS.md, prompts_codex.md e os dados curados após o Prompt 3. Use senior-finance-analyst e data-ml-excellence.

Objetivo: construir um modelo transparente de priorização para vendedores, sem alegar probabilidade de compra ou causalidade não demonstrada.

Tarefas:
1. Implemente três saídas separadas: fit estrutural, timing comercial e confiança dos dados.
2. Proponha pesos editáveis e versionados. Fit deve privilegiar complexidade de workflow, amplitude de ativos, atuação internacional, necessidade de dados/API e potencial de usuários. Timing deve priorizar lançamento de produtos, contratação, expansão, captação/resgates, M&A e mudanças operacionais. Performance terá peso limitado.
3. Para bancos, pontue cada área/mesa e associe possíveis workflows/produtos; não pontue o conglomerado como uma unidade homogênea.
4. Gere reason codes positivos e negativos, contribuição por fator e lista de evidências.
5. Implemente missingness sem converter ausência de dado em zero saudável.
6. Faça análise de sensibilidade dos pesos e testes contra rankings absurdos.
7. Não use ML supervisionado sem variável-alvo histórica de oportunidades/conversões. Deixe interface para calibração futura.

Critérios de aceite:
- score reproduzível e versionado;
- usuário consegue explicar cada ponto;
- confiança nunca substitui fit/timing;
- resultados mudam corretamente quando um sinal muda;
- testes cobrem dados ausentes, extremos, duplicatas e conflito de fontes;
- ranking do piloto vem com limitações explícitas, não como recomendação automática de compra.
```

### Prompt 5 — API e backend de produção para o MVP

```text
Leia AGENTS.md, prompts_codex.md e o resultado do Prompt 4. Use backend-production-excellence, security-best-practices e general-code-review.

Objetivo: expor os dados e scores por uma API FastAPI consistente, segura e testada.

Tarefas:
1. Crie endpoints versionados para accounts, business-units, offices/map, funds/performance, signals, scores/explanations, comparisons e data-quality.
2. Implemente filtros, ordenação, paginação e busca canônica.
3. Use schemas Pydantic distintos para persistência e resposta.
4. Acrescente health/readiness, logs estruturados, correlation id e métricas básicas.
5. Implemente cache somente onde não esconde atualização de dados.
6. Documente erros, unidades, datas e nulidade no OpenAPI.
7. Aplique CORS restrito, validação de entrada, rate limit local e configuração segura por ambiente.

Critérios de aceite:
- pytest passa com cobertura das regras críticas;
- OpenAPI abre e exemplos correspondem ao banco;
- nenhuma resposta expõe segredo, stack trace ou dado pessoal desnecessário;
- consultas do mapa e ranking têm plano aceitável e índices adequados;
- todos os endpoints do frontend planejado estão disponíveis.
```

### Prompt 6 — Frontend Bloomberg-inspired e mapa interativo

```text
Leia AGENTS.md, prompts_codex.md e a OpenAPI após o Prompt 5. Use frontend-design, frontend-design-excellence e playwright.

Objetivo: criar um dashboard React/TypeScript profissional, denso, acessível e fiel ao workflow comercial, sem copiar a identidade proprietária da Bloomberg.

Tarefas:
1. Implemente as cinco telas definidas em prompts_codex.md.
2. Crie design tokens: preto/grafite, branco/cinza, laranja/âmbar; verde/vermelho apenas para variações; azul secundário para ações.
3. Use Inter/Arial e IBM Plex Mono/JetBrains Mono, nunca redistribua AvenirNextPForBBG.
4. Construa tabela principal com filtros persistentes, colunas configuráveis e painel lateral Account 360.
5. Mostre fit, timing e confiança separadamente, com reason codes e links de fonte.
6. Implemente mapa MapLibre com clusters, heatmap de densidade e tooltip enxuto. Não use heatmap para sugerir causalidade.
7. Implemente estados loading, vazio, erro, dado vencido e fonte conflitante.
8. Garanta responsividade para notebook de apresentação, navegação por teclado, contraste e formatos brasileiros.

Critérios de aceite:
- nenhum dado mock aparece sem selo DEMO;
- mapa, filtros e ranking permanecem sincronizados;
- tooltip não expõe dados pessoais desnecessários;
- testes Vitest e Playwright cobrem jornada de seleção, comparação, filtro e Account 360;
- não há overflow, texto cortado, gráficos ilegíveis ou console errors em 1366x768 e 1440x900.
```

### Prompt 7 — Integração, QA e roteiro de apresentação

```text
Leia AGENTS.md, prompts_codex.md e todo o repositório após o Prompt 6. Use general-code-review, cybersecurity-defensive-review, backend-production-excellence e playwright.

Objetivo: entregar um MVP demonstrável e uma narrativa honesta para a banca.

Tarefas:
1. Execute lint, typecheck, testes unitários, integração e E2E; corrija falhas dentro do escopo.
2. Valide contagens, score, fontes, datas, coordenadas e gráficos por amostragem independente.
3. Faça revisão de segurança, dependências, segredos, CORS, logs e dados pessoais.
4. Prepare um comando único de demo e seed determinístico das 12 contas.
5. Crie docs/demo_script.md com versões de 90 segundos e 5 minutos, incluindo problema, hipótese, demonstração, limitações e próximos passos.
6. Crie docs/architecture.md com diagrama simples e decisões de trade-off.
7. Crie docs/pilot_metrics.md com métricas de validação: tempo para preparar conta, cobertura de dados, taxa de campos verificados, aceitação do ranking por vendedores, reuniões geradas e conversão — sem inventar resultados.
8. Atualize README com setup mínimo. Não crie PPT, PDF ou vídeo sem pedido explícito.

Critérios de aceite:
- aplicação sobe do zero com instruções testadas;
- suíte completa passa;
- demo funciona sem internet usando cache/seed e identifica dados DEMO;
- cada insight exibido é rastreável à fonte;
- limitações e necessidade de validação humana aparecem no roteiro;
- entrega final separa validação técnica, qualidade econômica do score e aprovação comercial da equipe Bloomberg.
```

## 7. Fontes de pesquisa usadas no planejamento

- Bloomberg Terminal: https://www.bloomberg.com/professional/solution/bloomberg-terminal/
- Bloomberg UX: https://www.bloomberg.com/ux/
- CVM Informe Diário: https://dados.cvm.gov.br/dataset/fi-doc-inf_diario
- Banco Central IF.data: https://www3.bcb.gov.br/ifdata/
- ANBIMA Developers: https://developers.anbima.com.br/pt/documentacao/fundos/introducao-aos-pacotes/
- ANPD — Legítimo Interesse: https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_hipoteses_legais_tratamento_de_dados_pessoais_legitimo_interesse
- Leandro Pena: https://br.linkedin.com/in/leandro-pena-332478112
- Yasmin La Manna: https://br.linkedin.com/in/yasmin-la-manna-m-pilatti-160a3b97/pt
- Webinar oficial com Yasmin La Manna: https://events.bloombergevents.com/event/website/84a943f7-9fd1-4762-b6a3-f16338461a98/landingPage
- Skills: https://skills.sh/
