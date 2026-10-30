import type { ReactNode } from 'react'
import { ApiError } from '../api/client'

export function LoadingRows({ rows = 8, label = 'Carregando dados' }: { rows?: number; label?: string }) {
  return (
    <div className="state" role="status" aria-live="polite" style={{ placeItems: 'stretch' }}>
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="skeleton" style={{ width: `${92 - (index % 3) * 9}%` }} />
      ))}
    </div>
  )
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="state" role="status">
      <div className="state__title">{title}</div>
      {children ? <div>{children}</div> : null}
      {action}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const apiError = error instanceof ApiError ? error : null
  const offline = apiError?.status === 0
  const title = offline ? 'A API está fora do ar' : apiError?.status === 404 ? 'Não encontrado' : 'Não foi possível carregar'
  const detail = offline
    ? 'Inicie a API (uvicorn) e o banco local; a tela tenta de novo ao clicar abaixo.'
    : apiError?.message ?? 'Erro inesperado no navegador.'
  return (
    <div className="state" role="alert">
      <div className="state__title">{title}</div>
      <div>{detail}</div>
      {apiError?.requestId ? <div className="state__meta">request_id {apiError.requestId}</div> : null}
      {onRetry ? (
        <button type="button" className="button button--primary" onClick={onRetry}>
          Tentar de novo
        </button>
      ) : null}
    </div>
  )
}
