import { useState } from 'react'
import { RefreshCw, X } from 'lucide-react'
import { startDataUpdate, useUpdateStatus } from '../api'

const STAGES = ['prices', 'features', 'recommendations', 'news'] as const

export default function SettingsModal({ onClose }: { onClose: () => void }) {
  const [includeNews, setIncludeNews] = useState(true)
  const [jobStarted, setJobStarted] = useState(false)
  const { data: state } = useUpdateStatus(jobStarted)
  const running = state?.status === 'running' || (jobStarted && state == null)
  const done = state?.status === 'done'
  const failed = state?.status === 'error'

  const trigger = async () => {
    setJobStarted(true)
    await startDataUpdate(includeNews)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-2xl border border-slate-800 bg-panel p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-start justify-between">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">Settings</h2>
            <p className="mt-1 text-xs text-slate-500">Dataset management</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-slate-300">
            <X size={16} />
          </button>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4">
          <p className="text-xs font-semibold text-slate-300">Update market data</p>
          <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
            Re-fetches prices & fundamentals for all tracked stocks, then regenerates features, AI scores,
            recommendations and (optionally) per-stock news summaries. Takes several minutes.
          </p>

          <label className="mt-3 flex items-center gap-2 text-xs text-slate-400">
            <input
              type="checkbox"
              name="include_news"
              checked={includeNews}
              onChange={(e) => setIncludeNews(e.target.checked)}
              disabled={running}
              className="accent-indigo-500"
            />
            Include news refresh (RSS + LLM summaries — slowest step)
          </label>

          <button
            onClick={trigger}
            disabled={running}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-900/40 hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw size={14} className={running ? 'animate-spin' : ''} />
            {running ? 'Update running…' : done ? 'Update again' : 'Update Data'}
          </button>

          {(running || state) && (
            <div className="mt-4">
              <div className="flex gap-1.5">
                {STAGES.map((stage) => {
                  const idx = STAGES.indexOf(stage)
                  const currentIdx = state?.stage ? STAGES.indexOf(state.stage as (typeof STAGES)[number]) : done || failed ? STAGES.length : -1
                  const isDone = currentIdx > idx || done
                  const isCurrent = state?.stage === stage
                  return (
                    <div key={stage} className="flex-1">
                      <div
                        className={`h-1.5 rounded-full ${
                          isDone ? 'bg-emerald-500' : isCurrent ? 'animate-pulse bg-indigo-400' : failed && currentIdx === idx ? 'bg-rose-500' : 'bg-slate-700'
                        }`}
                      />
                      <p className={`mt-1 text-center text-[9px] uppercase ${isCurrent ? 'text-indigo-300' : 'text-slate-600'}`}>
                        {stage}
                      </p>
                    </div>
                  )
                })}
              </div>
              {state?.log && (
                <ul className="mt-3 max-h-36 space-y-1 overflow-y-auto rounded-lg bg-black/30 p-2.5">
                  {state.log.slice(-8).map((line, i) => (
                    <li key={i} className="num text-[10px] text-slate-500">{line}</li>
                  ))}
                </ul>
              )}
              {failed && <p className="mt-2 text-[11px] text-rose-400">Failed: {state?.error}</p>}
              {done && (
                <button
                  onClick={() => window.location.reload()}
                  className="mt-2 w-full rounded-lg bg-emerald-500/15 py-2 text-xs font-bold text-emerald-400 hover:bg-emerald-500/25"
                >
                  ✓ Data updated — reload dashboard
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
