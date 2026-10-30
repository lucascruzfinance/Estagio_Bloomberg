import { useMemo } from 'react'
import type { FundPerformance } from '../api/types'
import { brlSigned, date } from '../lib/format'
import { CHART_TEXT, EChart } from './EChart'

const indexFmt = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** Quota rebased to 100: one series, so the title names it and no legend is drawn. */
export function QuotaChart({ performance }: { performance: FundPerformance }) {
  const option = useMemo(() => {
    const points = performance.points.filter((p) => p.quota_index !== null && p.quota_index !== undefined)
    const last = points.at(-1)?.quota_index ?? 100
    return {
      animation: false,
      grid: { left: 44, right: 56, top: 12, bottom: 28 },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'line', lineStyle: { color: CHART_TEXT.axis } },
        backgroundColor: CHART_TEXT.surface,
        borderColor: CHART_TEXT.axis,
        textStyle: { color: CHART_TEXT.primary, fontFamily: 'Inter, Arial', fontSize: 12 },
        formatter: (items: Array<{ dataIndex: number }>) => {
          const point = points[items[0]?.dataIndex ?? 0]
          if (!point) return ''
          return [
            `<b>${date(point.date)}</b>`,
            `Cota (base 100): ${indexFmt.format(point.quota_index ?? 0)}`,
            `Fluxo do dia: ${brlSigned(point.net_flow_brl)}`,
          ].join('<br/>')
        },
      },
      xAxis: {
        type: 'category',
        data: points.map((p) => p.date),
        boundaryGap: false,
        axisLine: { lineStyle: { color: CHART_TEXT.axis } },
        axisTick: { show: false },
        axisLabel: {
          color: CHART_TEXT.muted,
          fontSize: 11,
          formatter: (value: string) => value.slice(5, 7) + '/' + value.slice(2, 4),
          interval: Math.max(Math.floor(points.length / 6), 1),
        },
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitLine: { lineStyle: { color: CHART_TEXT.grid } },
        axisLabel: { color: CHART_TEXT.muted, fontSize: 11, formatter: (v: number) => indexFmt.format(v) },
      },
      series: [
        {
          type: 'line',
          data: points.map((p) => p.quota_index),
          showSymbol: false,
          lineStyle: { width: 2, color: '#3987e5' },
          itemStyle: { color: '#3987e5' },
          endLabel: {
            show: true,
            color: CHART_TEXT.primary,
            fontFamily: 'IBM Plex Mono, monospace',
            fontSize: 11,
            formatter: () => indexFmt.format(last),
          },
          markLine: {
            silent: true,
            symbol: 'none',
            label: { show: false },
            lineStyle: { color: CHART_TEXT.axis, type: 'dashed', width: 1 },
            data: [{ yAxis: 100 }],
          },
        },
      ],
    }
  }, [performance])

  return (
    <EChart
      option={option}
      label={`Evolução da cota de ${performance.name}, base 100 em ${date(performance.start)}`}
    />
  )
}
