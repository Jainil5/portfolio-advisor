import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { usePrices, useRecommendations, useStocks } from '../api'
import ChatPanel from '../components/ChatPanel'
import { Badge, Card, EmptyState, Metric, PageHeader, Spinner, TrendPill } from '../components/ui'
import { filterTimeframe, latestSma, rangePosition, suggestionForScore, sma } from '../utils/finance'
import type { Timeframe } from '../utils/finance'
import { fmtCompact, fmtDate, fmtINR, fmtNum, fmtPct } from '../utils/format'

const TIMEFRAMES: Timeframe[] = ['1W', '1M', '3M', '1Y']
const CHART_TOOLTIP = {
  background: '#111a2c',
  border: '1px solid #1e293b',
  borderRadius: 12,
  fontSize: 12,
}

export default function StockAnalysis() {
  const { data: stocks, loading } = useStocks()
  const { data: recommendations } = useRecommendations()
  const [params, setParams] = useSearchParams()
  const [query, setQuery] = useState('')
  const [timeframe, setTimeframe] = useState<Timeframe>('1M')
  const [tab, setTab] = useState<'technicals' | 'volatility' | 'fundamentals'>('technicals')

  const selectedId = Number(params.get('stock')) || null
  const stock = stocks?.find((s) => s.stock_id === selectedId) ?? null
  const { data: prices, loading: pricesLoading } = usePrices(selectedId)

  // Default to the top-scored stock when arriving without ?stock=
  useEffect(() => {
    if (!stocks || stocks.length === 0) return
    if (!selectedId || !stocks.some((s) => s.stock_id === selectedId)) {
      const top = [...stocks].sort((a, b) => (b.score ?? 0) - (a.score ?? 0))[0]
      setParams({ stock: String(top.stock_id) }, { replace: true })
    }
  }, [stocks, selectedId, setParams])

  const filtered = useMemo(() => {
    if (!prices || prices.length === 0) return []
    const trimmed = filterTimeframe(prices, timeframe)
    const start = prices.length - trimmed.length
    const sma20 = sma(prices, 20)
    const sma50 = sma(prices, 50)
    return trimmed.map((p, i) => ({
      ...p,
      sma20: sma20[start + i],
      sma50: sma50[start + i],
    }))
  }, [prices, timeframe])

  const chartPoints = useMemo(
    () =>
      filtered.map((p) => ({
        label: fmtDate(p.date),
        Price: p.close,
        'SMA 20': p.sma20 ?? undefined,
        'SMA 50': p.sma50 ?? undefined,
      })),
    [filtered],
  )

  const volumeChart = useMemo(
    () =>
      (prices ?? []).slice(-90).map((p) => ({
        label: fmtDate(p.date),
        Volume: p.volume ?? 0,
      })),
    [prices],
  )

  if (loading || !stocks) return <Spinner label="Loading market dataset…" />

  const stockList = stocks.filter(
    (s) =>
      s.company_name.toLowerCase().includes(query.toLowerCase()) ||
      s.ticker.toLowerCase().includes(query.toLowerCase()),
  )

  const suggestion = suggestionForScore(stock?.score)
  const ma20Latest = prices ? latestSma(prices, 20) : stock?.ma20 ?? null
  const ma50Latest = prices ? latestSma(prices, 50) : stock?.ma50 ?? null
  const bullishCross = ma20Latest != null && ma50Latest != null ? ma20Latest > ma50Latest : null
  const maGap =
    ma20Latest != null && ma50Latest ? ((ma20Latest - ma50Latest) / ma50Latest) * 100 : null
  const priceVsMa20 =
    ma20Latest && stock?.current_price != null
      ? ((stock.current_price - ma20Latest) / ma20Latest) * 100
      : null
  const low52 = stock?.['52w_low'] ?? null
  const high52 = stock?.['52w_high'] ?? null
  const rangePos =
    stock?.current_price != null && low52 != null && high52 != null
      ? rangePosition(stock.current_price, low52, high52)
      : null

  return (
    <div>
      <PageHeader title="Stock Intelligence" subtitle="Technical, volatility and fundamental analysis for any covered stock" />

      <div className="grid gap-6 xl:grid-cols-4">
        {/* Selector */}
        <Card title={`Universe (${stockList.length})`} className="self-start xl:col-span-1">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search company or ticker…"
            className="mb-3 w-full rounded-xl border border-slate-700/80 bg-slate-950/60 px-3.5 py-2 text-sm outline-none transition-colors focus:border-indigo-500/60"
          />
          <ul className="max-h-[26rem] space-y-0.5 overflow-y-auto pr-1">
            {stockList.map((s) => {
              const sug = suggestionForScore(s.score)
              return (
                <li key={s.stock_id}>
                  <button
                    onClick={() => {
                      setParams({ stock: String(s.stock_id) })
                      setQuery('')
                    }}
                    className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-sm transition-colors ${
                      s.stock_id === selectedId
                        ? 'bg-indigo-500/15 font-semibold text-indigo-300'
                        : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                    }`}
                  >
                    <span className="min-w-0 flex-1 truncate">{s.company_name}</span>
                    <span
                      className={`num shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold ${
                        sug.label === 'BUY'
                          ? 'bg-emerald-500/15 text-emerald-400'
                          : sug.label === 'HOLD'
                            ? 'bg-amber-500/15 text-amber-400'
                            : 'bg-rose-500/15 text-rose-400'
                      }`}
                    >
                      {s.score?.toFixed(1) ?? '—'}
                    </span>
                  </button>
                </li>
              )
            })}
            {stockList.length === 0 && <li className="px-2 py-4 text-sm text-slate-500">No matches.</li>}
          </ul>
        </Card>

        {/* Detail */}
        <div className="space-y-6 xl:col-span-3">
          {!stock ? (
            <EmptyState icon="🔎" title="Select a stock" message="Pick a company from the universe list." />
          ) : (
            <>
              <Card>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-3">
                      <h2 className="truncate text-xl font-bold text-slate-100">{stock.company_name}</h2>
                      <Badge tone={suggestion.label === 'BUY' ? 'buy' : suggestion.label === 'HOLD' ? 'hold' : 'sell'}>
                        {suggestion.label}
                      </Badge>
                      <TrendPill trend={stock.trend} />
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      {stock.ticker} · {stock.exchange} · {stock.sector} · {stock.industry} · {stock.market_cap}
                    </p>
                  </div>
                  <div className="w-full max-w-[180px]">
                    <div className="flex items-baseline justify-between text-xs text-slate-500">
                      <span>AI Score</span>
                      <span className="num font-bold text-slate-200">{fmtNum(stock.score)}/5.0</span>
                    </div>
                    <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-800">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${
                          suggestion.label === 'BUY'
                            ? 'bg-gradient-to-r from-emerald-500 to-teal-400'
                            : suggestion.label === 'HOLD'
                              ? 'bg-gradient-to-r from-amber-500 to-yellow-400'
                              : 'bg-gradient-to-r from-rose-500 to-red-400'
                        }`}
                        style={{ width: `${Math.min(100, ((stock.score ?? 0) / 5) * 100)}%` }}
                      />
                    </div>
                    {rangePos != null && (
                      <>
                        <div className="mt-3 flex items-baseline justify-between text-[10px] text-slate-500">
                          <span>52w L {fmtINR(low52)}</span>
                          <span>H {fmtINR(high52)}</span>
                        </div>
                        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-800">
                          <div className="relative h-full w-full">
                            <div
                              className="absolute top-1/2 h-3 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-400 shadow"
                              style={{ left: `${rangePos * 100}%` }}
                            />
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                <div className="mt-5 grid grid-cols-2 gap-4 md:grid-cols-4">
                  <Metric
                    label="Current Price"
                    value={fmtINR(stock.current_price)}
                    deltaPct={stock.daily_return}
                    deltaText="today"
                  />
                  <Metric
                    label="Predicted (next day)"
                    value={fmtINR(stock.predicted_price)}
                    deltaText={stock.predicted_direction ? `model says ${stock.predicted_direction}` : undefined}
                  />
                  <Metric label="30d Return" value={fmtPct(stock.return_30d)} deltaPct={stock.return_30d} />
                  <Metric label="30d Volatility" value={`${fmtNum(stock.volatility_30d)}%`} />
                </div>
              </Card>

              {/* Tabs */}
              <div className="flex gap-1 rounded-xl border border-slate-800/80 bg-panel/60 p-1">
                {(
                  [
                    ['technicals', '📈 Price & Technicals'],
                    ['volatility', '📊 Volatility & Volume'],
                    ['fundamentals', '🏢 Fundamentals & Profile'],
                  ] as const
                ).map(([key, label]) => (
                  <button
                    key={key}
                    onClick={() => setTab(key)}
                    className={`flex-1 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                      tab === key ? 'bg-indigo-500/20 text-indigo-300' : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {tab === 'technicals' && (
                <Card
                  title="Historical Price & Moving Averages"
                  actions={
                    <div className="flex gap-1 rounded-lg bg-slate-800/60 p-0.5">
                      {TIMEFRAMES.map((tf) => (
                        <button
                          key={tf}
                          onClick={() => setTimeframe(tf)}
                          className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
                            timeframe === tf ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          {tf}
                        </button>
                      ))}
                    </div>
                  }
                >
                  {pricesLoading ? (
                    <Spinner label="Loading price history…" />
                  ) : chartPoints.length < 2 ? (
                    <EmptyState
                      icon="📉"
                      title="Price history unavailable"
                      message="No exported price file for this stock; technical indicators fall back to pipeline features."
                    />
                  ) : (
                    <div className="h-80">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={chartPoints} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                          <defs>
                            <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
                              <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                          <XAxis dataKey="label" tick={{ fill: '#64748b', fontSize: 10 }} minTickGap={40} />
                          <YAxis
                            tick={{ fill: '#64748b', fontSize: 11 }}
                            width={72}
                            domain={['auto', 'auto']}
                            tickFormatter={(v) => `₹${fmtNum(v, 0)}`}
                          />
                          <Tooltip
                            contentStyle={CHART_TOOLTIP}
                            formatter={(v) => fmtINR(Number(v))}
                          />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                          <Area type="monotone" dataKey="Price" stroke="#818cf8" strokeWidth={2} fill="url(#priceFill)" dot={false} />
                          <Line type="monotone" dataKey="SMA 20" stroke="#22d3ee" strokeWidth={1.5} dot={false} connectNulls />
                          <Line type="monotone" dataKey="SMA 50" stroke="#fbbf24" strokeWidth={1.5} dot={false} connectNulls />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
                    <Metric
                      label="MA Crossover"
                      value={
                        bullishCross == null ? '—' : (
                          <span className={bullishCross ? 'text-emerald-400' : 'text-rose-400'}>
                            {bullishCross ? 'Golden 🟢' : 'Death 🔴'}
                          </span>
                        )
                      }
                      deltaText={maGap != null ? `${fmtPct(maGap)} gap (20d vs 50d)` : undefined}
                    />
                    <Metric label="20-Day SMA" value={fmtINR(ma20Latest)} deltaPct={priceVsMa20} deltaText="vs price" />
                    <Metric label="50-Day SMA" value={fmtINR(ma50Latest)} />
                  </div>
                </Card>
              )}

              {tab === 'volatility' && (
                <>
                  <Card title="Performance & Risk Profile">
                    <div className="grid grid-cols-3 gap-4">
                      <Metric label="1 Week Return" value={fmtPct(stock.return_7d)} deltaPct={stock.return_7d} />
                      <Metric label="1 Month Return" value={fmtPct(stock.return_30d)} deltaPct={stock.return_30d} />
                      <Metric label="6 Month Return" value={fmtPct(stock.return_180d)} deltaPct={stock.return_180d} />
                      <Metric label="1W Volatility" value={`${fmtNum(stock.volatility_7d)}%`} />
                      <Metric label="1M Volatility" value={`${fmtNum(stock.volatility_30d)}%`} />
                      <Metric label="6M Volatility" value={`${fmtNum(stock.volatility_180d)}%`} />
                    </div>
                  </Card>
                  <Card title="Daily Volume (last 90 sessions)">
                    {volumeChart.length < 2 ? (
                      <p className="text-sm text-slate-500">No volume history available.</p>
                    ) : (
                      <div className="h-56">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={volumeChart} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                            <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                            <XAxis dataKey="label" tick={{ fill: '#64748b', fontSize: 10 }} minTickGap={40} />
                            <YAxis tick={{ fill: '#64748b', fontSize: 11 }} width={56} tickFormatter={(v) => fmtCompact(Number(v))} />
                            <Tooltip
                              contentStyle={CHART_TOOLTIP}
                              formatter={(v) => [fmtCompact(Number(v)), 'Volume']}
                            />
                            <Bar dataKey="Volume" fill="#38bdf8" radius={[3, 3, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                    <div className="mt-4 grid grid-cols-3 gap-4">
                      <Metric label="7-Day Avg Volume" value={fmtCompact(stock.avg_volume_7d)} />
                      <Metric label="30-Day Avg Volume" value={fmtCompact(stock.avg_volume_30d)} />
                      <Metric label="180-Day Avg Volume" value={fmtCompact(stock.avg_volume_180d)} />
                    </div>
                  </Card>
                </>
              )}

              {tab === 'fundamentals' && (
                <>
                  <Card title="Fundamental Health">
                    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                      <Metric label="Market Cap Class" value={stock.market_cap || '—'} />
                      <Metric label="Debt / Equity" value={fmtNum(stock.debt_to_equity)} />
                      <Metric label="Debt / Assets" value={fmtNum(stock.debt_to_assets)} />
                      <Metric label="Cash Ratio" value={fmtNum(stock.cash_ratio)} />
                    </div>
                  </Card>
                  <Card title="Company Profile">
                    <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm md:grid-cols-3">
                      {(
                        [
                          ['Industry', stock.industry],
                          ['Sector', stock.sector],
                          ['Ticker', stock.ticker],
                          ['Exchange', stock.exchange],
                          ['Country', stock.country],
                          ['Status', stock.is_active ? 'Active 🟢' : 'Inactive 🔴'],
                        ] as const
                      ).map(([label, value]) => (
                        <div key={label}>
                          <dt className="text-xs uppercase tracking-wider text-slate-600">{label}</dt>
                          <dd className="mt-0.5 font-medium text-slate-200">{value || '—'}</dd>
                        </div>
                      ))}
                    </dl>
                  </Card>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {stock && (
        <div className="mt-6">
          <ChatPanel
            stocks={stocks}
            recommendations={recommendations ?? []}
            placeholder={`Ask about ${stock.company_name}, e.g. "How does its 30-day return look?"`}
          />
        </div>
      )}
    </div>
  )
}
