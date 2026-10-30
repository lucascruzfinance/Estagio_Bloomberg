import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { apiGet } from './client'
import type {
  AccountDetail,
  AccountSummary,
  Comparison,
  ConflictOut,
  DataQuality,
  FundPerformance,
  FundRow,
  Meta,
  OfficeFeatureCollection,
  Page,
  Readiness,
  ScoreExplanation,
  ScoreRow,
  SearchHit,
  UniverseDetail,
  UniverseRow,
  UniverseSummary,
} from './types'

// Data changes only when a new load runs; revalidation is cheap (ETag), so we
// refetch on focus instead of caching for long and showing stale numbers.
const STALE = 60_000

export const useMeta = () =>
  useQuery({ queryKey: ['meta'], queryFn: ({ signal }) => apiGet<Meta>('/api/v1/meta', {}, signal), staleTime: STALE })

export const useReadiness = () =>
  useQuery({
    queryKey: ['ready'],
    queryFn: ({ signal }) => apiGet<Readiness>('/ready', {}, signal),
    refetchInterval: 30_000,
    retry: false,
  })

export const useScores = () =>
  useQuery({
    queryKey: ['scores'],
    queryFn: ({ signal }) => apiGet<Page<ScoreRow>>('/api/v1/scores', { page_size: 200 }, signal),
    staleTime: STALE,
  })

export const useAccounts = () =>
  useQuery({
    queryKey: ['accounts'],
    queryFn: ({ signal }) =>
      apiGet<Page<AccountSummary>>('/api/v1/accounts', { page_size: 200, sort: 'priority' }, signal),
    staleTime: STALE,
  })

export const useAccount = (accountId: string | null) =>
  useQuery({
    queryKey: ['account', accountId],
    queryFn: ({ signal }) => apiGet<AccountDetail>(`/api/v1/accounts/${accountId}`, {}, signal),
    enabled: Boolean(accountId),
    staleTime: STALE,
  })

export const useExplanation = (unitKey: string | null) =>
  useQuery({
    queryKey: ['explanation', unitKey],
    queryFn: ({ signal }) =>
      apiGet<ScoreExplanation>(`/api/v1/scores/${encodeURIComponent(unitKey ?? '')}/explanation`, {}, signal),
    enabled: Boolean(unitKey),
    staleTime: STALE,
  })

export const useComparison = (units: string[]) =>
  useQuery({
    queryKey: ['comparison', units],
    queryFn: ({ signal }) => apiGet<Comparison>('/api/v1/comparisons', { units: units.join(',') }, signal),
    enabled: units.length >= 2 && units.length <= 5,
    placeholderData: keepPreviousData,
    staleTime: STALE,
  })

export const useFunds = (accountId: string | null, unitKey: string | null) =>
  useQuery({
    queryKey: ['funds', accountId, unitKey],
    queryFn: ({ signal }) =>
      apiGet<Page<FundRow>>(
        '/api/v1/funds',
        {
          account_id: accountId,
          unit_key: unitKey,
          with_metrics: true,
          fund_of_funds: false,
          sort: 'nav',
          page_size: 12,
        },
        signal,
      ),
    enabled: Boolean(accountId),
    staleTime: STALE,
  })

export const usePerformance = (classCnpj: string | null, subclassId: string) =>
  useQuery({
    queryKey: ['performance', classCnpj, subclassId],
    queryFn: ({ signal }) =>
      apiGet<FundPerformance>(
        `/api/v1/funds/${classCnpj}/performance`,
        { subclass_id: subclassId },
        signal,
      ),
    enabled: Boolean(classCnpj),
    staleTime: STALE,
  })

export const useOffices = () =>
  useQuery({
    queryKey: ['map-offices'],
    queryFn: ({ signal }) => apiGet<OfficeFeatureCollection>('/api/v1/map/offices', {}, signal),
    staleTime: STALE,
  })

export const useDataQuality = () =>
  useQuery({
    queryKey: ['data-quality'],
    queryFn: ({ signal }) => apiGet<DataQuality>('/api/v1/data-quality', {}, signal),
    staleTime: STALE,
  })

export const useConflicts = (status: string | null) =>
  useQuery({
    queryKey: ['conflicts', status],
    queryFn: ({ signal }) =>
      apiGet<Page<ConflictOut>>('/api/v1/data-quality/conflicts', { status, page_size: 200 }, signal),
    staleTime: STALE,
  })

export const useSearch = (q: string) =>
  useQuery({
    queryKey: ['search', q],
    queryFn: ({ signal }) => apiGet<SearchHit[]>('/api/v1/search', { q, limit: 8 }, signal),
    enabled: q.trim().length >= 2,
    placeholderData: keepPreviousData,
    staleTime: STALE,
  })

export interface UniverseFilters {
  tier: string | null
  side: string | null
  kind: string | null
  centre: string | null
  q: string | null
  sort: string
  page: number
  pageSize: number
}

export const useUniverseSummary = () =>
  useQuery({
    queryKey: ['universe-summary'],
    queryFn: ({ signal }) => apiGet<UniverseSummary>('/api/v1/universe/summary', {}, signal),
    staleTime: STALE,
  })

export const useUniverse = (filters: UniverseFilters) =>
  useQuery({
    queryKey: ['universe', filters],
    queryFn: ({ signal }) =>
      apiGet<Page<UniverseRow>>(
        '/api/v1/universe',
        {
          tier: filters.tier ?? undefined,
          side: filters.side ?? undefined,
          kind: filters.kind ?? undefined,
          centre: filters.centre ?? undefined,
          q: filters.q ?? undefined,
          sort: filters.sort,
          order: filters.sort === 'name' ? 'asc' : 'desc',
          page: filters.page,
          page_size: filters.pageSize,
        },
        signal,
      ),
    placeholderData: keepPreviousData,
    staleTime: STALE,
  })

export const useUniverseEntity = (cnpj: string | null) =>
  useQuery({
    queryKey: ['universe-entity', cnpj],
    queryFn: ({ signal }) => apiGet<UniverseDetail>(`/api/v1/universe/${cnpj}`, {}, signal),
    enabled: Boolean(cnpj),
    staleTime: STALE,
  })
