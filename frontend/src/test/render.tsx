import { render } from '@testing-library/react'
import App, { createQueryClient } from '../App'

/** Render the whole app at a URL with a fresh query cache (no retries in tests). */
export function renderApp(url = '/') {
  window.history.pushState({}, '', url)
  const client = createQueryClient()
  client.setDefaultOptions({ queries: { retry: false, refetchOnWindowFocus: false } })
  return { client, ...render(<App client={client} />) }
}
