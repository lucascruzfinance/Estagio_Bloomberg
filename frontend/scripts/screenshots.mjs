import { chromium } from '@playwright/test'
const out = process.argv[2]
const pages = [
  ['ranking', '/'],
  ['panel', '/?unit=org-verde-asset'],
  ['map', '/mapa?unit=org-kapitalo'],
  ['compare', '/comparar?units=org-verde-asset,org-spx-capital,org-btg-pactual:sales-trading-treasury'],
  ['account', '/contas/org-verde-asset'],
  ['account-bank', '/contas/org-btg-pactual?unit=org-btg-pactual:asset-management'],
  ['quality', '/qualidade'],
]
const browser = await chromium.launch()
for (const [w, h] of [[1366, 768], [1440, 900]]) {
  const context = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 })
  const page = await context.newPage()
  const errors = []
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message))
  for (const [name, path] of pages) {
    await page.goto('http://127.0.0.1:5173' + path, { waitUntil: 'load' })
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => undefined)
    await page.waitForTimeout(name === 'map' ? 3500 : 800)
    const overflow = await page.evaluate(() => ({ x: document.documentElement.scrollWidth > innerWidth, y: document.documentElement.scrollHeight > innerHeight }))
    await page.screenshot({ path: `${out}/${name}-${w}.png` })
    console.log(w, name, JSON.stringify(overflow))
  }
  console.log(w, 'errors:', JSON.stringify(errors.slice(0, 8)))
  await context.close()
}
await browser.close()
