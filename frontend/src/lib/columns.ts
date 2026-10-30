import { useCallback, useState } from 'react'

export type ColumnId =
  | 'rank'
  | 'unit'
  | 'tier'
  | 'priority'
  | 'fit'
  | 'timing'
  | 'confidence'
  | 'hq'
  | 'nav'
  | 'flow'
  | 'compare'

export interface ColumnDef {
  id: ColumnId
  label: string
  numeric?: boolean
  sortable: boolean
  locked?: boolean
  defaultVisible: boolean
}

export const COLUMNS: ColumnDef[] = [
  { id: 'rank', label: '#', sortable: true, locked: true, defaultVisible: true, numeric: true },
  { id: 'unit', label: 'Unidade', sortable: true, locked: true, defaultVisible: true },
  { id: 'tier', label: 'Faixa', sortable: true, defaultVisible: true },
  { id: 'priority', label: 'Prioridade', sortable: true, defaultVisible: true },
  { id: 'fit', label: 'Fit', sortable: true, defaultVisible: true },
  { id: 'timing', label: 'Timing', sortable: true, defaultVisible: true },
  { id: 'confidence', label: 'Confiança', sortable: true, defaultVisible: true, numeric: true },
  { id: 'hq', label: 'Sede', sortable: true, defaultVisible: false },
  { id: 'nav', label: 'PL não-FIC', sortable: true, defaultVisible: false, numeric: true },
  { id: 'flow', label: 'Captação 12m', sortable: true, defaultVisible: false, numeric: true },
  { id: 'compare', label: 'Comparar', sortable: false, locked: true, defaultVisible: true },
]

export interface SortState {
  id: ColumnId
  desc: boolean
}

const KEY = 'nsi.table.v1'

interface Stored {
  hidden: ColumnId[]
  shown: ColumnId[]
  sort: SortState
}

function load(): Stored {
  const fallback: Stored = { hidden: [], shown: [], sort: { id: 'rank', desc: false } }
  try {
    const raw = window.localStorage.getItem(KEY)
    return raw ? { ...fallback, ...(JSON.parse(raw) as Partial<Stored>) } : fallback
  } catch {
    return fallback
  }
}

function save(value: Stored): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(value))
  } catch {
    /* in-memory only */
  }
}

/** Column visibility and sort, persisted per browser. */
export function useTableConfig() {
  const [state, setState] = useState<Stored>(load)

  const isVisible = useCallback(
    (column: ColumnDef) =>
      column.locked ||
      (column.defaultVisible ? !state.hidden.includes(column.id) : state.shown.includes(column.id)),
    [state],
  )

  const toggle = useCallback((column: ColumnDef) => {
    setState((current) => {
      const visible = column.defaultVisible
        ? !current.hidden.includes(column.id)
        : current.shown.includes(column.id)
      const next: Stored = column.defaultVisible
        ? {
            ...current,
            hidden: visible ? [...current.hidden, column.id] : current.hidden.filter((id) => id !== column.id),
          }
        : {
            ...current,
            shown: visible ? current.shown.filter((id) => id !== column.id) : [...current.shown, column.id],
          }
      save(next)
      return next
    })
  }, [])

  const sortBy = useCallback((id: ColumnId) => {
    setState((current) => {
      const next: Stored = {
        ...current,
        sort:
          current.sort.id === id
            ? { id, desc: !current.sort.desc }
            : { id, desc: !['rank', 'unit', 'tier', 'hq'].includes(id) },
      }
      save(next)
      return next
    })
  }, [])

  return { columns: COLUMNS.filter(isVisible), all: COLUMNS, isVisible, toggle, sort: state.sort, sortBy }
}
