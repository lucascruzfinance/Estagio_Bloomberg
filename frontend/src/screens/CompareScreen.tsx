import { useEffect, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router'
import { useAccounts, useComparison, useScores } from '../api/hooks'
import { AssumptionBadge, TierBadge } from '../components/Badges'
import { SERIES, ScoreBand } from '../components/ScoreBand'
import { EmptyState, ErrorState, LoadingRows } from '../components/States'
import { MAX_COMPARE, setCompare, toggleCompare, useCompareSet } from '../lib/compare'
import { joinUnits, matchesFilters, useFilters } from '../lib/filters'
import { brlCompact, brlSigned, deltaClass, score } from '../lib/format'

const STATUS: Record<string, string> = {
  observed: 'observado',
  proxy: 'proxy',
  assumption: 'premissa',
  missing: 'sem evidência',
}

export function CompareScreen() {
  const [params, setParams] = useSearchParams()
  const compare = useCompareSet()
  const scores = useScores()
  const accounts = useAccounts()
  const { filters } = useFilters()

  // A shared link (?units=a,b) wins over the locally stored basket once.
  useEffect(() => {
    const fromUrl = params.get('units')
    if (fromUrl) {
      setCompare(fromUrl.split(',').filter(Boolean))
      const next = new URLSearchParams(params)
      next.delete('units')
      setParams(next, { replace: true })
    }
  }, [params, setParams])

  const comparison = useComparison(compare)
  const units = useMemo(
    () => joinUnits(scores.data?.data ?? [], accounts.data?.data ?? []),
    [scores.data, accounts.data],
  )
  const byKey = useMemo(() => new Map(units.map((unit) => [unit.unit_key, unit])), [units])
  const candidates = units.filter((unit) => matchesFilters(unit, filters) || compare.includes(unit.unit_key))

  const shareLink = `${window.location.origin}/comparar?units=${compare.map(encodeURIComponent).join(',')}`

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <h1 className="page__title">Comparador</h1>
          <p className="page__lede">
            Até {MAX_COMPARE} unidades lado a lado: os mesmos fatores, pesos e evidências do ranking. Adicione pela
            caixa de seleção do ranking ou pela lista abaixo.
          </p>
        </div>
        {compare.length ? (
          <div style={{ display: 'flex', gap: 6 }}>
            <button type="button" className="button" onClick={() => void navigator.clipboard?.writeText(shareLink)}>
              Copiar link
            </button>
            <button type="button" className="button button--ghost" onClick={() => setCompare([])}>
              Limpar seleção
            </button>
          </div>
        ) : null}
      </header>

      <details className="surface" style={{ padding: '8px 12px', marginBottom: 'var(--gap-4)' }} open={compare.length < 2}>
        <summary style={{ cursor: 'pointer' }}>
          Escolher unidades ({compare.length}/{MAX_COMPARE}) <span className="muted">lista segue os filtros ativos</span>
        </summary>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '2px 16px', marginTop: 8 }}>
          {candidates.map((unit) => (
            <label key={unit.unit_key} className="filter" style={{ color: 'var(--ink)' }}>
              <input
                type="checkbox"
                checked={compare.includes(unit.unit_key)}
                disabled={!compare.includes(unit.unit_key) && compare.length >= MAX_COMPARE}
                onChange={() => toggleCompare(unit.unit_key)}
              />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{unit.unit_name}</span>
            </label>
          ))}
        </div>
      </details>

      {compare.length < 2 ? (
        <EmptyState title="Escolha de 2 a 5 unidades para comparar">
          No ranking, marque a coluna Comparar ou pressione <kbd>Espaço</kbd> na linha selecionada.
        </EmptyState>
      ) : comparison.isLoading ? (
        <LoadingRows rows={10} label="Carregando comparação" />
      ) : comparison.error || !comparison.data ? (
        <ErrorState error={comparison.error} onRetry={() => void comparison.refetch()} />
      ) : (
        <>
          {comparison.data.warnings.map((warning) => (
            <p key={warning} className="callout" style={{ marginBottom: 8 }}>
              {warning}
            </p>
          ))}
          <div className="surface" style={{ overflowX: 'auto' }}>
            <table className="grid" aria-label="Comparação de unidades">
              <thead>
                <tr>
                  <th scope="col" style={{ width: 220 }}>
                    Critério
                  </th>
                  {comparison.data.units.map((unit) => (
                    <th key={unit.unit_key} scope="col">
                      <span style={{ display: 'flex', gap: 6, alignItems: 'center', justifyContent: 'space-between' }}>
                        <Link to={`/contas/${unit.account_id}?unit=${encodeURIComponent(unit.unit_key)}`} style={{ color: 'var(--ink)' }}>
                          {unit.unit_name}
                        </Link>
                        <button
                          type="button"
                          className="button button--ghost"
                          aria-label={`Remover ${unit.unit_name}`}
                          onClick={() => toggleCompare(unit.unit_key)}
                        >
                          ✕
                        </button>
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr style={{ cursor: 'default' }}>
                  <th scope="row" className="secondary" style={{ position: 'static', background: 'none', border: 0, borderBottom: '1px solid var(--line)' }}>
                    Faixa
                  </th>
                  {comparison.data.units.map((unit) => (
                    <td key={unit.unit_key}>
                      <TierBadge tier={unit.tier} /> {unit.evidence_mode === 'assumption' ? <AssumptionBadge /> : null}
                    </td>
                  ))}
                </tr>
                {(
                  [
                    ['Prioridade', 'priority', SERIES.priority],
                    ['Fit', 'fit', SERIES.fit],
                    ['Timing', 'timing', SERIES.timing],
                  ] as const
                ).map(([label, key, color]) => (
                  <tr key={key} style={{ cursor: 'default' }}>
                    <th scope="row" className="secondary" style={{ position: 'static', background: 'none', border: 0, borderBottom: '1px solid var(--line)' }}>
                      {label}
                    </th>
                    {comparison.data!.units.map((unit) => (
                      <td key={unit.unit_key}>
                        <ScoreBand band={unit[key]} label={label} color={color} wide />
                      </td>
                    ))}
                  </tr>
                ))}
                <tr style={{ cursor: 'default' }}>
                  <th scope="row" className="secondary" style={{ position: 'static', background: 'none', border: 0, borderBottom: '1px solid var(--line)' }}>
                    Confiança dos dados
                  </th>
                  {comparison.data.units.map((unit) => (
                    <td key={unit.unit_key} className="num">
                      {score(unit.confidence)}
                    </td>
                  ))}
                </tr>
                <tr style={{ cursor: 'default' }}>
                  <th scope="row" className="secondary" style={{ position: 'static', background: 'none', border: 0, borderBottom: '1px solid var(--line)' }}>
                    PL e captação 12m da conta
                  </th>
                  {comparison.data.units.map((unit) => {
                    const account = byKey.get(unit.unit_key)?.account
                    return (
                      <td key={unit.unit_key} className="num">
                        {brlCompact(account?.nav_brl_non_fic)}{' '}
                        <span className={deltaClass(account?.net_flow_12m_brl)}>{brlSigned(account?.net_flow_12m_brl)}</span>
                      </td>
                    )
                  })}
                </tr>
                {comparison.data.factors.map((factor) => (
                  <tr key={factor.key} style={{ cursor: 'default' }}>
                    <th scope="row" style={{ position: 'static', background: 'none', border: 0, borderBottom: '1px solid var(--line)', fontWeight: 400 }}>
                      <span className="muted" style={{ fontSize: 'var(--fs-xs)' }}>{factor.group === 'fit' ? 'Fit' : 'Timing'} </span>
                      {factor.label}
                    </th>
                    {comparison.data!.units.map((unit) => {
                      const cell = factor.values[unit.unit_key] as { value: number | null; status: string; points: number | null } | undefined
                      const value = cell?.value ?? null
                      return (
                        <td key={unit.unit_key}>
                          <div className="factor-cell" title={STATUS[cell?.status ?? 'missing']}>
                            <span className="num">{value === null ? '—' : value.toFixed(2).replace('.', ',')}</span>
                            <span className="factor-bar" aria-hidden="true">
                              {value === null ? (
                                <span className="band__unknown" style={{ left: 0, right: 0 }} />
                              ) : (
                                <span
                                  className="factor-bar__fill"
                                  style={{
                                    width: `${value * 100}%`,
                                    background:
                                      cell?.status === 'assumption'
                                        ? 'var(--band-range)'
                                        : factor.group === 'fit'
                                          ? SERIES.fit
                                          : SERIES.timing,
                                  }}
                                />
                              )}
                            </span>
                          </div>
                          <div className="muted" style={{ fontSize: 'var(--fs-xs)' }}>
                            {STATUS[cell?.status ?? 'missing']}
                            {cell?.points !== null && cell?.points !== undefined ? `, ${cell.points.toFixed(1).replace('.', ',')} pts` : ''}
                          </div>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
