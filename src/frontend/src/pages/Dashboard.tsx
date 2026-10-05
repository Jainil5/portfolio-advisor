import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useRecommendations, useStocks, useTransactions } from '../api'
import ChatPanel from '../components/ChatPanel'
import HoldingsTable from '../components/HoldingsTable'
import { Card, EmptyState, Metric, PageHeader, Spinner } from '../components/ui'
import { buildPositions, portfolioTotals } from '../utils/finance'
import { fmtINR } from '../utils/format'

const PIE_COLORS = ['#6366f1', '#22d3ee', '#34d399', '#fbbf24', '#fb7185', '#a78bfa', '#f472b6', '#38bdf8']

export default function Dashboard() {
  const { data: stocks, loading: stocksLoading } = useStocks()
  const { data: transactions, loading: txLoading } = useTransactions()
  const { data: recommendations } = useRecommendations()

  const positions = useMemo(
    () => buildPositions(transactions ?? [], stocks ?? [], []),
    [transactions, stocks],
  )
  const totals = useMemo(() => portfolioTotals(positions), [positions])

  const sectorSlices = useMemo(() => {
    const bySector = new Map<string, number>()
    for (const p of positions) {
      bySector.set(p.sector ?? 'Other', (bySector.get(p.sector ?? 'Other') ?? 0) + p.currentValue)
    }
    return [...bySector.entries()]
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8)
  }, [positions])

  const topPicks = useMemo(
    () => [...(stocks ?? [])].sort((a, b) => (b.score ?? 0) - (a.score ?? 0)).slice(0, 5),
    [stocks],
  )

  if (stocksLoading || txLoading) return <Spinner label="Loading market data…" />

  return (
    <div>
      <PageHeader
        title="Portfolio Dashboard"
        subtitle="Live snapshot of your holdings, sector mix and AI signals"
      />

      {positions.length === 0 ? (
        <EmptyState
          icon="💼"
          title="Your portfolio is empty"
          message="Add stocks on the Portfolio page to see KPIs, charts and insights here."
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            <Metric label="Total Investment" value={fmtINR(totals.investment)} />
            <Metric label="Current Value" value={fmtINR(totals.currentValue)} emphasize />
            <Metric
              label="Profit / Loss"
              value={fmtINR(totals.profit)}
              deltaPct={totals.returnPct}
              deltaText="overall return"
            />
            <Metric label="Positions" value={positions.length} deltaText={`${sectorSlices.length} sectors`} />
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-3">
            <Card title="Holdings Overview" className="xl:col-span-2">
              <HoldingsTable positions={positions} />
            </Card>

            <div className="space-y-6">
              <Card title="Sector Allocation">
                {sectorSlices.length === 0 ? (
                  <p className="text-sm text-slate-500">No sector data available.</p>
                ) : (
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={sectorSlices}
                          dataKey="value"
                          nameKey="name"
                          innerRadius={52}
                          outerRadius={82}
                          paddingAngle={3}
                          strokeWidth={0}
                        >
                          {sectorSlices.map((_, i) => (
                            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(v) => fmtINR(Number(v))}
                          contentStyle={{
                            background: '#111a2c',
                            border: '1px solid #1e293b',
                            borderRadius: 12,
                            fontSize: 12,
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                )}
                <ul className="mt-2 space-y-1">
                  {sectorSlices.slice(0, 5).map((s, i) => (
                    <li key={s.name} className="flex items-center gap-2 text-xs text-slate-400">
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ background: PIE_COLORS[i % PIE_COLORS.length] }}
                      />
                      {s.name}
                      <span className="num ml-auto text-slate-500">{fmtINR(s.value)}</span>
                    </li>
                  ))}
                </ul>
              </Card>

              <Card
                title="Top AI Signals"
                actions={
                  <Link to="/analysis" className="text-xs text-indigo-400 hover:text-indigo-300">
                    Analyze →
                  </Link>
                }
              >
                <ul className="space-y-2">
                  {topPicks.map((s) => (
                    <li key={s.stock_id} className="flex items-center justify-between gap-3 text-sm">
                      <Link
                        to={`/analysis?stock=${s.stock_id}`}
                        className="truncate text-slate-300 hover:text-indigo-300"
                      >
                        {s.company_name}
                      </Link>
                      <span className="num shrink-0 rounded-lg bg-emerald-500/10 px-2 py-0.5 text-xs font-bold text-emerald-400">
                        {s.score?.toFixed(2) ?? '—'}
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            </div>
          </div>
        </>
      )}

      <div className="mt-6">
        <ChatPanel
          stocks={stocks ?? []}
          recommendations={recommendations ?? []}
          compact
          title="🤖 AI Portfolio Advisor"
        />
      </div>
    </div>
  )
}
