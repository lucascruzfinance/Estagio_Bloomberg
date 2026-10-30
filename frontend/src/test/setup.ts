import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { server } from './server'

// jsdom gaps (real browsers implement these; Playwright covers them for real).
if (!Element.prototype.scrollIntoView) Element.prototype.scrollIntoView = () => undefined

beforeAll(() => server.listen({ onUnhandledFrame: 'error' }))
afterEach(() => {
  server.resetHandlers()
  cleanup()
  window.localStorage.clear()
})
afterAll(() => server.close())
