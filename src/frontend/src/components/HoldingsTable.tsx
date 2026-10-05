import { Link } from 'react-router-dom'
import type { Position } from '../types'
import { fmtINR } from '../utils/format'
import { PnL } from './ui'

/** Shared holdings table used by Dashboard and My Portfolio. */
export default function HoldingsTable({
  positions,
  onDeleteLocal,
}: {
  positions: Position[]
  onDeleteLocal?: (key: string) => void
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-500">
            <th className="py-2.5 pr-4 font-medium">Stock</th>
            <th className="py-2.5 pr-4 text-right font-medium">Qty</th>
            <th className="py-2.5 pr-4 text-right font-medium">Buy Price</th>
            <th className="py-2.5 pr-4 text-right font-medium">Current</th>
            <th className="py-2.5 pr-4 text-right font-medium">Invested</th>
            <th className="py-2.5 pr-4 text-right font-medium">Profit / Loss</th>
            <th className="py-2.5 pr-4 text-right font-medium">Return %</th>
            {onDeleteLocal && <th className="py-2.5 w-8" />}
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => (
            <tr key={p.key} className="border-b border-slate-800/60 transition-colors hover:bg-slate-800/30">
              <td className="py-2.5 pr-4">
                <div className="font-medium text-slate-200">
                  {p.stockId != null ? (
                    <Link to={`/analysis?stock=${p.stockId}`} className="hover:text-indigo-300">
                      {p.name}
                    </Link>
                  ) : (
                    p.name
                  )}
                </div>
                <div className="text-[11px] text-slate-600">
                  {p.sector ?? '—'}
                  {p.local && <span className="ml-1.5 rounded bg-sky-500/15 px-1 py-px text-[10px] font-semibold text-sky-300">LOCAL</span>}
                </div>
              </td>
              <td className="num py-2.5 pr-4 text-right text-slate-300">{p.quantity}</td>
              <td className="num py-2.5 pr-4 text-right text-slate-400">{fmtINR(p.buyPrice)}</td>
              <td className="num py-2.5 pr-4 text-right text-slate-200">{fmtINR(p.currentPrice)}</td>
              <td className="num py-2.5 pr-4 text-right text-slate-400">{fmtINR(p.investment)}</td>
              <td className="py-2.5 pr-4 text-right">
                <PnL value={p.profit} />
              </td>
              <td className="py-2.5 pr-4 text-right">
                <PnL value={p.returnPct} suffix="%" />
              </td>
              {onDeleteLocal && (
                <td className="py-2.5 text-right">
                  {p.local && (
                    <button
                      onClick={() => onDeleteLocal(p.key)}
                      title="Remove local holding"
                      className="text-slate-600 transition-colors hover:text-rose-400"
                    >
                      ✕
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
