import type { components } from './schema'

type S = components['schemas']

export type AccountSummary = S['AccountSummary']
export type AccountDetail = S['AccountDetail']
export type ScoreRow = S['ScoreRow']
export type ScoreBand = S['ScoreBand']
export type ScoreExplanation = S['ScoreExplanation']
export type FactorOut = S['FactorOut']
export type ReasonOut = S['ReasonOut']
export type ProductOut = S['ProductOut']
export type Comparison = S['Comparison']
export type FundRow = S['FundRow']
export type FundPerformance = S['FundPerformance']
export type SignalOut = S['SignalOut']
export type OfficeFeatureCollection = S['OfficeFeatureCollection']
export type OfficeFeature = S['OfficeFeature']
export type DensityGrid = S['DensityGrid']
export type DataQuality = S['DataQuality']
export type ConflictOut = S['ConflictOut']
export type FreshnessOut = S['FreshnessOut']
export type SearchHit = S['SearchHit']
export type Meta = S['Meta']
export type Readiness = S['Readiness']
export type LegalEntityOut = S['LegalEntityOut']
export type OfficeOut = S['OfficeOut']

export interface Page<T> {
  data: T[]
  meta: { page: number; page_size: number; total: number; sort?: string | null; order?: string | null }
}

export const TIERS = [
  'Prioridade agora',
  'Desenvolver relacionamento',
  'Oportunidade tática',
  'Monitorar',
  'Fit alto — timing desconhecido',
  'Fit baixo — timing desconhecido',
  'Evidência insuficiente',
] as const
export type Tier = (typeof TIERS)[number]

export type UniverseRow = S['UniverseRow']
export type UniverseDetail = S['UniverseDetail']
export type UniverseSummary = S['UniverseSummary']
