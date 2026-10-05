import type { Position, PricePoint, Stock, Transaction } from '../types'

export type Timeframe = '1W' | '1M' | '3M' | '1Y'

const TF_DAYS: Record<Timeframe, number> = { '1W': 7, '1M': 30, '3M': 90, '1Y': 365 }

/** Simple Moving Average over close prices; null until enough bars exist. */
export function sma(prices: PricePoint[], window: number): (number | null)[] {
  const out: (number | null)[] = []
  let sum = 0
  for (let i = 0; i < prices.length; i++) {
    sum += prices[i].close
    if (i >= window) sum -= prices[i - window].close
    out.push(i >= window - 1 ? sum / window : null)
  }
  return out
}

/** Latest SMA value computed over the full series (matches the pandas pipeline). */
export function latestSma(prices: PricePoint[], window: number): number | null {
  const series = sma(prices, window)
  return series.length ? series[series.length - 1] : null
}

/** Trim history to the trailing N days, with a minimum-bar fallback like the Streamlit app. */
export function filterTimeframe(prices: PricePoint[], tf: Timeframe): PricePoint[] {
  const lastDate = new Date(prices[prices.length - 1].date).getTime()
  const cutoff = lastDate - TF_DAYS[tf] * 24 * 3600 * 1000
  const filtered = prices.filter((p) => new Date(p.date).getTime() >= cutoff)
  const minBars: Record<Timeframe, number> = { '1W': 2, '1M': 5, '3M': 15, '1Y': 50 }
  if (filtered.length < minBars[tf]) return prices.slice(-TF_DAYS[tf] || 7)
  return filtered
}

export interface Suggestion {
  label: 'BUY' | 'HOLD' | 'SELL'
  badge: string
  text: string
}

/** Thresholds mirror streamlit_app/pages/stock_analysis.py. */
export function suggestionForScore(score: number | null | undefined): Suggestion {
  const s = score ?? 0
  if (s >= 3) return { label: 'BUY', badge: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/30', text: 'text-emerald-400' }
  if (s >= 1.5) return { label: 'HOLD', badge: 'bg-amber-500/15 text-amber-400 ring-amber-500/30', text: 'text-amber-400' }
  return { label: 'SELL', badge: 'bg-rose-500/15 text-rose-400 ring-rose-500/30', text: 'text-rose-400' }
}

function findStock(tx: Transaction, stocks: Stock[]): Stock | undefined {
  if (tx.stock_id != null) {
    const byId = stocks.find((s) => s.stock_id === tx.stock_id)
    if (byId) return byId
  }
  const name = tx.stock_name?.toLowerCase().trim()
  return stocks.find((s) => s.company_name.toLowerCase().trim() === name)
}

/** Join transactions with feature data; `local` positions override nothing. */
export function buildPositions(
  transactions: Transaction[],
  stocks: Stock[],
  localAdditions: Transaction[],
): Position[] {
  const all = [...transactions, ...localAdditions]
  return all.map((tx, i) => {
    const stock = findStock(tx, stocks)
    const currentPrice = stock?.current_price ?? tx.buy_price
    const investment = tx.buy_price * tx.quantity
    const currentValue = currentPrice * tx.quantity
    const profit = currentValue - investment
    return {
      key: `${tx.stock_name}-${i}`,
      stockId: stock?.stock_id ?? tx.stock_id ?? null,
      name: stock?.company_name ?? tx.stock_name,
      quantity: tx.quantity,
      buyPrice: tx.buy_price,
      buyDate: tx.buy_date,
      currentPrice,
      investment,
      currentValue,
      profit,
      returnPct: investment > 0 ? (profit / investment) * 100 : 0,
      sector: stock?.sector ?? null,
      score: stock?.score ?? null,
      local: (tx as Transaction & { local?: boolean }).local === true,
    }
  })
}

export interface PortfolioTotals {
  investment: number
  currentValue: number
  profit: number
  returnPct: number
}

export function portfolioTotals(positions: Position[]): PortfolioTotals {
  const investment = positions.reduce((a, p) => a + p.investment, 0)
  const currentValue = positions.reduce((a, p) => a + p.currentValue, 0)
  const profit = currentValue - investment
  return {
    investment,
    currentValue,
    profit,
    returnPct: investment > 0 ? (profit / investment) * 100 : 0,
  }
}

/** Position of a price within the 52-week range, clamped to [0, 1]. */
export function rangePosition(price: number, low: number, high: number): number {
  if (high - low <= 0) return 0.5
  return Math.min(1, Math.max(0, (price - low) / (high - low)))
}
