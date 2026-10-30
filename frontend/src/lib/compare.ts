import { useSyncExternalStore } from 'react'

const KEY = 'nsi.compare.v1'
export const MAX_COMPARE = 5
const listeners = new Set<() => void>()

function read(): string[] {
  try {
    const raw = window.localStorage.getItem(KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === 'string').slice(0, MAX_COMPARE) : []
  } catch {
    return []
  }
}

let current: string[] = typeof window === 'undefined' ? [] : read()

function emit(next: string[]): void {
  current = next
  try {
    window.localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    /* keep in memory only */
  }
  listeners.forEach((listener) => listener())
}

export function toggleCompare(unitKey: string): void {
  if (current.includes(unitKey)) emit(current.filter((key) => key !== unitKey))
  else if (current.length < MAX_COMPARE) emit([...current, unitKey])
}

export function setCompare(keys: string[]): void {
  emit(Array.from(new Set(keys)).slice(0, MAX_COMPARE))
}

export function useCompareSet(): string[] {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    () => current,
    () => current,
  )
}

/** Test helper: reset module state between tests. */
export function resetCompareForTests(): void {
  current = []
  listeners.forEach((listener) => listener())
}
