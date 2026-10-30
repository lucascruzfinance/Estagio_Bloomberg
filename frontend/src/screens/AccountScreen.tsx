import { lazy, Suspense, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { useAccount, useDataQuality, useExplanation, useFunds, usePerformance } from '../api/hooks'
import type { FundRow } from '../api/types'
import { ScoreStack } from '../components/AccountPanel'
import { AssumptionBadge, ConflictBadge, FreshnessBadge, PrecisionBadge, TierBadge } from '../components/Badges'
import { FactorTable } from '../components/FactorTable'
import { ReasonList } from '../components/Reasons'
import { EvidenceText, SourceLink } from '../components/SourceLink'
import { EmptyState, ErrorState, LoadingRows } from '../components/States'
import { MAX_COMPARE, toggleCompare, useCompareSet } from '../lib/compare'
import { addressCase, brlCompact, brlSigned, cnpj, date, deltaClass, percent, phone, ratio, score } from '../lib/format'

// ECharts only loads when a fund chart is actually shown.
const QuotaChart = lazy(() => import('../charts/QuotaChart').then((module) => ({ default: module.QuotaChart })))

const RELATION: Record<string, string> = {
  primary_manager: 'Gestora principal',
  affiliate_manager: 'Afiliada',
  bank_entity: 'Entidade bancária',
}

function FundsTable({ funds, selected, onSelect }: { funds: FundRow[]; selected: string | null; onSelect: (key: string) => void }) {
  return (
    <div className="table-scroll">
    <table className="grid grid--compact" aria-label="Maiores classes por PL">
      <thead>
        <tr>
          <th scope="col">Classe</th>
          <th scope="col">Classificação</th>
          <th scope="col" className="num-col">PL</th>
          <th scope="col" className="num-col">12m</th>
          <th scope="col" className="num-col">Capt. 12m</th>
        </tr>
      </thead>
      <tbody>
        {funds.map((fund) => {
          const key = `${fund.class_cnpj}|${fund.subclass_id}`
          const metrics = fund.metrics
          return (
            <tr
              key={key}
              aria-selected={selected === key}
              tabIndex={0}
              onClick={() => onSelect(key)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  onSelect(key)
                }
              }}
            >
              <td className="name-cell" style={{ maxWidth: 190 }} title={fund.name}>
                {fund.name}
              </td>
              <td className="secondary name-cell" style={{ maxWidth: 130 }} title={fund.anbima_classification ?? fund.classification ?? undefined}>
                {fund.anbima_classification ?? fund.classification ?? '—'}
              </td>
              <td className="num num-col">{brlCompact(metrics?.latest_nav_brl)}</td>
              <td
                className={`num num-col ${deltaClass(metrics?.return_12m)}`}
                title={metrics?.return_12m_status !== 'ok' ? `Não comparável: ${metrics?.return_12m_status ?? 'sem série'}` : undefined}
              >
                {metrics?.return_12m_status === 'ok' ? percent(metrics.return_12m, true) : 'n/c'}
              </td>
              <td className={`num num-col ${deltaClass(metrics?.net_flow_12m_brl)}`}>
                {metrics?.net_flow_status === 'ok' ? brlSigned(metrics.net_flow_12m_brl) : 'n/c'}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
    </div>
  )
}

function FundPanel({ fundKey }: { fundKey: string }) {
  const [classCnpj, subclass] = fundKey.split('|')
  const performance = usePerformance(classCnpj ?? null, subclass ?? '')
  if (performance.isLoading) return <LoadingRows rows={4} label="Carregando série do fundo" />
  if (performance.error || !performance.data) return <ErrorState error={performance.error} onRetry={() => void performance.refetch()} />
  const data = performance.data
  const m = data.metrics
  return (
    <div>
      <h4 style={{ margin: '8px 0 2px', fontSize: 'var(--fs-md)' }}>{data.name}</h4>
      <p className="muted" style={{ margin: 0, fontSize: 'var(--fs-xs)' }}>
        Cota rebaseada a 100 em {date(data.start)}, até {date(data.end)}. {data.note}
      </p>
      {data.points.length > 1 ? (
        <Suspense fallback={<LoadingRows rows={4} label="Carregando gráfico" />}>
          <QuotaChart performance={data} />
        </Suspense>
      ) : (
        <EmptyState title="Série insuficiente para o gráfico" />
      )}
      {m ? (
        <dl className="facts" style={{ gridTemplateColumns: '120px 1fr 120px 1fr' }}>
          <dt>Retorno 12m</dt>
          <dd className={`num ${deltaClass(m.return_12m)}`}>{m.return_12m_status === 'ok' ? percent(m.return_12m, true) : `n/c (${m.return_12m_status})`}</dd>
          <dt>No ano</dt>
          <dd className={`num ${deltaClass(m.return_ytd)}`}>{m.return_ytd_status === 'ok' ? percent(m.return_ytd, true) : 'n/c'}</dd>
          <dt>Volatilidade 12m</dt>
          <dd className="num">{ratio(m.volatility_12m)}</dd>
          <dt>Pior queda 12m</dt>
          <dd className="num">{percent(m.max_drawdown_12m)}</dd>
        </dl>
      ) : null}
    </div>
  )
}

export function AccountScreen() {
  const { accountId } = useParams()
  const [params, setParams] = useSearchParams()
  const account = useAccount(accountId ?? null)
  const quality = useDataQuality()
  const compare = useCompareSet()
  // The chosen fund belongs to one account+unit; switching either falls back to the largest fund.
  const [fundChoice, setFundChoice] = useState<{ scope: string; key: string } | null>(null)

  const units = account.data?.scores ?? []
  const requested = params.get('unit')
  const unitKey = units.some((u) => u.unit_key === requested) ? requested : (units[0]?.unit_key ?? null)
  const explanation = useExplanation(unitKey)
  const unit = units.find((u) => u.unit_key === unitKey)
  const deskUnit = unit && unit.unit_key.includes(':') ? unit.unit_key : null
  const funds = useFunds(account.data ? account.data.account_id : null, unit?.evidence_mode === 'observed' ? deskUnit : null)

  const scope = `${accountId ?? ''}|${unitKey ?? ''}`
  const firstFund = funds.data?.data[0]
  const activeFund =
    (fundChoice?.scope === scope ? fundChoice.key : null) ??
    (firstFund ? `${firstFund.class_cnpj}|${firstFund.subclass_id}` : null)
  const setFundKey = (key: string) => setFundChoice({ scope, key })

  const accountQuality = account.data?.quality
  const bankFreshness = quality.data?.freshness.find((f) => f.source_id === 'bcb_ifdata_cadastro')

  const sources = useMemo(() => {
    const entries = account.data?.legal_entities.map((e) => e.source) ?? []
    return Array.from(new Map(entries.map((s) => [`${s.source_type}${s.sha256 ?? ''}`, s])).values())
  }, [account.data])

  if (!accountId) {
    return (
      <div className="page">
        <EmptyState title="Selecione uma conta" action={<Link className="button button--primary" to="/">Ir para o ranking</Link>}>
          Escolha uma linha no ranking ou busque pelo nome, razão social ou CNPJ com <kbd>/</kbd>.
        </EmptyState>
      </div>
    )
  }
  if (account.isLoading) return <div className="page"><LoadingRows rows={14} label="Carregando conta" /></div>
  if (account.error || !account.data) {
    return <div className="page"><ErrorState error={account.error} onRetry={() => void account.refetch()} /></div>
  }
  const detail = account.data

  return (
    <div className="page">
      <header className="page__head">
        <div style={{ minWidth: 0 }}>
          <h1 className="page__title">{detail.canonical_name}</h1>
          <p className="page__lede">
            {detail.legal_name ?? 'Razão social não identificada'}
            {detail.cnpj ? <span className="num"> {cnpj(detail.cnpj)}</span> : null}. {detail.institution_type}, {detail.strategy_profile}.
          </p>
          <div className="chips" style={{ marginTop: 6 }}>
            {detail.tier ? <TierBadge tier={detail.tier} /> : null}
            <ConflictBadge count={detail.open_conflicts} accountId={detail.account_id} />
          </div>
        </div>
        <Link className="button" to={{ pathname: '/', search: params.toString() }}>
          Voltar ao ranking
        </Link>
      </header>

      <div className="tile-row" role="list" aria-label="Indicadores da conta">
        <div className="tile" role="listitem">
          <div className="tile__label">PL não-FIC</div>
          <div className="tile__value">{brlCompact(detail.nav_brl_non_fic)}</div>
        </div>
        <div className="tile" role="listitem">
          <div className="tile__label">Captação líquida 12m</div>
          <div className={`tile__value ${deltaClass(detail.net_flow_12m_brl)}`}>{brlSigned(detail.net_flow_12m_brl)}</div>
        </div>
        <div className="tile" role="listitem">
          <div className="tile__label">Classes ativas</div>
          <div className="tile__value">{accountQuality ? accountQuality.active_classes : '—'}</div>
        </div>
        <div className="tile" role="listitem">
          <div className="tile__label">Retorno 12m comparável</div>
          <div className="tile__value">{ratio(accountQuality?.comparable_12m_share)}</div>
        </div>
        <div className="tile" role="listitem">
          <div className="tile__label">Unidades pontuadas</div>
          <div className="tile__value">{units.length}</div>
        </div>
      </div>

      {units.length > 1 ? (
        <section className="section" aria-labelledby="units-title">
          <h2 className="section__title" id="units-title">
            Mesas e áreas <small>cada uma pontuada separadamente</small>
          </h2>
          <div className="chips" role="tablist" aria-label="Unidade analisada">
            {units.map((u) => (
              <button
                key={u.unit_key}
                type="button"
                role="tab"
                aria-selected={u.unit_key === unitKey}
                className="button"
                style={u.unit_key === unitKey ? { borderColor: 'var(--amber)', color: 'var(--amber)' } : undefined}
                onClick={() => {
                  const next = new URLSearchParams(params)
                  next.set('unit', u.unit_key)
                  setParams(next, { replace: true })
                }}
              >
                {u.unit_name.split(' — ')[1] ?? u.unit_name} <span className="num muted">{score(u.priority.point ?? u.fit.point)}</span>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {unit ? (
        <div className="columns-360" style={{ marginTop: 'var(--gap-4)' }}>
          <div>
            <section className="section" aria-labelledby="score-title" style={{ marginTop: 0 }}>
              <h2 className="section__title" id="score-title">
                <span>
                  {unit.unit_name} {unit.evidence_mode === 'assumption' ? <AssumptionBadge /> : null}
                </span>
                <button
                  type="button"
                  className="button"
                  aria-pressed={compare.includes(unit.unit_key)}
                  disabled={!compare.includes(unit.unit_key) && compare.length >= MAX_COMPARE}
                  onClick={() => toggleCompare(unit.unit_key)}
                >
                  {compare.includes(unit.unit_key) ? 'No comparador' : 'Adicionar ao comparador'}
                </button>
              </h2>
              <ScoreStack score={unit} />
            </section>

            {explanation.isLoading ? <LoadingRows rows={6} /> : null}
            {explanation.error ? <ErrorState error={explanation.error} onRetry={() => void explanation.refetch()} /> : null}
            {explanation.data ? (
              <>
                <section className="section" aria-labelledby="why-title">
                  <h2 className="section__title" id="why-title">
                    Por que está aqui <small>reason codes com pontos de contribuição</small>
                  </h2>
                  <ReasonList reasons={explanation.data.reasons} />
                </section>
                <section className="section" aria-labelledby="fit-title">
                  <h2 className="section__title" id="fit-title">
                    Fit estrutural <small>peso, valor normalizado e evidência</small>
                  </h2>
                  <FactorTable factors={explanation.data.factors} group="fit" />
                </section>
                <section className="section" aria-labelledby="timing-title">
                  <h2 className="section__title" id="timing-title">
                    Timing comercial <small>performance limitada a 10% do peso</small>
                  </h2>
                  <FactorTable factors={explanation.data.factors} group="timing" />
                </section>
                <section className="section" aria-labelledby="products-title">
                  <h2 className="section__title" id="products-title">
                    Workflows a explorar <small>hipóteses para a conversa</small>
                  </h2>
                  <ul className="reasons">
                    {explanation.data.products.map((product) => (
                      <li key={product.product_code}>
                        <strong>{product.product_name}</strong>
                        <span className="secondary">: {product.workflow}. </span>
                        <span className="muted">{product.rationale}</span>
                      </li>
                    ))}
                  </ul>
                </section>
                <section className="section" aria-labelledby="limits-title">
                  <h2 className="section__title" id="limits-title">
                    Limitações do modelo
                  </h2>
                  <ul className="reasons muted">
                    {explanation.data.limitations.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </section>
              </>
            ) : null}
          </div>

          <div>
            {unit.analysis_unit === 'mesa/área' && bankFreshness && bankFreshness.status !== 'fresh' ? (
              <p className="callout callout--critical" style={{ marginTop: 0 }}>
                <FreshnessBadge status={bankFreshness.status} /> IF.data (Banco Central) indisponível desde a última
                coleta: dados prudenciais do banco não entram no score.
              </p>
            ) : null}

            <section className="section" aria-labelledby="entities-title" style={{ marginTop: 0 }}>
              <h2 className="section__title" id="entities-title">
                Entidades e contato institucional <small>cadastro de gestores da CVM</small>
              </h2>
              <table className="grid grid--compact" aria-label="Entidades legais">
                <thead>
                  <tr>
                    <th scope="col">Entidade</th>
                    <th scope="col">CNPJ</th>
                    <th scope="col">Telefone</th>
                    <th scope="col">Situação</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.legal_entities.map((entity) => (
                    <tr key={entity.cnpj} style={{ cursor: 'default' }}>
                      <td className="name-cell" style={{ maxWidth: 220 }} title={`${entity.legal_name}. ${entity.relation_evidence}`}>
                        {entity.trade_name ?? entity.legal_name}
                        <div className="muted" style={{ fontSize: 'var(--fs-xs)' }}>{RELATION[entity.relation] ?? entity.relation}</div>
                      </td>
                      <td className="num">{cnpj(entity.cnpj)}</td>
                      <td className="num">{phone(entity.phone_official)}</td>
                      <td className={entity.cvm_status === 'EM FUNCIONAMENTO NORMAL' ? 'secondary' : ''} style={{ fontSize: 'var(--fs-xs)' }}>
                        {entity.cvm_status === 'EM FUNCIONAMENTO NORMAL' ? 'ativa' : entity.cvm_status.toLowerCase()}
                        {entity.approval_status === 'pending_human_review' ? <div className="muted">vínculo a revisar</div> : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {detail.people.length ? (
                <p className="secondary" style={{ fontSize: 'var(--fs-sm)', marginTop: 8 }}>
                  Diretor de gestão registrado na CVM:{' '}
                  {detail.people.map((person) => person.full_name).join(', ')}. Registro público; outros cargos não
                  são coletados.
                </p>
              ) : null}
            </section>

            <section className="section" aria-labelledby="offices-title">
              <h2 className="section__title" id="offices-title">
                Escritórios <small>endereços CVM geocodificados; planilha não confirmada fica sem ponto</small>
              </h2>
              <ul className="reasons">
                {detail.offices.map((office) => (
                  <li key={office.office_key} style={{ display: 'flex', gap: 8, justifyContent: 'space-between' }}>
                    <span style={{ minWidth: 0 }}>
                      {addressCase(office.location.address)}
                      {office.office_kind === 'workbook' ? <span className="muted"> (planilha)</span> : null}
                    </span>
                    {office.office_kind === 'regulatory' ? (
                      <PrecisionBadge exact={office.location.is_exact} precision={office.location.precision} />
                    ) : (
                      <span className="badge badge--assumption">não confirmado</span>
                    )}
                  </li>
                ))}
              </ul>
            </section>

            {unit.evidence_mode === 'observed' ? (
              <section className="section" aria-labelledby="funds-title">
                <h2 className="section__title" id="funds-title">
                  Fundos <small>maiores classes não-FIC por PL; n/c = não comparável</small>
                </h2>
                {funds.isLoading ? <LoadingRows rows={5} /> : null}
                {funds.error ? <ErrorState error={funds.error} onRetry={() => void funds.refetch()} /> : null}
                {funds.data && funds.data.data.length === 0 ? <EmptyState title="Sem classes com métricas" /> : null}
                {funds.data && funds.data.data.length > 0 ? (
                  <>
                    <FundsTable funds={funds.data.data} selected={activeFund} onSelect={setFundKey} />
                    {activeFund ? <FundPanel fundKey={activeFund} /> : null}
                  </>
                ) : null}
              </section>
            ) : null}

            <section className="section" aria-labelledby="signals-title">
              <h2 className="section__title" id="signals-title">
                Sinais de timing <small>com fonte e data</small>
              </h2>
              {detail.signals.filter((s) => !unitKey || s.unit_key === unitKey).length === 0 ? (
                <p className="muted" style={{ fontSize: 'var(--fs-sm)' }}>Nenhum sinal observado para esta unidade.</p>
              ) : (
                <ul className="reasons">
                  {detail.signals
                    .filter((s) => !unitKey || s.unit_key === unitKey)
                    .map((signal) => (
                      <li key={`${signal.signal_type}-${signal.observed_at}`}>
                        <strong>{signal.label ?? signal.signal_type}</strong>: {signal.explanation}
                        <div className="muted" style={{ fontSize: 'var(--fs-xs)' }}>
                          <SourceLink source={signal.source} /> {signal.evidence[0] ? <EvidenceText text={signal.evidence[0]} /> : null}
                        </div>
                      </li>
                    ))}
                </ul>
              )}
            </section>

            <section className="section" aria-labelledby="quality-title">
              <h2 className="section__title" id="quality-title">
                Qualidade dos dados desta conta
                <Link to={`/qualidade?conta=${detail.account_id}`} style={{ fontSize: 'var(--fs-xs)' }}>
                  ver conflitos
                </Link>
              </h2>
              <ul className="reasons">
                {(accountQuality?.gaps.length ? accountQuality.gaps : ['Nenhuma lacuna crítica nas fontes deste piloto.']).map((gap) => (
                  <li key={gap} className="secondary">
                    {gap}
                  </li>
                ))}
              </ul>
              <p className="muted" style={{ fontSize: 'var(--fs-xs)', marginTop: 8 }}>
                Fontes:{' '}
                {sources.map((source, index) => (
                  <span key={`${source.source_type}${source.sha256 ?? ''}`}>
                    {index ? ', ' : ''}
                    <SourceLink source={source} />
                  </span>
                ))}
              </p>
            </section>
          </div>
        </div>
      ) : (
        <EmptyState title="Conta sem score na rodada atual" />
      )}
    </div>
  )
}
