import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { DemoBadge, FreshnessBadge, PrecisionBadge } from './Badges'
import { ScoreBand } from './ScoreBand'
import { tooltipHtml } from '../screens/MapScreen'
import type { OfficeFeature } from '../api/types'

describe('ScoreBand', () => {
  it('descreve ponto e faixa de incerteza para leitores de tela', () => {
    render(<ScoreBand band={{ point: 72.4, lower: 60, upper: 80 }} label="Fit" />)
    expect(screen.getByRole('img', { name: 'Fit: 72 de 100, faixa 60–80' })).toBeInTheDocument()
  })

  it('mostra ausência de evidência sem converter em zero', () => {
    const { container } = render(<ScoreBand band={{ point: null, lower: 0, upper: 100 }} label="Timing" />)
    expect(screen.getByRole('img', { name: /Timing: sem evidência observada, faixa 0–100/ })).toBeInTheDocument()
    expect(container.querySelector('.band__unknown')).not.toBeNull()
    expect(container.querySelector('.band__point')).toBeNull()
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})

describe('selos de estado', () => {
  it('distingue dado vencido, fonte indisponível e precisão aproximada', () => {
    render(
      <MemoryRouter>
        <FreshnessBadge status="stale" />
        <FreshnessBadge status="unavailable" />
        <PrecisionBadge exact={false} precision="street" />
        <PrecisionBadge exact precision="address" />
        <DemoBadge />
      </MemoryRouter>,
    )
    expect(screen.getByText('dado vencido')).toBeInTheDocument()
    expect(screen.getByText('fonte indisponível')).toBeInTheDocument()
    expect(screen.getByText('aprox. rua')).toBeInTheDocument()
    expect(screen.getByText('endereço exato')).toBeInTheDocument()
    expect(screen.getByText('DEMO')).toBeInTheDocument()
  })
})

describe('tooltip do mapa', () => {
  const properties = {
    office_key: 'k',
    account_id: 'org-x',
    canonical_name: 'Gestora <X>',
    institution_type: 'gestora independente',
    legal_name: 'GESTORA X LTDA',
    entity_cnpj: '19749539000176',
    relation: 'primary_manager',
    address: 'Av. Brigadeiro Faria Lima, 3600',
    city: 'SÃO PAULO',
    state: 'SP',
    phone_official: '+551149358500',
    precision: 'street',
    is_exact: false,
    tier: 'Prioridade agora',
    priority_point: 70,
    fit_point: 72,
    timing_point: 60,
    confidence: 80,
    nav_brl_non_fic: 12e9,
    net_flow_12m_brl: -2.2e9,
  } satisfies OfficeFeature['properties']

  it('é enxuto, escapa HTML e não expõe dados pessoais', () => {
    const html = tooltipHtml(properties)
    expect(html).toContain('Gestora &#60;X&#62;')
    expect(html).toContain('(11) 4935-8500')
    expect(html).toContain('aproximado (rua)')
    expect(html).toContain('R$ 12,0 bi')
    expect(html).not.toMatch(/@|diretor|CPF|e-mail/i)
  })
})
