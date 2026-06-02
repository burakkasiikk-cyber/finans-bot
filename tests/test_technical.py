"""Trader modu teknik skorlama testleri — regresyon koruması."""
import math

from scripts.technical import (
    rsi, macd, bollinger_pos, atr, stochastic, support_resistance,
    trade_setup, simple_signal, score_from_history, rescore_report,
)


def _bars(closes, vol=1000):
    """Kapanış listesinden basit OHLCV barları üret (h/l ±%1)."""
    return [
        {"t": i, "o": c, "h": round(c * 1.01, 2), "l": round(c * 0.99, 2),
         "c": c, "v": vol}
        for i, c in enumerate(closes)
    ]


def _uptrend(n=60, start=10.0, step=0.15):
    return _bars([round(start + i * step, 2) for i in range(n)])


def _downtrend(n=60, start=20.0, step=0.15):
    return _bars([round(start - i * step, 2) for i in range(n)])


# ── Göstergeler ──
def test_rsi_range():
    r = rsi([10 + i for i in range(30)])
    assert r is not None and 0 <= r <= 100


def test_rsi_insufficient_data():
    assert rsi([1, 2, 3]) is None


def test_macd_uptrend_bullish():
    m = macd([10 + i * 0.2 for i in range(40)])
    assert m is not None and m["sig"] == "AL"


def test_bollinger_pos_bounds():
    p = bollinger_pos([10 + (i % 3) for i in range(30)])
    assert p is not None


def test_atr_positive():
    a = atr(_uptrend())
    assert a is not None and a > 0


def test_stochastic_range():
    st = stochastic(_uptrend())
    assert st is not None and 0 <= st["k"] <= 100


def test_support_resistance_order():
    sup, res = support_resistance(_uptrend())
    assert sup < res


# ── İşlem kurulumu ──
def test_trade_setup_level_order():
    """Stop < giriş < hedef her zaman; RR pozitif."""
    ts = trade_setup(_uptrend())
    assert ts is not None
    assert ts["stop"] < ts["entry"] < ts["target"]
    assert ts["rr"] is None or ts["rr"] > 0


def test_trade_setup_insufficient():
    assert trade_setup(_bars([10, 11, 12])) is None


# ── Sinyal ──
def test_signal_uptrend_is_buy_or_profit():
    bars = _uptrend()
    closes = [b["c"] for b in bars]
    sig = simple_signal(closes, bars, 80)
    assert sig["key"] in ("buy", "strong_buy", "hold")  # yükselişte AL ya da kâr-al


def test_signal_downtrend_is_sell():
    bars = _downtrend()
    closes = [b["c"] for b in bars]
    sig = simple_signal(closes, bars, 30)
    assert sig["key"] in ("sell", "strong_sell")


# ── Bütünleşik skorlama ──
def test_score_from_history_structure():
    res = score_from_history(_uptrend())
    assert res is not None
    assert 0 <= res["score"] <= 100
    assert set(["trend", "momentum", "volatility", "setup"]).issubset(res["dimensions"])
    # Rozet ile sinyal AYNI kaynaktan → asla çelişmez
    assert res["verdict_key"] == res["signal"]["key"]
    assert res["trade_setup"] is not None


def test_score_from_history_insufficient_returns_none():
    assert score_from_history(_bars([10, 11, 12])) is None


def test_rescore_report_skips_errors_and_short():
    report = {"stocks": [
        {"symbol": "UP", "price_history": _uptrend()},
        {"symbol": "ERR", "error": "yok"},
        {"symbol": "SHORT", "price_history": _bars([10, 11, 12])},
    ]}
    n = rescore_report(report)
    assert n == 1  # sadece UP skorlandı
    syms = [s["symbol"] for s in report["stocks"]]
    assert "UP" in syms
    # top3 ve risk_alerts üretildi
    assert "top3" in report and "risk_alerts" in report


# ── Haber duygu analizi ──
from scripts.news_sentiment import analyze_titles, _relevance_keys


def test_news_positive():
    res = analyze_titles(["Company beats record profit", "Stock surges on upgrade"])
    assert res["adjustment"] > 0 and res["sentiment"] == "olumlu"


def test_news_negative():
    res = analyze_titles(["Company misses estimates, stock plunges", "lawsuit and probe announced"])
    assert res["adjustment"] < 0 and res["sentiment"] == "olumsuz"


def test_news_capped_at_5():
    res = analyze_titles(["beats record surge upgrade rally profit buyback dividend wins"] * 5)
    assert -5 <= res["adjustment"] <= 5


def test_news_relevance_filter():
    # rel_keys 'apple' içeriyorsa sadece apple geçen başlık sayılır
    titles = ["Apple beats record profit", "Generic market rally continues today"]
    res = analyze_titles(titles, {"apple"})
    assert res["count"] == 1  # sadece ilgili başlık sayıldı


def test_relevance_keys_drops_generic():
    keys = _relevance_keys("AAPL", "Apple Inc")
    assert "aapl" in keys and "apple" in keys and "inc" not in keys
