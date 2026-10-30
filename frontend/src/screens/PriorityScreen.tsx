import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { useAccounts, useScores } from '../api/hooks'
import { TIERS } from '../api/types'
import { AccountPanel } from '../components/AccountPanel'
import { AssumptionBadge, TierBadge } from '../components/Badges'
import { SERIES, ScoreBand } from '../components/ScoreBand'
import { EmptyState, ErrorState, LoadingRows } from '../components/States'
import type { ColumnDef, ColumnId, SortState } from '../lib/columns'
import { useTableConfig } from '../lib/columns'
import { MAX_COMPARE, toggleCompare, useCompareSet } from '../lib/compare'
import { joinUnits, matchesFilters, useFilters, type UnitRow } from '../lib/filters'
import { brlCompact, brlSigned, deltaClass, score, titleCase } from '../lib/format'

function sortValue(row: UnitRow, id: ColumnId): number | string | null {
  switch (id) {
    case 'rank':
      return row.rank
    case 'unit':
      return row.unit_name
    case 'tier':
      return TIERS.indexOf(row.tier as (typeof TIERS)[number])
    case 'priority':
      return row.priority.point ?? null
    case 'fit':
      return row.fit.point ?? null
    case 'timing':
      return row.timing.point ?? null
    case 'confidence':
      return row.confidence
    case 'hq':
      return row.city ?? null
    case 'nav':
      return row.account?.nav_brl_non_fic ?? null
    case 'flow':
      return row.account?.net_flow_12m_brl ?? null
    default:
      return null
  }
}

export function sortRows(rows: UnitRow[], sort: SortState): UnitRow[] {
  return [...rows].sort((a, b) => {
    const va = sortValue(a, sort.id)
    const vb = sortValue(b, sort.id)
    if (va === null && vb === null) return a.rank - b.rank
    if (va === null) return 1 // nulls last in both directions
    if (vb === null) return -1
    const cmp = typeof va === 'string' ? va.localeCompare(String(vb), 'pt-BR') : va - (vb as number)
    return (sort.desc ? -cmp : cmp) || a.rank - b.rank
  })
}

function Cell({ column, row, inCompare, compareFull }: { column: ColumnDef; row: UnitRow; inCompare: boolean; compareFull: boolean }) {
  switch (column.id) {
    case 'rank':
      return <td className="rank num num-col">{row.rank}</td>
    case 'unit': {
      const [org, desk] = row.unit_name.split(' — ')
      const conflicts = row.account?.open_conflicts ?? 0
      return (
        <td className="name-cell">
          <span className="unit-name">
            <span className="unit-name__text" title={row.unit_name}>
              {org}
              {desk ? <span className="desk"> / {desk}</span> : null}
            </span>
            {row.evidence_mode === 'assumption' ? <AssumptionBadge /> : null}
            {conflicts > 0 ? (
              <span className="badge badge--conflict" title={`${conflicts} conflito(s) entre planilha e fonte oficial`}>
                <span aria-hidden="true">⚑</span>
                {conflicts}
                <span className="sr-only"> conflitos de fonte</span>
              </span>
            ) : null}
          </span>
        </td>
      )
    }
    case 'tier':
      return (
        <td>
          <TierBadge tier={row.tier} />
        </td>
      )
    case 'priority':
      return (
        <td>
          <ScoreBand band={row.priority} label="Prioridade" color={SERIES.priority} />
        </td>
      )
    case 'fit':
      return (
        <td>
          <ScoreBand band={row.fit} label="Fit" color={SERIES.fit} />
        </td>
      )
    case 'timing':
      return (
        <td>
          <ScoreBand band={row.timing} label="Timing" color={SERIES.timing} />
        </td>
      )
    case 'confidence':
      return <td className="num num-col">{score(row.confidence)}</td>
    case 'hq':
      return <td className="secondary">{row.city ? `${titleCase(row.city)}/${row.state}` : '—'}</td>
    case 'nav':
      return <td className="num num-col">{brlCompact(row.account?.nav_brl_non_fic)}</td>
    case 'flow':
      return (
        <td className={`num num-col ${deltaClass(row.account?.net_flow_12m_brl)}`}>
          {brlSigned(row.account?.net_flow_12m_brl)}
        </td>
      )
    case 'compare':
      return (
        <td onClick={(event) => event.stopPropagation()} style={{ textAlign: 'center' }}>
          <input
            type="checkbox"
            checked={inCompare}
            disabled={!inCompare && compareFull}
            aria-label={`Comparar ${row.unit_name}`}
            onChange={() => toggleCompare(row.unit_key)}
            tabIndex={-1}
          />
        </td>
      )
    default:
      return <td />
  }
}

function ColumnPicker({ config }: { config: ReturnType<typeof useTableConfig> }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="column-picker">
      <button type="button" className="button" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        Colunas
      </button>
      {open ? (
        <div className="column-picker__menu" role="group" aria-label="Colunas visíveis" onMouseLeave={() => setOpen(false)}>
          {config.all
            .filter((column) => !column.locked)
            .map((column) => (
              <label key={column.id}>
                <input type="checkbox" checked={config.isVisible(column)} onChange={() => config.toggle(column)} />
                {column.label}
              </label>
            ))}
        </div>
      ) : null}
    </div>
  )
}

export function PriorityScreen() {
  const navigate = useNavigate()
  const scores = useScores()
  const accounts = useAccounts()
  const { filters, clear, active, selected, select } = useFilters()
  const config = useTableConfig()
  const compare = useCompareSet()
  const bodyRef = useRef<HTMLTableSectionElement>(null)

  const rows = useMemo(() => {
    const joined = joinUnits(scores.data?.data ?? [], accounts.data?.data ?? [])
    return sortRows(joined.filter((row) => matchesFilters(row, filters)), config.sort)
  }, [scores.data, accounts.data, filters, config.sort])

  const selectedIndex = rows.findIndex((row) => row.unit_key === selected)

  const focusRow = (index: number) => {
    const row = rows[index]
    if (!row) return
    select(row.unit_key)
    const element = bodyRef.current?.querySelectorAll<HTMLTableRowElement>('tr')[index]
    element?.focus()
    element?.scrollIntoView({ block: 'nearest' })
  }

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && selected) {
        const target = event.target as HTMLElement | null
        if (target?.tagName === 'INPUT') return
        select(null)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected, select])

  const body = () => {
    if (scores.isLoading || accounts.isLoading) return <LoadingRows rows={12} label="Carregando ranking" />
    if (scores.error || accounts.error) {
      return (
        <ErrorState
          error={scores.error ?? accounts.error}
          onRetry={() => {
            void scores.refetch()
            void accounts.refetch()
          }}
        />
      )
    }
    if (rows.length === 0) {
      return (
        <EmptyState
          title="Nenhuma unidade com esses filtros"
          action={
            active ? (
              <button type="button" className="button button--primary" onClick={clear}>
                Limpar filtros
              </button>
            ) : null
          }
        >
          Ajuste faixa, tipo, UF ou evidência para ver mais contas.
        </EmptyState>
      )
    }
    return (
      <table className="grid" aria-label="Ranking de unidades" aria-rowcount={rows.length}>
        <thead>
          <tr>
            {config.columns.map((column) => {
              const sorted = config.sort.id === column.id
              const ariaSort = column.sortable ? (sorted ? (config.sort.desc ? 'descending' : 'ascending') : 'none') : undefined
              return (
                <th key={column.id} scope="col" aria-sort={ariaSort} className={column.numeric ? 'num-col' : undefined}>
                  {column.sortable ? (
                    <button type="button" onClick={() => config.sortBy(column.id)}>
                      {column.label}
                      <span aria-hidden="true" style={{ color: sorted ? 'var(--amber)' : 'var(--line-strong)' }}>
                        {sorted ? (config.sort.desc ? '▼' : '▲') : '↕'}
                      </span>
                    </button>
                  ) : (
                    column.label
                  )}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody ref={bodyRef}>
          {rows.map((row, index) => (
            <tr
              key={row.unit_key}
              aria-selected={row.unit_key === selected}
              tabIndex={index === (selectedIndex >= 0 ? selectedIndex : 0) ? 0 : -1}
              data-unit={row.unit_key}
              onClick={() => select(row.unit_key)}
              onDoubleClick={() => navigate(`/contas/${row.account_id}?unit=${encodeURIComponent(row.unit_key)}`)}
              onKeyDown={(event) => {
                if (event.key === 'ArrowDown') {
                  event.preventDefault()
                  focusRow(Math.min(index + 1, rows.length - 1))
                } else if (event.key === 'ArrowUp') {
                  event.preventDefault()
                  focusRow(Math.max(index - 1, 0))
                } else if (event.key === 'Enter') {
                  event.preventDefault()
                  navigate(`/contas/${row.account_id}?unit=${encodeURIComponent(row.unit_key)}`)
                } else if (event.key === ' ') {
                  event.preventDefault()
                  toggleCompare(row.unit_key)
                } else if (event.key === 'Home') {
                  event.preventDefault()
                  focusRow(0)
                } else if (event.key === 'End') {
                  event.preventDefault()
                  focusRow(rows.length - 1)
                }
              }}
              onFocus={() => {
                if (row.unit_key !== selected) select(row.unit_key)
              }}
            >
              {config.columns.map((column) => (
                <Cell
                  key={column.id}
                  column={column}
                  row={row}
                  inCompare={compare.includes(row.unit_key)}
                  compareFull={compare.length >= MAX_COMPARE}
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    )
  }

  return (
    <div className={`split${selected ? '' : ' split--closed'}`}>
      <section className="pane" aria-label="Ranking">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', gap: 12 }}>
          <p className="secondary" style={{ margin: 0, fontSize: 'var(--fs-sm)', maxWidth: '80ch' }}>
            Prioridade combina fit (60%) e timing (40%) só quando há evidência de timing. A faixa cinza mostra quanto
            o score pode mudar com os dados que ainda faltam.
          </p>
          <ColumnPicker config={config} />
        </div>
        {body()}
      </section>
      {selected ? (
        <aside className="side" aria-label="Conta 360">
          <AccountPanel unitKey={selected} onClose={() => select(null)} />
        </aside>
      ) : null}
    </div>
  )
}
