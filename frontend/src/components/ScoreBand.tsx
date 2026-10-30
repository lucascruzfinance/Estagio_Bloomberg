import type { ScoreBand as Band } from '../api/types'
import { score } from '../lib/format'

export const SERIES = {
  priority: 'var(--ink)',
  fit: 'var(--series-fit)',
  timing: 'var(--series-timing)',
} as const

interface Props {
  band: Band | null | undefined
  label: string
  color?: string
  wide?: boolean
}

const clamp = (value: number) => Math.max(0, Math.min(100, value))

/**
 * The product's signature glyph: the observed score as a point over the range it
 * could take if every missing factor were 0 or 1. Missing data widens the band
 * instead of silently counting as zero.
 */
export function ScoreBand({ band, label, color = SERIES.priority, wide = false }: Props) {
  if (!band) {
    return (
      <span className={`band${wide ? ' band--wide' : ''}`} aria-label={`${label}: sem score`}>
        <span className="band__value muted">—</span>
        <span className="band__track" />
      </span>
    )
  }
  const lower = clamp(band.lower)
  const upper = clamp(band.upper)
  const point = band.point === null || band.point === undefined ? null : clamp(band.point)
  const range = upper - lower >= 0.5 ? `faixa ${score(lower)}–${score(upper)}` : 'sem dados ausentes'
  const description =
    point === null
      ? `${label}: sem evidência observada, ${range}`
      : `${label}: ${score(point)} de 100, ${range}`
  return (
    <span className={`band${wide ? ' band--wide' : ''}`} role="img" aria-label={description} title={description}>
      <span className={`band__value${point === null ? ' muted' : ''}`}>{score(point)}</span>
      <span className="band__track">
        {point === null ? (
          <span className="band__unknown" style={{ left: `${lower}%`, right: `${100 - upper}%` }} />
        ) : (
          <>
            <span className="band__range" style={{ left: `${lower}%`, width: `${Math.max(upper - lower, 0)}%` }} />
            <span className="band__point" style={{ left: `${point}%`, background: color }} />
          </>
        )}
      </span>
    </span>
  )
}
