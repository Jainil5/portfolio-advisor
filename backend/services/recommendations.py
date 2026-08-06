import pandas as pd

FEATURES_FILE = "data/features.csv"
OUTPUT_FILE = "data/recommendations.csv"


def generate_recommendation(row):
    score = row.get("score", 0)

    if score == 4:
        return "STRONG BUY"
    elif score == 3:
        return "BUY"
    elif score == 2:
        return "HOLD"
    else:
        return "SELL"


def generate_explanation(row):
    reasons = []
    risks = []

    if row.get("return_30d", 0) > 0:
        reasons.append("positive short-term returns")
    else:
        risks.append("negative short-term returns")

    if row.get("return_180d", 0) > 0:
        reasons.append("strong long-term performance")
    else:
        risks.append("weak long-term performance")

    if row.get("trend") == "Bullish":
        reasons.append("bullish trend")
    else:
        risks.append("bearish trend")

    vol = row.get("volatility_30d", 0)
    if 0 < vol < 20:
        reasons.append("low volatility (stable)")
    elif vol > 30:
        risks.append("high volatility (risky)")

    if row.get("debt_to_equity", 0) < 1:
        reasons.append("low debt levels")
    else:
        risks.append("high debt")

    if row.get("cash_ratio", 0) > 0.3:
        reasons.append("good liquidity")

    text = f"{row.get('recommendation')} because:\n"

    for r in reasons:
        text += f"- {r}\n"

    if risks:
        text += "\nRisks:\n"
        for r in risks:
            text += f"- {r}\n"

    return text


def generate_recommendations():
    df = pd.read_csv(FEATURES_FILE)

    if df.empty:
        print("No features data found")
        return

    df["recommendation"] = df.apply(generate_recommendation, axis=1)
    df["explanation"] = df.apply(generate_explanation, axis=1)

    df = df.sort_values(by="score", ascending=False)

    cols = [
        "stock_id",
        "company_name",
        "ticker",
        "sector",
        "current_price",
        "return_30d",
        "return_180d",
        "volatility_30d",
        "trend",
        "debt_to_equity",
        "cash_ratio",
        "score",
        "recommendation",
        "explanation"
    ]

    df = df[[c for c in cols if c in df.columns]]

    df.to_csv(OUTPUT_FILE, index=False)

    print("Recommendations generated")


if __name__ == "__main__":
    generate_recommendations()