# Roteiro da demonstração

Público: Sales Team Leader de Brazil Buy-Side e Sales Team Leader de Banks and Brokers. Mensagem central: **não estou prevendo quem compra; estou reduzindo o tempo para preparar uma conta e deixando explícito por que ela entra na fila, com fonte para cada número.**

Números citados abaixo vêm da base carregada (dados públicos até 27/10/2026, modelo `opportunity-v1.0.0`). Se a base for recarregada, confira-os na tela antes de falar.

## Antes de entrar na sala (10 min)

1. `python scripts/demo.py` e abrir http://127.0.0.1:4173 (selo **DEMO** no topo indica base congelada). Não substitua o `.env` desta máquina pelo `.env.example`: ele guarda a porta e a senha do banco local.
2. Tela em 1366×768 ou maior; zoom do navegador em 100%.
3. Abrir uma vez Ranking, Mapa e Conta 360 da Verde para aquecer o cache.
4. Plano B sem internet: o mapa mostra os escritórios sobre fundo liso com aviso; todo o resto funciona. Se a API cair, rodar o mesmo comando de novo (sobe do zero em ~2 min).

## Versão de 90 segundos

1. **Problema (15 s).** Preparar uma conta hoje significa juntar CVM, site, LinkedIn e planilha; leva horas e cada vendedor prioriza de um jeito. A hipótese de que "fundo que performa bem compra Terminal" não está demonstrada.
2. **Proposta (15 s).** Três leituras separadas: *fit* (o workflow depende de dados?), *timing* (há mudança recente que abre conversa?) e *confiança* (quanto disso está apoiado em fonte recente). Onde falta dado, mostro uma faixa, não um zero.
3. **Demonstração (45 s).**
   - Ranking (tecla `1`): 22 unidades das 12 contas; os bancos aparecem por mesa.
   - Selecionar **Verde Asset Management**: fit 64, timing 38, confiança 86. Por quê: 6 famílias de estratégia, 28,6% das estratégias com mandato exterior, mas captação líquida de −R$ 2,2 bi em 12 meses. Telefone e endereço vêm do cadastro da CVM, com link.
   - Mapa (tecla `2`): corredor da Faria Lima; ponto cheio é endereço exato, anel é aproximado.
4. **Limitações e próximo passo (15 s).** Os pesos são premissas: ainda não há dado de conversão para calibrar. As mesas dos bancos são hipóteses, e os vínculos entre entidades precisam de revisão humana. O próximo passo é validar o ranking com vocês num piloto de 4 semanas e medir se reduz o tempo de preparação.

## Versão de 5 minutos

### 0:00 – 0:40 Problema e hipótese corrigida

- O trabalho do analista é deixar o vendedor pronto para a conversa certa, na área certa, na hora certa.
- Comecei com a hipótese "performance do fundo → assinatura". Ela tem viés de sobrevivência, confunde retorno do fundo com lucro da gestora e não tem dado de conversão para ser testada. Por isso performance entra com no máximo 10% do peso de timing.
- O produto separa **fit estrutural**, **timing comercial** e **confiança dos dados**. A confiança nunca altera o fit nem o timing.

### 0:40 – 1:40 Ranking e explicação (Buy-Side)

- Tecla `1`. Mostrar a coluna de faixa: o ponto é o que está observado; a faixa cinza é quanto o score pode mudar com os dados que faltam.
- Topo: BTG Wealth & Family Office (prioridade 78), BTG Asset Management (70), Portofino (67), Kinea (60).
- Ser honesto sobre o primeiro lugar: o BTG Wealth lidera por **escala de plataforma** (35 fundos abertos lançados em 12 meses, 67,7% das estratégias com mandato exterior), não por sofisticação de gestão. Isso está escrito nas limitações.
- Final da lista: Constellation (prioridade 18). Clicar e mostrar os sinais negativos: captação líquida de −28,1% do PL inicial e retorno 12m 11,9 pontos abaixo dos pares, agravado pelo choque de 26/10/2026 nas classes de ações. É timing ruim, não fit ruim: research de ações é workflow intensivo em dados.

### 1:40 – 2:40 Conta 360 (preparação da reunião)

- `Enter` na Verde. Mostrar:
  - fatores de fit e timing com peso, valor normalizado, pontos e evidência;
  - gráfico de cota do Verde Master: +12,8% em 12 meses, com a nota "retorno do fundo, não lucro da gestora";
  - entidades e contato institucional (cadastro CVM), escritórios com precisão, diretor de gestão registrado (dado regulatório público; nada de LinkedIn);
  - workflows a explorar: são **hipóteses** para a conversa, não intenção de compra.

### 2:40 – 3:30 Bancos por mesa (Banks and Brokers)

- Abrir BTG Pactual na Conta 360 e alternar entre as mesas.
- Asset Management e Wealth são **observados** (entidades CVM mapeadas). Sales & Trading, Research, Risco e Market Data são **premissas** marcadas como tal: fit por premissa editável, timing desconhecido, confiança baixa (≈ 26–29).
- O ponto para a banca: a resposta não é "vender um Terminal ao banco", e sim identificar a área e o workflow (B-PIPE e FXGO para trading, Data License para dados e risco, MARS e BVAL para risco e precificação).
- IF.data do Banco Central estava indisponível na coleta (HTTP 500 após retries); a tela avisa em vez de esconder.

### 3:30 – 4:10 Comparador e qualidade

- Tecla `3`: Verde × SPX × BTG Sales & Trading. O próprio comparador avisa que mistura unidades observadas com mesas por premissa.
- Tecla `4`: freshness por fonte, cobertura por conta e fila de revisão humana (9 conflitos pendentes; por exemplo, a planilha diz 17º andar para a Jive e a CVM diz 18º, com CEP diferente).

### 4:10 – 4:40 Limitações (dizer em voz alta)

1. Os pesos são premissas especialistas; não há resultado comercial para calibrar.
2. A CVM só vê veículos no Brasil: fundos offshore não entram. Por isso uma checagem de sanidade falha e eu a deixei falhando: a SPX (macro global) aparece com fit menor que a Portofino.
3. 30% do peso de timing (contratações, M&A, mudanças operacionais) depende de sinais curados com fonte, ainda vazios. As faixas mostram esse efeito.
4. Vínculos de afiliadas e as 12 mesas de banco precisam de validação humana.
5. Endereço exato só quando o número da porta foi conferido; 18 endereços ficaram sem coordenada.

### 4:40 – 5:00 Próximos passos e pedido

- Piloto de 4 semanas com 2 vendedores (1 Buy-Side, 1 Banks and Brokers), medindo o que está em `docs/pilot_metrics.md`: tempo de preparação, cobertura, aceitação do ranking, reuniões e conversão.
- Curar sinais de timing com fonte e ligar o CRM para calibrar os pesos.
- Pedido concreto: 30 minutos com cada um de vocês para validar as 12 contas e as mesas dos bancos.

## Perguntas prováveis

| Pergunta | Resposta curta |
|---|---|
| Isso prevê quem vai comprar? | Não. Prioriza e explica. Sem histórico de oportunidades não existe modelo preditivo honesto; a interface de calibração está pronta para quando houver. |
| Por que o BTG Wealth está em primeiro? | Escala da plataforma e lançamentos; a limitação está documentada. Com sinais de contratação e dados de headcount o fit mediria sofisticação, não só escala. |
| De onde vêm os telefones? | Cadastro de administradores de carteira da CVM, com data e link. E-mails pessoais foram descartados na coleta. |
| E LGPD? | Só dado institucional e o diretor de gestão registrado na CVM (registro público), para planejamento de conta. Nada de LinkedIn autenticado. |
| Como sei que os números estão certos? | `docs/validation_report.md`: um script independente recalcula scores, retornos, séries e coordenadas a partir dos arquivos brutos e compara com a API. |
| Quanto custa manter? | Fontes públicas e gratuitas; o enriquecimento roda em minutos e é idempotente. Escalar para centenas de contas pede revisão humana proporcional dos vínculos. |
