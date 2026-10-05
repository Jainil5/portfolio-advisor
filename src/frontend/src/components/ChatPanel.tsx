import { useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import type { Recommendation, Stock } from '../types'
import { answerQuery } from '../agent/localAgent'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

/** Minimal inline renderer: **bold**, _italic_, plain text. */
function renderInline(text: string): ReactNode[] {
  const parts: ReactNode[] = []
  const regex = /(\*\*[^*]+\*\*|_[^_]+_|`[^`]+`)/g
  let last = 0
  let match: RegExpExecArray | null
  let key = 0
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index))
    const token = match[0]
    if (token.startsWith('**')) {
      parts.push(
        <strong key={key++} className="font-semibold text-slate-100">
          {token.slice(2, -2)}
        </strong>,
      )
    } else if (token.startsWith('_')) {
      parts.push(
        <em key={key++} className="text-slate-400">
          {token.slice(1, -1)}
        </em>,
      )
    } else {
      parts.push(
        <code key={key++} className="rounded bg-slate-800 px-1 py-0.5 text-[11px] text-sky-300">
          {token.slice(1, -1)}
        </code>,
      )
    }
    last = match.index + token.length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

function RichText({ text }: { text: string }) {
  return (
    <div className="space-y-1 text-sm leading-relaxed">
      {text.split('\n').map((line, i) => {
        if (line.trim() === '') return <div key={i} className="h-1" />
        if (/^\s*[-•]\s+/.test(line) || /^\s*\d+\.\s+/.test(line)) {
          return (
            <div key={i} className="flex gap-2 pl-1">
              <span className="mt-0.5 text-indigo-400">›</span>
              <span>{renderInline(line.replace(/^\s*([-•]|\d+\.)\s+/, ''))}</span>
            </div>
          )
        }
        return <p key={i}>{renderInline(line)}</p>
      })}
    </div>
  )
}

const SUGGESTIONS = [
  'Should I buy Reliance?',
  'Compare Adani Energy and NTPC',
  'Recommend me some stocks',
  'What is the 30-day return for Vedanta?',
]

export default function ChatPanel({
  stocks,
  recommendations,
  placeholder = 'Ask about stocks like "Should I buy TCS?"',
  compact = false,
  title = '🤖 Portfolio Advisor Agent',
}: {
  stocks: Stock[]
  recommendations: Recommendation[]
  placeholder?: string
  compact?: boolean
  title?: string
}) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  function ask(question: string) {
    const q = question.trim()
    if (!q || thinking) return
    setMessages((m) => [...m, { role: 'user', content: q }])
    setInput('')
    setThinking(true)
    // small delay so the "analyzing" state is visible, mirroring st.spinner
    setTimeout(() => {
      const answer = answerQuery(q, stocks, recommendations)
      setMessages((m) => [...m, { role: 'assistant', content: answer }])
      setThinking(false)
      requestAnimationFrame(() => {
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
      })
    }, 400)
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    ask(input)
  }

  return (
    <div className="flex flex-col rounded-2xl border border-slate-800/80 bg-panel/80">
      <div className="flex items-center justify-between border-b border-slate-800/80 px-4 py-3">
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        {messages.length > 0 && (
          <button
            onClick={() => setMessages([])}
            className="text-xs text-slate-500 transition-colors hover:text-slate-300"
          >
            Clear
          </button>
        )}
      </div>

      <div
        ref={scrollRef}
        className={`flex-1 space-y-3 overflow-y-auto px-4 py-3 ${compact ? 'max-h-64' : 'min-h-[220px] max-h-[50vh]'}`}
      >
        {messages.length === 0 && (
          <div>
            <p className="text-sm text-slate-500">
              I analyze the market dataset (momentum, volatility, trend, fundamentals). Try:
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => ask(s)}
                  className="rounded-full border border-slate-700/80 bg-slate-800/40 px-3 py-1 text-xs text-slate-300 transition-colors hover:border-indigo-500/50 hover:text-indigo-300"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div
              className={
                m.role === 'user'
                  ? 'max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-3.5 py-2 text-sm text-white'
                  : 'max-w-[92%] rounded-2xl rounded-bl-sm border border-slate-800 bg-slate-900/90 px-3.5 py-2.5 text-slate-200'
              }
            >
              {m.role === 'user' ? <p className="text-sm">{m.content}</p> : <RichText text={m.content} />}
            </div>
          </div>
        ))}

        {thinking && (
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-600 border-t-indigo-400" />
            Analyzing market data…
          </div>
        )}
      </div>

      <form onSubmit={onSubmit} className="flex gap-2 border-t border-slate-800/80 p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          className="min-w-0 flex-1 rounded-xl border border-slate-700/80 bg-slate-950/60 px-3.5 py-2 text-sm text-slate-200 placeholder-slate-600 outline-none transition-colors focus:border-indigo-500/60"
        />
        <button
          type="submit"
          disabled={!input.trim() || thinking}
          className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  )
}
