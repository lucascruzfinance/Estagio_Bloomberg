// Refresh the Vitest fixtures from the running API (real data, used only in tests).
// Usage: node scripts/capture-fixtures.mjs   (API on http://127.0.0.1:8000)
import { writeFileSync } from 'node:fs'

const base = process.env.API_ORIGIN ?? 'http://127.0.0.1:8000'
const targets = {
  meta: '/api/v1/meta',
  scores: '/api/v1/scores?page_size=200',
  accounts: '/api/v1/accounts?page_size=200&sort=priority',
  'account-verde': '/api/v1/accounts/org-verde-asset',
  'explanation-verde': '/api/v1/scores/org-verde-asset/explanation',
  'explanation-btg-trading': '/api/v1/scores/org-btg-pactual:sales-trading-treasury/explanation',
  'account-btg': '/api/v1/accounts/org-btg-pactual',
  comparison: '/api/v1/comparisons?units=org-verde-asset,org-btg-pactual:sales-trading-treasury',
  quality: '/api/v1/data-quality',
  conflicts: '/api/v1/data-quality/conflicts?status=pending_review&page_size=200',
  search: '/api/v1/search?q=verde&limit=8',
  ready: '/ready',
  'funds-verde': '/api/v1/funds?account_id=org-verde-asset&with_metrics=true&fund_of_funds=false&sort=nav&page_size=12',
}
for (const [name, path] of Object.entries(targets)) {
  const response = await fetch(base + path)
  if (!response.ok) throw new Error(`${path} → ${response.status}`)
  writeFileSync(`src/test/fixtures/${name}.json`, JSON.stringify(await response.json()))
}
const funds = (await import('./../src/test/fixtures/funds-verde.json', { with: { type: 'json' } })).default
const first = funds.data[0]
const perf = await fetch(`${base}/api/v1/funds/${first.class_cnpj}/performance?subclass_id=${first.subclass_id}`)
writeFileSync('src/test/fixtures/performance-verde.json', JSON.stringify(await perf.json()))
console.log(`${Object.keys(targets).length + 1} fixtures refreshed from ${base}`)
