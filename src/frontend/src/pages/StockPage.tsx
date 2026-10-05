import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Sparkles } from 'lucide-react'
import { useAnalysis, useHistory, useNews, useStocks, type StockAnalysis } from '../api'
import { Badge, Card, PageHeader, Spinner, TrendPill } from '../components/ui'
import TvChart, { type ChartToggles } from '../components/TvChart'
import { rsi as rsiLatest, rsiLabel } from '../market/indicators'
import { suggestionForScore } from '../utils/finance'
import { fmtCompact, fmtDate, fmtINR, fmtPct } from '../utils/format'

const RANGES: [string, string][] = [
  ['1w', '1W'],
  ['1m', '1M'],
  ['3m', '3M'],
  ['6m', '6M'],
  ['1y', '1Y'],
  ['3y', '3Y'],
  ['5y', '5Y'],
]

function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: 'up' | 'down' }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-800/50 py-1.5 text-xs last:border-0">
      <span className="text-slate-500">{label}</span>
      <span className={`num font-semibold ${tone === 'up' ? 'text-emerald-400' : tone === 'down' ? 'text-rose-400' : 'text-slate-200'}`}>
        {value}
      </span>
    </div>
  )
}

function AnalysisBox({ stockId, ticker }: { stockId: number; ticker: string }) {
  const [refresh, setRefresh] = useState(false)
  const [started, setStarted] = useState(false)
  const { data, loading, error } = useAnalysis(started ? stockId : null, refresh)

  if (!started)
    return (
      <button
        onClick={() => setStarted(true)}
        className="flex w-full items-center justify-center gap-2 rounded-xl border border-indigo-500/30 bg-indigo-500/10 py-2.5 text-xs font-semibold text-indigo-300 hover:bg-indigo-500/20"
      >
        <Sparkles size={14} /> Run AI analysis
      </button>
    )
  if (loading) return <Spinner label="Agent is analyzing (local LLM, may take ~1 min)…" />
  if (error) return <p className="text-xs text-rose-400">Analysis failed: {error}</p>
  const a = data as StockAnalysis
  return (
    <div>
      <p className="whitespace-pre-wrap text-xs leading-relaxed text-slate-300">{a.analysis}</p>
      <button onClick={() => setRefresh(!refresh)} className="mt-3 text-[11px] text-indigo-400 hover:text-indigo-300">
        ↻ Regenerate for {ticker}
      </button>
    </div>
  )
}

export default function StockPage() {
  const { stockId } = useParams()
  const id = Number(stockId)
  const { data: stocks, loading } = useStocks()
  const [range, setRange] = useState('1y')
  const { data: candles, loading: candlesLoading } = useHistory(id, range)
  const [toggles, setToggles] = useState<ChartToggles>({ ma20: true, ma50: true, rsi: false, logScale: false })

  const stock = useMemo(() => (stocks ?? []).find((s) => s.stock_id === id), [stocks, id])
  const { data: news } = useNews(stock ? stock.ticker.replace('.NS', '') : null, 8)

  if (loading) return <Spinner label="Loading…" />
  if (!stock)
    return (
      <div className="py-16 text-center">
        <p className="text-sm text-slate-400">Stock #{stockId} not found in the dataset.</p>
        <Link to="/" className="mt-3 inline-block text-xs text-indigo-400">← Back to screener</Link>
      </div>
    )

  const closes = (candles ?? []).map((c) => c.close)
  const rsiV = rsiLatest(closes, 14)
  const rl = rsiLabel(rsiV)
  const suggestion = suggestionForScore(stock.score)
  const toggle = (k: keyof ChartToggles) => setToggles((t) => ({ ...t, [k]: !t[k] }))

  return (
    <div>
      <button onClick={() => window.history.back()} className="mb-3 flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300">
        <ArrowLeft size={13} /> Back
      </button>

      <PageHeader
        title={stock.company_name}
        subtitle={`${stock.ticker} · ${stock.exchange || 'NSE'} · ${stock.sector}`}
        right={
          <div className="text-right">
            <p className="num text-2xl font-bold text-slate-100">{fmtINR(stock.current_price)}</p>
            <p className={`num text-sm font-semibold ${(stock.daily_return ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {fmtPct(stock.daily_return)} today
            </p>
          </div>
        }
      />

      <div className="mt-4 grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <Card
            title="Chart"
            actions={
              <div className="flex items-center gap-1.5 text-[11px]">
                {(
                  [
                    ['ma20', 'MA20'],
                    ['ma50', 'MA50'],
                    ['rsi', 'RSI'],
                    ['logScale', 'LOG'],
                  ] as [keyof ChartToggles, string][]
                ).map(([key, label]) => (
                  <button
                    key={key}
                    onClick={() => toggle(key)}
                    className={`rounded-md px-2 py-1 font-semibold ${
                      toggles[key] ? 'bg-indigo-500/20 text-indigo-300 ring-1 ring-indigo-500/40' : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            }
          >
            {candlesLoading || !candles ? (
              <Spinner label="Loading history…" />
            ) : (
              <>
                <TvChart candles={candles} toggles={toggles} />
                <div className="mt-2 flex gap-1">
                  {RANGES.map(([key, label]) => (
                    <button
                      key={key}
                      onClick={() => setRange(key)}
                      className={`rounded-md px-2.5 py-1 text-[11px] font-semibold ${
                        range === key ? 'bg-indigo-500/20 text-indigo-300' : 'text-slate-500 hover:bg-slate-800/60 hover:text-slate-300'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="Market Info">
            <Stat label="Market Cap" value={stock.market_cap} />
            <Stat label="52W High" value={fmtINR(stock['52w_high'])} />
            <Stat label="52W Low" value={fmtINR(stock['52w_low'])} />
            <Stat label="Avg Volume (7d)" value={fmtCompact(stock.avg_volume_7d)} />
            <Stat label="Debt / Equity" value={stock.debt_to_equity ?? '—'} />
            <Stat label="Cash Ratio" value={stock.cash_ratio ?? '—'} />
            <Stat label="Volatility (30d)" value={stock.volatility_30d != null ? `${stock.volatility_30d.toFixed(2)}%` : '—'} />
          </Card>

          <Card title="Technicals">
            <Stat label="MA 20" value={fmtINR(stock.ma20)} tone={rsiV != null && stock.current_price! > (stock.ma20 ?? 0) ? 'up' : 'down'} />
            <Stat label="MA 50" value={fmtINR(stock.ma50)} tone={stock.current_price! > (stock.ma50 ?? 0) ? 'up' : 'down'} />
            <div className="flex items-center justify-between py-1.5 text-xs">
              <span className="text-slate-500">RSI (14)</span>
              <span className={`num font-semibold ${rl.tone === 'up' ? 'text-emerald-400' : rl.tone === 'down' ? 'text-rose-400' : 'text-slate-400'}`}>
                {rsiV != null ? `${rsiV.toFixed(1)} · ${rl.text}` : '—'}
              </span>
            </div>
            <Stat label="Predicted Price" value={fmtINR(stock.predicted_price)} />
            <div className="flex items-center justify-between py-1.5 text-xs">
              <span className="text-slate-500">AI Call</span>
              <span className="flex items-center gap-2">
                <TrendPill trend={stock.trend} />
                <Badge tone={suggestion.label === 'BUY' ? 'buy' : suggestion.label === 'SELL' ? 'sell' : 'hold'}>
                  {suggestion.label} · {stock.score?.toFixed(2) ?? '—'}
                </Badge>
              </span>
            </div>
          </Card>

          <Card title="AI Analysis">
            <AnalysisBox stockId={stock.stock_id} ticker={stock.ticker.replace('.NS', '')} />
          </Card>

          <Card title="News">
            {news && news.length > 0 ? (
              <ul className="space-y-2">
                {news.map((n) => (
                  <li key={n.id} className="text-xs">
                    <p className="text-slate-300">{n.headline ?? n.subject}</p>
                    <p className="text-[10px] text-slate-600">{fmtDate(n.published_at)}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-500">No BSE announcements for this stock yet.</p>
            )}
          </Card>

          <Card title="About">
            <p className="text-xs leading-relaxed text-slate-400">
              <span className="font-semibold text-slate-200">{stock.company_name}</span> trades on{' '}
              {stock.exchange || 'NSE'} in the {stock.sector} sector ({stock.industry || '—'}). Data reflects the
              latest pipeline run; use Settings → Update Data to refresh prices, fundamentals, scores and news.
            </p>
          </Card>
        </div>
      </div>
    </div>
  )
}
