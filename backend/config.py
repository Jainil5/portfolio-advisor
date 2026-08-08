import os

from langchain_ollama import ChatOllama, OllamaEmbeddings


# PATH CONFIGURATION

STOCK_DATA_ROOT = os.getenv(
    "STOCK_DATA_ROOT",
    "backend/data",
)

# Bronze — raw data
BRONZE_DIR = os.path.join(
    STOCK_DATA_ROOT,
    "bronze",
)

PRICE_DIR = os.path.join(
    BRONZE_DIR,
    "prices",
)

FUNDAMENTAL_DIR = os.path.join(
    BRONZE_DIR,
    "fundamentals",
)

STOCKS_FILE = os.path.join(
    BRONZE_DIR,
    "stocks.csv",
)

# Silver — processed data
SILVER_DIR = os.path.join(
    STOCK_DATA_ROOT,
    "silver",
)

# Pipeline metadata
METADATA_FILE = os.path.join(
    BRONZE_DIR,
    "metadata.json",
)

FEATURES_FILE = os.path.join(
    SILVER_DIR,
    "features.csv",
)

RECOMMENDATIONS_FILE = os.path.join(
    SILVER_DIR,
    "recommendations.csv",
)

# LLM CONFIGURATION

embeddings = OllamaEmbeddings(
    model="nomic-embed-text:latest",
)

model = ChatOllama(
    model="gpt-oss:20b-cloud",
    temperature=0,
)