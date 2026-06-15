"""apply_market_context — rejim + göreli güç hem analyze hem update_prices'ta taze kalmalı."""
from scripts.analyze import apply_market_context


def _stock(sym, closes):
    return {"symbol": sym, "exchange": "BIST",
            "price_history": [{"t": i, "c": c} for i, c in enumerate(closes)]}


def test_applies_fresh_regime_and_rel_strength():
    report = {"stocks": [_stock("UP", [10 + i * 0.2 for i in range(30)])],
              "market_regime": {"bist": {"trend": "düşüş", "adj": -3}}}
    ctx = {"bist": {"trend": "yatay", "ret_1m": -5.0, "adj": 0, "above_ma50": True}}
    apply_market_context(report, ctx=ctx)
    # rejim taze değerle GÜNCELLENİR (bayat "düşüş" yok olur)
    assert report["market_regime"]["bist"]["trend"] == "yatay"
    assert report["regime_adj"]["BIST"] == 0
    # göreli güç: hisse +12.6% (21g), endeks -5% → rel +17.6 > 5 → rel_adj 3
    s = report["stocks"][0]
    assert s["rel_strength"] > 5 and s["rel_adj"] == 3


def test_keeps_existing_regime_when_fetch_unknown():
    # endeks verisi çekilemezse (bilinmiyor) eski sağlam rejim KORUNUR
    report = {"stocks": [_stock("X", [5] * 30)],
              "market_regime": {"bist": {"trend": "yükseliş", "adj": 2}},
              "regime_adj": {"BIST": 2}}
    ctx = {"bist": {"trend": "bilinmiyor", "ret_1m": None, "adj": 0, "above_ma50": None}}
    apply_market_context(report, ctx=ctx)
    assert report["market_regime"]["bist"]["trend"] == "yükseliş"
    assert report["regime_adj"]["BIST"] == 2


def test_handles_short_history():
    report = {"stocks": [_stock("S", [10, 11, 12])],
              "market_regime": {"bist": {"trend": "yatay", "adj": 0}}}
    ctx = {"bist": {"trend": "yatay", "ret_1m": -2.0, "adj": 0, "above_ma50": True}}
    apply_market_context(report, ctx=ctx)
    s = report["stocks"][0]
    assert s["rel_strength"] is None and s["rel_adj"] == 0
