from unittest.mock import patch, MagicMock
from scripts.fetch_bist import fetch_bist_stock

MOCK_INFO = {
    "longName": "Türk Hava Yolları A.O.",
    "currentPrice": 285.50,
    "regularMarketChangePercent": 1.2,
    "trailingPE": 8.2,
    "priceToBook": 1.4,
    "returnOnEquity": 0.22,
    "revenueGrowth": 0.18,
    "debtToEquity": 85.0,
    "currentRatio": 0.9,
    "fiftyTwoWeekHigh": 310.0,
    "fiftyTwoWeekLow": 180.0,
    "52WeekChange": 0.35,
}

@patch("scripts.fetch_bist.yf.Ticker")
def test_fetch_bist_returns_expected_shape(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.info = MOCK_INFO
    mock_ticker_cls.return_value = mock_ticker

    result = fetch_bist_stock("THYAO")
    assert result["symbol"] == "THYAO"
    assert result["exchange"] == "BIST"
    assert result["price"] == 285.50
    assert "score" in result
    assert result["score"] is not None

@patch("scripts.fetch_bist.yf.Ticker")
def test_fetch_bist_handles_error(mock_ticker_cls):
    mock_ticker_cls.side_effect = Exception("network error")
    result = fetch_bist_stock("THYAO")
    assert "error" in result
