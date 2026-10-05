# TradingView-Style UI Overhaul — Design Spec

Date: 2026-10-05
Status: Approved in chat (page model, theme, widget engine, endpoints)

## Goal

Turn the portfolio-advisor React frontend into a live TradingView-style
terminal: dark token theme throughout, a customizable portfolio-analysis
dashboard as the home page, a ticker-driven screener with an integrated stock
workspace, and a live BSE news page fed through a `/api/bse-news` endpoint.

## 1. Pages & routes (new order)

| Route | Page | Content |
|-------|------|---------|
| `/` | **Home — Portfolio Desk** | Customizable widget grid (see §3). Portfolio KPIs, best/worst performers, sector allocation, top AI signals, market movers, latest BSE headlines. Edit-layout mode: drag/resize, add/remove widgets; persisted to localStorage. |
| `/screener` | **Screener** | Ticker/company search box + universe table with green/red % cells. Selecting a row opens the stock workspace (chart, AI analysis, fundamentals, Google News) as a split view on wide screens. Deep link `/stock/:stockId` renders the same workspace. |
| `/portfolio` | **My Portfolio** | Existing ledger + positions page, restyled. |
| `/recommendations` | **Recommendations** | Existing AI picks, restyled. |
| `/advisor` | **AI Agent** | Existing LangChain/Ollama chat, restyled. |
| `/bse-news` | **Live BSE News** | Auto-refreshing announcement feed from `data/news.duckdb` (see §5). Filters: ticker/company search, hide-routine toggle. |

Retired routes: `/dashboard` (absorbed into Home widgets) and `/analysis`
(absorbed into the screener workspace). Both redirect. `/market` redirect
stays.

## 2. Theme — TradingView dark tokens

A single token pass in `index.css` (`@theme`) + shared primitives in
`components/ui.tsx`, so every page inherits it:

- Surfaces: base `#0b0f18`, panel `#131722`, elevated `#182230`, hairline borders `rgba(140,160,185,0.18)`.
- Trend colors: up `#16C784`, down `#EA3943` (matches chart series colors already in TvChart).
- Accent: `#2962FF` (TradingView blue) for selection/links/buttons.
- Typography: Inter for UI, tabular numerals (`.num`) for every figure; smaller uppercase section labels.
- Controls: segmented button groups (timeframes, toggles), subtle hover elevations, 4–8px radii (TV is dense, not pillowy).
- Chart widgets, tables and badges all consume the same tokens; no per-page color literals.

## 3. Widget engine (Home)

- Library: `react-grid-layout` (12-col grid, drag + resize, React 19 compat verified at install; fallback = custom HTML5-drag grid if it breaks).
- `src/frontend/src/widgets/registry.tsx`: each widget = `{ id, title, defaultLayout, component }`.
- Initial widgets: `kpis`, `best-worst` (top/bottom performers by 30d return within holdings + universe), `sector-allocation` (donut), `ai-signals` (top scores), `movers` (gainers/losers), `bse-news` (latest 8), `holdings-sparkline`.
- State: layout array + visible widget ids in localStorage key `home.layout.v1`; "Edit layout" toggle shows drag handles, resize borders, remove buttons, and an "Add widget" catalog popover; a Reset restores defaults.
- Widgets are read-only consumers of existing API hooks — no widget-specific backend.

## 4. Screener + stock workspace

- Screener keeps current table semantics (sortable % columns, sector filter) but adds: sticky search input matching ticker symbol **or** company name (client-side filter), keyboard up/down + Enter to open.
- Workspace (right pane / `/stock/:id`): existing TvChart + timeframe/indicator controls, Market Info, Technicals, AI analysis panel, Google News panel (`/api/news/summary/{ticker}`), About. Fundamentals panel shows the CSV-available ratios (D/E, D/A, cash ratio, volatilities, avg volumes) plus score/prediction; no fabricated P/E.
- Layout: ≥1440px split view (table 420px + workspace flex); below that, row click navigates to `/stock/:id` full page.

## 5. Backend — BSE news endpoints

In `src/backend/api/news.py` (DuckDB `announcements` table, short-lived read-only connections):

- `GET /api/bse-news?search=&days=&hide_routine=&limit=` → rows ordered `published_at DESC`; fields from `db.COLUMNS` serialized like existing `/news`. `search` matches ticker or company name (case-insensitive LIKE).
- `POST /api/bse-news` → ingest one announcement (or a list) into DuckDB so external tooling can push data to the same store the page reads. Validates required fields (`company_name`, `title`, `published_at`); dedupes on existing natural key used by the scraper.
- Old `GET /api/news` remains for the stock-page news widget.

## 6. Error handling

- Home widgets degrade independently: any widget whose fetch fails renders an inline "unavailable" state; the grid never blocks on one widget.
- POST /api/bse-news returns 422 on missing fields, 503 if DuckDB write lock can't be acquired after retries.
- localStorage layout is version-keyed (`home.layout.v1`); malformed JSON falls back to defaults silently.

## 7. Testing

- pytest: GET /api/bse-news filters (search/days/hide_routine), POST ingest + dedupe + 422.
- `tsc --noEmit` + `npm run build` clean.
- Manual browser pass: home edit-mode drag persists across reload; screener search opens workspace; BSE news page auto-refreshes.

## Out of scope

- Watchlists, orders/paper trading, intraday data, server-side widget config.
