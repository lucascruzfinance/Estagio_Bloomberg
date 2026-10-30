const LOCALE = 'pt-BR'

const number0 = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 })
const number1 = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const pct1 = new Intl.NumberFormat(LOCALE, { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 })
const dateFmt = new Intl.DateTimeFormat(LOCALE, { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'UTC' })
const dateTimeFmt = new Intl.DateTimeFormat(LOCALE, {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

export const DASH = '—'

export function score(value: number | null | undefined): string {
  return value === null || value === undefined ? DASH : number0.format(value)
}

/** Compact BRL: R$ 488,3 bi · R$ 998 mi · R$ 12 mil. */
export function brlCompact(value: number | null | undefined): string {
  if (value === null || value === undefined) return DASH
  const sign = value < 0 ? '−' : ''
  const abs = Math.abs(value)
  if (abs >= 1e9) return `${sign}R$ ${number1.format(abs / 1e9)} bi`
  if (abs >= 1e6) return `${sign}R$ ${number0.format(abs / 1e6)} mi`
  if (abs >= 1e3) return `${sign}R$ ${number0.format(abs / 1e3)} mil`
  return `${sign}R$ ${number0.format(abs)}`
}

/** Signed BRL for flows: +R$ 0,8 bi / −R$ 13,7 bi. */
export function brlSigned(value: number | null | undefined): string {
  if (value === null || value === undefined) return DASH
  return value > 0 ? `+${brlCompact(value)}` : brlCompact(value)
}

export function percent(value: number | null | undefined, signed = false): string {
  if (value === null || value === undefined) return DASH
  const text = pct1.format(Math.abs(value))
  if (!signed) return value < 0 ? `−${text}` : text
  return value > 0 ? `+${text}` : value < 0 ? `−${text}` : text
}

export function ratio(value: number | null | undefined): string {
  return value === null || value === undefined ? DASH : pct1.format(value)
}

export function date(value: string | null | undefined): string {
  if (!value) return DASH
  const parsed = new Date(value.length === 10 ? `${value}T00:00:00Z` : value)
  return Number.isNaN(parsed.getTime()) ? DASH : dateFmt.format(parsed)
}

export function dateTime(value: string | null | undefined): string {
  if (!value) return DASH
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? DASH : dateTimeFmt.format(parsed)
}

export function cnpj(value: string | null | undefined): string {
  if (!value) return DASH
  const d = value.replace(/\D/g, '')
  if (d.length !== 14) return value
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`
}

/** E.164 (+5511…) to Brazilian display: (11) 4935-8500 / (11) 98765-4321. */
export function phone(value: string | null | undefined): string {
  if (!value) return DASH
  const d = value.replace(/\D/g, '').replace(/^55/, '')
  if (d.length === 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  if (d.length === 11) return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`
  return value
}

export function deltaClass(value: number | null | undefined): string {
  if (value === null || value === undefined || value === 0) return ''
  return value > 0 ? 'delta-up' : 'delta-down'
}

const SMALL_WORDS = new Set(['de', 'da', 'do', 'das', 'dos', 'e'])

/** CVM registers addresses in upper case; render them in normal case, keeping UF and CEP. */
export function addressCase(value: string | null | undefined): string {
  if (!value) return DASH
  if (value !== value.toUpperCase()) return value
  return value
    .toLowerCase()
    .replace(/\p{L}[\p{L}'’.]*/gu, (word: string, offset: number) =>
      offset > 0 && SMALL_WORDS.has(word) ? word : word.charAt(0).toUpperCase() + word.slice(1),
    )
    .replace(/\/([a-z]{2})\b/gi, (_, uf: string) => `/${uf.toUpperCase()}`)
    .replace(/\bCep\b/g, 'CEP')
    .replace(/\bS\/n\b/g, 'S/N')
}

export function titleCase(value: string | null | undefined): string {
  if (!value) return DASH
  return value
    .toLowerCase()
    .replace(/(^|[\s/(-])([a-zà-ú])/g, (_, prefix: string, letter: string) => prefix + letter.toUpperCase())
}
