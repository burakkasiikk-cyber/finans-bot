from unittest.mock import patch, MagicMock
from scripts.notify import build_morning_message, send_telegram, build_change_message

SAMPLE_REPORT = {
    "generated_at": "2026-05-26T06:03:00Z",
    "macro": {"usd_try": 32.45, "gold_usd": 2318.5, "sp500_change_pct": 0.42},
    "top3": ["NVDA", "AAPL", "THYAO"],
    "risk_alerts": ["GARAN"],
    "stocks": [
        {"symbol": "NVDA",  "score": 89, "verdict": "GÜÇLÜ AL", "change_pct": 2.4},
        {"symbol": "AAPL",  "score": 76, "verdict": "GÜÇLÜ AL", "change_pct": 0.8},
        {"symbol": "THYAO", "score": 71, "verdict": "AL",        "change_pct": 1.2},
        {"symbol": "GARAN", "score": 41, "verdict": "SAT",       "change_pct": -2.1},
    ],
}

def test_build_morning_message_contains_top3():
    msg = build_morning_message(SAMPLE_REPORT)
    assert "NVDA" in msg
    assert "AAPL" in msg
    assert "THYAO" in msg

def test_build_morning_message_contains_risk_alert():
    msg = build_morning_message(SAMPLE_REPORT)
    assert "GARAN" in msg

def test_build_morning_message_contains_macro():
    msg = build_morning_message(SAMPLE_REPORT)
    assert "32.45" in msg

def test_change_message_detects_upgrade_and_downgrade():
    report = {"stocks": [
        {"symbol": "AAA", "verdict_key": "strong_buy", "prev": {"verdict_key": "buy"}},
        {"symbol": "BBB", "verdict_key": "sell",       "prev": {"verdict_key": "hold"}},
        {"symbol": "CCC", "verdict_key": "buy",        "prev": {"verdict_key": "buy"}},  # değişmedi
    ]}
    msg = build_change_message(report)
    assert msg is not None
    assert "AAA" in msg and "BBB" in msg and "CCC" not in msg
    assert "Fırsat" in msg and "Dikkat" in msg


def test_change_message_none_when_no_change():
    report = {"stocks": [
        {"symbol": "AAA", "verdict_key": "buy", "prev": {"verdict_key": "buy"}},
        {"symbol": "ERR", "error": "x"},
        {"symbol": "NOPREV", "verdict_key": "buy"},  # prev yok
    ]}
    assert build_change_message(report) is None


@patch("scripts.notify.requests.post")
def test_send_telegram_calls_api(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    send_telegram("test message", bot_token="TOKEN", chat_id="123")
    mock_post.assert_called_once()
    call_json = mock_post.call_args[1]["json"]
    assert call_json["text"] == "test message"
    assert call_json["chat_id"] == "123"
