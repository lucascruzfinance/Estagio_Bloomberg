# Revisão de segurança e privacidade

Escopo: repositório, pipeline de dados, banco, API e dashboard do MVP. Revisão feita em 30/10/2026 com varreduras reais, não só leitura de código. Itens marcados **corrigido** foram encontrados nesta revisão ou nos testes dos prompts 5–7.

## Resultado das varreduras

| Área | Como foi verificado | Resultado |
|---|---|---|
| Segredos no repositório | Busca da senha real do `.env` e de padrões de chave (AWS, GitHub, OpenAI, Slack, chaves privadas) em todos os arquivos versionáveis (169) | Nenhum segredo real. `.env` ignorado pelo git. A senha `local-development-only-change-me` aparece só como padrão de desenvolvimento documentado e é **recusada em produção** pela validação de configuração |
| Dependências Python | `pip-audit` em `project.lock` e `dev.lock` | Nenhuma vulnerabilidade conhecida |
| Dependências do dashboard | `npm audit` (produção e completo) | 0 vulnerabilidades |
| CORS | Pré-voo com origem estranha | Recusado (400); só GET e só as origens configuradas; sem credenciais |
| Hosts confiáveis | Requisição com `Host: evil.example` | 400 |
| Métodos | POST em rota de leitura | 405; a API não tem rota de escrita |
| Injeção | `sort=name;DROP TABLE…`, `q=' OR 1=1--` | 422 e lista vazia; toda ordenação vem de lista branca e todo valor é parâmetro ligado |
| Respostas de erro | 404, 422 e 500 forçado em teste | RFC 7807 sem stack trace, sem ecoar a entrada e com `request_id` |
| Cabeçalhos | `/api/v1/meta` | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, CSP `default-src 'none'`; **corrigido**: removido o cabeçalho `server: uvicorn` |
| Dashboard | Build de produção | **corrigido**: CSP restrita à própria origem e ao servidor de tiles; tooltip do mapa escapa HTML (teste dedicado) |
| Logs | 143 linhas da API em uso real | Sem e-mails, CPFs, senhas ou query strings; rotas registradas como template. **Corrigido**: tracebacks não gravam mais variáveis locais (teste de regressão) |
| Disponibilidade | Banco fora do ar | **Corrigido**: `/ready` travava ~130 s sem timeout de conexão; agora falha em ~2 s. Timeout de consulta de 5 s por requisição e rate limit local por cliente |
| Banco | Sessão da API | Transação `READ ONLY` (teste confirma que UPDATE é recusado) |
| Migrações em teste | Revisão de `migrations/env.py` | **Corrigido**: a URL explícita do chamador tem prioridade, eliminando o risco de um teste migrar ou apagar o banco principal |

## Dados pessoais (LGPD)

| Dado | Coletado? | Base e limite |
|---|---|---|
| Nome do diretor responsável pela gestão de carteiras (Res. CVM 21) | Sim, 15 registros | Registro regulatório público; uso restrito ao planejamento de conta; outros cargos (compliance, risco, PLD) não são coletados |
| E-mails | Só caixas institucionais (compliance@, juridico@ etc.) | E-mails pessoais do cadastro CVM são descartados na coleta; nenhum aparece nas saídas versionadas (19 endereços, todos institucionais) |
| Telefones | Só os institucionais do cadastro CVM | Exibidos na Conta 360 e no tooltip do mapa |
| LinkedIn | Não | Links da planilha original não são exibidos nem raspados |
| Tooltip do mapa | Somente dados institucionais | Teste unitário e E2E garantem ausência de e-mail e de nomes de pessoas |

## Riscos residuais e recomendações

1. **Autenticação ausente.** A API e o dashboard não têm login; servem só em `127.0.0.1`. Antes de qualquer uso compartilhado: SSO corporativo na borda (proxy), HTTPS e rate limit no gateway.
2. **Rate limit em memória.** Por processo e por IP; atrás de proxy vê o IP do proxy. Em produção, aplicar na borda.
3. **Senha local do banco.** Gerada aleatoriamente e guardada só no `.env`; o cluster escuta apenas em localhost.
4. **Basemap de terceiro.** O navegador consulta `tiles.openfreemap.org` (sem dados do usuário além do IP e da área visualizada). Para uso corporativo, servir tiles internamente.
5. **Revisão humana dos vínculos.** Erros de grupo econômico são um risco de qualidade, não de segurança; a fila de revisão está em `data/review/conflicts.csv`.
6. **Cache bruto local.** `data/raw` contém arquivos públicos da CVM (inclui e-mails pessoais publicados no cadastro original); fica fora do git e não deve ser redistribuído.
