# PAD: Portfolio Advisory Dashboard 📈

An AI-powered stock market advisory analysis system focused on the Indian market (Nifty 100). PAD helps investors make data-driven decisions by combining technical indicators, fundamental ratios, and AI-powered insights.

## Features
- **Automated Data Pipeline**: Scrapes Nifty 100 listings and fetches pricing/fundamentals via Yahoo Finance.
- **AI-Powered Analysis**: Uses advanced scoring algorithms to categorize stocks into Buy/Hold/Sell.
- **Interactive Dashboard**: Visualize price trends, technical metrics, and fundamental health.
- **Deep Insights**: Contextual explanations for every recommendation.

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

# Install dependencies
pip install -r requirements.txt
```

### 3. Data Initialization
Before running the UI, you must populate the local database with the latest market data. This script fetches the Nifty 100 list, historical prices, and company fundamentals.

```bash
python update_data.py
```
*Note: This process may take 5-10 minutes depending on your internet connection.*

### 4. Launching the Dashboard
Once the data is ready, launch the Streamlit interface:

```bash
streamlit run app.py
```

## Documentation
For a deep dive into the system architecture, scoring logic, and agentic workflows, refer to the technical overview or source code comments.
