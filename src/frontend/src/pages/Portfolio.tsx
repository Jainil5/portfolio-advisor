import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useRecommendations, useStocks, useTransactions } from '../api'
import ChatPanel from '../components/ChatPanel'
import HoldingsTable from '../components/HoldingsTable'
import { Card, EmptyState, Metric, PageHeader, Spinner } from '../components/ui'
import { buildPositions } from '../utils/finance'
import { fmtINR, fmtPct } from '../utils/format'
import { loadLocalHoldings, removeLocalHolding, saveLocalHolding } from '../utils/userPortfolio'
import type { Transaction } from '../types'

export default function Portfolio() {
  const { data: stocks, loading: stocksLoading } = useStocks()
  const { data: transactions, loading: txLoading } = useTransactions()
  const { data: recommendations } = useRecommendations()

  const [localHoldings, setLocalHoldings] = useState<Transaction[]>(loadLocalHoldings)
  const [selected, setSelected] = useState('')
  const [qty, setQty] = useState(1)
  const [price, setPrice] = useState<number | ''>('')
  const [flash, setFlash] = useState<string | null>(null)

  const txCount = transactions?.length ?? 0
  const positions = useMemo(
    () => buildPositions(transactions ?? [], stocks ?? [], localHoldings),
    [transactions, stocks, localHoldings],
  )

  const best = useMemo(
    () => (positions.length ? positions.reduce((a, b) => (b.returnPct > a.returnPct ? b : a)) : null),
    [positions],
  )
  const worst = useMemo(
    () => (positions.length ? positions.reduce((a, b) => (b.returnPct < a.returnPct ? b : a)) : null),
    [positions],
  )
  const investedTotal = positions.reduce((a, p) => a + p.investment, 0)

  const chartData = useMemo(
    () =>
      positions.map((p) => ({
        name: p.name.replace(/ (Ltd\.?|Ltd)$/i, ''),
        returnPct: Number(p.returnPct.toFixed(2)),
      })),
    [positions],
  )

  if (stocksLoading || txLoading) return <Spinner label="Loading portfolio…" />
  if (!stocks) {
    return (
      <EmptyState
        icon="🗂️"
        title="No exported data found"
        message="Run `python scripts/export_frontend_data.py` to generate public/data/*.json, then refresh."
      />
    )
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    const stock = stocks!.find((s) => String(s.stock_id) === selected)
    if (!stock || qty < 1 || price === '' || price <= 0) return
    const next = saveLocalHolding({
      stock_id: stock.stock_id,
      stock_name: stock.company_name,
      quantity: qty,
      buy_price: Number(price),
      buy_date: new Date().toISOString().slice(0, 10),
      asset_type: 'Stock',
    })
    setLocalHoldings(next)
    setSelected('')
    setQty(1)
    setPrice('')
    setFlash(`Added ${qty} shares of ${stock.company_name} (stored locally in your browser).`)
    setTimeout(() => setFlash(null), 4000)
  }

  function onDelete(key: string) {
    const i = Number(key.split('-').pop())
    if (Number.isNaN(i) || i < txCount) return
    setLocalHoldings(removeLocalHolding(i - txCount))
  }

  const activeStocks = stocks.filter((s) => s.is_active)

  return (
    <div>
      <PageHeader title="My Portfolio" subtitle="Track holdings, add positions and review performance" />

      {flash && (
        <div className="mb-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
          ✓ {flash}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-3">
        <Card title="➕ Add New Stock" className="xl:col-span-1">
          <p className="mb-4 text-xs leading-relaxed text-slate-500">
            There is no write backend yet — positions you add here are stored in your browser
            (localStorage) and merged with the exported portfolio file.
          </p>
          <form onSubmit={onSubmit} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-400">Company</label>
              <input
                list="stock-options"
                required
                value={selected ? stocks!.find((s) => String(s.stock_id) === selected)?.company_name ?? '' : ''}
                onChange={(e) => {
                  const hit = activeStocks.find(
                    (s) => s.company_name.toLowerCase() === e.target.value.toLowerCase(),
                  )
                  setSelected(hit ? String(hit.stock_id) : e.target.value === '' ? '' : selected)
                }}
                placeholder="Type a company name…"
                className="w-full rounded-xl border border-slate-700/80 bg-slate-950/60 px-3.5 py-2 text-sm outline-none transition-colors focus:border-indigo-500/60"
              />
              <datalist id="stock-options">
                {activeStocks.map((s) => (
                  <option key={s.stock_id} value={s.company_name} />
                ))}
              </datalist>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">Quantity</label>
                <input
                  type="number"
                  min={1}
                  step={1}
                  required
                  value={qty}
                  onChange={(e) => setQty(Math.max(1, Number(e.target.value)))}
                  className="num w-full rounded-xl border border-slate-700/80 bg-slate-950/60 px-3.5 py-2 text-sm outline-none focus:border-indigo-500/60"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">Buy Price (₹)</label>
                <input
                  type="number"
                  min={0.01}
                  step={0.1}
                  required
                  value={price}
                  onChange={(e) => setPrice(e.target.value === '' ? '' : Number(e.target.value))}
                  className="num w-full rounded-xl border border-slate-700/80 bg-slate-950/60 px-3.5 py-2 text-sm outline-none focus:border-indigo-500/60"
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={!stocks.some((s) => String(s.stock_id) === selected)}
              className="w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Add Stock
            </button>
          </form>
        </Card>

        <div className="grid grid-cols-2 gap-4 self-start xl:col-span-2 xl:grid-cols-2">
          <Metric label="Total Invested" value={fmtINR(investedTotal)} />
          <Metric label="Positions" value={positions.length} hint={`${localHoldings.length} added locally`} />
          {best && (
            <div className="animate-rise rounded-2xl border border-emerald-500/25 bg-emerald-500/5 p-4">
              <p className="text-xs font-medium uppercase tracking-wider text-emerald-500/80">🏆 Best Performer</p>
              <p className="mt-1 truncate font-semibold text-slate-100">{best.name}</p>
              <p className="num text-sm font-bold text-emerald-400">{fmtPct(best.returnPct)}</p>
            </div>
          )}
          {worst && (
            <div className="animate-rise rounded-2xl border border-rose-500/25 bg-rose-500/5 p-4">
              <p className="text-xs font-medium uppercase tracking-wider text-rose-500/80">⚠️ Worst Performer</p>
              <p className="mt-1 truncate font-semibold text-slate-100">{worst.name}</p>
              <p className="num text-sm font-bold text-rose-400">{fmtPct(worst.returnPct)}</p>
            </div>
          )}
        </div>
      </div>

      {positions.length === 0 ? (
        <div className="mt-6">
          <EmptyState icon="💼" title="Portfolio is empty" message="Add your first stock above to start tracking." />
        </div>
      ) : (
        <>
          <Card title="Holdings Overview" className="mt-6">
            <HoldingsTable positions={positions} onDeleteLocal={onDelete} />
          </Card>

          <Card title="Return % by Holding" className="mt-6">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: '#64748b', fontSize: 10 }}
                    interval={0}
                    angle={-20}
                    textAnchor="end"
                    height={54}
                  />
                  <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(v) => `${v}%`} width={48} />
                  <Tooltip
                    formatter={(v) => [`${v}%`, 'Return']}
                    contentStyle={{ background: '#111a2c', border: '1px solid #1e293b', borderRadius: 12, fontSize: 12 }}
                  />
                  <Bar dataKey="returnPct" radius={[6, 6, 0, 0]}>
                    {chartData.map((d, i) => (
                      <Cell key={i} fill={d.returnPct >= 0 ? '#34d399' : '#fb7185'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </>
      )}

      <div className="mt-6">
        <ChatPanel
          stocks={stocks}
          recommendations={recommendations ?? []}
          placeholder="Ask about your holdings, e.g. 'Should I buy Reliance?'"
        />
      </div>
    </div>
  )
}
