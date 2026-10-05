import type { Recommendation, Stock } from '../types'
import { fmtINR, fmtPct } from '../utils/format'
import { suggestionForScore } from '../utils/finance'

/** Common trading aliases that do not appear verbatim in company names. */
const ALIASES: Record<string, string> = {
  tcs: 'tata consultancy services',
  infy: 'infosys',
  ensol: 'adani energy',
  sbi: 'state bank of india',
  ongc: 'oil and natural gas',
}

const STOP_WORDS = new Set(['ltd', 'limited', 'the', 'of', 'and', 'co'])

function normalize(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

/** Token-prefix matching: "Reliance" → Reliance Industries, "Tata Motors" wins over "Tata Capital". */
function findStock(query: string, stocks: Stock[]): Stock | null {
  const q = ` ${normalize(query)} `
  let expanded = q
  for (const [alias, target] of Object.entries(ALIASES)) {
    if (expanded.includes(` ${alias} `)) expanded = expanded.replace(` ${alias} `, ` ${target} `)
  }
  let best: { stock: Stock; score: number } | null = null
  for (const stock of stocks) {
    const tokens = normalize(stock.company_name).split(' ').filter((t) => !STOP_WORDS.has(t))
    if (tokens.length === 0) continue
    const full = tokens.join(' ')
    let score = 0
    if (expanded.includes(` ${full} `)) score = tokens.length * 3
    else {
      // match the first token only when it is distinctive (e.g. "Reliance", "Vedanta")
      const first = tokens[0]
      const ambiguity = stocks.filter((s) => normalize(s.company_name).startsWith(first)).length
      if (expanded.includes(` ${first} `)) score = ambiguity === 1 ? 2 : 0
      // match the first two tokens ("Tata Motors", "Adani Energy")
      if (tokens.length > 1 && expanded.includes(` ${tokens.slice(0, 2).join(' ')} `)) {
        score = Math.max(score, 4)
      }
    }
    if (score > 0 && (!best || score > best.score)) best = { stock, score }
  }
  return best?.stock ?? null
}

function findAll(query: string, stocks: Stock[]): Stock[] {
  const found: Stock[] = []
  const q = normalize(query)
  let rest = ` ${q} `
  for (let i = 0; i < 4; i++) {
    const hit = findStock(rest, stocks)
    if (!hit) break
    found.push(hit)
    const tokens = normalize(hit.company_name)
      .split(' ')
      .filter((t) => !STOP_WORDS.has(t))
    rest = ` ${rest} `.replace(` ${tokens.join(' ')} `, ' ').replace(` ${tokens[0]} `, ' ')
  }
  return found
}

function verdict(s: Stock): string {
  const sug = suggestionForScore(s.score)
  return `${sug.label} (AI Score ${s.score?.toFixed(2) ?? '—'}/5.0)`
}

function describeStock(s: Stock): string {
  const lines = [
    `**${s.company_name}** (${s.ticker}) — ${verdict(s)}`,
    '',
    `- Current price: ${fmtINR(s.current_price)} (today ${fmtPct(s.daily_return)})`,
    `- Returns: 7d ${fmtPct(s.return_7d)} · 30d ${fmtPct(s.return_30d)} · 180d ${fmtPct(s.return_180d)}`,
    `- Volatility 30d: ${s.volatility_30d?.toFixed(2) ?? '—'}% · Trend: ${s.trend ?? 'Unknown'}`,
    `- 52-week range: ${fmtINR(s['52w_low'])} – ${fmtINR(s['52w_high'])}`,
    `- Sector: ${s.sector} (${s.market_cap})`,
  ]
  if (s.predicted_price != null) {
    lines.push(`- Next-day model outlook: ${fmtINR(s.predicted_price)} (${s.predicted_direction ?? '—'})`)
  }
  if ((s.debt_to_equity ?? 0) > 1.5) {
    lines.push(`- ⚠ Elevated leverage: debt/equity ${s.debt_to_equity?.toFixed(2)}`)
  }
  return lines.join('\n')
}

function compare(a: Stock, b: Stock): string {
  const rows = [
    ['AI Score', `${a.score?.toFixed(2) ?? '—'}`, `${b.score?.toFixed(2) ?? '—'}`],
    ['Current price', fmtINR(a.current_price), fmtINR(b.current_price)],
    ['30d return', fmtPct(a.return_30d), fmtPct(b.return_30d)],
    ['180d return', fmtPct(a.return_180d), fmtPct(b.return_180d)],
    ['Volatility 30d', `${a.volatility_30d?.toFixed(1) ?? '—'}%`, `${b.volatility_30d?.toFixed(1) ?? '—'}%`],
    ['Trend', a.trend ?? '—', b.trend ?? '—'],
  ]
  const lines = [
    `**${a.company_name}** vs **${b.company_name}**`,
    '',
    ...rows.map(([label, x, y]) => `- ${label}: ${x}  vs  ${y}`),
    '',
  ]
  const winner = (a.score ?? 0) >= (b.score ?? 0) ? a : b
  const loser = winner === a ? b : a
  lines.push(`Verdict: on the quantitative score, **${winner.company_name}** (${verdict(winner)}) screens better than ${loser.company_name} (${verdict(loser)}).`)
  return lines.join('\n')
}

function topPicks(stocks: Stock[]): string {
  const top = [...stocks].sort((x, y) => (y.score ?? 0) - (x.score ?? 0)).slice(0, 5)
  const lines = ['**Top 5 stocks by AI score right now:**', '']
  top.forEach((s, i) => {
    lines.push(`${i + 1}. **${s.company_name}** — score ${s.score?.toFixed(2)}/5.0 · ${s.trend} · 30d ${fmtPct(s.return_30d)} · ${fmtINR(s.current_price)}`)
  })
  lines.push('', 'Ask me about any of them, e.g. "Should I buy ' + (top[0]?.company_name.split(' ')[0] ?? 'TCS') + '?".')
  return lines.join('\n')
}

function inRecommendations(name: string, recs: Recommendation[]): Recommendation | undefined {
  const n = normalize(name)
  return recs.find((r) => normalize(r.company_name).includes(n.split(' ')[0]))
}

/**
 * Client-side preview of the Python stock agent (portfolio_advisor.agents.stock_agent).
 * Answers are generated from the exported features dataset — no LLM, no server.
 */
export function answerQuery(query: string, stocks: Stock[], recs: Recommendation[]): string {
  if (stocks.length === 0) return 'Dataset is still loading — try again in a moment.'
  const q = query.toLowerCase()
  const hits = findAll(query, stocks)

  if (/recommend|best stock|top pick|which stock/i.test(q) && hits.length === 0) {
    return topPicks(stocks)
  }

  if (/compare| vs\.? |versus/i.test(q) && hits.length >= 2) {
    return compare(hits[0], hits[1])
  }

  if (hits.length >= 1) {
    const s = hits[0]
    if (/why.*grow|why.*fall|why.*drop|why.*rising/i.test(q)) {
      return `**Why is ${s.company_name} moving?**\n\n${describeStock(s)}\n\nRecent momentum: ${fmtPct(s.return_7d)} over 1 week and ${fmtPct(s.return_30d)} over 1 month, with a ${s.trend?.toLowerCase()} trend.`
    }
    if (/return/i.test(q)) {
      return `**${s.company_name} returns**\n\n- 7-day: ${fmtPct(s.return_7d)}\n- 30-day: ${fmtPct(s.return_30d)}\n- 180-day: ${fmtPct(s.return_180d)}\n- Volatility (30d): ${s.volatility_30d?.toFixed(2) ?? '—'}%`
    }
    const rec = inRecommendations(s.company_name, recs)
    let answer = describeStock(s)
    if (rec) answer += `\n\n⭐ It is currently on the recommendations list: ${rec.reason.split('\n')[0]}`
    return answer
  }

  return [
    "I couldn't identify a company in that question. Try naming a stock, e.g.:",
    '',
    '- "Should I buy Reliance?"',
    '- "Compare Adani Energy and NTPC"',
    '- "What is the 30-day return for Vedanta?"',
    '- "Recommend me some stocks"',
    '',
    `_Note: this is the client-side preview agent. The full LLM agent lives in \`portfolio_advisor.agents.stock_agent\` and needs a backend API._`,
  ].join('\n')
}
