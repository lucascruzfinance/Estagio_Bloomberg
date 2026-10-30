import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { resetCompareForTests } from './lib/compare'
import { renderApp } from './test/render'
import { fixtures, server } from './test/server'

// Canvas charts are exercised in Playwright; jsdom has no canvas.
vi.mock('./charts/QuotaChart', () => ({ QuotaChart: () => <div data-testid="quota-chart" /> }))

const TOTAL = fixtures.scores.data.length

async function ranking() {
  return screen.findByRole('table', { name: 'Ranking de unidades' })
}

function bodyRows(table: HTMLElement) {
  return within(table).getAllByRole('row').slice(1)
}

beforeEach(() => resetCompareForTests())

describe('jornada: ranking e filtros', () => {
  it('lista todas as unidades em ordem de rank com faixas de incerteza', async () => {
    renderApp('/')
    const table = await ranking()
    expect(bodyRows(table)).toHaveLength(TOTAL)
    expect(screen.getByText(`${TOTAL} de ${TOTAL} unidades`)).toBeInTheDocument()
    const first = bodyRows(table)[0]!
    expect(within(first).getByText(fixtures.scores.data[0]!.unit_name.split(' — ')[0]!)).toBeInTheDocument()
    expect(within(first).getAllByRole('img').length).toBeGreaterThanOrEqual(3)
  })

  it('filtra por faixa, sincroniza a URL e persiste o filtro entre visitas', async () => {
    const user = userEvent.setup()
    const view = renderApp('/')
    await ranking()
    await user.selectOptions(screen.getByLabelText('Faixa'), 'Prioridade agora')
    const expected = fixtures.scores.data.filter((row) => row.tier === 'Prioridade agora').length
    await waitFor(() => expect(bodyRows(screen.getByRole('table', { name: 'Ranking de unidades' }))).toHaveLength(expected))
    expect(window.location.search).toContain('tier=Prioridade+agora')
    expect(JSON.parse(window.localStorage.getItem('nsi.filters.v1') ?? '{}').tier).toBe('Prioridade agora')

    view.unmount()
    renderApp('/') // new visit without query string restores the stored filter
    await waitFor(() => expect(window.location.search).toContain('tier=Prioridade'))
    expect(bodyRows(await ranking())).toHaveLength(expected)
  })

  it('mostra estado vazio com ação para limpar filtros', async () => {
    const user = userEvent.setup()
    renderApp('/?q=zzzz-inexistente')
    expect(await screen.findByText('Nenhuma unidade com esses filtros')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Limpar filtros' }))
    expect(bodyRows(await ranking())).toHaveLength(TOTAL)
  })

  it('ordena por coluna com aria-sort', async () => {
    const user = userEvent.setup()
    renderApp('/')
    const table = await ranking()
    const header = within(table).getByRole('columnheader', { name: /Fit/ })
    await user.click(within(header).getByRole('button'))
    expect(header).toHaveAttribute('aria-sort', 'descending')
    const fits = fixtures.scores.data.map((row) => row.fit.point ?? -1).sort((a, b) => b - a)
    const firstFit = within(bodyRows(table)[0]!).getByRole('img', { name: /^Fit:/ })
    expect(firstFit.getAttribute('aria-label')).toContain(String(Math.round(fits[0]!)))
  })
})

describe('jornada: seleção e Account 360', () => {
  it('abre o painel ao selecionar e fecha com Esc', async () => {
    const user = userEvent.setup()
    renderApp('/')
    const table = await ranking()
    const verde = bodyRows(table).find((row) => row.getAttribute('data-unit') === 'org-verde-asset')!
    await user.click(verde)
    const panel = await screen.findByRole('article', { name: /Conta 360 de Verde/ })
    expect(within(panel).getByText('Por que está aqui')).toBeInTheDocument()
    expect(within(panel).getByText('Confiança')).toBeInTheDocument()
    expect(window.location.search).toContain('unit=org-verde-asset')
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('article')).not.toBeInTheDocument())
  })

  it('navega pelo teclado e adiciona ao comparador com Espaço', async () => {
    const user = userEvent.setup()
    renderApp('/')
    const table = await ranking()
    bodyRows(table)[0]!.focus()
    await user.keyboard('{ArrowDown}')
    const second = fixtures.scores.data[1]!.unit_key
    await waitFor(() => expect(window.location.search).toContain(`unit=${encodeURIComponent(second)}`))
    await user.keyboard(' ')
    expect(screen.getByRole('link', { name: /Comparador \(1\)/ })).toBeInTheDocument()
  })

  it('mostra a conta completa com entidades, conflitos, fundos e fontes', async () => {
    renderApp('/contas/org-verde-asset')
    expect(await screen.findByRole('heading', { level: 1, name: 'Verde Asset Management' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Entidades legais' })).toBeInTheDocument()
    expect(await screen.findByRole('table', { name: 'Fatores de fit' })).toBeInTheDocument()
    expect(await screen.findByRole('table', { name: 'Maiores classes por PL' })).toBeInTheDocument()
    expect(await screen.findByTestId('quota-chart')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Cadastro de gestores \(CVM\)/ }).length).toBeGreaterThan(0)
  })

  it('sinaliza mesas por premissa e fonte bancária indisponível', async () => {
    renderApp('/contas/org-btg-pactual?unit=org-btg-pactual:sales-trading-treasury')
    expect(await screen.findByRole('heading', { level: 1, name: 'BTG Pactual' })).toBeInTheDocument()
    expect(await screen.findByText(/IF.data \(Banco Central\) indisponível/)).toBeInTheDocument()
    expect(screen.getAllByText('premissa').length).toBeGreaterThan(0)
    expect(screen.getByRole('tab', { name: /Sales & Trading/ })).toHaveAttribute('aria-selected', 'true')
  })
})

describe('jornada: comparação', () => {
  it('compara unidades e avisa quando mistura evidência observada e premissa', async () => {
    window.localStorage.setItem('nsi.compare.v1', JSON.stringify([]))
    renderApp('/comparar?units=org-verde-asset,org-btg-pactual:sales-trading-treasury')
    expect(await screen.findByRole('table', { name: 'Comparação de unidades' })).toBeInTheDocument()
    expect(screen.getByText(/mistura unidades observadas/)).toBeInTheDocument()
    expect(screen.getByRole('rowheader', { name: /Captação\/resgates/ })).toBeInTheDocument()
    expect(screen.getAllByText('sem evidência').length).toBeGreaterThan(0)
  })

  it('pede ao menos duas unidades', async () => {
    renderApp('/comparar')
    expect(await screen.findByText('Escolha de 2 a 5 unidades para comparar')).toBeInTheDocument()
  })
})

describe('estados de erro, vencido e conflito', () => {
  it('mostra erro da API com request_id e permite tentar de novo', async () => {
    const user = userEvent.setup()
    server.use(
      http.get('*/api/v1/scores', () =>
        HttpResponse.json(
          { type: 'internal', title: 'Erro interno', status: 500, detail: 'Falha inesperada', instance: '/api/v1/scores', request_id: 'req-abc123' },
          { status: 500 },
        ),
      ),
    )
    renderApp('/')
    expect(await screen.findByText('Não foi possível carregar')).toBeInTheDocument()
    expect(screen.getByText('request_id req-abc123')).toBeInTheDocument()
    server.resetHandlers()
    await user.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    expect(bodyRows(await ranking())).toHaveLength(TOTAL)
  })

  it('avisa quando a API está fora do ar', async () => {
    server.use(http.get('*/api/v1/scores', () => HttpResponse.error()))
    renderApp('/')
    expect(await screen.findByText('A API está fora do ar')).toBeInTheDocument()
  })

  it('marca dado vencido no painel quando o informe diário passa do limite', async () => {
    const stale = structuredClone(fixtures.quality)
    const daily = stale.freshness.find((item) => item.source_id === 'cvm_inf_diario')!
    daily.status = 'stale'
    daily.age_days = 21
    server.use(http.get('*/api/v1/data-quality', () => HttpResponse.json(stale)))
    renderApp('/?unit=org-verde-asset')
    expect(await screen.findByText(/Informe diário com 21 dias/)).toBeInTheDocument()
    expect(screen.getByText('dado vencido')).toBeInTheDocument()
  })

  it('leva da fonte conflitante à fila de revisão da conta', async () => {
    renderApp('/qualidade?conta=org-jive')
    expect(await screen.findByRole('heading', { level: 1, name: 'Qualidade dos dados' })).toBeInTheDocument()
    const table = await screen.findByRole('table', { name: 'Conflitos de fonte' })
    const rows = within(table).getAllByRole('row').slice(1)
    expect(rows.length).toBeGreaterThan(0)
    rows.forEach((row) => expect(row).toHaveTextContent('Jive Investments'))
    expect(screen.getAllByText('fonte indisponível').length).toBeGreaterThan(0)
  })

  it('não exibe selo DEMO com dados reais', async () => {
    renderApp('/')
    await ranking()
    expect(screen.queryByText('DEMO')).not.toBeInTheDocument()
  })
})

describe('modo demonstração', () => {
  it('identifica a base congelada com selo DEMO e nota com a data', async () => {
    server.use(
      http.get('*/api/v1/meta', () =>
        HttpResponse.json({
          ...fixtures.meta,
          data_mode: 'demo',
          data_note: 'Base de demonstração congelada (dados públicos até 2026-10-27); não há atualização ao vivo.',
        }),
      ),
    )
    renderApp('/')
    expect(await screen.findByText('DEMO')).toBeInTheDocument()
    expect(screen.getByText(/Base de demonstração congelada/)).toBeInTheDocument()
  })
})
