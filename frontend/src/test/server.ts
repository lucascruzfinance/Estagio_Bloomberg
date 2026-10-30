// Test-only network layer: real API responses captured from the loaded database.
// The running app never reads these fixtures.
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import accountBtg from './fixtures/account-btg.json'
import accountVerde from './fixtures/account-verde.json'
import accounts from './fixtures/accounts.json'
import comparison from './fixtures/comparison.json'
import conflicts from './fixtures/conflicts.json'
import explanationBtgTrading from './fixtures/explanation-btg-trading.json'
import explanationVerde from './fixtures/explanation-verde.json'
import fundsVerde from './fixtures/funds-verde.json'
import meta from './fixtures/meta.json'
import performanceVerde from './fixtures/performance-verde.json'
import quality from './fixtures/quality.json'
import ready from './fixtures/ready.json'
import scores from './fixtures/scores.json'
import search from './fixtures/search.json'

export const fixtures = {
  accountBtg,
  accountVerde,
  accounts,
  comparison,
  conflicts,
  explanationBtgTrading,
  explanationVerde,
  fundsVerde,
  meta,
  performanceVerde,
  quality,
  ready,
  scores,
  search,
}

const explanations: Record<string, unknown> = {
  'org-verde-asset': explanationVerde,
  'org-btg-pactual:sales-trading-treasury': explanationBtgTrading,
}
const accountsById: Record<string, unknown> = {
  'org-verde-asset': accountVerde,
  'org-btg-pactual': accountBtg,
}

function notFound(path: string) {
  return HttpResponse.json(
    { type: 'not-found', title: 'Recurso não encontrado', status: 404, detail: 'fixture ausente', instance: path, request_id: 'test-404' },
    { status: 404, headers: { 'Content-Type': 'application/problem+json' } },
  )
}

export const handlers = [
  http.get('*/ready', () => HttpResponse.json(ready)),
  http.get('*/api/v1/meta', () => HttpResponse.json(meta)),
  http.get('*/api/v1/scores', () => HttpResponse.json(scores)),
  http.get('*/api/v1/accounts', () => HttpResponse.json(accounts)),
  http.get('*/api/v1/accounts/:id', ({ params }) => {
    const body = accountsById[String(params.id)]
    return body ? HttpResponse.json(body) : notFound(`/api/v1/accounts/${String(params.id)}`)
  }),
  http.get('*/api/v1/scores/:unit/explanation', ({ params }) => {
    const body = explanations[decodeURIComponent(String(params.unit))]
    return body ? HttpResponse.json(body) : HttpResponse.json(explanationVerde)
  }),
  http.get('*/api/v1/comparisons', () => HttpResponse.json(comparison)),
  http.get('*/api/v1/data-quality', () => HttpResponse.json(quality)),
  http.get('*/api/v1/data-quality/conflicts', () => HttpResponse.json(conflicts)),
  http.get('*/api/v1/search', () => HttpResponse.json(search)),
  http.get('*/api/v1/funds', () => HttpResponse.json(fundsVerde)),
  http.get('*/api/v1/funds/:cnpj/performance', () => HttpResponse.json(performanceVerde)),
  http.get('*/api/v1/signals', () => HttpResponse.json({ data: [], meta: { page: 1, page_size: 50, total: 0 } })),
]

export const server = setupServer(...handlers)
