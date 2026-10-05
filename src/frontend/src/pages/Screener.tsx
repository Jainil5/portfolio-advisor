import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Newspaper, TrendingDown, TrendingUp } from 'lucide-react'
import { useMovers, useNews, useSectors, useStocks } from '../api'
import { Card, EmptyState, PageHeader, Spinner } from '../components/ui'
import { fmtCompact, fmtINR, fmtPct, fmtDate } from '../utils/format'
import type { Stock } from '../types'

type SortKey = 'company_name' | 'avg_volume_7d' | 'current_price' | 'daily_return' | 'return_7d' | 'return_30d' | 'return_100d' | 'return_180d' | 'return_365d'

const PCT_COLS: { key: SortKey; label: string }[] = [
  { key: 'daily_return', label: 'Daily %Chg' },
  { key: 'return_7d', label: '5D %' },
  { key: 'return_30d', label: '30D %' },
  { key: 'return_100d', label: '100D %' },
  { key: 'return_180d', label: '180D %' },
  { key: 'return_365d', label: '365D %' },
]

/** NSE-style filled green/red percentage cell. */
function PctCell({ value }: { value: number | null }) {
  if (value == null) return <td className="px-2 py-1.5 text-center text-slate-600">—</td>
  const up = value >= 0
  return (
    <td className="px-1.5 py-1">
      <span
        className={`num block rounded-md px-2 py-1 text-right text-xs font-semibold ${
          up ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'
        }`}
      >
        {fmtPct(value)}
      </span>
    </td>
  )
}

function MoverList({ title, icon, rows }: { title: string; icon: React.ReactNode; rows: Stock[] }) {
  const navigate = useNavigate()
  return (
    <div>
      <p className="mb-2 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
        {icon} {title}
      </p>
      <ul className="space-y-1">
        {rows.map((s) => (
          <li key={s.stock_id}>
            <button
              onClick={() => navigate(`/stock/${s.stock_id}`)}
              className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1 text-left text-xs hover:bg-slate-800/60"
            >
              <span className="truncate text-slate-300">{s.company_name}</span>
              <span
                className={`num shrink-0 rounded-md px-1.5 py-0.5 font-bold ${
                  (s.daily_return ?? 0) >= 0 ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'
                }`}
              >
                {fmtPct(s.daily_return)}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Screener() {
  const navigate = useNavigate()
  const { data: stocks, loading } = useStocks()
  const { data: movers } = useMovers()
  const { data: sectors } = useSectors()
  const { data: news } = useNews(null, 8)

  const [query, setQuery] = useState('')
  const [sector, setSector] = useState('all')
  const [sortKey, setSortKey] = useState<SortKey>('daily_return')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const rows = useMemo(() => {
    let list = stocks ?? []
    const q = query.trim().toLowerCase()
    if (q) list = list.filter((s) => s.company_name.toLowerCase().includes(q) || s.ticker.toLowerCase().includes(q))
    if (sector !== 'all') list = list.filter((s) => s.sector === sector)
    const dir = sortDir === 'asc' ? 1 : -1
    return [...list].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      if (typeof av === 'string' || typeof bv === 'string') return dir * String(av ?? '').localeCompare(String(bv ?? ''))
      return dir * ((av as number | null ?? -Infinity) - (bv as number | null ?? -Infinity))
    })
  }, [stocks, query, sector, sortKey, sortDir])

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else {
      setSortKey(key)
      setSortDir(key === 'company_name' ? 'asc' : 'desc')
    }
  }

  if (loading) return <Spinner label="Loading screener…" />

  return (
    <div>
      <PageHeader title="Stock Screener" subtitle="Nifty universe — price action, momentum and news at a glance" />

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Card title="Stocks That Moved The Market">
          <div className="grid grid-cols-2 gap-4">
            <MoverList title="Top Gainers" icon={<TrendingUp size={13} className="text-emerald-400" />} rows={movers?.gainers ?? []} />
            <MoverList title="Top Losers" icon={<TrendingDown size={13} className="text-rose-400" />} rows={movers?.losers ?? []} />
          </div>
        </Card>

        <Card title="Sectors">
          <ul className="space-y-1">
            {(sectors ?? []).slice(0, 8).map((s) => (
              <li key={s.sector}>
                <button
                  onClick={() => setSector(sector === s.sector ? 'all' : s.sector)}
                  className={`flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1 text-left text-xs hover:bg-slate-800/60 ${
                    sector === s.sector ? 'bg-indigo-500/15 ring-1 ring-indigo-500/30' : ''
                  }`}
                >
                  <span className="truncate text-slate-300">{s.sector}</span>
                  <span className="shrink-0 text-slate-500">
                    <span className={`num font-semibold ${(s.avg_daily_return ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {fmtPct(s.avg_daily_return)}
                    </span>{' '}
                    · {s.stock_count}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Latest News">
          {news && news.length > 0 ? (
            <ul className="space-y-2">
              {news.map((n) => (
                <li key={n.id} className="text-xs">
                  <div className="flex items-start gap-1.5">
                    <Newspaper size={12} className="mt-0.5 shrink-0 text-indigo-400" />
                    <div className="min-w-0">
                      <p className="truncate text-slate-300">{n.headline ?? n.subject}</p>
                      <p className="text-[10px] text-slate-600">
                        {n.symbol ?? n.company_name} · {fmtDate(n.published_at)}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500">No news ingested yet — run Settings → Update Data.</p>
          )}
        </Card>
      </div>

      <Card
        title={`Universe (${rows.length})`}
        className="mt-6"
        actions={
          <div className="flex items-center gap-2">
            {sector !== 'all' && (
              <button onClick={() => setSector('all')} className="rounded-lg bg-indigo-500/15 px-2 py-1 text-xs text-indigo-300">
                {sector} ✕
              </button>
            )}
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search stock / ticker…"
              className="w-44 rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-1.5 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-indigo-500/50"
            />
          </div>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full border-separate border-spacing-0 text-sm">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-wider text-slate-500">
                <th className="sticky top-0 bg-panel px-2 py-2 text-right">#</th>
                {(
                  [
                    ['company_name', 'Stock'],
                    ['avg_volume_7d', 'Traded Qty'],
                    ['current_price', 'LTP'],
                  ] as [SortKey, string][]
                ).map(([key, label]) => (
                  <th key={key} className="sticky top-0 cursor-pointer bg-panel px-3 py-2 hover:text-slate-300" onClick={() => toggleSort(key)}>
                    {label}
                    {sortKey === key && <span> {sortDir === 'asc' ? '↑' : '↓'}</span>}
                  </th>
                ))}
                {PCT_COLS.map((c) => (
                  <th
                    key={c.key}
                    className="sticky top-0 cursor-pointer bg-panel px-2 py-2 text-right hover:text-slate-300"
                    onClick={() => toggleSort(c.key)}
                  >
                    {c.label}
                    {sortKey === c.key && <span> {sortDir === 'asc' ? '↑' : '↓'}</span>}
                  </th>
                ))}
                <th className="sticky top-0 bg-panel px-3 py-2 text-right">Cap</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s, i) => (
                <tr
                  key={s.stock_id}
                  onClick={() => navigate(`/stock/${s.stock_id}`)}
                  className="cursor-pointer border-b border-slate-800/50 hover:bg-indigo-500/5"
                >
                  <td className="num px-2 py-1.5 text-right text-[11px] text-slate-600">{i + 1}</td>
                  <td className="px-3 py-1.5">
                    <p className="max-w-52 truncate text-xs font-medium text-slate-200">{s.company_name}</p>
                    <p className="text-[10px] text-slate-600">{s.ticker.replace('.NS', '')} · {s.sector}</p>
                  </td>
                  <td className="num px-3 py-1.5 text-right text-xs text-slate-400">{fmtCompact(s.avg_volume_7d)}</td>
                  <td className="num px-3 py-1.5 text-right text-xs font-semibold text-slate-100">{fmtINR(s.current_price)}</td>
                  {PCT_COLS.map((c) => (
                    <PctCell key={c.key} value={s[c.key] as number | null} />
                  ))}
                  <td className="px-3 py-1.5 text-right text-[11px] text-slate-500">{s.market_cap?.replace(' Cap', '') ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && <EmptyState icon="🔍" title="No stocks match" message="Adjust the search or sector filter." />}
        </div>
      </Card>
    </div>
  )
}
