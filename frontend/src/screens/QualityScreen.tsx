import { useNavigate, useSearchParams } from 'react-router'
import { useConflicts, useDataQuality } from '../api/hooks'
import { FreshnessBadge } from '../components/Badges'
import { EmptyState, ErrorState, LoadingRows } from '../components/States'
import { date, dateTime, ratio } from '../lib/format'

const RESOLUTION: Record<string, string> = {
  pending_review: 'pendente',
  accept_source: 'aceitar fonte',
  keep_workbook: 'manter planilha',
  both_valid: 'ambos válidos',
  dismissed: 'descartado',
  no_longer_detected: 'não detectado',
}
const RULE: Record<string, string> = {
  phone_not_in_official_registry: 'telefone diferente do cadastro',
  official_phone_malformed: 'telefone oficial malformado',
  address_not_in_official_registry: 'endereço fora do cadastro',
  street_number_differs: 'número diferente',
  floor_differs: 'andar diferente',
  postal_code_differs: 'CEP diferente',
  website_domain_differs: 'domínio diferente',
}

export function QualityScreen() {
  const quality = useDataQuality()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const status = params.get('status') ?? 'pending_review'
  const accountFilter = params.get('conta')
  const conflicts = useConflicts(status === 'all' ? null : status)

  if (quality.isLoading) return <div className="page"><LoadingRows rows={14} label="Carregando qualidade" /></div>
  if (quality.error || !quality.data) {
    return <div className="page"><ErrorState error={quality.error} onRetry={() => void quality.refetch()} /></div>
  }
  const q = quality.data
  const problems = q.freshness.filter((f) => f.status !== 'fresh' && f.status !== 'not_used')
  const db = q.database as Record<string, number | string | null>
  const conflictRows = (conflicts.data?.data ?? []).filter((c) => !accountFilter || c.account_id === accountFilter)

  const setParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <h1 className="page__title">Qualidade dos dados</h1>
          <p className="page__lede">
            Relatório de {dateTime(q.run_at)}, fundos até {date(q.fund_reference_date)}. Toda pontuação depende destas
            fontes; quando uma falha, o ranking mostra a lacuna em vez de assumir zero.
          </p>
        </div>
      </header>

      <div className="tile-row" role="list" aria-label="Resumo da base">
        <div className="tile" role="listitem">
          <div className="tile__label">Fontes com problema</div>
          <div className="tile__value" style={{ color: problems.length ? 'var(--status-warning)' : undefined }}>
            {problems.length} de {q.freshness.length}
          </div>
        </div>
        <div className="tile" role="listitem">
          <div className="tile__label">Escritórios no mapa</div>
          <div className="tile__value">
            {String(db.located_offices ?? '—')} <span className="muted" style={{ fontSize: 'var(--fs-sm)' }}>{String(db.exact_offices ?? '—')} exatos</span>
          </div>
        </div>
        <div className="tile" role="listitem">
          <div className="tile__label">Classes de fundos</div>
          <div className="tile__value">{Number(db.fund_classes ?? 0).toLocaleString('pt-BR')}</div>
        </div>
        <div className="tile" role="listitem">
          <div className="tile__label">Conflitos pendentes</div>
          <div className="tile__value" style={{ color: q.conflicts_by_status.pending_review ? 'var(--status-serious)' : undefined }}>
            {q.conflicts_by_status.pending_review ?? 0}
          </div>
        </div>
        <div className="tile" role="listitem">
          <div className="tile__label">Última carga no banco</div>
          <div className="tile__value" style={{ fontSize: 'var(--fs-md)' }}>{dateTime(db.last_load as string | null)}</div>
        </div>
      </div>

      <div className="columns-2">
        <section aria-labelledby="fresh-title">
          <h2 className="section__title" id="fresh-title">
            Atualização das fontes <small>limite de idade por fonte</small>
          </h2>
          <table className="grid grid--compact" aria-label="Atualização das fontes">
            <thead>
              <tr>
                <th scope="col">Fonte</th>
                <th scope="col">Situação</th>
                <th scope="col">Dados de</th>
                <th scope="col" className="num-col">Idade</th>
              </tr>
            </thead>
            <tbody>
              {q.freshness.map((item) => (
                <tr key={item.source_id} style={{ cursor: 'default' }} title={item.detail ?? undefined}>
                  <td className="name-cell" style={{ maxWidth: 260 }}>{item.title}</td>
                  <td>{item.status === 'fresh' ? <span className="secondary">em dia</span> : <FreshnessBadge status={item.status} />}</td>
                  <td className="num">{date(item.data_as_of)}</td>
                  <td className="num num-col">
                    {item.age_days === null || item.age_days === undefined ? '—' : `${item.age_days} d`}
                    <span className="muted"> / {item.max_age_days} d</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {problems.map((item) => (
            <p key={item.source_id} className={`callout${item.status === 'unavailable' ? ' callout--critical' : ''}`} style={{ marginTop: 8 }}>
              <strong>{item.title}</strong>: {item.detail || 'sem detalhe'}
            </p>
          ))}
        </section>

        <section aria-labelledby="rules-title">
          <h2 className="section__title" id="rules-title">
            Regras aplicadas
          </h2>
          <ul className="reasons secondary">
            {q.rules.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>
        </section>
      </div>

      <section className="section" aria-labelledby="coverage-title">
        <h2 className="section__title" id="coverage-title">
          Cobertura por conta <small>clique para abrir a conta</small>
        </h2>
        <div className="surface" style={{ overflowX: 'auto' }}>
          <table className="grid grid--compact" aria-label="Cobertura por conta">
            <thead>
              <tr>
                <th scope="col">Conta</th>
                <th scope="col" className="num-col">Entidades</th>
                <th scope="col">Sede</th>
                <th scope="col" className="num-col">Classes ativas</th>
                <th scope="col" className="num-col">Com informe</th>
                <th scope="col" className="num-col">Retorno comparável</th>
                <th scope="col" className="num-col">Conflitos</th>
                <th scope="col">Principal lacuna</th>
              </tr>
            </thead>
            <tbody>
              {q.accounts.map((account) => (
                <tr
                  key={account.account_id}
                  tabIndex={0}
                  onClick={() => navigate(`/contas/${account.account_id}`)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') navigate(`/contas/${account.account_id}`)
                  }}
                >
                  <td>{account.canonical_name}</td>
                  <td className="num num-col">
                    {account.entities_found}/{account.entities_registered}
                  </td>
                  <td className="secondary">
                    {account.geocode_precision === 'address' ? 'exata' : account.geocode_precision === 'street' ? 'aprox. rua' : 'sem ponto'}
                  </td>
                  <td className="num num-col">{account.active_classes}</td>
                  <td className="num num-col">{account.classes_with_daily_report}</td>
                  <td className="num num-col">{ratio(account.comparable_12m_share)}</td>
                  <td className="num num-col" style={{ color: account.open_conflicts ? 'var(--status-serious)' : undefined }}>
                    {account.open_conflicts}
                  </td>
                  <td className="secondary name-cell" style={{ maxWidth: 360 }} title={account.gaps.join('\n')}>
                    {account.gaps[0] ?? 'nenhuma lacuna crítica'}
                    {account.gaps.length > 1 ? <span className="muted"> (+{account.gaps.length - 1})</span> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section" aria-labelledby="conflicts-title">
        <h2 className="section__title" id="conflicts-title">
          Fila de revisão humana <small>planilha vs cadastro oficial; decisões ficam em data/review/conflicts.csv</small>
        </h2>
        <div className="filters" style={{ background: 'transparent', border: 0, padding: '0 0 8px' }}>
          <label className="filter">
            Situação
            <select value={status} onChange={(event) => setParam('status', event.target.value === 'pending_review' ? null : event.target.value)}>
              <option value="pending_review">Pendentes</option>
              <option value="all">Todas</option>
              <option value="no_longer_detected">Não detectadas</option>
              <option value="accept_source">Aceitar fonte</option>
              <option value="keep_workbook">Manter planilha</option>
            </select>
          </label>
          <label className="filter">
            Conta
            <select value={accountFilter ?? ''} onChange={(event) => setParam('conta', event.target.value || null)}>
              <option value="">Todas</option>
              {q.accounts.map((account) => (
                <option key={account.account_id} value={account.account_id}>
                  {account.canonical_name}
                </option>
              ))}
            </select>
          </label>
        </div>
        {conflicts.isLoading ? <LoadingRows rows={4} /> : null}
        {conflicts.error ? <ErrorState error={conflicts.error} onRetry={() => void conflicts.refetch()} /> : null}
        {conflicts.data && conflictRows.length === 0 ? <EmptyState title="Nenhum conflito com esses filtros" /> : null}
        {conflictRows.length ? (
          <div className="surface" style={{ overflowX: 'auto' }}>
            <table className="grid grid--compact" aria-label="Conflitos de fonte">
              <thead>
                <tr>
                  <th scope="col">Conta</th>
                  <th scope="col">Divergência</th>
                  <th scope="col">Gravidade</th>
                  <th scope="col">Planilha</th>
                  <th scope="col">Cadastro oficial</th>
                  <th scope="col">Situação</th>
                </tr>
              </thead>
              <tbody>
                {conflictRows.map((conflict) => (
                  <tr key={conflict.conflict_id} style={{ cursor: 'default' }}>
                    <td>{q.accounts.find((a) => a.account_id === conflict.account_id)?.canonical_name ?? conflict.account_id}</td>
                    <td>{RULE[conflict.rule] ?? conflict.rule}</td>
                    <td>
                      <span className={`badge ${conflict.severity === 'low' ? 'badge--assumption' : 'badge--conflict'}`}>
                        {conflict.severity === 'low' ? 'baixa' : conflict.severity === 'medium' ? 'média' : 'alta'}
                      </span>
                    </td>
                    <td className="secondary name-cell" style={{ maxWidth: 240 }} title={conflict.workbook_value}>
                      {conflict.workbook_value || '—'}
                    </td>
                    <td className="secondary name-cell" style={{ maxWidth: 260 }} title={conflict.source_value}>
                      {conflict.source_value}
                    </td>
                    <td>{RESOLUTION[conflict.resolution_status] ?? conflict.resolution_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  )
}
