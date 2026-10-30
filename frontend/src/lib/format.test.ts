import { describe, expect, it } from 'vitest'
import { brlCompact, brlSigned, cnpj, date, percent, phone, score } from './format'

describe('formatos brasileiros', () => {
  it('formata BRL compacto com vírgula decimal e unidade explícita', () => {
    expect(brlCompact(488_284_000_000)).toBe('R$ 488,3 bi')
    expect(brlCompact(998_000_000)).toBe('R$ 998 mi')
    expect(brlCompact(-13_744_000_000)).toBe('−R$ 13,7 bi')
    expect(brlSigned(761_000_000)).toBe('+R$ 761 mi')
    expect(brlCompact(null)).toBe('—')
  })

  it('formata percentuais com sinal opcional', () => {
    expect(percent(0.1286, true)).toBe('+12,9%')
    expect(percent(-0.307, true)).toBe('−30,7%')
    expect(percent(null)).toBe('—')
  })

  it('formata datas, CNPJ e telefone', () => {
    expect(date('2026-10-27')).toBe('27/10/2026')
    expect(cnpj('19749539000176')).toBe('19.749.539/0001-76')
    expect(phone('+551149358500')).toBe('(11) 4935-8500')
    expect(phone('+5511987654321')).toBe('(11) 98765-4321')
  })

  it('nunca mostra nulo como zero', () => {
    expect(score(null)).toBe('—')
    expect(score(0)).toBe('0')
  })
})

describe('endereços da CVM', () => {
  it('converte caixa alta mantendo UF, CEP e preposições', async () => {
    const { addressCase } = await import('./format')
    expect(addressCase('AVENIDA BRIGADEIRO FARIA LIMA, 3.600, 11º ANDAR (PARTE), ITAIM BIBI, SÃO PAULO/SP, CEP 04538-132')).toBe(
      'Avenida Brigadeiro Faria Lima, 3.600, 11º Andar (Parte), Itaim Bibi, São Paulo/SP, CEP 04538-132',
    )
    expect(addressCase('RUA MINAS DE PRATA, 30')).toBe('Rua Minas de Prata, 30')
    expect(addressCase('Avenida Brigadeiro Faria Lima, 3555')).toBe('Avenida Brigadeiro Faria Lima, 3555')
  })
})
