const inr = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
})

export function fmtINR(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  return inr.format(n)
}

export function fmtPct(n: number | null | undefined, signed = true): string {
  if (n == null || Number.isNaN(n)) return '—'
  const sign = signed && n > 0 ? '+' : ''
  return `${sign}${n.toFixed(2)}%`
}

export function fmtNum(n: number | null | undefined, digits = 2): string {
  if (n == null || Number.isNaN(n)) return '—'
  return n.toLocaleString('en-IN', { maximumFractionDigits: digits })
}

/** 1,234,567 -> "12.3L"; 123,456,789 -> "1.2Cr" (Indian market convention). */
export function fmtCompact(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  if (n >= 1e7) return `${(n / 1e7).toFixed(2)}Cr`
  if (n >= 1e5) return `${(n / 1e5).toFixed(2)}L`
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`
  return `${n}`
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}
