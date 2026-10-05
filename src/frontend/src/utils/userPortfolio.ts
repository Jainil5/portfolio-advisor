import type { Transaction } from '../types'

const KEY = 'pa.localHoldings'

/** Holdings the user added in the browser (no backend yet, so localStorage). */
export function loadLocalHoldings(): Transaction[] {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as Transaction[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveLocalHolding(h: Transaction): Transaction[] {
  const next = [...loadLocalHoldings(), { ...h, local: true } as Transaction & { local: boolean }]
  localStorage.setItem(KEY, JSON.stringify(next))
  return next
}

export function removeLocalHolding(index: number): Transaction[] {
  const next = loadLocalHoldings().filter((_, i) => i !== index)
  localStorage.setItem(KEY, JSON.stringify(next))
  return next
}
