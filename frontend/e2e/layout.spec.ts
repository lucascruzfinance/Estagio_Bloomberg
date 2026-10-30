import AxeBuilder from '@axe-core/playwright'
import { expect, freshStart, test } from './fixtures'

const SCREENS: Array<[string, string]> = [
  ['ranking', '/'],
  ['ranking com painel', '/?unit=org-verde-asset'],
  ['mapa', '/mapa?unit=org-kapitalo'],
  ['comparador', '/comparar?units=org-verde-asset,org-spx-capital,org-btg-pactual:sales-trading-treasury'],
  ['conta 360', '/contas/org-verde-asset'],
  ['conta 360 banco', '/contas/org-btg-pactual?unit=org-btg-pactual:asset-management'],
  ['qualidade', '/qualidade'],
]

for (const [name, path] of SCREENS) {
  test(`${name}: sem overflow, texto cortado ou violação de acessibilidade`, async ({ page }) => {
    await freshStart(page, path)
    await page.waitForLoadState('load')
    await expect(page.locator('.skeleton')).toHaveCount(0, { timeout: 15_000 })
    if (path.startsWith('/mapa')) await page.waitForTimeout(1500)

    const layout = await page.evaluate(() => {
      const root = document.documentElement
      // Headings, buttons, badges and tile values must never clip; long names in
      // table cells use an intentional ellipsis with the full text in a title.
      const clipped = [...document.querySelectorAll<HTMLElement>('h1, h2, h3, .button, .badge, .tier, .tile__value, .nav__link, label')]
        .filter((el) => el.offsetParent !== null && el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflow !== 'visible')
        .map((el) => el.textContent?.trim().slice(0, 40))
      const ellipsisWithoutTitle = [...document.querySelectorAll<HTMLElement>('.name-cell, .unit-name__text')]
        .filter((el) => el.scrollWidth > el.clientWidth + 1 && !el.title && !el.closest('[title]'))
        .map((el) => el.textContent?.trim().slice(0, 40))
      return {
        horizontal: root.scrollWidth > window.innerWidth,
        vertical: root.scrollHeight > window.innerHeight,
        clipped,
        ellipsisWithoutTitle,
      }
    })
    expect(layout.horizontal, 'page scrolls horizontally').toBe(false)
    expect(layout.vertical, 'page scrolls vertically (panes should scroll instead)').toBe(false)
    expect(layout.clipped).toEqual([])
    expect(layout.ellipsisWithoutTitle).toEqual([])

    const results = await new AxeBuilder({ page })
      .exclude('.maplibregl-canvas')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()
    const serious = results.violations
      .filter((violation) => ['serious', 'critical'].includes(violation.impact ?? ''))
      .map((violation) => `${violation.id}: ${violation.nodes.slice(0, 3).map((node) => node.target.join(' ')).join(' | ')}`)
    expect(serious).toEqual([])
  })
}
