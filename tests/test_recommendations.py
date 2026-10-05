"""Pure scoring/labeling rules from the recommendations pipeline."""

from backend.pipelines.recommendations import (
    generate_explanation,
    generate_recommendation,
)


def test_recommendation_labels_by_score():
    assert generate_recommendation({"score": 4}) == "STRONG BUY"
    assert generate_recommendation({"score": 3}) == "BUY"
    assert generate_recommendation({"score": 2}) == "HOLD"
    assert generate_recommendation({"score": 1}) == "SELL"
    assert generate_recommendation({"score": 0}) == "SELL"


def test_explanation_surfaces_reasons_and_risks():
    row = {
        "recommendation": "BUY",
        "return_30d": 5,
        "return_180d": -3,
        "trend": "Bullish",
        "volatility_30d": 40,
        "debt_to_equity": 0.5,
        "cash_ratio": 0.6,
    }
    text = generate_explanation(row)

    assert "positive short-term returns" in text
    assert "bullish trend" in text
    assert "low debt levels" in text
    assert "good liquidity" in text
    assert "Risks:" in text
    assert "negative short-term returns" not in text
    assert "weak long-term performance" in text
