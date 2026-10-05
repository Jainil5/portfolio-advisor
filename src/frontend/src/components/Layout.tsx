import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { Settings } from 'lucide-react'
import { useMeta } from '../api'
import { fmtDate } from '../utils/format'
import SettingsModal from './SettingsModal'

const NAV_GROUPS: { title: string; items: { to: string; icon: string; label: string }[] }[] = [
  {
    title: 'Overview',
    items: [
      { to: '/', icon: '📡', label: 'Screener' },
      { to: '/dashboard', icon: '🏠', label: 'Dashboard' },
      { to: '/portfolio', icon: '💼', label: 'My Portfolio' },
    ],
  },
  {
    title: 'Research',
    items: [
      { to: '/analysis', icon: '📈', label: 'Stock Analysis' },
      { to: '/recommendations', icon: '⭐', label: 'Recommendations' },
    ],
  },
  {
    title: 'AI',
    items: [{ to: '/advisor', icon: '🤖', label: 'AI Advisor' }],
  },
]

export default function Layout() {
  const { data: meta } = useMeta()
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 flex-col border-r border-slate-800/80 bg-panel/60 backdrop-blur lg:flex">
        <div className="flex items-center gap-2.5 px-5 py-6">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-lg shadow-lg shadow-indigo-900/40">
            📈
          </span>
          <div>
            <p className="text-sm font-bold leading-tight text-slate-100">Portfolio Advisor</p>
            <p className="text-[11px] text-slate-500">AI-powered FinTech</p>
          </div>
        </div>

        <nav className="flex-1 space-y-6 overflow-y-auto px-3 pb-6">
          {NAV_GROUPS.map((group) => (
            <div key={group.title}>
              <p className="mb-1.5 px-3 text-[10px] font-bold uppercase tracking-widest text-slate-600">
                {group.title}
              </p>
              <ul className="space-y-0.5">
                {group.items.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.to === '/'}
                      className={({ isActive }) =>
                        `flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors ${
                          isActive
                            ? 'bg-indigo-500/15 font-semibold text-indigo-300'
                            : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                        }`
                      }
                    >
                      <span aria-hidden>{item.icon}</span>
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        <div className="border-t border-slate-800/80 px-5 py-4 text-[11px] text-slate-600">
          <div className="flex items-start justify-between gap-2">
            <div>
              {meta ? (
                <>
                  Dataset: <span className="num text-slate-400">{meta.stocks}</span> stocks ·{' '}
                  <span className="num text-slate-400">{meta.recommendations}</span> recs
                  <br />
                  Updated {fmtDate(meta.data_updated_at)}
                </>
              ) : (
                <>Backend offline — run <code className="text-slate-500">uvicorn backend.api:app --port 8000</code></>
              )}
            </div>
            <button
              onClick={() => setSettingsOpen(true)}
              title="Settings"
              className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-slate-800/70 hover:text-slate-300"
            >
              <Settings size={15} />
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile top nav */}
      <div className="fixed inset-x-0 top-0 z-20 flex items-center gap-1 overflow-x-auto border-b border-slate-800/80 bg-panel/90 px-3 py-2 backdrop-blur lg:hidden">
        {NAV_GROUPS.flatMap((g) => g.items).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `whitespace-nowrap rounded-lg px-3 py-1.5 text-xs ${
                isActive ? 'bg-indigo-500/20 font-semibold text-indigo-300' : 'text-slate-400'
              }`
            }
          >
            {item.icon} {item.label}
          </NavLink>
        ))}
      </div>

      <main className="min-w-0 flex-1 px-5 pb-16 pt-16 lg:ml-60 lg:px-8 lg:pt-8">
        <Outlet />
      </main>

      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
    </div>
  )
}
