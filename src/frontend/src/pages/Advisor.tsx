import { useRecommendations, useStocks } from '../api'
import ChatPanel from '../components/ChatPanel'
import { PageHeader, Spinner } from '../components/ui'

/** Full-page chat, mirroring streamlit_app/pages/ai_advisor.py. */
export default function Advisor() {
  const { data: stocks, loading: stocksLoading } = useStocks()
  const { data: recommendations, loading: recsLoading } = useRecommendations()

  if (stocksLoading || recsLoading) return <Spinner label="Loading the master dataset…" />

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="AI Portfolio Advisor"
        subtitle="Answers are generated from the exported master dataset: technical features, fundamentals and recommendations."
      />
      <ChatPanel
        stocks={stocks ?? []}
        recommendations={recommendations ?? []}
        placeholder="Ask about a stock or your portfolio…"
        title="🤖 Stock Agent (client-side preview)"
      />
      <p className="mt-3 text-center text-xs text-slate-600">
        The RAG-powered agent (<code>portfolio_advisor.agents.stock_agent</code>) requires a backend
        API — this preview reasons over <span className="num">{stocks?.length ?? 0}</span> exported stocks.
      </p>
    </div>
  )
}
