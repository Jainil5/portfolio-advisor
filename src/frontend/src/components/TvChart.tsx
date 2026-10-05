import { useEffect, useMemo, useRef } from 'react'
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from 'lightweight-charts'
import { smaSeries } from '../market/indicators'
import type { PricePoint } from '../types'

export interface ChartToggles {
  ma20: boolean
  ma50: boolean
  rsi: boolean
  logScale: boolean
}

const UP = '#16C784'
const DOWN = '#EA3943'
const GRID = 'rgba(140, 152, 176, 0.10)'
const TEXT = '#8A98B0'

/** TradingView-grade candlestick chart: volume histogram, MA20/50 overlays, RSI sub-pane, log scale. */
export default function TvChart({
  candles,
  toggles,
  height = 460,
}: {
  candles: PricePoint[]
  toggles: ChartToggles
  height?: number
}) {
  const hostRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<{
    candles: ISeriesApi<'Candlestick'>
    volume: ISeriesApi<'Histogram'>
    ma20: ISeriesApi<'Line'>
    ma50: ISeriesApi<'Line'>
    rsi: ISeriesApi<'Line'>
  } | null>(null)

  const sorted = useMemo(
    () => [...candles].sort((a, b) => a.date.localeCompare(b.date)),
    [candles],
  )
  const closes = useMemo(() => sorted.map((c) => c.close), [sorted])

  useEffect(() => {
    if (!hostRef.current) return
    const chart = createChart(hostRef.current, {
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: TEXT, fontSize: 11 },
      grid: { vertLines: { color: GRID }, horzLines: { color: GRID } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: 'rgba(140,152,176,0.2)' },
      timeScale: { borderColor: 'rgba(140,152,176,0.2)' },
      height,
      autoSize: true,
    })
    const s = {
      candles: chart.addSeries(CandlestickSeries, {
        upColor: UP,
        downColor: DOWN,
        wickUpColor: UP,
        wickDownColor: DOWN,
        borderVisible: false,
      }),
      volume: chart.addSeries(HistogramSeries, {
        priceFormat: { type: 'volume' },
        priceScaleId: 'vol',
      }),
      ma20: chart.addSeries(LineSeries, { color: '#fbbf24', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }),
      ma50: chart.addSeries(LineSeries, { color: '#38bdf8', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }),
      rsi: chart.addSeries(LineSeries, { color: '#a78bfa', lineWidth: 1, priceScaleId: 'rsi', priceLineVisible: false }),
    }
    chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.84, bottom: 0 } })
    chart.priceScale('rsi').applyOptions({ scaleMargins: { top: 0.86, bottom: 0 } })
    chartRef.current = chart
    seriesRef.current = s
    return () => {
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [height])

  useEffect(() => {
    const s = seriesRef.current
    if (!s) return
    s.candles.setData(
      sorted.map((c) => ({
        time: c.date as Time,
        open: c.open ?? c.close,
        high: c.high ?? c.close,
        low: c.low ?? c.close,
        close: c.close,
      })),
    )
    s.volume.setData(
      sorted.map((c) => ({
        time: c.date as Time,
        value: c.volume ?? 0,
        color: c.close >= (c.open ?? c.close) ? 'rgba(22,199,132,0.35)' : 'rgba(234,57,67,0.35)',
      })),
    )
    s.ma20.setData(pairs(smaSeries(closes, 20)))
    s.ma50.setData(pairs(smaSeries(closes, 50)))
    s.rsi.setData(rsiSeries(closes, sorted.map((c) => c.date as Time)))
    s.rsi.applyOptions({ visible: toggles.rsi })
    function pairs(values: (number | null)[]) {
      const times = sorted.map((c) => c.date as Time)
      return values
        .map((v, i) => (v == null ? null : { time: times[i], value: v }))
        .filter((p): p is { time: Time; value: number } => p !== null)
    }
  }, [sorted, closes, toggles.rsi])

  // MA visibility toggles
  useEffect(() => {
    const s = seriesRef.current
    if (!s) return
    s.ma20.applyOptions({ visible: toggles.ma20 })
    s.ma50.applyOptions({ visible: toggles.ma50 })
  }, [toggles.ma20, toggles.ma50])

  // Log / linear price scale
  useEffect(() => {
    const chart = chartRef.current
    if (!chart) return
    chart.priceScale('right').applyOptions({ mode: toggles.logScale ? 2 : 0 })
    if (toggles.logScale) chart.timeScale().scrollToRealTime()
  }, [toggles.logScale])

  return <div ref={hostRef} className="w-full" style={{ height }} />
}

/** Wilder-smoothed rolling RSI(14). */
function rsiSeries(closes: number[], times: Time[], period = 14) {
  const out: { time: Time; value: number }[] = []
  if (closes.length <= period) return out
  let avgGain = 0
  let avgLoss = 0
  for (let i = 1; i < closes.length; i++) {
    const change = closes[i] - closes[i - 1]
    const gain = Math.max(change, 0)
    const loss = Math.max(-change, 0)
    if (i <= period) {
      avgGain += gain
      avgLoss += loss
      if (i === period) {
        avgGain /= period
        avgLoss /= period
      } else continue
    } else {
      avgGain = (avgGain * (period - 1) + gain) / period
      avgLoss = (avgLoss * (period - 1) + loss) / period
    }
    const rsi = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
    out.push({ time: times[i], value: Number(rsi.toFixed(2)) })
  }
  return out
}
