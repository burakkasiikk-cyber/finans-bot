#!/usr/bin/env python3
"""
Trader modu için yalın fiyat geçmişi çekici — hem BIST hem ABD, tek kaynak: yfinance.

Skorlama tamamen teknik (price_history) olduğundan Finnhub'a / temel verilere
gerek yok. Bu modül her hisse için OHLCV bar listesi + güncel fiyat + günlük
değişim + isim döndürür. Skorlamayı scripts/technical.rescore_report yapar.
"""
import math

import yfinance as yf

MIN_BARS = 30   # trader analizi için gereken asgari işlem günü (MA/MACD/ATR vb.)


def fetch_trader_stock(symbol: str, exchange: str = "BIST") -> dict:
    yticker = f"{symbol}.IS" if exchange == "BIST" else symbol
    try:
        ticker = yf.Ticker(yticker)
        hist = ticker.history(period="3mo")
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

    bars = [
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
    ][-60:]

    if len(bars) < MIN_BARS:
        return {"symbol": symbol, "error": f"yetersiz fiyat geçmişi ({len(bars)} bar)"}

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

    return {
        "symbol":        symbol,
        "name":          name,
        "exchange":      exchange,
        "price":         round(float(price), 2),
        "change_pct":    change_pct if change_pct is not None else 0.0,
        "price_history": bars,
    }
