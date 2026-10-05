import type { ReactNode } from 'react'
import { fmtPct } from '../utils/format'

export function Card({
  title,
  actions,
  children,
  className = '',
}: {
  title?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={`animate-rise rounded-2xl border border-slate-800/80 bg-panel/80 p-5 shadow-lg shadow-black/20 backdrop-blur ${className}`}
    >
      {(title || actions) && (
        <header className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </section>
  )
}

/** KPI card replacing st.metric: big value, optional colored delta. */
export function Metric({
  label,
  value,
  deltaPct,
  deltaText,
  hint,
  emphasize = false,
}: {
  label: string
  value: ReactNode
  deltaPct?: number | null
  deltaText?: string
  hint?: string
  emphasize?: boolean
}) {
  const positive = deltaPct != null && deltaPct >= 0
  return (
    <div
      className={`animate-rise rounded-2xl border p-4 ${
        emphasize
          ? 'border-indigo-500/30 bg-gradient-to-br from-indigo-500/10 to-panel'
          : 'border-slate-800/80 bg-panel/80'
      }`}
    >
      <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{label}</p>
      <p className="num mt-1 text-2xl font-bold text-slate-100">{value}</p>
      {deltaPct != null && (
        <p className={`num mt-1 text-xs font-semibold ${positive ? 'text-emerald-400' : 'text-rose-400'}`}>
          {positive ? '▲' : '▼'} {fmtPct(Math.abs(deltaPct), false)}
          {deltaText ? <span className="ml-1 font-normal text-slate-500">{deltaText}</span> : null}
        </p>
      )}
      {deltaPct == null && deltaText && <p className="mt-1 text-xs text-slate-500">{deltaText}</p>}
      {hint && <p className="mt-1 text-[11px] text-slate-600">{hint}</p>}
    </div>
  )
}

const TONES: Record<string, string> = {
  buy: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/30',
  hold: 'bg-amber-500/15 text-amber-400 ring-amber-500/30',
  sell: 'bg-rose-500/15 text-rose-400 ring-rose-500/30',
  neutral: 'bg-slate-500/15 text-slate-300 ring-slate-500/30',
  info: 'bg-sky-500/15 text-sky-300 ring-sky-500/30',
}

export function Badge({ tone = 'neutral', children }: { tone?: keyof typeof TONES; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold tracking-wide ring-1 ${TONES[tone] ?? TONES.neutral}`}
    >
      {children}
    </span>
  )
}

export function TrendPill({ trend }: { trend: string | null | undefined }) {
  if (!trend) return null
  const bullish = trend.toLowerCase() === 'bullish'
  return (
    <span className={`text-xs font-semibold ${bullish ? 'text-emerald-400' : 'text-rose-400'}`}>
      {bullish ? '🟢 Bullish' : '🔴 Bearish'}
    </span>
  )
}

/** Green/red/gray signed value used across P&L tables. */
export function PnL({ value, pct, suffix = '' }: { value: number; pct?: number; suffix?: string }) {
  const cls = value > 0 ? 'text-emerald-400' : value < 0 ? 'text-rose-400' : 'text-slate-400'
  return (
    <span className={`num font-semibold ${cls}`}>
      {value.toLocaleString('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 2 })}
      {suffix}
      {pct != null && <span className="ml-1 text-xs font-normal opacity-80">({fmtPct(pct)})</span>}
    </span>
  )
}

export function EmptyState({ icon = '📭', title, message }: { icon?: string; title: string; message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-800 py-16 text-center">
      <div className="text-4xl">{icon}</div>
      <p className="mt-3 font-semibold text-slate-300">{title}</p>
      {message && <p className="mt-1 max-w-md text-sm text-slate-500">{message}</p>}
    </div>
  )
}

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-10 text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-indigo-400" />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function PageHeader({ title, subtitle, right }: { title: string; subtitle?: string; right?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {right}
    </div>
  )
}
