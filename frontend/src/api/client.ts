import type { components } from './schema'

export type Problem = components['schemas']['Problem']

/** Error carrying the API's RFC 7807 body and correlation id. */
export class ApiError extends Error {
  readonly status: number
  readonly requestId: string | null
  readonly problem: Problem | null

  constructor(status: number, message: string, requestId: string | null, problem: Problem | null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.requestId = requestId
    this.problem = problem
  }
}

type Params = Record<string, string | number | boolean | null | undefined>

export function buildUrl(path: string, params: Params = {}): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const query = search.toString()
  return query ? `${path}?${query}` : path
}

export async function apiGet<T>(path: string, params: Params = {}, signal?: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await fetch(buildUrl(path, params), {
      headers: { Accept: 'application/json' },
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, 'A API não respondeu. Verifique se o servidor está em execução.', null, null)
  }
  const requestId = response.headers.get('x-request-id')
  if (!response.ok) {
    let problem: Problem | null = null
    try {
      problem = (await response.json()) as Problem
    } catch {
      problem = null
    }
    const detail = problem?.detail ?? problem?.title ?? `HTTP ${response.status}`
    throw new ApiError(response.status, detail, problem?.request_id ?? requestId, problem)
  }
  return (await response.json()) as T
}
