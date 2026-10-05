# TradingView UI Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the frontend into a TradingView-style terminal: customizable portfolio-analysis Home, ticker-driven Screener with integrated stock workspace, live BSE News page, all on a shared dark token theme.

**Architecture:** FastAPI (`src/backend/api`) serves CSV/DuckDB data; React 19 + Vite + Tailwind v4 frontend (`src/frontend`) consumes it. A widget registry + react-grid-layout (fallback: custom HTML5-drag grid) powers the Home page. The stock workspace is one component reused by the Screener split view and `/stock/:id`.

**Tech Stack:** FastAPI, DuckDB (`backend/news/db.py`), pydantic v2, pytest (TestClient), react-grid-layout, lightweight-charts, lucide-react, Tailwind v4 `@theme`.

**Spec:** `docs/superpowers/specs/2026-10-05-tradingview-ui-overhaul-design.md`

## Global Constraints

- Python 3.11; imports absolute (`from backend...`); editable install (`pip install -e .`).
- Run pytest with the repo venv: `venv/bin/python -m pytest tests -q` (from repo root).
- Frontend checks: `cd src/frontend && npx tsc --noEmit && npm run build` must stay clean.
- Theme tokens (exact values): base `#0b0f18`, panel `#131722`, elevated `#182230`, hairline `rgba(140,160,185,0.18)`, up `#16C784`, down `#EA3943`, accent `#2962FF`.
- Never fabricate data: P/E, EPS, Dividend Yield are NOT in the CSVs; no intraday/1D range.
- React 19 — any new npm dependency must install without a peer conflict (check `npm info <pkg> peerDependencies` first).
- Commit after every task.

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/backend/api/news.py` | modify | add `GET /api/bse-news`, `POST /api/bse-news` |
| `tests/test_bse_news_api.py` | create | endpoint tests (filters, ingest, validation) |
| `src/frontend/src/index.css` | modify | TradingView theme tokens |
| `src/frontend/src/components/ui.tsx` | modify | restyle primitives; add `Segmented`, `Button` |
| `src/frontend/src/api.ts` | modify | `useBseNews()` hook |
| `src/frontend/src/components/StockWorkspace.tsx` | create | chart + market info + technicals + AI analysis + news + about for one stock |
| `src/frontend/src/pages/StockPage.tsx` | modify | thin route wrapper around StockWorkspace |
| `src/frontend/src/pages/Screener.tsx` | modify | `/screener`: search + universe table + split-view workspace |
| `src/frontend/src/widgets/registry.tsx` | create | widget catalog (id, title, default layout, component) |
| `src/frontend/src/widgets/*.tsx` | create | 7 Home widgets |
| `src/frontend/src/pages/Home.tsx` | create | widget grid, edit mode, localStorage persistence |
| `src/frontend/src/pages/BseNews.tsx` | create | live BSE announcements feed page |
| `src/frontend/src/hooks/useLocalStorage.ts` | create | persisted state with malformed-JSON fallback |
| `src/frontend/src/App.tsx` | modify | new routes + redirects |
| `src/frontend/src/components/Layout.tsx` | modify | new nav order |
| `src/frontend/src/pages/Portfolio.tsx`, `Recommendations.tsx`, `Advisor.tsx`, `components/SettingsModal.tsx` | modify | adopt theme tokens (class swaps only) |
| delete | `src/frontend/src/pages/Dashboard.tsx`, `src/frontend/src/pages/StockAnalysis.tsx` | absorbed into Home widgets / Screener workspace |
| `README.md` | modify | document page order + endpoints |

---

### Task 1: `GET /api/bse-news` endpoint

**Files:**
- Modify: `src/backend/api/news.py`
- Test: `tests/test_bse_news_api.py`

**Interfaces:**
- Consumes: `backend.news.db` (`COLUMNS`, `connect`), existing `_rows`/`_serialize` helpers in `news.py`.
- Produces: `GET /api/bse-news?search=&days=&hide_routine=&limit=` → JSON array of announcement dicts with keys `id, scrip_code, symbol, company_name, headline, subject, category, subcategory, published_at, pdf_url, is_critical, is_routine` (ISO strings for timestamps). Task 4 (frontend hook) and Task 8 (BseNews page) consume it.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bse_news_api.py`. It seeds a **temporary** DuckDB so the real `data/news.duckdb` is untouched (fixture pattern: monkeypatch the module-level path that `db.connect` falls back to):

```python
"""Tests for the /api/bse-news endpoints (temp DuckDB, never the real data file)."""

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.news import config as news_config
from backend.news import db as news_db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "news.duckdb"
    monkeypatch.setattr(news_config, "NEWS_DB_FILE", str(db_file))
    now = dt.datetime(2026, 10, 5, 12, 0)

    def seed(**over):
        row = {c: None for c in news_db.COLUMNS}
        row.update(over, scrip_code=over.get("scrip_code", "0"), fetched_at=now)
        return row

    news_db.upsert(
        [
            seed(
                id="1", symbol="TATASTEEL", company_name="Tata Steel",
                headline="Board approves capex", subject="Board Meetings",
                category="Policy", published_at=now, pdf_flag=1,
                is_critical=True, is_routine=False,
            ),
            seed(
                id="2", symbol="INFY", company_name="Infosys",
                headline="Compliance certificate submitted", subject="Compliance",
                published_at=now - dt.timedelta(days=10), pdf_flag=0,
                is_critical=False, is_routine=True,
            ),
        ],
        path=str(db_file),
    )
    with TestClient(app) as c:
        yield c


def test_bse_news_returns_all_newest_first(client):
    body = client.get("/api/bse-news").json()
    assert [r["id"] for r in body] == ["1", "2"]


def test_bse_news_search_matches_symbol_and_company(client):
    assert {r["id"] for r in client.get("/api/bse-news", params={"search": "tata"}).json()} == {"1"}
    assert {r["id"] for r in client.get("/api/bse-news", params={"search": "infy"}).json()} == {"2"}


def test_bse_news_days_filter(client):
    body = client.get("/api/bse-news", params={"days": 7}).json()
    assert [r["id"] for r in body] == ["1"]


def test_bse_news_hide_routine(client):
    body = client.get("/api/bse-news", params={"hide_routine": "true"}).json()
    assert [r["id"] for r in body] == ["1"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/python -m pytest tests/test_bse_news_api.py -v`
Expected: FAIL — 404 responses (endpoint does not exist) or fixture errors.

- [ ] **Step 3: Implement the endpoint**

In `src/backend/api/news.py`, add imports at the top (`from datetime import datetime, timedelta`) and the route below `get_news`:

```python
@router.get("/bse-news")
def get_bse_news(search: str | None = None, days: int = 30, hide_routine: bool = False, limit: int = 50):
    """Live BSE feed: newest-first announcements with terminal-style filters."""
    conds, params = [], []
    if search and search.strip():
        s = f"%{search.strip()}%"
        conds.append("(UPPER(symbol) LIKE ? OR company_name ILIKE ? OR headline ILIKE ?)")
        params += [s.upper(), s, s]
    if days > 0:
        conds.append("published_at >= ?")
        params.append(datetime.now() - timedelta(days=min(days, 365)))
    if hide_routine:
        conds.append("COALESCE(is_routine, FALSE) = FALSE")
    where = f"WHERE {' AND '.join(conds)}" if conds else ""
    rows = _rows(
        f"SELECT {COLUMN_SQL} FROM announcements {where} ORDER BY published_at DESC NULLS LAST",
        params,
        limit=min(max(limit, 1), 200),
    )
    return _serialize(rows)
```

Note: `_rows` already returns `[]` when the DB file is missing (`FileNotFoundError`). `days=0` disables the window. The existing `GET /api/news` stays untouched for the stock-page widget.

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_bse_news_api.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Full suite + commit**

Run: `venv/bin/python -m pytest tests -q` → all pass.

```bash
git add src/backend/api/news.py tests/test_bse_news_api.py
git commit -m "Add GET /api/bse-news filtered BSE announcements endpoint"
```

---

### Task 2: `POST /api/bse-news` ingest endpoint

**Files:**
- Modify: `src/backend/api/news.py`
- Test: `tests/test_bse_news_api.py`

**Interfaces:**
- Consumes: `backend.news.db.upsert(rows)` (dedupes on `id`, updates `UPDATABLE` fields), `db.COLUMNS`.
- Produces: `POST /api/bse-news` body = single announcement or list; success → `{"inserted": int, "received": int}`; missing required fields → 422. Required: `company_name`, `headline`, `published_at` (ISO 8601). `id` optional — generated deterministically (`sha1(f"{scrip_code}|{published_at}|{headline}")[:16]`) when absent so repeat pushes dedupe.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_bse_news_api.py` (reuses the `client` fixture):

```python
def test_post_bse_news_ingests_and_dedupes(client):
    payload = {
        "scrip_code": "777",
        "symbol": "ABC",
        "company_name": "Acme Corp",
        "headline": "Acme wins 500cr order",
        "subject": "Orders",
        "published_at": "2026-10-05T09:30:00",
        "is_routine": False,
    }
    first = client.post("/api/bse-news", json=payload)
    assert first.status_code == 200
    assert first.json()["inserted"] == 1
    second = client.post("/api/bse-news", json=payload)
    assert second.status_code == 200
    assert second.json()["inserted"] == 0  # same id -> deduped
    body = client.get("/api/bse-news", params={"search": "acme"}).json()
    assert len(body) == 1


def test_post_bse_news_list(client):
    rows = [
        {"company_name": f"Fiz {i}", "headline": f"Q{i} results", "published_at": "2026-10-04T10:00:00"}
        for i in range(3)
    ]
    res = client.post("/api/bse-news", json=rows)
    assert res.status_code == 200
    assert res.json() == {"inserted": 3, "received": 3}


def test_post_bse_news_validation(client):
    assert client.post("/api/bse-news", json={"company_name": "No Headline Co"}).status_code == 422
    assert client.post(
        "/api/bse-news",
        json={"company_name": "X", "headline": "Y", "published_at": "not-a-date"},
    ).status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/python -m pytest tests/test_bse_news_api.py -v -k post`
Expected: FAIL — 404/405 (no POST route).

- [ ] **Step 3: Implement the ingest**

In `src/backend/api/news.py` add imports (`import hashlib`, `from fastapi import APIRouter, HTTPException` — extend existing import — and `from pydantic import BaseModel, field_validator`) plus:

```python
class AnnouncementIn(BaseModel):
    id: str | None = None
    scrip_code: str | None = None
    symbol: str | None = None
    company_name: str
    headline: str
    subject: str | None = None
    category: str | None = None
    subcategory: str | None = None
    published_at: str
    attachment_name: str | None = None
    pdf_flag: int = 0
    pdf_url: str | None = None
    is_critical: bool = False
    is_routine: bool = False

    @field_validator("published_at")
    @classmethod
    def _iso(cls, v: str) -> str:
        datetime.fromisoformat(v)  # raises -> FastAPI 422
        return v

    def to_row(self) -> dict:
        row = {c: None for c in db.COLUMNS}
        row.update(
            id=self.id
            or hashlib.sha1(f"{self.scrip_code}|{self.published_at}|{self.headline}".encode()).hexdigest()[:16],
            scrip_code=self.scrip_code or "",
            symbol=self.symbol,
            company_name=self.company_name,
            headline=self.headline,
            subject=self.subject,
            category=self.category,
            subcategory=self.subcategory,
            published_at=datetime.fromisoformat(self.published_at),
            attachment_name=self.attachment_name,
            pdf_flag=self.pdf_flag,
            pdf_url=self.pdf_url,
            is_critical=self.is_critical,
            is_routine=self.is_routine,
            fetched_at=datetime.now(),
        )
        return row


@router.post("/bse-news")
def post_bse_news(item: AnnouncementIn | list[AnnouncementIn]):
    """Ingest announcements (single or batch) into the same DuckDB the feed reads."""
    items = item if isinstance(item, list) else [item]
    try:
        inserted = db.upsert([a.to_row() for a in items])
    except Exception as exc:  # duckdb write-lock / IO failure
        raise HTTPException(status_code=503, detail=f"News store unavailable: {exc}")
    return {"inserted": inserted, "received": len(items)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_bse_news_api.py -v`
Expected: PASS (all GET + POST tests).

- [ ] **Step 5: Full suite + commit**

Run: `venv/bin/python -m pytest tests -q` → all pass.

```bash
git add src/backend/api/news.py tests/test_bse_news_api.py
git commit -m "Add POST /api/bse-news announcement ingest with dedupe and validation"
```

---

### Task 3: Theme tokens + restyled UI primitives

**Files:**
- Modify: `src/frontend/src/index.css`
- Modify: `src/frontend/src/components/ui.tsx`
- Create: `src/frontend/src/hooks/useLocalStorage.ts` (needed by Home + reused by Screener)

**Interfaces:**
- Produces: Tailwind color utilities `bg-surface|bg-panel|bg-elevated|border-hairline|text-up|bg-up/15|text-down|bg-down/15|text-accent|bg-accent/15|ring-accent/40` (via `@theme`); components `Card`, `Metric`, `Badge`, `TrendPill`, `PnL`, `EmptyState`, `Spinner`, `PageHeader` (same props as before), plus new `Segmented<T>({ options: {value: T, label: string}[], value: T, onChange: (v: T) => void, className?: string })`; hook `useLocalStorage<T>(key, initial): [T, Dispatch<SetStateAction<T>>]`.
- Consumed by: every later task.

- [ ] **Step 1: Replace the `@theme` block in `index.css`**

```css
@theme {
  --font-sans: "Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  --color-surface: #0b0f18;
  --color-panel: #131722;
  --color-elevated: #182230;
  --color-hairline: rgba(140, 160, 185, 0.18);
  --color-up: #16c784;
  --color-down: #ea3943;
  --color-accent: #2962ff;
}
```

Keep everything else (`html`, `body`, `.num`, scrollbars, `.animate-rise`). Update `.focus-ring` ring color to `--color-accent` (`focus-visible:ring-accent`) and offset `#0b0f18`.

- [ ] **Step 2: Restyle `ui.tsx` primitives**

Global swap rules (apply to every literal in this file): `border-slate-800/80` → `border-hairline`; `bg-panel/80` → `bg-panel`; `rounded-2xl` → `rounded-lg` (TV is dense); `text-emerald-400` → `text-up`; `text-rose-400` → `text-down`; `bg-emerald-500/15` → `bg-up/15`; `bg-rose-500/15` → `bg-down/15`; `indigo` accent classes → `accent`; `backdrop-blur` → drop; `shadow-lg shadow-black/20` → `border border-hairline bg-panel`. Specifics:

- `Card`: `className="animate-rise rounded-lg border border-hairline bg-panel p-4"`; header title stays uppercase 11px `text-slate-500`, radius of the whole widget shell is owned by the widget wrapper, not Card.
- `Metric`: drop the gradient; emphasize = `border-accent/40 bg-elevated`; delta colors `text-up`/`text-down`.
- `TONES`: `buy: 'bg-up/15 text-up ring-up/30'`, `sell: 'bg-down/15 text-down ring-down/30'`, hold/neutral/info unchanged (amber/slate/sky still fine).
- `TrendPill`: replace emoji with colored triangle characters — `▲ Bullish` (`text-up`) / `▼ Bearish` (`text-down`).
- `PnL`: `text-up` / `text-down` / `text-slate-400`.
- `Spinner`: `border-t-accent`.
- Add:

```tsx
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  className = '',
}: {
  options: { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
  className?: string
}) {
  return (
    <div className={`flex items-center gap-0.5 rounded-md border border-hairline bg-surface/60 p-0.5 ${className}`}>
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={`rounded px-2.5 py-1 text-[11px] font-semibold transition-colors ${
            value === o.value ? 'bg-accent/20 text-accent' : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Create `src/frontend/src/hooks/useLocalStorage.ts`**

```ts
import { useEffect, useState } from 'react'

/** State persisted to localStorage; malformed JSON falls back to `initial`. */
export function useLocalStorage<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key)
      return raw ? (JSON.parse(raw) as T) : initial
    } catch {
      return initial
    }
  })
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch {
      /* storage full/blocked: keep in-memory state */
    }
  }, [key, value])
  return [value, setValue] as const
}
```

- [ ] **Step 4: Verify**

Run: `cd src/frontend && npx tsc --noEmit && npm run build` → clean. (Visual pass happens in Task 6 screenshots — pages still use old literals until Task 7/8.)

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/index.css src/frontend/src/components/ui.tsx src/frontend/src/hooks/useLocalStorage.ts
git commit -m "Adopt TradingView dark theme tokens and restyle UI primitives"
```

---

### Task 4: `useBseNews()` hook + page-shell route/nav swap

**Files:**
- Modify: `src/frontend/src/api.ts`
- Modify: `src/frontend/src/App.tsx`
- Modify: `src/frontend/src/components/Layout.tsx`

**Interfaces:**
- Consumes: Task 1 GET endpoint; existing `useJson<T>(path, pollMs)`.
- Produces: `useBseNews(opts: { search?: string; days?: number; hideRoutine?: boolean; limit?: number; pollMs?: number }): Json<NewsItem[]>` — same `NewsItem` shape already exported from `api.ts` (add `is_routine: boolean | null; subject: string | null` to it). New routes: `/` → Home (Task 6 file, stub for now), `/screener`, `/bse-news` (Task 8 file, stub), redirects `/dashboard → /`, `/analysis → /screener`.

- [ ] **Step 1: Add the hook**

In `api.ts`, extend `NewsItem` with `is_routine: boolean | null` and append:

```ts
export function useBseNews(opts: {
  search?: string
  days?: number
  hideRoutine?: boolean
  limit?: number
  pollMs?: number
} = {}): Json<NewsItem[]> {
  const { search, days = 30, hideRoutine = false, limit = 50, pollMs = 0 } = opts
  const params = new URLSearchParams({ days: String(days), hide_routine: String(hideRoutine), limit: String(limit) })
  if (search) params.set('search', search)
  return useJson<NewsItem[]>(`/api/bse-news?${params.toString()}`, pollMs)
}
```

- [ ] **Step 2: Stub pages so routes compile**

Create `src/frontend/src/pages/Home.tsx` and `src/frontend/src/pages/BseNews.tsx` each as `export default function Home() { return <PageHeader title="Portfolio Desk" subtitle="Widgets coming in this release" /> }`-style placeholders (replaced in Tasks 6/8).

- [ ] **Step 3: Swap routes in `App.tsx`**

```tsx
<Routes>
  <Route element={<Layout />}>
    <Route path="/" element={<Home />} />
    <Route path="/screener" element={<Screener />} />
    <Route path="/portfolio" element={<Portfolio />} />
    <Route path="/stock/:stockId" element={<StockPage />} />
    <Route path="/recommendations" element={<Recommendations />} />
    <Route path="/advisor" element={<Advisor />} />
    <Route path="/bse-news" element={<BseNews />} />
    <Route path="/dashboard" element={<Navigate to="/" replace />} />
    <Route path="/analysis" element={<Navigate to="/screener" replace />} />
    <Route path="/market" element={<Navigate to="/screener" replace />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Route>
</Routes>
```

(Remove the `Dashboard`/`StockAnalysis` imports — those pages still exist until Task 7 but are no longer routed; their files are deleted in Task 7 when their features move into widgets/workspace.)

- [ ] **Step 4: Reorder nav in `Layout.tsx`**

```tsx
const NAV_GROUPS = [
  {
    title: 'Trade',
    items: [
      { to: '/', icon: '🏠', label: 'Home' },
      { to: '/screener', icon: '📡', label: 'Screener' },
    ],
  },
  {
    title: 'Portfolio',
    items: [
      { to: '/portfolio', icon: '💼', label: 'My Portfolio' },
      { to: '/recommendations', icon: '⭐', label: 'Recommendations' },
    ],
  },
  {
    title: 'Live',
    items: [
      { to: '/bse-news', icon: '📰', label: 'BSE News' },
      { to: '/advisor', icon: '🤖', label: 'AI Agent' },
    ],
  },
]
```

Restyle the active nav state to the accent token: `bg-accent/15 font-semibold text-accent` / hover `text-slate-200`; brand mark `from-accent to-[#1e4fd6]`.

- [ ] **Step 5: Verify + commit**

`cd src/frontend && npx tsc --noEmit && npm run build` → clean.

```bash
git add src/frontend/src/api.ts src/frontend/src/App.tsx src/frontend/src/components/Layout.tsx src/frontend/src/pages/Home.tsx src/frontend/src/pages/BseNews.tsx
git commit -m "Add BSE news hook and swap routes/nav to Home-first TradingView terminal order"
```

---

### Task 5: StockWorkspace component + Screener split view

**Files:**
- Create: `src/frontend/src/components/StockWorkspace.tsx`
- Modify: `src/frontend/src/pages/StockPage.tsx`
- Modify: `src/frontend/src/pages/Screener.tsx`

**Interfaces:**
- Consumes: `useStocks/useHistory/useNews/useAnalysis`, `TvChart`, `rsi`/`rsiLabel` (market/indicators), `suggestionForScore` (utils/finance), `Segmented` (Task 3).
- Produces: `StockWorkspace({ stockId, onClose? }: { stockId: number; onClose?: () => void })` — full detail panel (chart + market info + technicals + AI analysis + news + about). `/stock/:stockId` renders it; Screener renders it in the right pane. Screener keeps its own exports (no consumers).

- [ ] **Step 1: Move the detail UI into `StockWorkspace.tsx`**

Move `Stat`, `AnalysisBox`, `RANGES`, and the whole render body of the current `StockPage` into a new `StockWorkspace.tsx`. Signature:

```tsx
export default function StockWorkspace({ stockId, onClose }: { stockId: number; onClose?: () => void }) {
  const { data: stocks, loading } = useStocks()
  const [range, setRange] = useState('1y')
  const { data: candles, loading: candlesLoading } = useHistory(stockId, range)
  const [toggles, setToggles] = useState<ChartToggles>({ ma20: true, ma50: true, rsi: false, logScale: false })
  const stock = useMemo(() => (stocks ?? []).find((s) => s.stock_id === stockId), [stocks, stockId])
  const { data: news } = useNews(stock ? stock.ticker.replace('.NS', '') : null, 8)
  ...
}
```

Behavior changes while moving (keep everything else as-is):
- If `onClose` is provided render a `✕` button (lucide `X`) in the header instead of the `<Back>` link.
- Timeframe row becomes `<Segmented options={RANGES.map(([v, l]) => ({ value: v, label: l }))} value={range} onChange={setRange} />`; indicator toggles stay as individual buttons but adopt `bg-accent/20 text-accent` active state (use `Segmented` for them too if trivial — do not add new component APIs).
- Apply Task 3's literal-swap rules (`indigo→accent`, `emerald-400→up`, `rose-400→down`, `border-slate-800/80→border-hairline`).
- Google News panel: under the BSE `News` card add a `Google News` card. In Task 4 Step 1, also export a summary hook from `api.ts`:

```ts
export interface NewsSummary { ticker: string; company?: string; headlines: string[]; summary: string | null }
export const useGoogleNewsSummary = (ticker: string | null) =>
  useJson<NewsSummary>(ticker ? `/api/news/summary/${encodeURIComponent(ticker)}` : null)
```

Render `headlines` (list, newest first) + `summary` paragraph; empty state "Run Settings → Update Data to refresh news."

- [ ] **Step 2: Make `StockPage.tsx` a thin wrapper**

```tsx
export default function StockPage() {
  const { stockId } = useParams()
  const id = Number(stockId)
  const { data: stocks, loading } = useStocks()
  if (loading) return <Spinner label="Loading…" />
  const stock = (stocks ?? []).find((s) => s.stock_id === id)
  if (!stock)
    return (
      <EmptyState icon="🔍" title="Stock not found" message="This id isn't in the current dataset." />
    )
  return <StockWorkspace stockId={id} />
}
```

- [ ] **Step 3: Rework `Screener.tsx` into `/screener`**

- Delete the three summary Cards (movers/sectors/news) — Home widgets own that content now (Task 6). Keep `PctCell` and the universe table exactly as-is.
- Promote the search to a sticky toolbar above the table: same `query` state (matches ticker or company name), add `useEffect` so ArrowDown/ArrowUp move a `highlighted` row index and Enter selects it.
- Split view:

```tsx
const [selected, setSelected] = useState<number | null>(null)
const wide = window.matchMedia('(min-width: 1440px)').matches
```

Wrap in `flex` layout: table pane `w-full shrink-0 xl:w-[440px]` (hide table when `wide && selected` is false? no — always show table when wide; workspace shows `EmptyState "Select a stock"` when nothing chosen). On row click: `wide ? setSelected(s.stock_id) : navigate(`/stock/${s.stock_id}`)`. Workspace pane: `<StockWorkspace stockId={selected} onClose={() => setSelected(null)} />` in a scrollable `min-w-0 flex-1 border-l border-hairline pl-4`.
- Add `PageHeader title="Screener" subtitle="Type a ticker or company — charts, analysis, fundamentals and news in one workspace"`.

- [ ] **Step 4: Verify**

`cd src/frontend && npx tsc --noEmit && npm run build` → clean. Manual: dev server, open `/screener`, select TCS row → workspace renders chart; `/stock/<id>` still works.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/components/StockWorkspace.tsx src/frontend/src/pages/StockPage.tsx src/frontend/src/pages/Screener.tsx
git commit -m "Add stock workspace component and ticker-driven screener split view"
```

---

### Task 6: Home widget dashboard (registry, grid, edit mode)

**Files:**
- Create: `src/frontend/src/widgets/registry.tsx`
- Create: `src/frontend/src/widgets/KpisWidget.tsx`, `BestWorstWidget.tsx`, `SectorAllocationWidget.tsx`, `AiSignalsWidget.tsx`, `MoversWidget.tsx`, `BseNewsWidget.tsx`, `HoldingsWidget.tsx`
- Create: `src/frontend/src/pages/Home.tsx` (replace Task 4 stub)
- Modify: `src/frontend/package.json` (add react-grid-layout)
- Test: `tests/test_api.py` unaffected; frontend verified by tsc/build + browser.

**Interfaces:**
- Consumes: all `api.ts` hooks, `useBseNews` (Task 4), `buildPositions`/`portfolioTotals` (utils/finance), `useLocalStorage` (Task 3), primitives (Task 3).
- Produces: `WidgetDef { id: string; title: string; defaultLayout: { x: number; y: number; w: number; h: number }; Component: () => JSX.Element }` and `WIDGETS: WidgetDef[]`. localStorage key `home.layout.v1` stores `{ visible: string[]; layouts: Record<string, {x,y,w,h}> }`.

- [ ] **Step 1: Install the grid library and probe React 19 compat**

Run: `npm info react-grid-layout version peerDependencies`, then `npm install react-grid-layout`. If npm errors on peer deps with React 19, or `npx tsc --noEmit` cannot resolve types (no bundled types), switch to the documented fallback (Step 3b) — decide here and record the choice in the commit message.

- [ ] **Step 2: Write the 7 widgets**

Each file exports one component, fetches its own data, renders loading/error inline, and never throws upward (spec §6). Content:

- `KpisWidget` — 4 `Metric` tiles: Investment / Current Value / Profit±delta / Positions (from `useTransactions`+`useStocks`+`buildPositions`+`portfolioTotals`, same math as today's Dashboard.tsx:57-67).
- `BestWorstWidget` — two columns "Best performers" / "Weakest" from positions sorted by `returnPct` (top 3 / bottom 3, colored `text-up`/`text-down`); falls back to universe `return_30d` when portfolio is empty. Row click → `navigate('/stock/'+stockId)`.
- `SectorAllocationWidget` — the PieChart block from Dashboard.tsx:24-33/104-120 verbatim, but `PIE_COLORS = ['#2962FF','#16C784','#F7A600','#EA3943','#9C27B0','#00BCD4','#8BC34A','#FF5722']` and tooltip surface `#131722`/`border-hairline`.
- `AiSignalsWidget` — top 5 by `score` (Dashboard.tsx:35-38 style), rows link to `/screener` with `?stock=<id>`; link target for now `/stock/<id>`.
- `MoversWidget` — `useMovers()` gainers/losers lists (Screener.tsx `MoverList` pattern), row click → `/stock/:id`.
- `BseNewsWidget` — `useBseNews({ days: 3, limit: 8 })`; headline + symbol + `fmtDate`, links to `/bse-news`.
- `HoldingsWidget` — positions list: name, value `fmtINR(currentValue)`, `PnL(profit, returnPct)`.

- [ ] **Step 3a: `registry.tsx` + Home with react-grid-layout**

```tsx
// widgets/registry.tsx
import type { ReactNode } from 'react'
import KpisWidget from './KpisWidget'
// ... other imports
export interface WidgetDef {
  id: string
  title: string
  defaultLayout: { x: number; y: number; w: number; h: number }
  Component: () => ReactNode
}
const ROW = 64 // keep in sync with Home rowHeight
export const WIDGETS: WidgetDef[] = [
  { id: 'kpis', title: 'Portfolio KPIs', defaultLayout: { x: 0, y: 0, w: 12, h: 2 }, Component: KpisWidget },
  { id: 'holdings', title: 'My Holdings', defaultLayout: { x: 0, y: 2, w: 7, h: 5 }, Component: HoldingsWidget },
  { id: 'best-worst', title: 'Best & Weakest Performers', defaultLayout: { x: 7, y: 2, w: 5, h: 5 }, Component: BestWorstWidget },
  { id: 'sector', title: 'Sector Allocation', defaultLayout: { x: 7, y: 7, w: 5, h: 6 }, Component: SectorAllocationWidget },
  { id: 'signals', title: 'Top AI Signals', defaultLayout: { x: 0, y: 7, w: 4, h: 6 }, Component: AiSignalsWidget },
  { id: 'movers', title: 'Market Movers', defaultLayout: { x: 4, y: 7, w: 3, h: 6 }, Component: MoversWidget },
  { id: 'bse-news', title: 'Latest BSE News', defaultLayout: { x: 0, y: 13, w: 12, h: 4 }, Component: BseNewsWidget },
]
```

`Home.tsx`: `useLocalStorage('home.layout.v1', { visible: WIDGETS.map(w => w.id), layouts: Object.fromEntries(WIDGETS.map(w => [w.id, w.defaultLayout])) })`; render `<ReactGridLayout className="layout" layout={items} cols={12} rowHeight={ROW} isDraggable={editing} isResizable={editing} draggableHandle=".widget-drag" onLayoutChange={...}>` with each widget wrapped in a panel: header strip (drag handle icon when editing, title, remove ✕) + `<w.Component />` + per-widget error boundary. Edit mode toolbar (PageHeader `right`): `Segmented` Edit/Done? no — a `Button`-style toggle "Edit layout", "Add widget" popover (unchecked ids from `WIDGETS`), "Reset layout" (writes defaults). Import `react-grid-layout/css/styles.css` and `react-resizable/css/styles.css`; add `width={window.innerWidth - sidebar 240 - padding}` via `useRef` container + ResizeObserver (RGL needs explicit width).

- [ ] **Step 3b: Fallback (only if Step 1 failed)**

Custom `Home.tsx` grid: CSS `grid grid-cols-12 gap-4`, each widget card takes `col-span-{w}` from a size cycle button (`w: 4|6|12`), HTML5 `draggable` attributes on the card header reorder the flat `visible` array via `dragstart/dragover/drop` indexes (12 lines); persistence identical. No resize heights.

- [ ] **Step 4: Verify**

`npx tsc --noEmit && npm run build` clean. Browser (new tab, don't hijack user's Chrome tab): `/` renders grid; Edit → drag a widget, resize, remove `Sector Allocation`, add it back, reload → layout persisted; widget with backend down shows inline unavailable state, grid still renders others.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/package.json src/frontend/package-lock.json src/frontend/src/widgets src/frontend/src/pages/Home.tsx
git commit -m "Add customizable portfolio-analysis home with drag-resize widget grid"
```

---

### Task 7: Absorb old Dashboard/StockAnalysis, delete retired pages

**Files:**
- Delete: `src/frontend/src/pages/Dashboard.tsx`, `src/frontend/src/pages/StockAnalysis.tsx`
- Modify: `src/frontend/src/App.tsx` (imports already removed in Task 4 — verify none remain)
- Modify: `src/frontend/src/components/ChatPanel.tsx` (literal swap rules only; it's used by Advisor)

**Interfaces:**
- Consumes: Task 5 (StockAnalysis' compare/analysis flow now lives in Screener+Workspace), Task 6 (Dashboard content now in widgets).
- Produces: nothing new; removes dead code.

- [ ] **Step 1: Check nothing still imports the deleted pages**

Run: `grep -rn "pages/Dashboard\|pages/StockAnalysis" src/frontend/src` → must be empty (App.tsx import removed in Task 4).
Check unique StockAnalysis features not in the workspace: if its cross-stock compare UI is genuinely absent elsewhere, port the compare table into `Screener.tsx` as a second tab "Compare" (multi-select via checkbox column) — otherwise delete.

- [ ] **Step 2: Delete files + token swap in ChatPanel**

`git rm src/frontend/src/pages/Dashboard.tsx src/frontend/src/pages/StockAnalysis.tsx`
ChatPanel: apply Task 3 literal-swap rules; replace `useNews` list (if shown) with `useBseNews({ days: 7, limit: 10 })`.

- [ ] **Step 3: Verify + commit**

`npx tsc --noEmit && npm run build` clean; `/advisor` renders chat, `/dashboard` redirect works.

```bash
git add -A src/frontend
git commit -m "Absorb Dashboard and StockAnalysis pages into home widgets and screener workspace"
```

---

### Task 8: Live BSE News page

**Files:**
- Create: `src/frontend/src/pages/BseNews.tsx` (replace Task 4 stub)

**Interfaces:**
- Consumes: `useBseNews` (Task 4), `Segmented`, `Badge`, `Card`, `EmptyState`, `fmtDate`.

- [ ] **Step 1: Implement the page**

```tsx
export default function BseNews() {
  const [search, setSearch] = useState('')
  const [days, setDays] = useState('7')
  const [hideRoutine, setHideRoutine] = useState(false)
  const { data, loading, error } = useBseNews({ search: search.trim() || undefined, days: Number(days), hideRoutine, limit: 100, pollMs: 30_000 })
  ...
}
```

Toolbar under `PageHeader title="Live BSE News"`: debounced search input (300 ms), `Segmented` days `1W/1M/3M` (values `7/30/90`), hide-routine toggle (styled `Segmented` pair On/Off). Feed: one row per announcement — left rail colored by `is_critical ? 'bg-down' : 'bg-accent'` (2px border-l), headline (`subject` fallback) in `text-slate-200`, meta line `symbol · company · category · fmtDate(published_at)`, `Badge tone='neutral'` "routine" when `is_routine`, `pdf_url` link "Filing ↗" (target `_blank` rel `noreferrer`). Live dot: `● Live` with `animate-pulse text-up` + last-refresh time. Error → inline EmptyState; empty → "No filings match — run Settings → Update Data or POST /api/bse-news".

- [ ] **Step 2: Verify**

`tsc --noEmit && npm run build` clean. Browser: `/bse-news` shows seeded real data; search filters (client types → refetch), toggle hide-routine changes result count, poll fires every 30s (Network tab).

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/pages/BseNews.tsx
git commit -m "Add live BSE news feed page with ticker search and routine-filing filters"
```

---

### Task 9: Theme adoption sweep on remaining pages + README

**Files:**
- Modify: `src/frontend/src/pages/Portfolio.tsx`, `Recommendations.tsx`, `Advisor.tsx`, `components/SettingsModal.tsx`, `components/HoldingsTable.tsx`

**Interfaces:**
- Consumes: Task 3 tokens/primitives.

- [ ] **Step 1: Mechanical literal swap**

Apply Task 3 rules to these five files (`indigo→accent`, `emerald-500/15|emerald-400→up`, `rose-400/500/15→down`, `border-slate-800/80→border-hairline`, `rounded-2xl→rounded-lg`, `bg-panel/80→bg-panel`, drop `backdrop-blur`). No structural changes — SettingsModal keeps its 4-stage progress bar; recolor stage-done `bg-up`, current `bg-accent animate-pulse`, failed `bg-down`.

- [ ] **Step 2: Verify each route in browser**

`/portfolio`, `/recommendations`, `/advisor`, Settings modal — screenshots of each, no leftover indigo (`grep -rn "indigo\|emerald\|rose-" src/frontend/src --include=*.tsx` should return only SettingsModal-free results; zero matches expected outside TvChart comment lines).

- [ ] **Step 3: README page list**

Update the frontend section: routes table (Home widget desk / Screener / My Portfolio / Recommendations / AI Agent / BSE News), document `GET/POST /api/bse-news`, note `home.layout.v1` persistence.

- [ ] **Step 4: Commit**

```bash
git add src/frontend README.md
git commit -m "Apply TradingView theme across remaining pages and document new routes"
```

---

### Task 10: Full verification pass

- [ ] **Step 1:** `venv/bin/python -m pytest tests -q` → all green.
- [ ] **Step 2:** `cd src/frontend && npx tsc --noEmit && npm run build` → clean.
- [ ] **Step 3:** Browser tour in a NEW Chrome tab (uvicorn :8000 + vite :5173 must be running): `/` (drag widget, reload, persisted) → `/screener` (type "power", Enter, chart renders, split view) → `/stock/<id>` → `/portfolio` → `/recommendations` → `/advisor` → `/bse-news` (search + filters) → Settings → Update Data (status flow renders; do not run a full pipeline refresh unless the user asks). Console: zero errors.
- [ ] **Step 4:** Screenshot Home + Screener + BSE News, show the user, and report any deferred issues (e.g. bundle-size warning).
