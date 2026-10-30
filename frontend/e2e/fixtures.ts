import { test as base, expect, type Page } from '@playwright/test'

/** Fails any test that logs a console error or throws in the page. */
export const test = base.extend<{ consoleErrors: string[] }>({
  consoleErrors: [
    async ({ page }, use) => {
      const errors: string[] = []
      page.on('console', (message) => {
        if (message.type() === 'error') errors.push(message.text())
      })
      page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
      await use(errors)
      expect(errors, 'console errors').toEqual([])
    },
    { auto: true },
  ],
})

export { expect }

export async function freshStart(page: Page, path = '/') {
  await page.goto('/')
  await page.evaluate(() => window.localStorage.clear())
  await page.goto(path)
}

export function rankingRows(page: Page) {
  return page.getByRole('table', { name: 'Ranking de unidades' }).locator('tbody tr')
}
