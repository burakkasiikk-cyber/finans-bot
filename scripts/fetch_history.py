#!/usr/bin/env python3
"""
Trader modu için yalın fiyat geçmişi çekici — hem BIST hem ABD, tek kaynak: yfinance.

Skorlama tamamen teknik (price_history) olduğundan Finnhub'a / temel verilere
gerek yok. Bu modül her hisse için OHLCV bar listesi + güncel fiyat + günlük
değişim + isim döndürür. Skorlamayı scripts/technical.rescore_report yapar.
"""
import math

import yfinance as yf

from scripts.technical import backtest_signals

MIN_BARS = 30    # trader analizi için gereken asgari işlem günü (MA/MACD/ATR vb.)
STORE_BARS = 90  # report.json'da saklanan bar sayısı (grafik + göstergeler)
LIQ_MIN_TRY = 5_000_000   # BIST için asgari günlük işlem hacmi (TL) — altı 'düşük likidite'


def fetch_trader_stock(symbol: str, exchange: str = "BIST") -> dict:
    yticker = f"{symbol}.IS" if exchange == "BIST" else symbol
    try:
        ticker = yf.Ticker(yticker)
        hist = ticker.history(period="1y")   # backtest + uzun vade için 1 yıl
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

    full = [
        {
            "t": int(ts.timestamp()),
            "o": round(float(row["Open"]),  4),
            "h": round(float(row["High"]),  4),
            "l": round(float(row["Low"]),   4),
            "c": round(float(row["Close"]), 4),
            "v": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,
        }
        for ts, row in hist.iterrows()
        if row["Close"] == row["Close"] and row["Close"] > 0   # NaN ve sıfır eler
    ]

    if len(full) < MIN_BARS:
        return {"symbol": symbol, "error": f"yetersiz fiyat geçmişi ({len(full)} bar)"}

    # Backtest tüm 1 yıllık seri üzerinde; saklamak için son STORE_BARS bar
    backtest = backtest_signals(full)
    bars = full[-STORE_BARS:]

    # Fiyat ve günlük değişim — bar verisinden güvenilir şekilde (her zaman var)
    price = bars[-1]["c"]
    change_pct = None
    if len(bars) >= 2 and bars[-2]["c"]:
        change_pct = round((bars[-1]["c"] / bars[-2]["c"] - 1) * 100, 2)

    # İsim ve (varsa) daha güncel anlık fiyat/değişim — info best-effort
    name = symbol
    try:
        info = ticker.info
        name = info.get("longName") or info.get("shortName") or symbol
        live = info.get("currentPrice") or info.get("regularMarketPrice")
        if live and live == live:
            price = round(float(live), 4)
        cp = info.get("regularMarketChangePercent")
        if cp is not None and not (isinstance(cp, float) and math.isnan(cp)):
            change_pct = round(float(cp), 2)
    except Exception:
        pass

    # Yaklaşan bilanço tarihi (best-effort) — pozisyon için olay riski
    next_earnings = None
    try:
        import datetime as _dt
        cal = ticker.calendar
        ed = None
        if isinstance(cal, dict):
            ed = cal.get("Earnings Date")
            if isinstance(ed, (list, tuple)) and ed:
                ed = ed[0]
        if ed is not None:
            d = ed if isinstance(ed, _dt.date) else None
            if d:
                days = (d - _dt.date.today()).days
                if 0 <= days <= 30:
                    next_earnings = {"date": d.isoformat(), "days": days}
    except Exception:
        pass

    # Likidite: son 20 günün ortalama işlem hacmi (fiyat × adet)
    recent = bars[-20:]
    turnover = sum(b["c"] * b["v"] for b in recent) / len(recent) if recent else 0
    if exchange == "BIST":
        liquidity = "low" if turnover < LIQ_MIN_TRY else "ok"
    else:
        liquidity = "ok"   # ABD evreni büyük şirketler — likit

    return {
        "symbol":        symbol,
        "name":          name,
        "exchange":      exchange,
        "price":         round(float(price), 2),
        "change_pct":    change_pct if change_pct is not None else 0.0,
        "price_history": bars,
        "backtest":      backtest,
        "liquidity":     liquidity,
        "turnover":      round(turnover),
        "next_earnings": next_earnings,
    }
