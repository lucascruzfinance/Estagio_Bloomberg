# Auditoria da base de networking — Prompt 1

Status: **limited**  
Data da análise: 2026-10-29  
Fonte: `C:\Users\Lucas\Desktop\Networking_estagio_v2.xlsx`  
SHA-256: `f72d87c70ddaaf06c138e366bbfab00699183c74bf7b69d53902f14b7bfadfdd`

## Mandato e política de mudança

- Objetivo: preparar uma base auditável para o MVP de sales intelligence.
- Corpus autorizado: workbook informado por Lucas e `prompts_codex.md`.
- Modo: auditoria read-only do Excel; o arquivo original não foi modificado.
- Escopo: reconciliação global da estrutura e perfil detalhado apenas das 12 contas do piloto.
- Evidência: todo conteúdo extraído do workbook é `source_stated`, não fato independentemente verificado.
- Dados ausentes permanecem nulos. Não foram inventados CNPJ, pessoas, AUM, performance ou contatos.

## Inventário

- Abas: 30.
- Abas ocultas: nenhuma.
- Linhas institucionais atuais nas 11 abas de categorias: 396.
- Nomes únicos exatos: 319.
- Nomes únicos após apenas caixa/acentos/pontuação: 319.
- Linhas duplicadas adicionais sob essa normalização: 77 em 64 grupos.
- Fórmulas no workbook: 634; fórmulas contendo `#REF!`: 0.

## Abas auditadas no escopo obrigatório

| Aba | Dimensão usada | Registros/linhas úteis | Fórmulas | Diagnóstico |
| --- | --- | --- | --- | --- |
| Base Completa E | 215 x 17 | 211 | 211 | 211 nomes; a linha 215 está fora do range oficial e desalinhada |
| Resumo E | 54 x 7 | 44 | 131 | fórmulas limitadas à Base Completa E até a linha 214 |
| Progresso | 5 x 3 | 4 | 0 | controle hardcoded; não deriva da base |
| PE E | 48 x 9 | 42 | 0 | linhas institucionais; cabeçalhos de seção foram excluídos |
| Hedge Fund E | 101 x 9 | 97 | 0 | linhas institucionais; cabeçalhos de seção foram excluídos |
| Asset E | 86 x 9 | 80 | 0 | linhas institucionais; cabeçalhos de seção foram excluídos |
| Family Office E | 8 x 9 | 6 | 0 | linhas institucionais; cabeçalhos de seção foram excluídos |
| IB E | 46 x 9 | 40 | 0 | linhas institucionais; cabeçalhos de seção foram excluídos |
| Pendências E | 58 x 6 | 54 | 0 | cópia estática de pendências; a própria aba informa que não se atualiza |

As abas de categoria são fontes observacionais e podem repetir a mesma instituição em verticais
diferentes. O piloto não preserva essas repetições como contas distintas: os 12 `account_id` são
únicos e os aliases brutos ficam registrados para revisão. Não houve merge automático por fuzzy match.

## Reconciliação de 210 versus 287/395

1. `Progresso!B2:C2` contém texto hardcoded: `287` e `de 287 casas unicas (395 linhas nas abas)`. Não há fórmula nem regra de aliases que permita reproduzir 287.
2. As 11 abas de categorias contêm hoje **396** linhas com nome e tipo preenchidos, não 395. A contagem hardcoded está uma linha defasada.
3. Essas linhas produzem **319** nomes únicos com normalização mecânica. Chegar a 287 exigiria uma tabela de aliases/exclusões que não existe no arquivo.
4. `Base Completa E` contém **211** linhas com nome. Entretanto, `Resumo E!B4` usa `=COUNTA('Base Completa E'!$B$5:$B$214)`, que termina na linha 214 e contabiliza 210 registros.
5. `Base Completa E!B215:Q215` é um append posterior de `Brunel` com colunas desalinhadas em relação ao schema consolidado; por isso fica fora do resumo.

**Conclusão:** 287/395 é um controle estático de uma versão ou metodologia anterior. A fotografia atual é 396 observações categorizadas, 319 nomes mecanicamente únicos e 210 registros dentro do range oficial do resumo, mais uma linha malformada fora dele. O número autoritativo do MVP só poderá ser definido após tabela canônica de aliases e revisão humana.

## Perfil de dados nas abas de categorias

| Campo | Ausentes/Não encontrado | % de 396 |
| --- | --- | --- |
| Tipo (Empresa/Boutique/Fundo) | 0 | 0.0% |
| Linkedin | 125 | 31.6% |
| Email | 233 | 58.8% |
| Celular | 189 | 47.7% |
| Site | 20 | 5.1% |
| Observações | 1 | 0.3% |
| Canal de candidatura (25/10/2026) | 98 | 24.7% |
| Endereço SP/RJ (verificado) | 151 | 38.1% |

O preenchimento de endereço ou telefone não comprova atualidade nem adequação para prospecção. E-mail geral, canal de recrutamento e contato comercial são entidades diferentes e não devem ser substituídos entre si.

## Regras de normalização e deduplicação

1. Preservar o nome bruto e criar `canonical_name` separado.
2. Remover caixa, acentos e pontuação apenas para gerar chaves auxiliares; nunca usar fuzzy match para merge automático.
3. Confirmar entidade por CNPJ quando disponível. CNPJ da gestora, banco, fundo e veículo não são intercambiáveis.
4. Manter `group_name` separado da unidade operacional. Kinea e Itaú BBA pertencem ao mesmo grupo, mas não são a mesma unidade.
5. Bancos recebem `analysis_unit=mesa/área`; o conglomerado não recebe um score comercial único.
6. Alias ambíguo ou combinação como `Itaú BBA / Kinea` exige revisão humana.
7. Endereço com duas cidades deve virar dois registros de escritório no Prompt 2, não duas cidades em uma célula.
8. `Não encontrado` vira nulo, preservando a lacuna em `missing_fields`.

## Qualidade das 12 contas do piloto

| Conta | Confiança | Status no workbook | Lacunas | Flags |
| --- | --- | --- | --- | --- |
| SPX Capital | high | Sede fora de SP — escritório em SP citado | legal_name \| cnpj \| email_public \| phone_public | multiple_offices_in_single_field |
| Verde Asset Management | medium | Confirmado — endereço | legal_name \| cnpj \| verification_source_url \| as_of_date | verification_source_url_missing \| verification_date_missing |
| Kapitalo Investimentos | medium | Confirmado — endereço | legal_name \| cnpj \| verification_source_url \| as_of_date | verification_source_url_missing \| verification_date_missing |
| Ibiúna Investimentos | medium | Confirmado — endereço | legal_name \| cnpj \| email_public \| phone_public \| website_url \| verification_source_url \| as_of_date | verification_source_url_missing \| verification_date_missing |
| Kinea Investimentos | high | Confirmado — endereço | legal_name \| cnpj \| phone_public | sem flag adicional |
| Pátria Investimentos | medium | Confirmado — endereço | legal_name \| cnpj \| linkedin_url \| email_public \| phone_public | verification_source_is_non_primary |
| Vinci Compass | high | Sede fora de SP — escritório em SP citado | legal_name \| cnpj | multiple_offices_in_single_field |
| Constellation Asset Management | medium | Confirmado — endereço | legal_name \| cnpj \| linkedin_url \| verification_source_url \| as_of_date | verification_source_url_missing \| verification_date_missing |
| Jive Investments | medium | Confirmado — endereço | legal_name \| cnpj \| email_public \| phone_public | verification_source_is_non_primary |
| Portofino Gestão de Recursos | high | Confirmado — endereço | legal_name \| cnpj | sem flag adicional |
| BTG Pactual | medium | Confirmado — SP (sem endereço) | legal_name \| cnpj \| email_public | desk_level_mapping_required \| base_verification_source_is_aggregated \| verification_source_is_non_primary |
| Itaú BBA | medium | Confirmado — SP (sem endereço) | legal_name \| cnpj \| email_public \| verification_source_url \| as_of_date | verification_source_url_missing \| verification_date_missing \| desk_level_mapping_required \| base_record_is_group_level |

## Backlog priorizado de lacunas

### P0 — antes de qualquer score ou demonstração externa

1. Confirmar razão social e CNPJ de cada uma das 12 contas em fonte oficial.
2. Revisar a linha malformada `Base Completa E!B215:Q215` e decidir se Brunel pertence ao universo.
3. Criar tabela de aliases aprovada e reconciliar formalmente 396 -> universo canônico.
4. Separar BTG e Itaú por mesa/área; não usar contato, endereço ou estratégia do grupo como se servissem a todas as unidades.
5. Revalidar endereço e fonte das contas sem URL de verificação no consolidado.

### P1 — necessário para Account 360 confiável

1. Criar tabela de escritórios com um endereço por linha, data e precisão.
2. Separar contato institucional, imprensa, recrutamento e comercial.
3. Mapear fundos/veículos por CNPJ e gestor sem fuzzy match silencioso.
4. Registrar pessoas públicas somente quando necessárias ao workflow e com política LGPD aprovada.

### P2 — necessário antes de modelar timing comercial

1. Ingerir séries públicas de PL, cota, captação, resgate e cotistas com cobertura explícita.
2. Definir eventos comerciais e janela de validade.
3. Obter histórico real de oportunidades/conversões antes de qualquer modelo supervisionado.

## Critérios de aceite do Prompt 1

- Contagens reconciliadas: **concluído com alerta de controle estático**.
- Piloto com 12 `account_id` e nomes canônicos únicos: **concluído**.
- Proveniência por linha: **concluído** por locator e hash.
- Dados ausentes não inventados: **concluído**.
- Testes de unicidade e obrigatoriedade: **executados pelo pytest**.
- Aprovação humana: **pendente** para aliases, CNPJ, endereços e desk mapping.

## Gates

- G0 Mandato: ready.
- G1 Fonte: limited — várias linhas não têm fonte primária adjacente.
- G2 Extração: ready para o recorte do piloto.
- G3 Modelo: not-run; fora do Prompt 1.
- G4 Narrativa: limited — ainda não existe score nem evidência causal.
- G5 Entrega: ready após testes.
- G6 Julgamento: limited — aprovação humana explicitamente pendente.

Status geral: **limited**, limitado pela falta de identidade legal/CNPJ, fontes primárias completas e reconciliação canônica aprovada.
