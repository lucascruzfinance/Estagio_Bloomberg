import { Link, useLocation } from 'react-router'
import { useAccount, useDataQuality, useExplanation } from '../api/hooks'
import type { ScoreRow } from '../api/types'
import { toggleCompare, useCompareSet, MAX_COMPARE } from '../lib/compare'
import { addressCase, brlCompact, brlSigned, cnpj, deltaClass, phone, score } from '../lib/format'
import { AssumptionBadge, ConflictBadge, FreshnessBadge, PrecisionBadge, TierBadge } from './Badges'
import { ReasonList } from './Reasons'
import { SERIES, ScoreBand } from './ScoreBand'
import { SourceLink } from './SourceLink'
import { ErrorState, LoadingRows } from './States'

export function ScoreStack({ score: row }: { score: ScoreRow }) {
  const rows = [
    { label: 'Prioridade', band: row.priority, color: SERIES.priority },
    { label: 'Fit', band: row.fit, color: SERIES.fit },
    { label: 'Timing', band: row.timing, color: SERIES.timing },
  ]
  return (
    <div className="scores">
      {rows.map(({ label, band, color }) => (
        <div className="score-row" key={label}>
          <span className="score-row__label">{label}</span>
          <ScoreBand band={band} label={label} color={color} wide />
          <span className="score-row__range">
            {score(band.lower)}–{score(band.upper)}
          </span>
        </div>
      ))}
      <div className="score-row">
        <span className="score-row__label">Confiança</span>
        <span className="num">{score(row.confidence)} / 100</span>
        <span />
      </div>
      <p className="scores__note">
        Confiança mede fonte, atualidade e conflitos dos dados; não altera fit, timing nem prioridade.
      </p>
    </div>
  )
}

export function AccountPanel({ unitKey, onClose }: { unitKey: string; onClose: () => void }) {
  const accountId = unitKey.split(':')[0] ?? unitKey
  const explanation = useExplanation(unitKey)
  const account = useAccount(accountId)
  const quality = useDataQuality()
  const compare = useCompareSet()
  const location = useLocation()

  if (explanation.isLoading || account.isLoading) return <LoadingRows rows={10} label="Carregando conta" />
  if (explanation.error || account.error || !explanation.data || !account.data) {
    return (
      <ErrorState
        error={explanation.error ?? account.error}
        onRetry={() => {
          void explanation.refetch()
          void account.refetch()
        }}
      />
    )
  }

  const row = explanation.data.score
  const detail = account.data
  const hq = detail.headquarters
  const entity = detail.legal_entities[0]
  const freshness = quality.data?.freshness ?? []
  const daily = freshness.find((item) => item.source_id === 'cvm_inf_diario')
  const bank = freshness.find((item) => item.source_id === 'bcb_ifdata_cadastro')
  const isBank = row.analysis_unit === 'mesa/área'
  const inCompare = compare.includes(unitKey)
  const sources = Array.from(
    new Map(detail.legal_entities.map((e) => [e.source.source_type + (e.source.sha256 ?? ''), e.source])).values(),
  )

  return (
    <article className="panel" aria-label={`Conta 360 de ${row.unit_name}`}>
      <div className="panel__head">
        <div style={{ minWidth: 0 }}>
          <h2 className="panel__title">{row.unit_name}</h2>
          <p className="panel__legal">
            {detail.legal_name ?? 'Razão social não identificada'} {detail.cnpj ? <span className="num">{cnpj(detail.cnpj)}</span> : null}
          </p>
        </div>
        <button type="button" className="button button--ghost" onClick={onClose} aria-label="Fechar painel (Esc)">
          ✕
        </button>
      </div>

      <div className="chips" style={{ marginTop: 8 }}>
        <TierBadge tier={row.tier} />
        {row.evidence_mode === 'assumption' ? <AssumptionBadge /> : null}
        <ConflictBadge count={detail.open_conflicts} accountId={detail.account_id} />
      </div>

      <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
        <Link className="button button--primary" to={{ pathname: `/contas/${detail.account_id}`, search: location.search }}>
          Abrir conta 360
        </Link>
        <button
          type="button"
          className="button"
          aria-pressed={inCompare}
          disabled={!inCompare && compare.length >= MAX_COMPARE}
          onClick={() => toggleCompare(unitKey)}
        >
          {inCompare ? 'Remover do comparador' : 'Adicionar ao comparador'}
        </button>
      </div>

      {row.evidence_mode === 'assumption' ? (
        <p className="callout callout--info" style={{ marginTop: 12 }}>
          Mesa pontuada por premissa editável: serve para estruturar a conversa por área, não para comparar com
          gestoras observadas.
        </p>
      ) : null}
      {isBank && bank && bank.status !== 'fresh' ? (
        <p className="callout callout--critical" style={{ marginTop: 8 }}>
          <FreshnessBadge status={bank.status} /> IF.data (Banco Central) sem resposta: dados prudenciais do banco
          ainda não entram no score.
        </p>
      ) : null}
      {daily && daily.status === 'stale' ? (
        <p className="callout" style={{ marginTop: 8 }}>
          <FreshnessBadge status="stale" /> Informe diário com {daily.age_days} dias; retornos e fluxos podem estar
          defasados.
        </p>
      ) : null}

      <section className="section" aria-labelledby="panel-scores">
        <h3 className="section__title" id="panel-scores">
          Pontuação <small>ponto observado sobre a faixa dos dados ausentes</small>
        </h3>
        <ScoreStack score={row} />
      </section>

      <section className="section" aria-labelledby="panel-facts">
        <h3 className="section__title" id="panel-facts">
          Contato institucional <small>cadastro CVM</small>
        </h3>
        <dl className="facts">
          <dt>Sede</dt>
          <dd>
            {hq ? (
              <>
                {addressCase(hq.address)} <PrecisionBadge exact={hq.is_exact} precision={hq.precision} />
              </>
            ) : (
              '—'
            )}
          </dd>
          <dt>Telefone</dt>
          <dd className="num">{phone(entity?.phone_official)}</dd>
          <dt>Site</dt>
          <dd>
            {entity?.website_official ? (
              <a href={/^https?:/.test(entity.website_official) ? entity.website_official : `https://${entity.website_official}`} target="_blank" rel="noreferrer noopener">
                {entity.website_official.replace(/^https?:\/\//, '')}
              </a>
            ) : (
              '—'
            )}
          </dd>
          <dt>PL não-FIC</dt>
          <dd className="num">{brlCompact(detail.nav_brl_non_fic)}</dd>
          <dt>Captação 12m</dt>
          <dd className={`num ${deltaClass(detail.net_flow_12m_brl)}`}>{brlSigned(detail.net_flow_12m_brl)}</dd>
        </dl>
      </section>

      <section className="section" aria-labelledby="panel-why">
        <h3 className="section__title" id="panel-why">
          Por que está aqui <small>+ favorável, − desfavorável, ? sem evidência, ~ premissa</small>
        </h3>
        <ReasonList reasons={explanation.data.reasons} limit={9} />
      </section>

      <section className="section" aria-labelledby="panel-products">
        <h3 className="section__title" id="panel-products">
          Workflows a explorar <small>hipóteses, não intenção de compra</small>
        </h3>
        <div className="chips">
          {explanation.data.products.map((product) => (
            <span key={product.product_code} className="chip" title={`${product.workflow}. ${product.rationale}`}>
              {product.product_name}
            </span>
          ))}
        </div>
      </section>

      <section className="section" aria-labelledby="panel-sources">
        <h3 className="section__title" id="panel-sources">
          Fontes
        </h3>
        <ul className="reasons">
          {sources.map((source) => (
            <li key={`${source.source_type}-${source.sha256 ?? ''}`}>
              <SourceLink source={source} />
            </li>
          ))}
          <li className="muted">Modelo {explanation.data.model_version}, dados até {explanation.data.as_of_date.split('-').reverse().join('/')}</li>
        </ul>
      </section>
    </article>
  )
}
