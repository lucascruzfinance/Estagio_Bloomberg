import { useEffect } from 'react'
import { NavLink, useLocation, useNavigate, useSearchParams } from 'react-router'
import { useCompareSet } from '../lib/compare'

interface Item {
  key: string
  to: string
  label: string
  keepSearch: boolean
}

export function Nav() {
  const navigate = useNavigate()
  const location = useLocation()
  const [params] = useSearchParams()
  const compare = useCompareSet()
  const selected = params.get('unit')
  const selectedAccount = selected?.split(':')[0] ?? null

  const items: Item[] = [
    { key: '1', to: '/', label: 'Prioridade', keepSearch: true },
    { key: '2', to: '/mapa', label: 'Mapa', keepSearch: true },
    { key: '3', to: '/comparar', label: `Comparador${compare.length ? ` (${compare.length})` : ''}`, keepSearch: true },
    { key: '4', to: '/qualidade', label: 'Qualidade dos dados', keepSearch: false },
    { key: '6', to: '/universo', label: 'Universo SP/RJ', keepSearch: false },
  ]

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return
      const target = event.target as HTMLElement | null
      if (target && ['INPUT', 'SELECT', 'TEXTAREA'].includes(target.tagName)) return
      const item = items.find((candidate) => candidate.key === event.key)
      if (item) {
        event.preventDefault()
        navigate({ pathname: item.to, search: item.keepSearch ? location.search : '' })
      } else if (event.key === '5' && selectedAccount) {
        event.preventDefault()
        navigate({ pathname: `/contas/${selectedAccount}`, search: location.search })
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  return (
    <nav className="nav" aria-label="Telas">
      {items.map((item) => (
        <NavLink
          key={item.key}
          to={{ pathname: item.to, search: item.keepSearch ? location.search : '' }}
          end={item.to === '/'}
          className="nav__link"
        >
          <kbd aria-hidden="true">{item.key}</kbd>
          {item.label}
        </NavLink>
      ))}
      <NavLink
        to={{ pathname: selectedAccount ? `/contas/${selectedAccount}` : '/contas', search: location.search }}
        className="nav__link"
        aria-disabled={!selectedAccount}
        onClick={(event) => {
          if (!selectedAccount && !location.pathname.startsWith('/contas')) event.preventDefault()
        }}
      >
        <kbd aria-hidden="true">5</kbd>
        Conta 360
      </NavLink>
      <span className="nav__spacer" />
    </nav>
  )
}
