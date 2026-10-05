"""FastAPI application: HTTP layer over the backend data + AI modules.

The React frontend talks only to these endpoints; CSVs and DuckDB never
leave this process. Data comes from the mtime-cached repository layer, so a
pipeline run (or POST /api/update_data) refreshes every endpoint
automatically.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.api import analysis, jobs, news, stocks
from backend.api.util import records
from backend.data import repository

app = FastAPI(title="Portfolio Advisor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router)
app.include_router(news.router)
app.include_router(analysis.router)
app.include_router(jobs.router)


@app.get("/api/meta")
def get_meta():
    features = stocks.enriched_df()
    return {
        "stocks": len(features),
        "recommendations": len(repository.load_recommendations_df()),
        "data_updated_at": stocks.data_updated_at(),
    }


@app.get("/api/portfolio")
def get_portfolio():
    return records(repository.load_portfolio_df())


@app.get("/api/transactions")
def get_transactions():
    return records(repository.load_transactions_df())


@app.get("/api/recommendations")
def get_recommendations():
    return records(repository.load_recommendations_df())
