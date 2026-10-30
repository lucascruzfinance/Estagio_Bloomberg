import { useCallback, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router'
import type { AccountSummary, ScoreRow } from '../api/types'

export const FILTER_KEYS = ['tier', 'mode', 'type', 'uf', 'q'] as const
export type FilterKey = (typeof FILTER_KEYS)[number]
export type Filters = Record<FilterKey, string>

const STORAGE_KEY = 'nsi.filters.v1'
const EMPTY: Filters = { tier: '', mode: '', type: '', uf: '', q: '' }

function readStored(): Partial<Filters> {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Partial<Filters>) : {}
  } catch {
    return {}
  }
}

function writeStored(filters: Filters): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(filters))
  } catch {
    /* storage can be unavailable (private mode); filters still live in the URL */
  }
}

/**
 * Filters live in the URL (shareable, back/forward aware) and are mirrored to
 * localStorage so they survive a reload or a screen change without a URL.
 * Every screen reads the same keys, which keeps ranking, map and comparison in sync.
 */
export function useFilters(): {
  filters: Filters
  setFilter: (key: FilterKey, value: string) => void
  clear: () => void
  active: number
  selected: string | null
  select: (unitKey: string | null) => void
} {
  const [params, setParams] = useSearchParams()

  useEffect(() => {
    const hasAny = FILTER_KEYS.some((key) => params.has(key))
    if (hasAny) return
    const stored = readStored()
    const entries = Object.entries(stored).filter(([, value]) => value)
    if (entries.length === 0) return
    setParams(
      (current) => {
        const next = new URLSearchParams(current)
        for (const [key, value] of entries) next.set(key, String(value))
        return next
      },
      { replace: true },
    )
    // run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const filters = useMemo<Filters>(() => {
    const result = { ...EMPTY }
    for (const key of FILTER_KEYS) result[key] = params.get(key) ?? ''
    return result
  }, [params])

  const setFilter = useCallback(
    (key: FilterKey, value: string) => {
      setParams(
        (current) => {
          const next = new URLSearchParams(current)
          if (value) next.set(key, value)
          else next.delete(key)
          const snapshot = { ...EMPTY }
          for (const k of FILTER_KEYS) snapshot[k] = next.get(k) ?? ''
          writeStored(snapshot)
          return next
        },
        { replace: true },
      )
    },
    [setParams],
  )

  const clear = useCallback(() => {
    writeStored(EMPTY)
    setParams(
      (current) => {
        const next = new URLSearchParams(current)
        for (const key of FILTER_KEYS) next.delete(key)
        return next
      },
      { replace: true },
    )
  }, [setParams])

  const select = useCallback(
    (unitKey: string | null) => {
      setParams(
        (current) => {
          const next = new URLSearchParams(current)
          if (unitKey) next.set('unit', unitKey)
          else next.delete('unit')
          return next
        },
        { replace: true },
      )
    },
    [setParams],
  )

  const active = FILTER_KEYS.filter((key) => filters[key]).length
  return { filters, setFilter, clear, active, selected: params.get('unit'), select }
}

/** A score row joined with its account context (HQ, money, conflicts). */
export interface UnitRow extends ScoreRow {
  account: AccountSummary | undefined
  state: string | null
  city: string | null
}

export function joinUnits(scores: ScoreRow[], accounts: AccountSummary[]): UnitRow[] {
  const byId = new Map(accounts.map((account) => [account.account_id, account]))
  return scores.map((row) => {
    const account = byId.get(row.account_id)
    return {
      ...row,
      account,
      state: account?.headquarters?.state ?? null,
      city: account?.headquarters?.city ?? null,
    }
  })
}

function normalize(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
}

export function matchesFilters(row: UnitRow, filters: Filters): boolean {
  if (filters.tier && row.tier !== filters.tier) return false
  if (filters.mode && row.evidence_mode !== filters.mode) return false
  if (filters.type && row.institution_type !== filters.type) return false
  if (filters.uf && row.state !== filters.uf) return false
  if (filters.q) {
    const needle = normalize(filters.q)
    const haystack = normalize(`${row.unit_name} ${row.canonical_name} ${row.account?.legal_name ?? ''}`)
    if (!haystack.includes(needle)) return false
  }
  return true
}

export function accountMatches(account: AccountSummary, units: UnitRow[], filters: Filters): boolean {
  return units.some((unit) => unit.account_id === account.account_id && matchesFilters(unit, filters))
}
