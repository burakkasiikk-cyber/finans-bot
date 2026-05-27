import os
import time
import requests


def fetch_macro(finnhub_key: str, exchange_key: str) -> dict:
    result = {
        "usd_try": None, "eur_try": None, "gold_usd": None,
        "sp500": None, "sp500_change_pct": None,
        "bist100": None, "bist100_change_pct": None,
        "tr_interest_rate": float(os.environ.get("TR_INTEREST_RATE", "46.0")),
    }

    # Exchange rates — ExchangeRate-API
    try:
        r = requests.get(
            f"https://v6.exchangerate-api.com/v6/{exchange_key}/latest/USD",
            timeout=8
        )
        rates = r.json().get("conversion_rates", {})
        result["usd_try"] = round(rates.get("TRY", 0), 4)
        eur_usd = rates.get("EUR", 1)
        result["eur_try"] = round(result["usd_try"] / eur_usd, 4) if eur_usd else None
    except Exception:
        pass

    # Gold — Finnhub OANDA:XAU_USD
    try:
        r = requests.get(
            f"https://finnhub.io/api/v1/quote?symbol=OANDA:XAU_USD&token={finnhub_key}",
            timeout=8
        )
        time.sleep(0.5)
        data = r.json()
        result["gold_usd"] = data.get("c")
    except Exception:
        pass

    # S&P 500 — Finnhub SPY
    try:
        r = requests.get(
            f"https://finnhub.io/api/v1/quote?symbol=SPY&token={finnhub_key}",
            timeout=8
        )
        time.sleep(0.5)
        data = r.json()
        result["sp500"] = data.get("c")
        result["sp500_change_pct"] = data.get("dp")
    except Exception:
        pass

    # BIST 100 — yfinance (fiyat + günlük değişim)
    try:
        import yfinance as yf
        xu = yf.Ticker("XU100.IS")
        xu_info = xu.info
        last = xu_info.get("regularMarketPrice") or xu_info.get("currentPrice")
        if last is None:
            last = xu.fast_info.last_price
        result["bist100"] = round(float(last), 2) if last else None
        chg_pct = xu_info.get("regularMarketChangePercent")
        if chg_pct is not None:
            result["bist100_change_pct"] = round(float(chg_pct), 4)
    except Exception:
        pass

    # Altın — yfinance fallback (GC=F vadeli)
    if not result.get("gold_usd"):
        try:
            import yfinance as yf
            gold = yf.Ticker("GC=F")
            gold_price = gold.fast_info.last_price
            if gold_price:
                result["gold_usd"] = round(float(gold_price), 2)
        except Exception:
            pass

    return result
