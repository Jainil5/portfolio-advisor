# Portfolio Advisor 📈 - Analyzing stocks simplified

An AI-powered stock market advisory analysis system focused on the Indian market (Nifty 100). PAD helps investors make data-driven decisions by combining technical indicators, fundamental ratios, and AI-powered insights.

## Features
- **Automated Data Pipeline**: Scrapes Nifty 100 listings and fetches pricing/fundamentals via Yahoo Finance.
- **AI-Powered Analysis**: Uses advanced scoring algorithms to categorize stocks into Buy/Hold/Sell.
- **Interactive Dashboard**: Visualize price trends, technical metrics, and fundamental health.
- **Deep Insights**: Contextual explanations for every recommendation.
- **Intelligent AI Agent**: Fetches the latest news for stocks, compares multiple stocks, and provides detailed, real-time information and insights.

## Enterprise Architecture & Scale
- **Apache Airflow**: Orchestrates and schedules the daily data pipelines, ensuring reliable and automated fetching of market data.
- **Databricks**: Provides a scalable, unified analytics platform to handle heavy computational workloads and model training.
- **PySpark**: Powers the distributed data processing engine, enabling rapid, parallelized calculation of complex technical indicators and large-scale feature engineering.
---
## DEMO
- **Stock Agent** - Agent that recommends, compares and analyze the stocks.
<img width="2059" height="1150" alt="SCR-20260811-srdh" src="https://github.com/user-attachments/assets/9077a3ad-21c3-4965-bf18-13ad45b23e70" />

- **Analysis Page** - Feature engineering on stocks with different metrics like Moving Averages, Volatality, and more.
<img width="2525" height="1220" alt="SCR-20260811-sqrc" src="https://github.com/user-attachments/assets/1bf33d6e-5ede-4c8f-8f37-9471b02975db" />



---
## Project Setup

### 1. Prerequisites
- **Python 3.11**: This project is tested and optimized for Python 3.11.
- Ensure you have `pip` and `venv` installed.

### 2. Installation
Clone the repository and set up a virtual environment:

```bash
# Create a virtual environment
python3.11 -m venv venv

# Activate the virtual environment (macOS/Linux)
source venv/bin/activate

# Install the package and its dependencies (editable)
pip install -e .

# Optional extras: PySpark feature generation, and dev tooling (pytest)
pip install -e ".[spark,dev]"
```

### 3. Data Initialization
Before running the UI, you must populate the local dataset with the latest market data. This fetches the Nifty listings, historical prices, and company fundamentals into `data/` (git-ignored).

```bash
python scripts/update_data.py            # bronze: prices + fundamentals
python -m backend.pipelines.features     # silver: features + AI scores
python -m backend.pipelines.recommendations
```

*Note: This process may take 5-10 minutes depending on your internet connection. You can also trigger the whole chain later from the app: Settings (⚙) → Update Data.*

### 4. Launching the App
The frontend is a React (Vite + TypeScript) app served against a FastAPI backend that reads the CSV/DuckDB data:

```bash
# Terminal 1 — API (port 8000)
uvicorn backend.api:app --reload --port 8000

# Terminal 2 — frontend (port 5173, proxies /api -> :8000)
cd src/frontend
npm install
npm run dev
```

Open http://localhost:5173 — the Stock Screener is the home page; click any row for the TradingView-style chart page (candles, MA20/50, RSI, 1W–5Y ranges, fundamentals, AI analysis, news).

### 5. Repository Layout

```
src/
├── backend/            # pip-installable Python package (backend.api, pipelines, agents, news, …)
└── frontend/           # React + Vite + TypeScript app
data/                   # bronze/ + silver/ datasets (git-ignored)
scripts/  dags/  tests/ # entry points, Airflow DAG, pytest suite
```

### 6. Latest News (optional)
Keeps a rolling news snapshot per stock in `data/bronze/stock_news.csv`: the 5 newest headlines (Google News, fetched with [Scrapling](https://github.com/D4Vinci/Scrapling)) plus a short LLM summary. Each run merges in fresh headlines, drops the oldest beyond 5, and rewrites the summary only when headlines changed. The AI advisor reads it through its `latest_stock_news` tool.

```bash
pip install -e ".[news]"

python -m backend.news.fetch                    # all active stocks
python -m backend.news.fetch --symbols TCS,INFY
python -m backend.news.fetch --no-summary       # headlines only, no LLM
```

Run it on a schedule (cron / Airflow) to keep it fresh.

**BSE corporate announcements.** Exchange filings are the primary source (results, dividends, orders, M&A are filed with BSE/NSE before the media reports them). This scrapes BSE's announcements for *all* listed companies into `data/bronze/bse_news.csv`, keeping the last 7 days. Rows for stocks in `stocks.csv` get a `ticker`; routine compliance filings are flagged `is_routine`.

```bash
python -m backend.news.bse_news            # today + yesterday, stops at already-stored filings
python -m backend.news.bse_news --days 7   # backfill
python -m backend.news.bse_news --full     # re-walk every page (repair an interrupted run)
```

## Documentation
For a deep dive into the system architecture, scoring logic, and agentic workflows, refer to the technical overview or source code comments.
