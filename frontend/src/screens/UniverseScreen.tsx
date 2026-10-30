import { BarChart, LineChart } from 'echarts/charts'
import * as echarts from 'echarts/core'
import { useMemo } from 'react'
import { useSearchParams } from 'react-router'
import { useUniverse, useUniverseEntity, useUniverseSummary } from '../api/hooks'
import type { UniverseDetail, UniverseRow } from '../api/types'
import { CHART_TEXT, EChart } from '../charts/EChart'
import { SourceLink } from '../components/SourceLink'
import { EmptyState, ErrorState, LoadingRows } from '../components/States'
import { brlCompact, brlSigned, cnpj, date, DASH, deltaClass, percent, titleCase } from '../lib/format'

echarts.use([BarChart, LineChart])

const KIND: Record<string, string> = {
  gestora: 'Gestora',
  banco_multiplo: 'Banco múltiplo',
  banco_investimento: 'Banco de investimento',
  caixa_economica: 'Caixa econômica',
  corretora: 'Corretora',
  distribuidora: 'Distribuidora',
  administrador_fiduciario: 'Administrador fiduciário',
  custodiante: 'Custodiante',
  escriturador: 'Escriturador',
  infraestrutura_mercado: 'Infraestrutura de mercado',
}
const TIER: Record<string, string> = { curated: 'Curada', radar: 'Radar', universe: 'Universo' }
const SORTS: Record<string, string> = {
  nav: 'PL',
  net_flow: 'Captação 12m',
  registered: 'Registro mais recente',
  administered: 'Fundos administrados',
  classes: 'Classes ativas',
  name: 'Nome',
}
const PAGE_SIZE = 100

function MonthlyChart({ detail }: { detail: UniverseDetail }) {
  const option = useMemo(() => {
    const months = detail.monthly.map((m) => m.month.slice(0, 7))
    return {
      animation: false,
      grid: { left: 64, right: 64, top: 24, bottom: 28 },
      tooltip: {
        trigger: 'axis',
        valueFormatter: (value: number) => brlCompact(value),
      },
      legend: { show: false },
      xAxis: {
        type: 'category',
        data: months,
        axisLabel: { color: CHART_TEXT.muted, fontSize: 10 },
        axisLine: { lineStyle: { color: CHART_TEXT.axis } },
      },
      yAxis: [
        {
          type: 'value',
          name: 'Captação líquida',
          nameTextStyle: { color: CHART_TEXT.muted, fontSize: 10 },
          axisLabel: { color: CHART_TEXT.muted, fontSize: 10, formatter: (v: number) => brlCompact(v) },
          splitLine: { lineStyle: { color: CHART_TEXT.grid } },
        },
        {
          type: 'value',
          name: 'PL',
          nameTextStyle: { color: CHART_TEXT.muted, fontSize: 10 },
          axisLabel: { color: CHART_TEXT.muted, fontSize: 10, formatter: (v: number) => brlCompact(v) },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: 'Captação líquida',
          type: 'bar',
          data: detail.monthly.map((m) => ({
            value: m.net_flow_brl,
            itemStyle: { color: (m.net_flow_brl ?? 0) >= 0 ? '#3fae6a' : '#e0584f' },
          })),
        },
        {
          name: 'PL',
          type: 'line',
          yAxisIndex: 1,
          showSymbol: false,
          lineStyle: { color: '#f2a03d', width: 2 },
          itemStyle: { color: '#f2a03d' },
          data: detail.monthly.map((m) => m.nav_brl),
        },
      ],
    }
  }, [detail])
  return (
    <EChart
      option={option}
      height={240}
      label={`PL e captação líquida mensal de ${detail.legal_name}, ${detail.monthly.length} meses`}
    />
  )
}

function EntityPanel({ cnpj: id }: { cnpj: string }) {
  const entity = useUniverseEntity(id)
  if (entity.isLoading) return <LoadingRows rows={8} label="Carregando entidade" />
  if (entity.error || !entity.data) return <ErrorState error={entity.error} onRetry={() => void entity.refetch()} />
  const d = entity.data
  const last12 = d.monthly.slice(-12)
  const net12 = last12.reduce((sum, m) => sum + (m.net_flow_brl ?? 0), 0)
  return (
    <div className="surface" style={{ padding: 16 }}>
      <h2 className="section__title" style={{ marginTop: 0 }}>
        {titleCase(d.trade_name || d.legal_name)} <small>{cnpj(d.cnpj)}</small>
      </h2>
      <p className="secondary" style={{ margin: '0 0 8px' }}>
        {d.kinds.map((k) => KIND[k] ?? k).join(' · ')} · {TIER[d.coverage_tier]} · grupo {d.group_name} (
        {d.group_members} {d.group_members === 1 ? 'entidade' : 'entidades'})
      </p>
      <p className="secondary" style={{ margin: '0 0 12px' }}>
        {[d.street, d.complement, d.district].filter(Boolean).join(', ')} — {d.city}/{d.state}
        {d.centre ? ` · ${d.centre}` : ''} · registro CVM {date(d.registration_date)}
      </p>
      <div className="tile-row" role="list" aria-label="Indicadores da entidade">
        <div className="tile" role="listitem">
          <div className="tile__label">PL (não FIC) {d.nav_month ? `em ${date(d.nav_month)}` : ''}</div>
          <div className="tile__value">{brlCompact(d.nav_brl)}</div>
        </div>
        <div className="tile" role="listitem">
          <div className="tile__label">Captação líquida 12m</div>
          <div className={`tile__value ${deltaClass(net12)}`}>{d.monthly.length ? brlSigned(net12) : DASH}</div>
        </div>
        <div className="tile" role="listitem">
          <div className="tile__label">Classes ativas / abertas</div>
          <div className="tile__value">
            {d.active_classes} / {d.selected_classes}
          </div>
        </div>
        <div className="tile" role="listitem">
          <div className="tile__label">Fundos administrados</div>
          <div className="tile__value">{d.funds_administered.toLocaleString('pt-BR')}</div>
        </div>
      </div>
      {d.monthly.length ? (
        <>
          <h3 className="section__title">
            PL e captação mês a mês <small>Informe Diário CVM, classes não FIC, inclui exclusivos</small>
          </h3>
          <MonthlyChart detail={d} />
        </>
      ) : (
        <p className="muted">Sem fundos com Informe Diário: entidade de serviços ou sell side.</p>
      )}
      {d.top_funds.length ? (
        <>
          <h3 className="section__title">Maiores fundos (série mensal)</h3>
          <table className="grid grid--compact" aria-label="Maiores fundos da entidade">
            <thead>
              <tr>
                <th scope="col">Classe</th>
                <th scope="col">Classificação</th>
                <th scope="col" className="num-col">PL</th>
                <th scope="col" className="num-col">Retorno 12m</th>
                <th scope="col" className="num-col">Captação 12m</th>
              </tr>
            </thead>
            <tbody>
              {d.top_funds.map((f) => (
                <tr key={f.class_cnpj} style={{ cursor: 'default' }}>
                  <td className="name-cell" title={cnpj(f.class_cnpj)} style={{ maxWidth: 280 }}>
                    {titleCase(f.class_name)}
                  </td>
                  <td className="secondary">{f.anbima_classification ?? f.classification ?? DASH}</td>
                  <td className="num num-col">{brlCompact(f.nav_brl)}</td>
                  <td className={`num num-col ${deltaClass(f.return_12m)}`}>{percent(f.return_12m, true)}</td>
                  <td className={`num num-col ${deltaClass(f.net_flow_12m_brl)}`}>{brlSigned(f.net_flow_12m_brl)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted" style={{ fontSize: 'var(--fs-xs)' }}>
            Retorno do fundo, não lucro da gestora. Retorno 12m pela cota de fim de mês; vazio se a série não cobre 12
            meses ou a classe só reporta por subclasse.
          </p>
        </>
      ) : null}
      <p className="secondary" style={{ marginTop: 12 }}>
        Fonte: <SourceLink source={d.source as unknown as Parameters<typeof SourceLink>[0]['source']} />
      </p>
    </div>
  )
}

export function UniverseScreen() {
  const [params, setParams] = useSearchParams()
  const filters = {
    tier: params.get('camada'),
    side: params.get('lado'),
    kind: params.get('tipo'),
    centre: params.get('centro'),
    q: params.get('q'),
    sort: params.get('ordem') ?? 'nav',
    page: Number(params.get('pagina') ?? '1'),
  }
  const selected = params.get('cnpj')
  const summary = useUniverseSummary()
  const list = useUniverse({ ...filters, pageSize: PAGE_SIZE })

  const setParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    if (key !== 'cnpj' && key !== 'pagina') next.delete('pagina')
    setParams(next, { replace: true })
  }

  const totals = summary.data?.totals as Record<string, number> | undefined
  const rows: UniverseRow[] = list.data?.data ?? []
  const total = list.data?.meta.total ?? 0
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <h1 className="page__title">Universo SP/RJ</h1>
          <p className="page__lede">
            Toda gestora e todo intermediário ativo na CVM com sede em São Paulo, Rio de Janeiro ou Osasco, com PL e
            captação do Informe Diário{summary.data ? ` até ${date(String(summary.data.as_of.fund_month ?? ''))}` : ''}.
            Vínculo só por CNPJ; grupos por conglomerado do Banco Central ou registro curado.
          </p>
        </div>
      </header>

      {totals ? (
        <div className="tile-row" role="list" aria-label="Resumo do universo">
          <div className="tile" role="listitem">
            <div className="tile__label">Entidades</div>
            <div className="tile__value">{(totals.entities ?? 0).toLocaleString('pt-BR')}</div>
          </div>
          <div className="tile" role="listitem">
            <div className="tile__label">Buy side / sell side</div>
            <div className="tile__value">
              {(totals.buy_side ?? 0).toLocaleString('pt-BR')} / {(totals.sell_side ?? 0).toLocaleString('pt-BR')}
            </div>
          </div>
          <div className="tile" role="listitem">
            <div className="tile__label">Radar (registradas há ≤ 2 anos)</div>
            <div className="tile__value">{(totals.radar ?? 0).toLocaleString('pt-BR')}</div>
          </div>
          <div className="tile" role="listitem">
            <div className="tile__label">Contas curadas</div>
            <div className="tile__value">{totals.curated_accounts}</div>
          </div>
          <div className="tile" role="listitem">
            <div className="tile__label">Grupos econômicos</div>
            <div className="tile__value">{(totals.groups ?? 0).toLocaleString('pt-BR')}</div>
          </div>
        </div>
      ) : null}

      <div className="filters" role="group" aria-label="Filtros do universo">
        <label className="filter">
          Busca
          <input
            type="search"
            defaultValue={filters.q ?? ''}
            placeholder="nome, grupo ou CNPJ"
            onKeyDown={(event) => {
              if (event.key === 'Enter') setParam('q', (event.target as HTMLInputElement).value.trim() || null)
            }}
          />
        </label>
        <label className="filter">
          Lado
          <select value={filters.side ?? ''} onChange={(e) => setParam('lado', e.target.value || null)}>
            <option value="">todos</option>
            <option value="buy_side">buy side</option>
            <option value="sell_side">sell side</option>
          </select>
        </label>
        <label className="filter">
          Camada
          <select value={filters.tier ?? ''} onChange={(e) => setParam('camada', e.target.value || null)}>
            <option value="">todas</option>
            {Object.entries(TIER).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="filter">
          Tipo
          <select value={filters.kind ?? ''} onChange={(e) => setParam('tipo', e.target.value || null)}>
            <option value="">todos</option>
            {Object.entries(KIND).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="filter">
          Centro
          <select value={filters.centre ?? ''} onChange={(e) => setParam('centro', e.target.value || null)}>
            <option value="">todos</option>
            {(summary.data?.by_centre ?? []).map((c) => (
              <option key={String(c.centre)} value={String(c.centre)}>
                {String(c.centre)} ({String(c.entities)})
              </option>
            ))}
          </select>
        </label>
        <label className="filter">
          Ordenar por
          <select value={filters.sort} onChange={(e) => setParam('ordem', e.target.value)}>
            {Object.entries(SORTS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="columns-2" style={{ alignItems: 'start' }}>
        <section aria-label="Lista do universo">
          {list.isLoading ? <LoadingRows rows={12} label="Carregando universo" /> : null}
          {list.error ? <ErrorState error={list.error} onRetry={() => void list.refetch()} /> : null}
          {list.data && !rows.length ? <EmptyState title="Nenhuma entidade com esses filtros" /> : null}
          {rows.length ? (
            <>
              <table className="grid grid--compact" aria-label="Entidades do universo">
                <thead>
                  <tr>
                    <th scope="col">Entidade</th>
                    <th scope="col">Tipo</th>
                    <th scope="col">Centro</th>
                    <th scope="col" className="num-col">PL</th>
                    <th scope="col" className="num-col">Captação 12m</th>
                    <th scope="col" className="num-col">Registro</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr
                      key={row.cnpj}
                      aria-selected={row.cnpj === selected}
                      tabIndex={0}
                      onClick={() => setParam('cnpj', row.cnpj)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') setParam('cnpj', row.cnpj)
                      }}
                    >
                      <td className="name-cell" style={{ maxWidth: 300 }} title={row.legal_name}>
                        {titleCase(row.trade_name || row.legal_name)}
                        <div className="muted" style={{ fontSize: 'var(--fs-xs)' }}>
                          {row.group_name !== (row.trade_name || row.legal_name) ? `${row.group_name} · ` : ''}
                          {TIER[row.coverage_tier]}
                        </div>
                      </td>
                      <td className="secondary">{KIND[row.primary_kind] ?? row.primary_kind}</td>
                      <td className="secondary">{row.centre ?? DASH}</td>
                      <td className="num num-col">{brlCompact(row.nav_brl)}</td>
                      <td className={`num num-col ${deltaClass(row.net_flow_12m_brl)}`}>{brlSigned(row.net_flow_12m_brl)}</td>
                      <td className="num num-col">{date(row.registration_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="filters" style={{ justifyContent: 'space-between' }}>
                <span className="muted">
                  {total.toLocaleString('pt-BR')} entidades · página {filters.page} de {pages}
                </span>
                <span>
                  <button
                    type="button"
                    className="button"
                    disabled={filters.page <= 1}
                    onClick={() => setParam('pagina', String(filters.page - 1))}
                  >
                    Anterior
                  </button>{' '}
                  <button
                    type="button"
                    className="button"
                    disabled={filters.page >= pages}
                    onClick={() => setParam('pagina', String(filters.page + 1))}
                  >
                    Próxima
                  </button>
                </span>
              </div>
            </>
          ) : null}
        </section>
        <aside aria-label="Detalhe da entidade">
          {selected ? (
            <EntityPanel cnpj={selected} />
          ) : (
            <EmptyState title="Selecione uma entidade">
              PL e captação mês a mês de 36 meses, maiores fundos, endereço e grupo econômico, com fonte.
            </EmptyState>
          )}
        </aside>
      </div>
    </div>
  )
}
