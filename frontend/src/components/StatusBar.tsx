import { useMeta, useReadiness } from '../api/hooks'

export function StatusBar() {
  const ready = useReadiness()
  const meta = useMeta()
  const demo = meta.data?.data_mode === 'demo'
  const ok = ready.data?.status === 'ready'
  const label = ready.isLoading
    ? 'verificando API'
    : ok
      ? `API pronta, migração ${String(ready.data?.checks.migration ?? '')}`
      : 'API indisponível'
  return (
    <footer className="status-bar">
      <span role="status">
        <span
          className="dot"
          aria-hidden="true"
          style={{ background: ready.isLoading ? 'var(--ink-3)' : ok ? 'var(--status-good)' : 'var(--status-critical)' }}
        />
        {label}
      </span>
      <span className="status-bar__grow">
        {demo ? <strong style={{ color: 'var(--amber)' }}>{meta.data?.data_note} </strong> : null}
        Dados públicos: CVM Dados Abertos. Mapa: © OpenStreetMap, OpenFreeMap. Retorno de fundo não é lucro da gestora.
      </span>
      <span aria-hidden="true">
        <kbd>1</kbd>–<kbd>5</kbd> telas <kbd>/</kbd> busca <kbd>↑</kbd>
        <kbd>↓</kbd> seleção <kbd>Enter</kbd> conta <kbd>Esc</kbd> fecha
      </span>
    </footer>
  )
}
