import { Link } from 'react-router'

const TIER_STYLE: Record<string, { color: string; hollow?: boolean }> = {
  'Prioridade agora': { color: 'var(--amber)' },
  'Desenvolver relacionamento': { color: 'var(--series-fit)' },
  'Oportunidade tática': { color: 'var(--series-timing)' },
  Monitorar: { color: 'var(--ink-3)' },
  'Fit alto — timing desconhecido': { color: 'var(--series-fit)', hollow: true },
  'Fit baixo — timing desconhecido': { color: 'var(--ink-3)', hollow: true },
  'Evidência insuficiente': { color: 'var(--ink-3)', hollow: true },
}

/** Short display labels; the canonical tier name stays in the title and filters. */
export const TIER_LABEL: Record<string, string> = {
  'Fit alto — timing desconhecido': 'Fit alto, sem timing',
  'Fit baixo — timing desconhecido': 'Fit baixo, sem timing',
}

export function TierBadge({ tier }: { tier: string }) {
  const style = TIER_STYLE[tier] ?? { color: 'var(--ink-3)', hollow: true }
  return (
    <span className="tier" title={tier}>
      <span
        className="tier__mark"
        aria-hidden="true"
        style={
          style.hollow
            ? { border: `1.5px solid ${style.color}` }
            : { background: style.color }
        }
      />
      {TIER_LABEL[tier] ?? tier}
    </span>
  )
}

export function AssumptionBadge() {
  return (
    <span className="badge badge--assumption" title="Mesa pontuada por premissa editável, sem entidade pública própria">
      premissa
    </span>
  )
}

export function ConflictBadge({ count, accountId }: { count: number; accountId: string }) {
  if (count <= 0) return null
  return (
    <Link
      to={`/qualidade?conta=${accountId}`}
      className="badge badge--conflict"
      title="Planilha e fonte oficial divergem; aguardando revisão humana"
      onClick={(event) => event.stopPropagation()}
    >
      <span aria-hidden="true">⚑</span> {count} {count === 1 ? 'conflito' : 'conflitos'}
    </Link>
  )
}

export function FreshnessBadge({ status }: { status: string }) {
  if (status === 'fresh') return null
  if (status === 'stale') {
    return (
      <span className="badge badge--stale">
        <span aria-hidden="true">◷</span> dado vencido
      </span>
    )
  }
  if (status === 'unavailable') {
    return (
      <span className="badge badge--unavailable">
        <span aria-hidden="true">✕</span> fonte indisponível
      </span>
    )
  }
  return <span className="badge badge--assumption">não usada</span>
}

export function PrecisionBadge({ exact, precision }: { exact: boolean; precision: string | null | undefined }) {
  if (exact) return <span className="badge badge--exact">endereço exato</span>
  const label =
    precision === 'street' ? 'aprox. rua' : precision === 'neighbourhood' ? 'aprox. bairro' : 'sem coordenada'
  return <span className="badge badge--approx">{label}</span>
}

export function DemoBadge() {
  return (
    <span className="badge badge--demo" title="Dado de demonstração, não vem da base real">
      DEMO
    </span>
  )
}
