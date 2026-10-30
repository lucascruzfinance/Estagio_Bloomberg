import { LineChart } from 'echarts/charts'
import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import type { EChartsCoreOption } from 'echarts/core'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { useEffect, useRef } from 'react'

echarts.use([LineChart, GridComponent, TooltipComponent, MarkLineComponent, CanvasRenderer])

export const CHART_TEXT = {
  primary: '#eceae4',
  secondary: '#b0afa7',
  muted: '#8a8a84',
  grid: '#2c3035',
  axis: '#41464d',
  surface: '#1f2226',
}

/** Thin ECharts wrapper: owns the instance, resizes with its box, disposes on unmount. */
export function EChart({ option, label, height = 220 }: { option: EChartsCoreOption; label: string; height?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!ref.current) return
    const instance = echarts.init(ref.current, undefined, { renderer: 'canvas' })
    chart.current = instance
    const observer = new ResizeObserver(() => instance.resize())
    observer.observe(ref.current)
    return () => {
      observer.disconnect()
      instance.dispose()
      chart.current = null
    }
  }, [])

  useEffect(() => {
    chart.current?.setOption(option, { notMerge: true })
  }, [option])

  return <div ref={ref} className="chart" style={{ height }} role="img" aria-label={label} />
}
