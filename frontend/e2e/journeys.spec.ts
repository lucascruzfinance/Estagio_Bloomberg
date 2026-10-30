import { expect, freshStart, rankingRows, test } from './fixtures'

test.describe('jornadas comerciais', () => {
  test('filtro mantém ranking e mapa sincronizados', async ({ page }) => {
    await freshStart(page)
    await expect(rankingRows(page)).toHaveCount(22)

    await page.getByRole('combobox', { name: 'Faixa', exact: true }).selectOption('Prioridade agora')
    await expect(page).toHaveURL(/tier=Prioridade/)
    await expect.poll(() => rankingRows(page).count()).toBeLessThan(22)
    const ranked = await rankingRows(page).count()
    expect(ranked).toBeGreaterThan(0)

    const rankingRowsAttr = async (target: typeof page) =>
      (await rankingRows(target).evaluateAll((rows) => rows.map((row) => row.getAttribute('data-unit') ?? '')))
    const unitsBefore = await rankingRowsAttr(page)
    await page.getByRole('link', { name: /Mapa/ }).click()
    await expect(page).toHaveURL(/\/mapa\?.*tier=Prioridade/)
    const mapList = page.getByRole('complementary', { name: 'Contas no mapa' }).locator('li')
    // The map lists accounts; bank desks of the same account collapse into one entry.
    const units = unitsBefore
    const accountsInRanking = new Set(units.map((unit) => unit.split(':')[0])).size
    await expect(mapList).toHaveCount(accountsInRanking)
    await expect(page.getByText(`${ranked} de 22 unidades`)).toBeVisible()

    // Selecting on the map list carries the selection back to the ranking.
    await mapList.nth(1).getByRole('button').click()
    await expect(page).toHaveURL(/unit=/)
    await page.getByRole('link', { name: /Prioridade/ }).first().click()
    await expect(page.getByRole('article', { name: /Conta 360 de/ })).toBeVisible()
    await expect(rankingRows(page).and(page.locator('[aria-selected="true"]'))).toHaveCount(1)
  })

  test('seleção abre Conta 360 com fontes, fatores e gráfico do fundo', async ({ page }) => {
    await freshStart(page)
    await rankingRows(page).filter({ hasText: 'Verde Asset Management' }).click()
    const panel = page.getByRole('article', { name: 'Conta 360 de Verde Asset Management' })
    await expect(panel.getByText('Por que está aqui')).toBeVisible()
    await expect(panel.getByRole('link', { name: /Cadastro de gestores \(CVM\)/ })).toHaveAttribute('href', /dados\.cvm\.gov\.br/)

    await panel.getByRole('link', { name: 'Abrir conta 360' }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Verde Asset Management' })).toBeVisible()
    await expect(page.getByRole('table', { name: 'Fatores de fit' })).toBeVisible()
    await expect(page.getByRole('table', { name: 'Fatores de timing' })).toBeVisible()
    await expect(page.getByRole('img', { name: /Evolução da cota/ })).toBeVisible()
    await expect(page.locator('.chart canvas')).toHaveCount(1)
  })

  test('comparação de unidades pelo ranking', async ({ page }) => {
    await freshStart(page)
    await page.getByRole('checkbox', { name: 'Comparar Verde Asset Management' }).check()
    await page.getByRole('checkbox', { name: /Comparar BTG Pactual — Sales/ }).check()
    await expect(page.getByRole('link', { name: /Comparador \(2\)/ })).toBeVisible()
    await page.getByRole('link', { name: /Comparador/ }).click()
    const table = page.getByRole('table', { name: 'Comparação de unidades' })
    await expect(table.getByRole('columnheader')).toHaveCount(3)
    await expect(page.getByText(/mistura unidades observadas/)).toBeVisible()
    await expect(table.getByRole('rowheader', { name: /Captação\/resgates/ })).toBeVisible()
  })

  test('teclado: telas, seleção, comparação e busca', async ({ page }) => {
    await freshStart(page)
    await rankingRows(page).first().focus()
    await page.keyboard.press('ArrowDown')
    await expect(page).toHaveURL(/unit=/)
    await page.keyboard.press('Space')
    await expect(page.getByRole('link', { name: /Comparador \(1\)/ })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('article')).toHaveCount(0)

    await page.keyboard.press('4')
    await expect(page.getByRole('heading', { level: 1, name: 'Qualidade dos dados' })).toBeVisible()
    await page.keyboard.press('/')
    await expect(page.getByRole('combobox', { name: /Buscar conta/ })).toBeFocused()
    await page.keyboard.type('19.749.539')
    await expect(page.getByRole('option').first()).toContainText('Verde')
    await page.keyboard.press('Enter')
    await expect(page.getByRole('heading', { level: 1, name: 'Verde Asset Management' })).toBeVisible()
  })

  test('mapa: tooltip enxuto e densidade sem sugerir performance', async ({ page }) => {
    await freshStart(page, '/mapa?unit=org-kapitalo')
    const canvas = page.locator('.maplibregl-canvas')
    await expect(canvas).toBeVisible()
    await page.waitForFunction(() => document.querySelectorAll('.maplibregl-ctrl').length > 0)
    await page.waitForTimeout(2500) // tiles and fly-to animation

    // Hover over the selected office (map is centered on it after the fly-to).
    const box = (await canvas.boundingBox())!
    const popup = page.locator('.maplibregl-popup-content')
    for (const [dx, dy] of [[0, 0], [2, 2], [-2, -2], [4, 0], [0, 4]]) {
      await page.mouse.move(box.x + box.width / 2 + dx, box.y + box.height / 2 + dy)
      if (await popup.isVisible().catch(() => false)) break
      await page.waitForTimeout(250)
    }
    await expect(popup).toBeVisible()
    await expect(popup).toContainText('Telefone')
    await expect(popup).toContainText('Localização')
    await expect(popup).not.toContainText('@')
    await expect(popup).not.toContainText(/diretor/i)

    await page.getByRole('button', { name: 'Densidade' }).click()
    await expect(page.getByLabel('Legenda do mapa')).toContainText('Não representa performance')
  })
})
