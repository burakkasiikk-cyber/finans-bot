import time
import requests
from scripts.scoring import score_metric, dim_score, verdict_of, risk_level, analyst_score, WEIGHTS

BASE = "https://finnhub.io/api/v1"


def finnhub_get(path: str, api_key: str) -> dict:
    sep = "&" if "?" in path else "?"
    r = requests.get(f"{BASE}{path}{sep}token={api_key}", timeout=10)
    r.raise_for_status()
    time.sleep(0.5)  # respect 60 req/min limit
    return r.json()


def _range_pos(price, low52, high52):
    """Position of price within 52-week range (0-100)."""
    if not price or not low52 or not high52 or high52 == low52:
        return None
    return round((price - low52) / (high52 - low52) * 100, 1)


def fetch_us_stock(symbol: str, api_key: str) -> dict:
    try:
        quote   = finnhub_get(f"/quote?symbol={symbol}", api_key)
        profile = finnhub_get(f"/stock/profile2?symbol={symbol}", api_key)
        metrics = finnhub_get(f"/stock/metric?symbol={symbol}&metric=all", api_key)
        rec     = finnhub_get(f"/stock/recommendation?symbol={symbol}", api_key)
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

    m = metrics.get("metric", {})
    price = quote.get("c")

    val_raw  = {"pe": m.get("peTTM"),    "pb": m.get("pbAnnual"),   "ps": m.get("psTTM")}
    prof_raw = {"roe": m.get("roeTTM"),  "roa": m.get("roaTTM"),
                "net_margin": m.get("netProfitMarginTTM"),
                "gross_margin": m.get("grossMarginTTM")}
    grow_raw = {"rev_growth": m.get("revenueGrowthTTMYoy"),
                "eps_growth": m.get("epsGrowthTTMYoy"),
                "rev_5y": m.get("revenueGrowth5Y")}
    hlth_raw = {"current_ratio": m.get("currentRatioAnnual"),
                "debt_equity": m.get("totalDebt/totalEquityAnnual"),
                "quick_ratio": m.get("quickRatioAnnual")}
    tech_raw = {"ret52":    m.get("52WeekPriceReturnDaily"),
                "ret13":    m.get("13WeekPriceReturnDaily"),
                "range_pos": _range_pos(price, m.get("52WeekLow"), m.get("52WeekHigh"))}

    def score_dim(raw):
        return {k: score_metric(v, k) for k, v in raw.items()}

    val_sc  = score_dim(val_raw)
    prof_sc = score_dim(prof_raw)
    grow_sc = score_dim(grow_raw)
    hlth_sc = score_dim(hlth_raw)
    tech_sc = score_dim(tech_raw)

    latest_rec = rec[0] if rec else {}
    an_sc = analyst_score(latest_rec.get("buy", 0),
                          latest_rec.get("hold", 0),
                          latest_rec.get("sell", 0))

    dims = {
        "valuation": {"score": dim_score(val_sc),  "metrics": val_raw},
        "profit":    {"score": dim_score(prof_sc),  "metrics": prof_raw},
        "growth":    {"score": dim_score(grow_sc),  "metrics": grow_raw},
        "health":    {"score": dim_score(hlth_sc),  "metrics": hlth_raw},
        "technical": {"score": dim_score(tech_sc),  "metrics": tech_raw},
        "analyst":   {"score": an_sc, "metrics": {
            "buy": latest_rec.get("buy", 0),
            "hold": latest_rec.get("hold", 0),
            "sell": latest_rec.get("sell", 0)
        }},
    }

    weighted, total_w = 0.0, 0.0
    for key, w in WEIGHTS.items():
        s = dims[key]["score"]
        if s is not None:
            weighted += s * w
            total_w  += w
    overall = round(weighted / total_w) if total_w else None

    verdict_label, verdict_key = verdict_of(overall)

    DIM_NAMES = {
        "valuation": "Değerleme", "profit": "Kârlılık", "growth": "Büyüme",
        "health": "Finansal Sağlık", "technical": "Teknik/Momentum", "analyst": "Analist Görüşü"
    }
    scored_dims = [(k, v["score"]) for k, v in dims.items() if v["score"] is not None]
    scored_dims.sort(key=lambda x: x[1], reverse=True)
    pros = [f"{DIM_NAMES[k]} skoru güçlü ({s}/100)" for k, s in scored_dims[:2] if s >= 70]
    cons = [f"{DIM_NAMES[k]} skoru zayıf ({s}/100)" for k, s in scored_dims[-2:] if s < 50]

    return {
        "symbol":      symbol,
        "name":        profile.get("name", symbol),
        "exchange":    "NASDAQ",
        "price":       price,
        "change_pct":  quote.get("dp"),
        "score":       overall,
        "verdict":     verdict_label,
        "verdict_key": verdict_key,
        "risk":        risk_level(overall),
        "dimensions":  dims,
        "pros":        pros,
        "cons":        cons,
        "dividends":   [],
    }
