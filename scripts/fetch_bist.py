import yfinance as yf
from scripts.scoring import score_metric, dim_score, verdict_of, risk_level, WEIGHTS


def fetch_bist_stock(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(f"{symbol}.IS")
        info = ticker.info
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

    price = info.get("currentPrice") or info.get("regularMarketPrice")
    change_pct = info.get("regularMarketChangePercent")

    def pct(v):
        return round(v * 100, 2) if v is not None else None

    pe = info.get("trailingPE")
    pb = info.get("priceToBook")
    roe = pct(info.get("returnOnEquity"))
    rev_g = pct(info.get("revenueGrowth"))
    de = info.get("debtToEquity")
    # yfinance gives debtToEquity as 100x (85.0 = 0.85 ratio)
    debt_equity = round(de / 100, 2) if de is not None else None
    cur_ratio = info.get("currentRatio")

    high52 = info.get("fiftyTwoWeekHigh")
    low52 = info.get("fiftyTwoWeekLow")
    ret52 = pct(info.get("52WeekChange"))

    range_pos = None
    if price and high52 and low52 and high52 != low52:
        range_pos = round((price - low52) / (high52 - low52) * 100, 1)

    # Fiyat geçmişi — skorlamadan ÖNCE çek ki kısa vadeli momentum hesaplanabilsin
    try:
        hist = ticker.history(period="3mo")
        price_history = [
            {
                "t": int(ts.timestamp()),
                "o": round(float(row["Open"]),  2),
                "h": round(float(row["High"]),  2),
                "l": round(float(row["Low"]),   2),
                "c": round(float(row["Close"]), 2),
            }
            for ts, row in hist.iterrows()
            if row["Close"] > 0
        ][-60:]
    except Exception:
        price_history = []

    # Kısa vadeli momentum (günlük güncellenir) — son kapanışa göre 1 hafta / 1 ay getiri
    def _ret(closes, n):
        if len(closes) > n and closes[-1-n]:
            return round((closes[-1] / closes[-1-n] - 1) * 100, 2)
        return None
    closes = [b["c"] for b in price_history]
    ret_1w = _ret(closes, 5)   # ~5 işlem günü
    ret_1m = _ret(closes, 21)  # ~21 işlem günü

    val_raw  = {"pe": pe, "pb": pb}
    prof_raw = {"roe": roe}
    grow_raw = {"rev_growth": rev_g}
    hlth_raw = {"current_ratio": cur_ratio, "debt_equity": debt_equity}
    tech_raw = {"ret52": ret52, "range_pos": range_pos, "ret_1m": ret_1m, "ret_1w": ret_1w}

    def score_dim(raw):
        return {k: score_metric(v, k) for k, v in raw.items()}

    dims = {
        "valuation": {"score": dim_score(score_dim(val_raw)),  "metrics": val_raw},
        "profit":    {"score": dim_score(score_dim(prof_raw)), "metrics": prof_raw},
        "growth":    {"score": dim_score(score_dim(grow_raw)), "metrics": grow_raw},
        "health":    {"score": dim_score(score_dim(hlth_raw)), "metrics": hlth_raw},
        "technical": {"score": dim_score(score_dim(tech_raw)), "metrics": tech_raw},
        "analyst":   {"score": None, "metrics": {}},
    }

    weighted, total_w = 0.0, 0.0
    for key, w in WEIGHTS.items():
        s = dims[key]["score"]
        if s is not None:
            weighted += s * w
            total_w += w
    overall = round(weighted / total_w) if total_w else None

    verdict_label, verdict_key = verdict_of(overall)

    return {
        "symbol":        symbol,
        "name":          info.get("longName", symbol),
        "exchange":      "BIST",
        "price":         price,
        "change_pct":    change_pct,
        "score":         overall,
        "verdict":       verdict_label,
        "verdict_key":   verdict_key,
        "risk":          risk_level(overall),
        "dimensions":    dims,
        "pros":          [],
        "cons":          [],
        "dividends":     [],
        "price_history": price_history,
    }
