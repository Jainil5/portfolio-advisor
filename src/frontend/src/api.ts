/// <reference types="vite/client" />
import { useEffect, useMemo, useState } from 'react'
import type { Meta, PricePoint, Recommendation, SectorStat, Stock, Transaction } from './types'

// Dev: vite proxies /api -> uvicorn :8000. Prod: set VITE_API_BASE.
const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? ''

export interface Json<T> {
  data: T | null
  error: string | null
  loading: boolean
  refetch: () => void
}

function useJson<T>(path: string | null, pollMs = 0): Json<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(Boolean(path))
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!path) {
      setData(null)
      setLoading(false)
      return
    }
    let alive = true
    const load = () => {
      setLoading(data === null)
      fetch(BASE + path)
        .then(async (res) => {
          if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
          return (await res.json()) as T
        })
        .then((d) => {
          if (!alive) return
          setData(d)
          setError(null)
        })
        .catch((e: Error) => {
          if (alive) setError(e.message)
        })
        .finally(() => {
          if (alive) setLoading(false)
        })
    }
    load()
    const timer = pollMs > 0 ? setInterval(load, pollMs) : null
    return () => {
      alive = false
      if (timer) clearInterval(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick, pollMs])

  return { data, error, loading, refetch: () => setTick((t) => t + 1) }
}

export const useStocks = () => useJson<Stock[]>('/api/stocks')
export const useRecommendations = () => useJson<Recommendation[]>('/api/recommendations')
export const useMeta = () => useJson<Meta>('/api/meta')
export const useMovers = () => useJson<{ gainers: Stock[]; losers: Stock[] }>('/api/movers')
export const useSectors = () => useJson<SectorStat[]>('/api/sectors')

interface LedgerRow {
  transaction_id: string
  stock_id: number
  stock_name: string
  action: string
  quantity: number
  price: number
  date: string
}

/** Transaction ledger rows mapped to the buy-position view finance.ts consumes. */
export function useTransactions(): Json<Transaction[]> {
  const raw = useJson<LedgerRow[]>('/api/transactions')
  const data = useMemo(
    () =>
      (raw.data ?? [])
        .filter((t) => t.action === 'buy')
        .map((t) => ({
          stock_id: t.stock_id,
          stock_name: t.stock_name,
          quantity: t.quantity,
          buy_price: t.price,
          buy_date: t.date,
          asset_type: 'stock',
        })),
    [raw.data],
  )
  return { data, error: raw.error, loading: raw.loading, refetch: raw.refetch }
}

export function usePrices(stockId: number | null | undefined): Json<PricePoint[]> {
  return useHistory(stockId, '5y')
}

export function useHistory(stockId: number | null | undefined, range: string): Json<PricePoint[]> {
  const res = useJson<{ candles: PricePoint[] }>(
    stockId != null ? `/api/stocks/${stockId}/history?range=${range}` : null,
  )
  return {
    data: res.data?.candles ?? null,
    error: res.error,
    loading: res.loading,
    refetch: res.refetch,
  }
}

export interface NewsItem {
  id: string
  symbol: string | null
  company_name: string | null
  headline: string | null
  subject: string | null
  category: string | null
  published_at: string | null
  pdf_url: string | null
}

export const useNews = (symbol?: string | null, limit = 15) =>
  useJson<NewsItem[]>(
    `/api/news?limit=${limit}${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ''}`,
  )

export interface StockAnalysis {
  stock_id: number
  ticker: string
  company_name: string
  analysis: string
  generated_at: number
}

export function useAnalysis(stockId: number | null, refresh = false): Json<StockAnalysis> {
  return useJson<StockAnalysis>(
    stockId != null ? `/api/stocks/${stockId}/analysis${refresh ? '?refresh=true' : ''}` : null,
  )
}

export interface UpdateState {
  status: 'idle' | 'running' | 'done' | 'error'
  stage: string | null
  started_at: string | null
  finished_at: string | null
  error: string | null
  log: string[]
}

export function startDataUpdate(includeNews = true): Promise<{ status: string } | null> {
  return fetch(`${BASE}/api/update_data?include_news=${includeNews}`, { method: 'POST' })
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status}`))))
    .catch(() => null)
}

/** Poll the update job status every 2s while `active`. */
export const useUpdateStatus = (active: boolean) =>
  useJson<UpdateState>(active ? '/api/update_data/status' : null, active ? 2000 : 0)
