import { expect, test } from '@playwright/test'

// Simulates the presentation room without internet: anything outside localhost fails.
// Blocked requests log network errors by design, so this spec only forbids uncaught
// page exceptions instead of using the console-clean fixture.
test.describe('demonstração sem internet', () => {
  test.beforeEach(async ({ context }) => {
    await context.route('**/*', (route) => {
      const host = new URL(route.request().url()).hostname
      return host === '127.0.0.1' || host === 'localhost' ? route.continue() : route.abort('internetdisconnected')
    })
  })

  test('ranking, conta e mapa continuam utilizáveis', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (error) => pageErrors.push(error.message))

    await page.goto('/')
    await expect(page.getByRole('table', { name: 'Ranking de unidades' }).locator('tbody tr')).toHaveCount(22)

    await page.goto('/contas/org-verde-asset')
    await expect(page.getByRole('heading', { level: 1, name: 'Verde Asset Management' })).toBeVisible()
    await expect(page.getByRole('img', { name: /Evolução da cota/ })).toBeVisible()

    await page.goto('/mapa?unit=org-kapitalo')
    await expect(page.getByText(/Mapa de fundo indisponível/)).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('.maplibregl-canvas')).toBeVisible()
    await expect(page.getByText(/endereços no mapa/)).toBeVisible()

    // Fonts are self-hosted: no request ever left localhost successfully.
    const fonts = await page.evaluate(() => [...document.fonts].filter((font) => font.status === 'loaded').map((font) => font.family))
    expect(fonts.some((family) => family.includes('Inter'))).toBe(true)
    expect(pageErrors).toEqual([])
  })
})
