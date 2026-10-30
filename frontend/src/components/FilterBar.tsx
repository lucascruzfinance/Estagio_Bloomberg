import type { ReactNode } from 'react'
import { useMemo } from 'react'
import { useAccounts, useScores } from '../api/hooks'
import { TIERS } from '../api/types'
import { TIER_LABEL } from './Badges'
import { joinUnits, matchesFilters, useFilters } from '../lib/filters'

export function FilterBar({ children }: { children?: ReactNode }) {
  const { filters, setFilter, clear, active } = useFilters()
  const scores = useScores()
  const accounts = useAccounts()

  const units = useMemo(
    () => joinUnits(scores.data?.data ?? [], accounts.data?.data ?? []),
    [scores.data, accounts.data],
  )
  const types = useMemo(() => Array.from(new Set(units.map((u) => u.institution_type))).sort(), [units])
  const states = useMemo(
    () => Array.from(new Set(units.map((u) => u.state).filter((s): s is string => Boolean(s)))).sort(),
    [units],
  )
  const visible = units.filter((unit) => matchesFilters(unit, filters)).length

  return (
    <div className="filters" role="search" aria-label="Filtros do ranking e do mapa">
      <label className="filter">
        Faixa
        <select value={filters.tier} onChange={(event) => setFilter('tier', event.target.value)}>
          <option value="">Todas</option>
          {TIERS.map((tier) => (
            <option key={tier} value={tier}>
              {TIER_LABEL[tier] ?? tier}
            </option>
          ))}
        </select>
      </label>
      <label className="filter">
        Tipo
        <select value={filters.type} onChange={(event) => setFilter('type', event.target.value)}>
          <option value="">Todos</option>
          {types.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </label>
      <label className="filter">
        UF da sede
        <select value={filters.uf} onChange={(event) => setFilter('uf', event.target.value)}>
          <option value="">Todas</option>
          {states.map((state) => (
            <option key={state} value={state}>
              {state}
            </option>
          ))}
        </select>
      </label>
      <label className="filter">
        Evidência
        <select value={filters.mode} onChange={(event) => setFilter('mode', event.target.value)}>
          <option value="">Todas</option>
          <option value="observed">Observada</option>
          <option value="assumption">Premissa (mesas)</option>
        </select>
      </label>
      <label className="filter">
        Nome
        <input
          type="text"
          value={filters.q}
          placeholder="filtrar"
          size={14}
          onChange={(event) => setFilter('q', event.target.value)}
          aria-label="Filtrar por nome"
        />
      </label>
      {active > 0 ? (
        <button type="button" className="button button--ghost" onClick={clear}>
          Limpar filtros ({active})
        </button>
      ) : null}
      {children}
      <span className="filters__count" aria-live="polite">
        {scores.isLoading ? 'carregando…' : `${visible} de ${units.length} unidades`}
      </span>
    </div>
  )
}
