import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useRecommendations, useStocks, useMeta } from '../api'
import ChatPanel from '../components/ChatPanel'
import { Badge, Card, EmptyState, PageHeader, Spinner } from '../components/ui'
import { suggestionForScore } from '../utils/finance'
import { fmtINR, fmtPct } from '../utils/format'
import type { Recommendation, Stock } from '../types'

interface ParsedReason {
  label: string
  positives: string[]
  risks: string[]
}

/** reason format: "STRONG BUY because:\n- p1\n...\n\nRisks:\n- r1\n..." */
function parseReason(reason: string): ParsedReason {
  const lines = (reason ?? '').split('\n').map((l) => l.trim())
  const label = lines[0]?.replace(/because:?$/i, '').trim().toUpperCase() || 'BUY'
  const positives: string[] = []
  const risks: string[] = []
  let inRisks = false
  for (const line of lines.slice(1)) {
    if (!line) continue
    if (/^risks?:?$/i.test(line)) {
      inRisks = true
      continue
    }
    const bullet = line.replace(/^[-•]\s*/, '')
    if (!bullet) continue
    ;(inRisks ? risks : positives).push(bullet)
  }
  return { label, positives, risks }
}

const LABEL_TONE = (label: string): 'buy' | 'hold' | 'sell' => {
  if (label.includes('SELL')) return 'sell'
  if (label.includes('HOLD')) return 'hold'
  return 'buy'
}

function RecCard({ rec, stock }: { rec: Recommendation; stock: Stock | undefined }) {
  const parsed = parseReason(rec.reason)
  const upside =
    rec.current_price && rec.predicted_price
      ? ((rec.predicted_price - rec.current_price) / rec.current_price) * 100
      : null
  const suggestion = suggestionForScore(stock?.score)

  return (
    <Card className="flex flex-col">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-bold text-slate-100">
          {stock ? (
            <Link to={`/analysis?stock=${stock.stock_id}`} className="hover:text-indigo-300">
              {rec.company_name}
            </Link>
          ) : (
            rec.company_name
          )}
        </h3>
        <div className="flex items-center gap-2">
          <Badge tone={LABEL_TONE(parsed.label)}>{parsed.label}</Badge>
          {stock && <Badge tone={suggestion.label === 'BUY' ? 'buy' : suggestion.label === 'HOLD' ? 'hold' : 'sell'}>Score {fmtNumScore(stock.score)}</Badge>}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-600">Current</p>
          <p className="num font-semibold text-slate-100">{fmtINR(rec.current_price)}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-600">Predicted</p>
          <p className="num font-semibold text-slate-100">{fmtINR(rec.predicted_price)}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-600">Model Upside</p>
          <p className={`num font-semibold ${upside != null && upside >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {upside != null ? fmtPct(upside) : '—'}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-600">30d Return</p>
          <p className="num font-semibold text-slate-100">{stock ? fmtPct(stock.return_30d) : '—'}</p>
        </div>
      </div>

      <div className="mt-4 grid flex-1 gap-4 sm:grid-cols-2">
        <ul className="space-y-1.5">
          {parsed.positives.map((p, i) => (
            <li key={i} className="flex gap-2 text-xs text-slate-400">
              <span className="text-emerald-400">✓</span>
              {p}
            </li>
          ))}
        </ul>
        {parsed.risks.length > 0 && (
          <ul className="space-y-1.5">
            {parsed.risks.map((r, i) => (
              <li key={i} className="flex gap-2 text-xs text-slate-400">
                <span className="text-rose-400">✗</span>
                {r}
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  )
}

function fmtNumScore(score: number | null | undefined): string {
  return score == null ? '—' : score.toFixed(2)
}

export default function Recommendations() {
  const { data: recs, loading } = useRecommendations()
  const { data: stocks } = useStocks()
  const { data: meta } = useMeta()

  const enriched = useMemo(() => {
    if (!recs) return []
    return recs.map((r) => ({
      rec: r,
      stock: stocks?.find((s) => s.company_name === r.company_name),
    }))
  }, [recs, stocks])

  if (loading) return <Spinner label="Loading recommendations…" />

  return (
    <div>
      <PageHeader
        title="Top Stock Recommendations"
        subtitle={
          enriched.length
            ? `${enriched.length} AI-scored picks${meta?.data_updated_at ? ` · dataset updated ${new Date(meta.data_updated_at).toLocaleDateString('en-IN')}` : ''}`
            : 'Generated by the scoring pipeline'
        }
      />

      {!enriched.length ? (
        <EmptyState
          icon="⭐"
          title="No recommendations available"
          message="Run the backend pipeline (scripts/update_data.py), then export_frontend_data.py."
        />
      ) : (
        <div className="grid gap-5 xl:grid-cols-2">
          {enriched.map(({ rec, stock }) => (
            <RecCard key={rec.company_name} rec={rec} stock={stock} />
          ))}
        </div>
      )}

      <div className="mt-6">
        <ChatPanel
          stocks={stocks ?? []}
          recommendations={recs ?? []}
          placeholder="Ask about these recommendations, e.g. 'Why is JSW Steel recommended?'"
        />
      </div>
    </div>
  )
}
