import type { FactorOut } from '../api/types'
import { EvidenceText } from './SourceLink'
import { SERIES } from './ScoreBand'

const STATUS_LABEL: Record<string, string> = {
  observed: 'observado',
  proxy: 'proxy',
  assumption: 'premissa',
  missing: 'sem evidência',
}

/** Factor-by-factor account of a score: weight, normalised value, points, evidence. */
export function FactorTable({ factors, group }: { factors: FactorOut[]; group: 'fit' | 'timing' }) {
  const rows = factors.filter((factor) => factor.group === group)
  const color = group === 'fit' ? SERIES.fit : SERIES.timing
  return (
    <table className="grid grid--compact" aria-label={group === 'fit' ? 'Fatores de fit' : 'Fatores de timing'}>
      <thead>
        <tr>
          <th scope="col">Fator</th>
          <th scope="col" className="num-col">
            Peso
          </th>
          <th scope="col">Valor 0–1</th>
          <th scope="col" className="num-col">
            Pontos
          </th>
          <th scope="col">Evidência</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((factor) => (
          <tr key={factor.key} style={{ cursor: 'default' }}>
            <td>
              {factor.label}
              <div className="muted" style={{ fontSize: 'var(--fs-xs)' }}>
                {STATUS_LABEL[factor.status] ?? factor.status}
              </div>
            </td>
            <td className="num-col num">{factor.weight === null || factor.weight === undefined ? '—' : `${Math.round(factor.weight * 100)}%`}</td>
            <td>
              <div className="factor-cell">
                <span className="num">{factor.value === null || factor.value === undefined ? '—' : factor.value.toFixed(2).replace('.', ',')}</span>
                <span className="factor-bar" aria-hidden="true">
                  {factor.value === null || factor.value === undefined ? (
                    <span className="band__unknown" style={{ left: 0, right: 0 }} />
                  ) : (
                    <span
                      className="factor-bar__fill"
                      style={{
                        width: `${factor.value * 100}%`,
                        background: factor.status === 'assumption' ? 'var(--band-range)' : color,
                      }}
                    />
                  )}
                </span>
              </div>
            </td>
            <td className="num-col num">
              {factor.contribution_points === null || factor.contribution_points === undefined
                ? '—'
                : factor.contribution_points.toFixed(1).replace('.', ',')}
            </td>
            <td style={{ whiteSpace: 'normal', minWidth: 220, fontSize: 'var(--fs-sm)', padding: '4px 8px' }}>
              <div>{factor.explanation}</div>
              {factor.evidence.length ? (
                <div className="muted" style={{ fontSize: 'var(--fs-xs)' }}>
                  <EvidenceText text={factor.evidence[0] ?? ''} />
                </div>
              ) : null}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
