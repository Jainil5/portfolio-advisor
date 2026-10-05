"""News pipeline configuration: paths, pacing, schedule and routine keywords."""

import os

from backend.config import DATA_ROOT, PROJECT_ROOT, STOCKS_FILE

# ------------------------------------------------------------------
# Paths (all inside the project / DATA_ROOT)
# ------------------------------------------------------------------
STOCK_LIST_FILE = STOCKS_FILE
SYMBOL_COLUMN = "ticker"          # values look like "TCS.NS"; suffix is stripped
NAME_COLUMN = "company_name"

SCRIP_MAP_FILE = os.path.join(DATA_ROOT, "scrip_map.csv")
NEWS_DB_FILE = os.path.join(DATA_ROOT, "news.duckdb")
FILINGS_DIR = os.path.join(DATA_ROOT, "filings")
BSE_DOWNLOAD_DIR = os.path.join(DATA_ROOT, "bse_tmp")  # required by bse.BSE(); unused
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "news_ingest.log")
AGENTS_DIR = os.path.join(PROJECT_ROOT, "agents")

# NSE index constituents, used only for the ISIN fallback in scrip mapping.
NSE_INDEX_CSV_URL = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"

# ------------------------------------------------------------------
# BSE endpoints
# ------------------------------------------------------------------
# PDFFLAG=0 -> AttachLive, PDFFLAG=1 -> AttachHis (verified against live data).
# Filings move from Live to His as they age.
ATTACHMENT_BASE = "https://www.bseindia.com/xml-data/corpfiling"
ATTACH_LIVE = "AttachLive"
ATTACH_HIS = "AttachHis"

# ------------------------------------------------------------------
# Pacing / retries
# ------------------------------------------------------------------
SCRIP_LOOKUP_DELAY_S = 1.5
INGEST_DELAY_S = 1.0
MAX_RETRIES = 4
BACKOFF_BASE_S = 2.0              # 2, 4, 8, 16 s
HTTP_TIMEOUT_S = 30

# ------------------------------------------------------------------
# Scheduler
# ------------------------------------------------------------------
TIMEZONE = "Asia/Kolkata"
MARKET_HOURS = (9, 16)            # 5-min runs 09:00-15:55 IST; off-hours cadence from 16:00
MARKET_INTERVAL_MIN = 5
OFF_HOURS_INTERVAL_MIN = 30
SCHEDULED_LOOKBACK_DAYS = 2

# ------------------------------------------------------------------
# Tool limits
# ------------------------------------------------------------------
LATEST_ALL_MAX_ROWS = 50
FILING_MAX_CHARS = 15000

# ------------------------------------------------------------------
# Routine compliance filings (case-insensitive substring match against
# subject / headline / subcategory). Based on stock-news' blacklist.
# ------------------------------------------------------------------
ROUTINE_KEYWORDS = (
    "trading window",
    "reg. 74 (5)",
    "regulation 74(5)",
    "regulation 74 (5)",
    "book closure",
    "loss of share",
    "loss of certificate",
    "duplicate certificate",
    "duplicate share certificate",
    "shares in physical",
    "newspaper publication",
    "newspaper advertisement",
    "investor complaints",
    "statement of investor complaints",
    "compliances-certificate under reg. 74",
    "compliance certificate",
    "reg. 40 (9)",
    "reg. 40 (10)",
    "reg. 39 (3)",
    "closure of trading window",
)
