import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router'
import { ApiError } from './api/client'
import { CommandBar } from './components/CommandBar'
import { FilterBar } from './components/FilterBar'
import { Nav } from './components/Nav'
import { LoadingRows } from './components/States'
import { StatusBar } from './components/StatusBar'
import { AccountScreen } from './screens/AccountScreen'
import { CompareScreen } from './screens/CompareScreen'
import { PriorityScreen } from './screens/PriorityScreen'
import { QualityScreen } from './screens/QualityScreen'
import { UniverseScreen } from './screens/UniverseScreen'

const MapScreen = lazy(() => import('./screens/MapScreen').then((module) => ({ default: module.MapScreen })))

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: true,
        retry: (failures, error) => {
          // 429 is transient (local rate limit): retry after a pause; other 4xx are final.
          if (error instanceof ApiError && error.status === 429) return failures < 3
          if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false
          return failures < 2
        },
        retryDelay: (attempt, error) =>
          error instanceof ApiError && error.status === 429 ? 2_000 * (attempt + 1) : Math.min(1_000 * 2 ** attempt, 8_000),
      },
    },
  })
}

function Layout() {
  const location = useLocation()
  const showFilters = ['/', '/mapa', '/comparar'].includes(location.pathname)
  return (
    <div className="shell" style={showFilters ? { gridTemplateRows: '44px auto auto minmax(0, 1fr) 24px' } : undefined}>
      <CommandBar />
      <Nav />
      {showFilters ? <FilterBar /> : null}
      <main className="main" id="conteudo">
        <Routes>
          <Route path="/" element={<PriorityScreen />} />
          <Route
            path="/mapa"
            element={
              <Suspense fallback={<LoadingRows rows={6} label="Carregando mapa" />}>
                <MapScreen />
              </Suspense>
            }
          />
          <Route path="/comparar" element={<CompareScreen />} />
          <Route path="/qualidade" element={<QualityScreen />} />
          <Route path="/universo" element={<UniverseScreen />} />
          <Route path="/contas" element={<AccountScreen />} />
          <Route path="/contas/:accountId" element={<AccountScreen />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <StatusBar />
    </div>
  )
}

export default function App({ client = createQueryClient() }: { client?: QueryClient }) {
  return (
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
