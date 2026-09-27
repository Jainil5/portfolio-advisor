# Portfolio Advisor Repo Restructure — Design Spec

Date: 2026-09-27
Status: Approved (Option B — src-layout domain package; data relocated to git-ignored top-level `data/`)

## Goal

Move the project from a post-move broken state (`backend/` relocated into `src/` with all
`from backend.*` imports now broken) to an industry-standard src-layout Python package named
`portfolio_advisor`, with clear architectural layers, an installable `pyproject.toml`, a clean
test suite, and the ~400 bronze/silver CSVs moved out of the source tree into a git-ignored
top-level `data/` directory.

## Target Layout

```
portfolio-advisor/
├── pyproject.toml              # installable package, deps, pytest config
├── README.md                   # updated setup/run instructions
├── .env.example                # documents env vars (no secrets)
├── data/                       # git-ignored; bronze/ + silver/ moved from src/backend/data
│   ├── bronze/{prices,fundamentals}/*.csv, stocks.csv, transactions.csv, metadata.json
│   └── silver/{features,recommendations}.csv
├── scripts/
│   └── update_data.py          # entry point: runs the daily ingest pipeline
├── dags/
│   └── finance_flow.py         # Airflow DAG (moved from src/test/airflow, paths updated)
├── streamlit_app/
│   ├── app.py                  # was root app.py; uses st.Page + st.navigation
│   └── pages/                  # renamed: my_portfolio.py, stock_analysis.py,
│                               #   recommendations.py, ai_advisor.py (no space/numeral names)
├── src/portfolio_advisor/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py         # re-exports all path constants (compat surface)
│   │   └── settings.py         # PROJECT_ROOT-relative DATA_ROOT + derived paths
│   ├── data/
│   │   ├── __init__.py
│   │   └── repository.py       # cached/safe CSV read+write helpers (only file access)
│   ├── pipelines/
│   │   ├── ingest.py           # was services/data_updates/fetch_stocks_data.py
│   │   ├── update_pipeline.py  # was services/data_updates/update_data_pipeline.py
│   │   ├── features.py         # was services/generations/generate_features_pd.py
│   │   ├── features_spark.py   # was services/generations/generate_features_spark.py (Databricks entry)
│   │   └── recommendations.py  # was services/generations/recommendations.py
│   ├── analytics/
│   │   └── predict.py          # was services/predict_stock.py
│   ├── agents/
│   │   ├── llm.py              # was backend/model.py
│   │   └── stock_agent.py      # was services/stock_agent.py
│   ├── services/
│   │   └── user_transactions.py
│   └── utils/
│       └── market_data.py      # was services/helper_functions.py
└── tests/                      # pytest suite only
```

## Module Mapping (old → new)

| Old | New |
|---|---|
| `src/backend/config.py` | `portfolio_advisor/config/settings.py` (+ re-export in `config/__init__.py`) |
| `src/backend/model.py` | `portfolio_advisor/agents/llm.py` |
| `src/backend/services/helper_functions.py` | `portfolio_advisor/utils/market_data.py` |
| `src/backend/services/stock_agent.py` | `portfolio_advisor/agents/stock_agent.py` |
| `src/backend/services/user_transactions.py` | `portfolio_advisor/services/user_transactions.py` |
| `src/backend/services/predict_stock.py` | `portfolio_advisor/analytics/predict.py` |
| `src/backend/services/fetch_stocks_data.py` | **deleted** (legacy duplicate of data_updates copy) |
| `src/backend/services/data_updates/fetch_stocks_data.py` | `portfolio_advisor/pipelines/ingest.py` |
| `src/backend/services/data_updates/update_data_pipeline.py` | `portfolio_advisor/pipelines/update_pipeline.py` |
| `src/backend/services/generations/generate_features_pd.py` | `portfolio_advisor/pipelines/features.py` |
| `src/backend/services/generations/generate_features_spark.py` | `portfolio_advisor/pipelines/features_spark.py` |
| `src/backend/services/generations/recommendations.py` | `portfolio_advisor/pipelines/recommendations.py` |
| `src/test/airflow/finance_flow.py` | `dags/finance_flow.py` |
| `pages/*` + root `app.py` | `streamlit_app/app.py` + `streamlit_app/pages/*` |

## Import Strategy

- Absolute intra-package imports everywhere: `from portfolio_advisor.config import PRICE_DIR`.
  Pure relative (`from ..config`) imports are deliberately avoided — they break under
  `streamlit run` and dynamic page loading.
- `pyproject.toml` + `pip install -e .` makes the package importable from any CWD; all
  `sys.path.insert` hacks in pages/tests are deleted.
- Streamlit multi-page app is rebuilt on `st.Page(...)` + `st.navigation(...)` declared in
  `app.py` because the legacy automatic `pages/` discovery cannot locate a `pages/` folder
  that is not beside the CWD. Page files lose numeral/space prefixes (valid module names,
  stable nav order via explicit list).

## Config & Data Paths

- `settings.py` computes `PROJECT_ROOT = Path(__file__).resolve().parents[3]` and defaults
  `DATA_ROOT = PROJECT_ROOT / "data"`; overridable via absolute `STOCK_DATA_ROOT` env var.
  All bronze/silver constants derive from it — no more CWD-dependent relative strings.
- `data/` (bronze + silver) is physically moved from `src/backend/data/` to top-level `data/`
  and git-ignored; existing CSVs keep working in place (no regeneration).
- `.env` is updated to drop the stale relative `STOCK_DATA_ROOT` default; `.env.example`
  documents available env vars.

## Optimization Strategy (applied in this restructure)

1. **Deduplicate**: delete legacy `services/fetch_stocks_data.py` (superseded copy of the
   `data_updates/` variant, which adds `os.makedirs` guards and `output_file` params).
2. **Lazy, cached data access**: module-level `pd.read_csv(...)` side effects in
   `stock_agent.py`, `market_data.py` (ex-`helper_functions`), and pages are replaced by
   repository functions in `portfolio_advisor/data/repository.py` that (a) resolve paths via
   settings, (b) cache by file mtime, (c) raise clear errors on missing files. Imports no
   longer crash when data is absent, and the 60s autorefresh loop stops re-parsing unchanged
   CSVs.
3. **Dashboard double-lookup fix**: `app.py` computed `current_price` per row twice
   (`load_portfolio` apply + the render loop); the loop now reuses the cached column.
4. **Duplicated literal paths in pages** (`pd.read_csv("backend/data/silver/features.csv")`)
   are replaced with repository calls.
5. **Concurrency**: already present in `update_pipeline` (ThreadPoolExecutor, 10 workers) —
   no change beyond the move; recorded here as verified.
6. **Hygiene**: `.gitignore` updated (`data/` replaces `backend/data/`), stale scratch files
   deleted, `__pycache__` dirs pruned, deps consolidated into `pyproject.toml`.

Deliberately deferred (out of scope): extracting shared feature logic between the pandas and
Spark generators (they run in different runtimes; merge needs a Databricks-side eval), and
monorepo packaging.

## Deletions

- `src/main.py` (empty), `src/backend/services/fetch_stocks_data.py` (duplicate),
  `src/test/a.py`, `src/backend/test/a.py`, `src/backend/test/update_data.py`,
  `src/backend/test/generate_features_spark.py` (stale copies), `src/test/update_data.py`
  (replaced by `scripts/update_data.py`), `src/test/test_api.py` (imports non-existent
  `backend.services.news`), `demo_payload.txt`, all `__pycache__`, root `app/__init__.py`
  leftovers if present.
- `src/backend/requirements.txt` → consolidated into `pyproject.toml`.

## Error Handling

- Repository layer centralizes existence checks: `read_csv(name)` raises `FileNotFoundError`
  with the resolved path in the message; write helpers `os.makedirs(..., exist_ok=True)` the
  parent. No behavior changes to scoring/agent logic.

## Testing & Verification Gate

1. `tests/test_imports.py` — every package module imports successfully.
2. `tests/test_settings.py` — `DATA_ROOT` resolves under project root by default and honors
   an absolute env override.
3. `tests/test_repository.py` — round-trip read/write against tmp fixtures (no real data).
4. `tests/test_recommendations.py` — score→label and explanation rules of the pure functions.
5. Manual gate: `pip install -e .` → `pytest` → `python scripts/update_data.py` (idempotent
   daily-update check; network-dependent) → `streamlit run streamlit_app/app.py` renders the
   dashboard and all four pages without errors.
