/** Row shape of GET /api/stocks (silver/features.csv + derived returns). */
export interface Stock {
  stock_id: number
  company_name: string
  ticker: string
  sector: string
  industry: string
  market_cap: string
  country: string
  exchange: string
  is_active: boolean
  current_price: number | null
  daily_return: number | null
  '52w_high': number | null
  '52w_low': number | null
  ma20: number | null
  ma50: number | null
  trend: string | null
  return_7d: number | null
  return_30d: number | null
  return_100d: number | null
  return_180d: number | null
  return_365d: number | null
  volatility_7d: number | null
  volatility_30d: number | null
  volatility_180d: number | null
  avg_volume_7d: number | null
  avg_volume_30d: number | null
  avg_volume_180d: number | null
  debt_to_equity: number | null
  debt_to_assets: number | null
  cash_ratio: number | null
  score: number | null
  predicted_price: number | null
  predicted_direction: string | null
}

/** Row shape of public/data/recommendations.json. */
export interface Recommendation {
  company_name: string
  current_price: number | null
  predicted_price: number | null
  reason: string
}

/** Row shape of public/data/portfolio.json (bronze/transactions.csv). */
export interface Transaction {
  stock_id: number | null
  stock_name: string
  quantity: number
  buy_price: number
  buy_date: string
  asset_type: string
}

/** One OHLCV bar from public/data/prices/<stock_id>.json. */
export interface PricePoint {
  date: string
  open: number | null
  high: number | null
  low: number | null
  close: number
  volume: number | null
}

export interface Meta {
  stocks: number
  recommendations: number
  data_updated_at: string | null
}

export interface SectorStat {
  sector: string
  avg_daily_return: number
  stock_count: number
}

/** A resolved holding: a transaction joined with live stock data. */
export interface Position {
  key: string
  stockId: number | null
  name: string
  quantity: number
  buyPrice: number
  buyDate: string
  currentPrice: number
  investment: number
  currentValue: number
  profit: number
  returnPct: number
  sector: string | null
  score: number | null
  /** true when the position came from localStorage, not the exported file */
  local: boolean
}
