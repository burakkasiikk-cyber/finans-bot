import pytest
from unittest.mock import patch, MagicMock
from scripts.fetch_us import fetch_us_stock

MOCK_QUOTE = {"c": 1125.40, "dp": 2.4, "h": 1130.0, "l": 1100.0}
MOCK_METRICS = {
    "metric": {
        "peTTM": 45.2, "pbAnnual": 28.1, "psTTM": 18.3,
        "roeTTM": 124.0, "roaTTM": 55.0,
        "netProfitMarginTTM": 55.0, "grossMarginTTM": 76.0,
        "revenueGrowthTTMYoy": 77.0, "epsGrowthTTMYoy": 85.0,
        "revenueGrowth5Y": 42.0,
        "currentRatioAnnual": 4.2, "totalDebt/totalEquityAnnual": 0.42,
        "quickRatioAnnual": 3.8,
        "52WeekPriceReturnDaily": 210.0, "13WeekPriceReturnDaily": 38.0,
        "52WeekHigh": 1200.0, "52WeekLow": 500.0,
    }
}
MOCK_REC = [{"buy": 38, "hold": 5, "sell": 1, "period": "2026-05-01"}]
MOCK_PROFILE = {"name": "NVIDIA Corporation"}

@patch("scripts.fetch_us.finnhub_get")
def test_fetch_us_stock_returns_expected_shape(mock_get):
    mock_get.side_effect = [MOCK_QUOTE, MOCK_PROFILE, MOCK_METRICS, MOCK_REC]
    result = fetch_us_stock("NVDA", api_key="test_key")
    assert result["symbol"] == "NVDA"
    assert result["price"] == 1125.40
    assert result["exchange"] == "NASDAQ"
    assert "score" in result
    assert result["score"] > 70  # high quality stock
    assert result["dimensions"]["valuation"]["score"] is not None

@patch("scripts.fetch_us.finnhub_get")
def test_fetch_us_stock_handles_api_error(mock_get):
    mock_get.side_effect = Exception("API error")
    result = fetch_us_stock("NVDA", api_key="test_key")
    assert "error" in result
    assert result["symbol"] == "NVDA"
