import { useEffect, useId, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useDataQuality, useMeta, useSearch } from '../api/hooks'
import { cnpj, date } from '../lib/format'
import { DemoBadge } from './Badges'

function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(handle)
  }, [value, delay])
  return debounced
}

export function CommandBar() {
  const navigate = useNavigate()
  const meta = useMeta()
  const quality = useDataQuality()
  const [text, setText] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const query = useDebounced(text, 180)
  const search = useSearch(query)
  const inputRef = useRef<HTMLInputElement>(null)
  const listId = useId()
  const hits = open && query.trim().length >= 2 ? (search.data ?? []) : []

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      const typing = target && ['INPUT', 'SELECT', 'TEXTAREA'].includes(target.tagName)
      if (event.key === '/' && !typing) {
        event.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const choose = (accountId: string) => {
    setOpen(false)
    setText('')
    navigate(`/contas/${accountId}`)
  }

  const notFresh = (quality.data?.freshness ?? []).filter((item) => item.status !== 'fresh' && item.status !== 'not_used')

  return (
    <header className="command-bar">
      <Link to="/" className="wordmark" style={{ color: 'var(--ink)', textDecoration: 'none' }}>
        <span className="wordmark__glyph" aria-hidden="true" />
        Prospecção de contas
        <span className="wordmark__sub">piloto</span>
        {meta.data?.data_mode === 'demo' ? (
          <span title={meta.data.data_note}>
            <DemoBadge />
          </span>
        ) : null}
      </Link>

      <div className="command">
        <svg className="command__icon" width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
          <circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <path d="M11 11l3.5 3.5" stroke="currentColor" strokeWidth="1.6" />
        </svg>
        <input
          ref={inputRef}
          className="command__input"
          type="search"
          role="combobox"
          aria-label="Buscar conta por nome, razão social ou CNPJ"
          aria-expanded={hits.length > 0}
          aria-controls={listId}
          aria-activedescendant={hits.length ? `${listId}-${active}` : undefined}
          placeholder="Buscar conta, razão social ou CNPJ"
          value={text}
          onChange={(event) => {
            setText(event.target.value)
            setOpen(true)
            setActive(0)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => window.setTimeout(() => setOpen(false), 120)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown') {
              event.preventDefault()
              setActive((index) => Math.min(index + 1, Math.max(hits.length - 1, 0)))
            } else if (event.key === 'ArrowUp') {
              event.preventDefault()
              setActive((index) => Math.max(index - 1, 0))
            } else if (event.key === 'Enter' && hits[active]) {
              event.preventDefault()
              choose(hits[active].account_id)
            } else if (event.key === 'Escape') {
              setOpen(false)
              ;(event.target as HTMLInputElement).blur()
            }
          }}
        />
        {!text ? (
          <span className="command__hint" aria-hidden="true">
            <kbd>/</kbd>
          </span>
        ) : null}
        {hits.length > 0 ? (
          <ul className="command__results" role="listbox" id={listId} aria-label="Resultados da busca">
            {hits.map((hit, index) => (
              <li
                key={hit.account_id}
                id={`${listId}-${index}`}
                role="option"
                aria-selected={index === active}
                className="command__result"
                onMouseDown={(event) => {
                  event.preventDefault()
                  choose(hit.account_id)
                }}
                onMouseEnter={() => setActive(index)}
              >
                <span>
                  {hit.canonical_name}
                  <span className="muted"> {hit.institution_type}</span>
                </span>
                <span className="muted num">{hit.match_kind === 'cnpj' ? cnpj(hit.matched) : hit.matched}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <dl className="run-info" aria-label="Versão e datas de referência">
        <div>
          <dt>Scores de</dt>
          <dd className="num">{date(meta.data?.score_as_of_date)}</dd>
        </div>
        <div className="optional">
          <dt>Modelo</dt>
          <dd className="num">{meta.data?.model_version ?? '—'}</dd>
        </div>
        <div>
          <dt>Fontes</dt>
          <dd>
            {quality.isLoading ? (
              '—'
            ) : notFresh.length === 0 ? (
              <span>
                <span className="dot" style={{ background: 'var(--status-good)' }} aria-hidden="true" />
                em dia
              </span>
            ) : (
              <Link to="/qualidade" style={{ color: 'var(--status-warning)' }}>
                <span aria-hidden="true">◷ </span>
                {notFresh.length} {notFresh.length === 1 ? 'fonte com problema' : 'fontes com problema'}
              </Link>
            )}
          </dd>
        </div>
      </dl>
    </header>
  )
}
