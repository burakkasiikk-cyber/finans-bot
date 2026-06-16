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
    assert set(["trend", "timing", "momentum", "setup"]).issubset(res["dimensions"])
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


# ── Güvenlik kapıları: rejim freni + backtest kapısı + hacim teyidi ──
def _healthy_uptrend(strong_volume=True):
    """Yükseliş + yatay konsolidasyon — organik olarak AL/GÜÇLÜ AL üretir.

    strong_volume=True: son günler hacimli (hacim teyidi VAR) — AL kalabilir.
    strong_volume=False: hacim sönük — hacim kapısına takılmalı."""
    closes = [round(10 + i * 0.25, 2) for i in range(50)]
    closes += [22.5, 22.3, 22.4, 22.2, 22.3, 22.1, 22.2, 22.0, 22.1, 22.0]
    bars = _bars(closes)
    if strong_volume:
        for b in bars[-5:]:
            b["v"] = 3000   # 5g ort 3000 / 20g ort 1500 = 2.0 ≥ 1.2
    return bars


def _one_stock_report(stock_extra=None, **report_extra):
    """AL/GÜÇLÜ AL üreten tek hisselik rapor iskeleti."""
    stock = {"symbol": "UP", "exchange": "BIST", "price_history": _healthy_uptrend()}
    stock.update(stock_extra or {})
    report = {"stocks": [stock]}
    report.update(report_extra)
    return report


def test_regime_gate_buy_capped_in_downtrend():
    # Endeks düşüş rejimindeyken teknik AL → TUT'a çekilir (kovalama önlenir)
    report = _one_stock_report(
        market_regime={"bist": {"trend": "düşüş", "above_ma50": False}},
        regime_adj={"BIST": -3},
    )
    rescore_report(report)
    s = report["stocks"][0]
    assert s["verdict_key"] == "hold"
    assert "regime" in s["gates"]
    assert s["signal"]["action"] == "BEKLE"
    # Rozet ile sinyal tutarlılığı korunur
    assert s["verdict_key"] == s["signal"]["key"]


def test_regime_gate_inactive_in_uptrend():
    report = _one_stock_report(
        market_regime={"bist": {"trend": "yükseliş", "above_ma50": True}},
        regime_adj={"BIST": 2},
    )
    rescore_report(report)
    s = report["stocks"][0]
    assert s["verdict_key"] in ("buy", "strong_buy")
    assert s["gates"] == []


def test_backtest_gate_low_winrate_capped():
    # Hissenin kendi geçmiş sinyal isabeti zayıfsa AL rozeti verilmez (BJKAS vakası)
    report = _one_stock_report(
        {"backtest": {"n": 8, "win_rate": 33, "avg_ret": -2.5, "horizon": 10}}
    )
    rescore_report(report)
    s = report["stocks"][0]
    assert s["verdict_key"] == "hold"
    assert "backtest" in s["gates"]


def test_backtest_gate_ignores_small_sample():
    # 5'ten az işlem istatistiksel gürültü — kapı tetiklenmez
    report = _one_stock_report(
        {"backtest": {"n": 3, "win_rate": 33, "avg_ret": -2.5, "horizon": 10}}
    )
    rescore_report(report)
    assert report["stocks"][0]["verdict_key"] in ("buy", "strong_buy")


def test_volume_gate_blocks_buy_without_confirmation():
    # Lab kanıtı (2y): hacim teyidi isabeti %51→%53 yükseltti — AL için şart
    report = _one_stock_report(
        {"price_history": _healthy_uptrend(strong_volume=False)},
        market_regime={"bist": {"trend": "yükseliş", "above_ma50": True}},
        regime_adj={"BIST": 2},
    )
    rescore_report(report)
    s = report["stocks"][0]
    assert s["verdict_key"] == "hold"
    assert "hacim" in s["gates"]


def test_volume_gate_passes_with_confirmation():
    report = _one_stock_report(
        market_regime={"bist": {"trend": "yükseliş", "above_ma50": True}},
        regime_adj={"BIST": 2},
    )
    rescore_report(report)
    s = report["stocks"][0]
    assert s["verdict_key"] in ("buy", "strong_buy")
    assert s["gates"] == []


# ── Dip dönüşü adayları (düşüş/yatay rejimde izleme listesi) ──
def _oversold_turning():
    """Uzun düşüş + son gün yeşil — RSI<30 + dönüş teyidi."""
    closes = [round(30 - i * 0.35, 2) for i in range(58)]
    closes.append(round(closes[-1] + 0.3, 2))   # yeşil gün
    return _bars(closes)


def test_dip_candidates_listed_in_downtrend():
    report = {
        "stocks": [{"symbol": "DIP", "exchange": "BIST",
                    "price_history": _oversold_turning()}],
        "market_regime": {"bist": {"trend": "düşüş", "above_ma50": False}},
        "regime_adj": {"BIST": -3},
    }
    rescore_report(report)
    assert [d["symbol"] for d in report["dip_adaylari"]] == ["DIP"]
    d = report["dip_adaylari"][0]
    assert d["rsi"] is not None and d["rsi"] < 30


def test_dip_candidates_include_trade_levels():
    # Tepki trade'i tanımlı riskle oynanır: giriş/stop/hedef/RR aday üstünde gelir
    report = {
        "stocks": [{"symbol": "DIP", "exchange": "BIST",
                    "price_history": _oversold_turning()}],
        "market_regime": {"bist": {"trend": "düşüş", "above_ma50": False}},
        "regime_adj": {"BIST": -3},
    }
    rescore_report(report)
    d = report["dip_adaylari"][0]
    assert d["stop"] < d["entry"] < d["target"]
    assert d["rr"] is None or d["rr"] > 0


def test_dip_candidates_empty_in_sideways():
    # Lab kanıtı (2y, iki yarı): yatay rejimde dip adayı tutarlı şekilde KAYBEDİYOR
    # (%39/-0.50%, %37/-0.74%) → yalnız düşüş rejiminde gösterilir
    report = {
        "stocks": [{"symbol": "DIP", "exchange": "BIST",
                    "price_history": _oversold_turning()}],
        "market_regime": {"bist": {"trend": "yatay", "above_ma50": True}},
        "regime_adj": {"BIST": 0},
    }
    rescore_report(report)
    assert report["dip_adaylari"] == []


def test_dip_candidates_empty_in_uptrend():
    report = {
        "stocks": [{"symbol": "DIP", "exchange": "BIST",
                    "price_history": _oversold_turning()}],
        "market_regime": {"bist": {"trend": "yükseliş", "above_ma50": True}},
        "regime_adj": {"BIST": 2},
    }
    rescore_report(report)
    assert report["dip_adaylari"] == []


def test_dip_candidates_require_green_day():
    closes = [round(30 - i * 0.35, 2) for i in range(59)]   # son gün de kırmızı
    report = {
        "stocks": [{"symbol": "DWN", "exchange": "BIST",
                    "price_history": _bars(closes)}],
        "market_regime": {"bist": {"trend": "düşüş", "above_ma50": False}},
        "regime_adj": {"BIST": -3},
    }
    rescore_report(report)
    assert report["dip_adaylari"] == []


def test_gates_do_not_touch_sell_verdicts():
    # Kapılar yalnızca AL/GÜÇLÜ AL'i kısıtlar; SAT olduğu gibi kalır
    report = {
        "stocks": [{"symbol": "DN", "exchange": "BIST", "price_history": _downtrend()}],
        "market_regime": {"bist": {"trend": "düşüş", "above_ma50": False}},
        "regime_adj": {"BIST": -3},
    }
    rescore_report(report)
    s = report["stocks"][0]
    assert s["verdict_key"] in ("sell", "strong_sell", "hold")
    assert s["gates"] == []


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


# ── Giriş zamanı (timing) ──
from scripts.technical import timing_state


def test_timing_penalizes_overbought_parabolic():
    # Hızlanan parabolik yükseliş → aşırı alım, düşük timing skoru
    closes = [round(10 * (1.04 ** i), 2) for i in range(60)]
    res = timing_state(closes, _bars(closes))
    assert res["score"] is not None and res["score"] <= 40
    assert "alım" in res["durum"].lower()


def test_timing_pullback_beats_parabolic():
    # Sağlıklı geri çekilme, parabolik aşırı alımdan DAHA İYİ giriş skoru almalı
    parabolic = [round(10 * (1.04 ** i), 2) for i in range(60)]
    pull = [round(10 + i * 0.2, 2) for i in range(55)]
    pull += [round(pull[-1] - 0.25 * j, 2) for j in range(1, 6)]
    s_par = timing_state(parabolic, _bars(parabolic))["score"]
    s_pull = timing_state(pull, _bars(pull))["score"]
    assert s_pull > s_par   # geri çekilme > parabolik kovalama


# ── Backtest ──
from scripts.technical import backtest_signals, aggregate_backtest


def test_backtest_returns_stats_on_uptrend():
    closes = [round(10 + i * 0.1 + (i % 5) * 0.2, 2) for i in range(120)]
    bt = backtest_signals(_bars(closes), horizon=10)
    assert bt is not None
    assert 0 <= bt["win_rate"] <= 100 and bt["n"] >= 3
    assert isinstance(bt["avg_ret"], float)


def test_backtest_insufficient_returns_none():
    assert backtest_signals(_bars([10, 11, 12] * 5)) is None


def test_aggregate_backtest_combines():
    report = {"stocks": [
        {"symbol": "A", "backtest": {"n": 10, "win_rate": 60, "avg_ret": 2.0}},
        {"symbol": "B", "backtest": {"n": 30, "win_rate": 40, "avg_ret": -1.0}},
        {"symbol": "C", "error": "x"},
    ]}
    agg = aggregate_backtest(report)
    assert agg["trades"] == 40 and agg["stocks"] == 2
    assert agg["win_rate"] == 45   # (60*10+40*30)/40
