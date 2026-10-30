import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource, MapLayerMouseEvent, StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
// MapLibre derives its worker URL from its own module URL, which breaks once Vite
// pre-bundles or fingerprints it; ship the worker as our own ES module chunk instead.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router'
import { useAccounts, useOffices, useScores } from '../api/hooks'
import type { OfficeFeature } from '../api/types'
import { TierBadge } from '../components/Badges'
import { SERIES, ScoreBand } from '../components/ScoreBand'
import { ErrorState, LoadingRows } from '../components/States'
import { joinUnits, matchesFilters, useFilters } from '../lib/filters'
import { addressCase, brlCompact, brlSigned, deltaClass, phone } from '../lib/format'

maplibregl.setWorkerUrl(workerUrl)

const BASEMAP = 'https://tiles.openfreemap.org/styles/dark'
const FALLBACK_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#0d0e10' } }],
}
const VIEWS = {
  sp: { center: [-46.684, -23.588] as [number, number], zoom: 13.4 },
  rj: { center: [-43.205, -22.965] as [number, number], zoom: 12.2 },
  all: { center: [-45.3, -23.2] as [number, number], zoom: 6.6 },
}
const TIER_COLOR: Record<string, string> = {
  'Prioridade agora': '#ffa21f',
  'Desenvolver relacionamento': '#3987e5',
  'Oportunidade tática': '#9085e9',
  Monitorar: '#8a8a84',
}
const DEFAULT_COLOR = '#b0afa7'

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`)
}

/** Lean tooltip: institutional data only (no people, no e-mails). */
export function tooltipHtml(p: OfficeFeature['properties'] & { entities?: number }): string {
  const precision = p.is_exact ? 'endereço exato' : p.precision === 'street' ? 'aproximado (rua)' : 'aproximado'
  const rows: Array<[string, string]> = [
    ['Faixa', p.tier ?? '—'],
    ['Telefone', phone(p.phone_official)],
    ['PL não-FIC', brlCompact(p.nav_brl_non_fic)],
    ['Captação 12m', brlSigned(p.net_flow_12m_brl)],
    ['Localização', precision],
    ...(p.entities && p.entities > 1 ? ([['Entidades', `${p.entities} no mesmo endereço`]] as Array<[string, string]>) : []),
  ]
  return `<div class="tip__title">${escapeHtml(p.canonical_name)}</div>
    <div class="muted">${escapeHtml(addressCase(p.address))}</div>
    <dl class="tip__grid">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${escapeHtml(v)}</dd>`).join('')}</dl>
    <div class="muted" style="margin-top:4px;font-size:11px">Fonte: cadastro CVM; geocodificação OpenStreetMap</div>`
}

type Mode = 'points' | 'density'

export function MapScreen() {
  const offices = useOffices()
  const scores = useScores()
  const accounts = useAccounts()
  const { filters, selected, select } = useFilters()
  const location = useLocation()
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const [ready, setReady] = useState(false)
  const [mode, setMode] = useState<Mode>('points')
  const [basemapFailed, setBasemapFailed] = useState(false)
  const selectRef = useRef<(accountId: string) => void>(() => undefined)
  const selectedAccount = selected?.split(':')[0] ?? null

  const units = useMemo(
    () => joinUnits(scores.data?.data ?? [], accounts.data?.data ?? []),
    [scores.data, accounts.data],
  )
  const visibleAccounts = useMemo(() => {
    const ids = new Set(units.filter((unit) => matchesFilters(unit, filters)).map((unit) => unit.account_id))
    return ids
  }, [units, filters])
  const bestUnit = useMemo(() => {
    const best = new Map<string, (typeof units)[number]>()
    for (const unit of units) {
      if (!matchesFilters(unit, filters)) continue
      const current = best.get(unit.account_id)
      if (!current || unit.rank < current.rank) best.set(unit.account_id, unit)
    }
    return best
  }, [units, filters])

  // One point per account and building: affiliates registered at the same address are
  // a single place to visit, so they collapse into one marker that counts them.
  const features = useMemo(() => {
    const rank = (relation: string | null | undefined) =>
      relation === 'primary_manager' ? 0 : relation === 'bank_entity' ? 1 : 2
    const groups = new Map<string, { feature: OfficeFeature; entities: number }>()
    for (const feature of offices.data?.features ?? []) {
      if (!visibleAccounts.has(feature.properties.account_id)) continue
      const [lon, lat] = feature.geometry.coordinates
      const key = `${feature.properties.account_id}|${lon.toFixed(4)}|${lat.toFixed(4)}`
      const current = groups.get(key)
      if (!current) {
        groups.set(key, { feature, entities: 1 })
        continue
      }
      current.entities += 1
      const better =
        rank(feature.properties.relation) < rank(current.feature.properties.relation) ||
        (feature.properties.is_exact && !current.feature.properties.is_exact)
      if (better) current.feature = feature
    }
    return Array.from(groups.values()).map(({ feature, entities }) => ({ ...feature, entities }))
  }, [offices.data, visibleAccounts])
  const geojson = useMemo(
    () => ({
      type: 'FeatureCollection' as const,
      features: features.map((f) => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: [f.geometry.coordinates[0], f.geometry.coordinates[1]] },
        properties: { ...f.properties, entities: f.entities, color: TIER_COLOR[f.properties.tier ?? ''] ?? DEFAULT_COLOR },
      })),
    }),
    [features],
  )

  // Map lifecycle
  useEffect(() => {
    if (!container.current) return
    let settled = false
    const instance = new maplibregl.Map({
      container: container.current,
      style: BASEMAP,
      center: VIEWS.sp.center,
      zoom: VIEWS.sp.zoom,
      attributionControl: { compact: false, customAttribution: 'Escritórios: CVM Dados Abertos; geocodificação Nominatim' },
      cooperativeGestures: false,
    })
    instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.current = instance
    const fallback = window.setTimeout(() => {
      if (!settled) {
        settled = true
        setBasemapFailed(true)
        instance.setStyle(FALLBACK_STYLE)
      }
    }, 8000)
    instance.on('error', (event: maplibregl.ErrorEvent) => {
      if (!settled && /style|tiles|Failed to fetch/i.test(String(event.error?.message ?? ''))) {
        settled = true
        setBasemapFailed(true)
        instance.setStyle(FALLBACK_STYLE)
      }
    })
    // The basemap references decorative patterns it does not ship; fill them with a
    // transparent pixel instead of logging a warning on every style load.
    instance.on('styleimagemissing', (event: { id: string }) => {
      if (!instance.hasImage(event.id)) instance.addImage(event.id, { width: 1, height: 1, data: new Uint8Array(4) })
    })
    instance.on('style.load', () => {
      settled = true
      window.clearTimeout(fallback)
      setReady(false)
      setReady(true)
    })
    return () => {
      window.clearTimeout(fallback)
      instance.remove()
      map.current = null
    }
  }, [])

  // Sources and layers (re-added after a style swap)
  useEffect(() => {
    const instance = map.current
    if (!instance || !ready) return
    const hasGlyphs = Boolean(instance.getStyle().glyphs)
    if (!instance.getSource('offices')) {
      instance.addSource('offices', { type: 'geojson', data: geojson, cluster: true, clusterRadius: 26, clusterMaxZoom: 14 })
      instance.addSource('offices-raw', { type: 'geojson', data: geojson })
      instance.addLayer({
        id: 'density',
        type: 'heatmap',
        source: 'offices-raw',
        paint: {
          'heatmap-weight': 1, // every office counts the same: density, never performance
          'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 8, 18, 14, 42],
          'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 8, 0.8, 14, 1.6],
          'heatmap-opacity': 0.85,
          'heatmap-color': [
            'interpolate', ['linear'], ['heatmap-density'],
            0, 'rgba(24,79,149,0)', 0.2, '#184f95', 0.45, '#256abf', 0.7, '#3987e5', 1, '#9ec5f4',
          ],
        },
      })
      instance.addLayer({
        id: 'clusters',
        type: 'circle',
        source: 'offices',
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': '#1f2226',
          'circle-stroke-color': '#b0afa7',
          'circle-stroke-width': 1.5,
          'circle-radius': ['step', ['get', 'point_count'], 14, 5, 18, 12, 24],
        },
      })
      if (hasGlyphs) {
        instance.addLayer({
          id: 'cluster-count',
          type: 'symbol',
          source: 'offices',
          filter: ['has', 'point_count'],
          layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 12, 'text-font': ['Noto Sans Regular'] },
          paint: { 'text-color': '#eceae4' },
        })
      }
      instance.addLayer({
        id: 'selected-halo',
        type: 'circle',
        source: 'offices',
        filter: ['==', ['get', 'account_id'], '__none__'],
        paint: { 'circle-radius': 13, 'circle-color': 'rgba(255,162,31,0.18)', 'circle-stroke-color': '#ffa21f', 'circle-stroke-width': 2 },
      })
      instance.addLayer({
        id: 'points',
        type: 'circle',
        source: 'offices',
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-radius': 6,
          'circle-color': ['case', ['get', 'is_exact'], ['get', 'color'], 'rgba(0,0,0,0)'],
          'circle-stroke-color': ['case', ['get', 'is_exact'], '#000000', ['get', 'color']],
          'circle-stroke-width': ['case', ['get', 'is_exact'], 1.5, 2.5],
        },
      })

      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 12, maxWidth: '300px' })
      instance.on('mousemove', 'points', (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0]
        if (!feature) return
        instance.getCanvas().style.cursor = 'pointer'
        const geometry = feature.geometry as unknown as { coordinates: [number, number] }
        popup.setLngLat(geometry.coordinates).setHTML(tooltipHtml(feature.properties as OfficeFeature['properties'])).addTo(instance)
      })
      instance.on('mouseleave', 'points', () => {
        instance.getCanvas().style.cursor = ''
        popup.remove()
      })
      instance.on('click', 'points', (event: MapLayerMouseEvent) => {
        const accountId = event.features?.[0]?.properties?.account_id as string | undefined
        if (accountId) selectRef.current(accountId)
      })
      instance.on('click', 'clusters', async (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0]
        if (!feature) return
        const source = instance.getSource('offices') as GeoJSONSource
        const zoom = await source.getClusterExpansionZoom(feature.properties?.cluster_id as number)
        const geometry = feature.geometry as unknown as { coordinates: [number, number] }
        instance.easeTo({ center: geometry.coordinates, zoom })
      })
      instance.on('mouseenter', 'clusters', () => (instance.getCanvas().style.cursor = 'pointer'))
      instance.on('mouseleave', 'clusters', () => (instance.getCanvas().style.cursor = ''))
    }
    ;(instance.getSource('offices') as GeoJSONSource).setData(geojson)
    ;(instance.getSource('offices-raw') as GeoJSONSource).setData(geojson)
  }, [ready, geojson])

  // Map clicks select the account's best visible unit (same URL state as the ranking).
  useEffect(() => {
    selectRef.current = (accountId: string) => {
      const unit = bestUnit.get(accountId)
      if (unit) select(unit.unit_key)
    }
  }, [bestUnit, select])

  // Mode and selection rendering
  useEffect(() => {
    const instance = map.current
    if (!instance || !ready || !instance.getLayer('points')) return
    const showPoints = mode === 'points'
    for (const id of ['clusters', 'cluster-count', 'points', 'selected-halo']) {
      if (instance.getLayer(id)) instance.setLayoutProperty(id, 'visibility', showPoints ? 'visible' : 'none')
    }
    instance.setLayoutProperty('density', 'visibility', showPoints ? 'none' : 'visible')
    instance.setFilter('selected-halo', [
      'all',
      ['!', ['has', 'point_count']],
      ['==', ['get', 'account_id'], selectedAccount ?? '__none__'],
    ])
  }, [mode, ready, selectedAccount, geojson])

  const flyToAccount = (accountId: string) => {
    const feature = features.find((f) => f.properties.account_id === accountId)
    if (feature && map.current) {
      map.current.easeTo({ center: [feature.geometry.coordinates[0], feature.geometry.coordinates[1]], zoom: Math.max(map.current.getZoom(), 15.2) })
    }
  }

  // Arriving with a selection (from the ranking or a shared link): center on it once.
  const centered = useRef(false)
  useEffect(() => {
    if (centered.current || !ready || !selectedAccount || features.length === 0) return
    centered.current = true
    flyToAccount(selectedAccount)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, selectedAccount, features.length])

  const list = useMemo(
    () => Array.from(bestUnit.values()).sort((a, b) => a.rank - b.rank),
    [bestUnit],
  )
  const exactCount = features.filter((f) => f.properties.is_exact).length
  const loading = offices.isLoading || scores.isLoading || accounts.isLoading
  const error = offices.error ?? scores.error ?? accounts.error

  return (
    <div className="map-layout">
      <section className="map" aria-label="Mapa de escritórios">
        <div ref={container} className="map__canvas" data-testid="map-canvas" />
        <div className="map__toolbar" role="toolbar" aria-label="Controles do mapa">
          <button type="button" className="button" aria-pressed={mode === 'points'} onClick={() => setMode('points')}>
            Escritórios
          </button>
          <button type="button" className="button" aria-pressed={mode === 'density'} onClick={() => setMode('density')}>
            Densidade
          </button>
          <span style={{ width: 8 }} />
          {(['sp', 'rj', 'all'] as const).map((view) => (
            <button key={view} type="button" className="button" onClick={() => map.current?.easeTo(VIEWS[view])}>
              {view === 'sp' ? 'São Paulo' : view === 'rj' ? 'Rio de Janeiro' : 'Todos'}
            </button>
          ))}
        </div>
        {basemapFailed ? (
          <p className="callout map__notice" role="status">
            Mapa de fundo indisponível (sem internet ou servidor de tiles fora). Os escritórios continuam
            posicionados pelas coordenadas.
          </p>
        ) : null}
        <div className="map__legend" aria-label="Legenda do mapa">
          {mode === 'points' ? (
            <>
              <div className="legend-row">
                <span className="legend-swatch" style={{ background: '#ffa21f', border: '1.5px solid #000' }} /> Prioridade agora
              </div>
              <div className="legend-row">
                <span className="legend-swatch" style={{ background: '#3987e5' }} /> Desenvolver relacionamento
              </div>
              <div className="legend-row">
                <span className="legend-swatch" style={{ background: '#9085e9' }} /> Oportunidade tática
              </div>
              <div className="legend-row">
                <span className="legend-swatch" style={{ background: '#8a8a84' }} /> Monitorar / timing desconhecido
              </div>
              <div className="legend-row">
                <span className="legend-swatch" style={{ border: '2.5px solid #b0afa7' }} /> anel = localização aproximada
              </div>
            </>
          ) : (
            <>
              <div>Densidade de escritórios de prospects (cada endereço pesa igual).</div>
              <div className="muted">Não representa performance nem probabilidade de compra.</div>
            </>
          )}
        </div>
      </section>

      <aside className="side" aria-label="Contas no mapa">
        <div className="panel">
          <h2 className="section__title" style={{ marginTop: 0 }}>
            Contas visíveis <small>mesmos filtros do ranking</small>
          </h2>
          {loading ? <LoadingRows rows={8} /> : null}
          {error ? (
            <ErrorState
              error={error}
              onRetry={() => {
                void offices.refetch()
                void scores.refetch()
                void accounts.refetch()
              }}
            />
          ) : null}
          {!loading && !error ? (
            <>
              <p className="muted" style={{ fontSize: 'var(--fs-xs)', margin: '0 0 8px' }}>
                {features.length} endereços no mapa ({exactCount} exatos), agrupando {offices.data?.meta.count ?? 0} registros de entidades. {offices.data?.meta.without_location ?? 0} sem
                coordenada não aparecem.
              </p>
              {list.length === 0 ? (
                <p className="secondary">Nenhuma conta com esses filtros.</p>
              ) : (
                <ul className="reasons" style={{ gap: 2 }}>
                  {list.map((unit) => {
                    const isSelected = unit.account_id === selectedAccount
                    const hasPoint = features.some((f) => f.properties.account_id === unit.account_id)
                    return (
                      <li key={unit.account_id}>
                        <button
                          type="button"
                          className="command__result"
                          aria-pressed={isSelected}
                          style={{
                            width: '100%',
                            background: isSelected ? 'var(--amber-wash)' : 'transparent',
                            border: 0,
                            boxShadow: isSelected ? 'inset 2px 0 0 var(--amber)' : undefined,
                            textAlign: 'left',
                          }}
                          onClick={() => {
                            select(unit.unit_key)
                            flyToAccount(unit.account_id)
                          }}
                        >
                          <span style={{ minWidth: 0 }}>
                            <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {unit.canonical_name}
                            </span>
                            <TierBadge tier={unit.tier} />
                            {!hasPoint ? <span className="muted" style={{ fontSize: 'var(--fs-xs)' }}> sem ponto no mapa</span> : null}
                          </span>
                          <ScoreBand band={unit.priority.point === null || unit.priority.point === undefined ? unit.fit : unit.priority} label={unit.priority.point == null ? 'Fit' : 'Prioridade'} color={unit.priority.point == null ? SERIES.fit : SERIES.priority} />
                        </button>
                        {isSelected ? (
                          <div style={{ padding: '4px 12px 8px', fontSize: 'var(--fs-sm)' }}>
                            <span className="secondary">PL não-FIC </span>
                            <span className="num">{brlCompact(unit.account?.nav_brl_non_fic)}</span>
                            <span className="secondary"> captação 12m </span>
                            <span className={`num ${deltaClass(unit.account?.net_flow_12m_brl)}`}>{brlSigned(unit.account?.net_flow_12m_brl)}</span>
                            <div style={{ marginTop: 4 }}>
                              <Link to={{ pathname: `/contas/${unit.account_id}`, search: location.search }}>Abrir conta 360</Link>
                            </div>
                          </div>
                        ) : null}
                      </li>
                    )
                  })}
                </ul>
              )}
            </>
          ) : null}
        </div>
      </aside>
    </div>
  )
}
