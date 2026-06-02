from typing import Optional

THRESHOLDS = {
    "pe":           {"dir": "down", "t": [15, 25, 40, 60]},
    "pb":           {"dir": "down", "t": [1.5, 3, 6, 10]},
    "ps":           {"dir": "down", "t": [2, 5, 10, 18]},
    "roe":          {"dir": "up",   "t": [20, 12, 5, 0]},
    "roa":          {"dir": "up",   "t": [12, 7, 3, 0]},
    "net_margin":   {"dir": "up",   "t": [20, 10, 3, 0]},
    "gross_margin": {"dir": "up",   "t": [50, 35, 20, 10]},
    "rev_growth":   {"dir": "up",   "t": [20, 8, 2, -5]},
    "eps_growth":   {"dir": "up",   "t": [20, 8, 0, -10]},
    "rev_5y":       {"dir": "up",   "t": [15, 8, 3, 0]},
    "current_ratio":{"dir": "up",   "t": [2, 1.5, 1, 0.8]},
    "debt_equity":  {"dir": "down", "t": [0.5, 1, 2, 3]},
    "quick_ratio":  {"dir": "up",   "t": [1.5, 1, 0.7, 0.4]},
    "ret52":        {"dir": "up",   "t": [25, 8, -5, -25]},
    "ret13":        {"dir": "up",   "t": [15, 3, -5, -15]},
    "ret_1m":       {"dir": "up",   "t": [10, 3, -3, -10]},   # ~21 işlem günü momentum (günlük güncellenir)
    "ret_1w":       {"dir": "up",   "t": [4, 1, -1, -4]},     # ~5 işlem günü momentum (günlük güncellenir)
    "range_pos":    {"dir": "up",   "t": [60, 40, 20, 5]},
}

WEIGHTS = {
    "valuation": 0.18,
    "profit":    0.17,
    "growth":    0.15,
    "health":    0.15,
    "technical": 0.25,   # momentum ağırlığı artırıldı — kararlar fiyat hareketine daha duyarlı
    "analyst":   0.10,
}

VERDICT_BANDS = [
    (75, "GÜÇLÜ AL",  "strong_buy"),
    (60, "AL",         "buy"),
    (45, "TUT / NÖTR", "hold"),
    (32, "SAT",        "sell"),
    (0,  "GÜÇLÜ SAT",  "strong_sell"),
]


def score_metric(value: Optional[float], key: str) -> Optional[int]:
    """Score a single metric 0-100. Returns None if value is missing."""
    if value is None or (isinstance(value, float) and value != value):  # NaN check
        return None
    cfg = THRESHOLDS.get(key)
    if not cfg:
        return None
    a, b, c, d = cfg["t"]
    if cfg["dir"] == "up":
        return 92 if value >= a else 74 if value >= b else 55 if value >= c else 38 if value >= d else 18
    else:  # down
        return 92 if value <= a else 74 if value <= b else 55 if value <= c else 38 if value <= d else 18


def dim_score(metric_scores: dict) -> Optional[int]:
    """Average score for a dimension, ignoring None values."""
    valid = [v for v in metric_scores.values() if v is not None]
    return round(sum(valid) / len(valid)) if valid else None


def verdict_of(score: Optional[int]) -> tuple:
    """Convert score to (label, key) verdict tuple."""
    if score is None:
        return ("VERİ YETERSİZ", "insufficient")
    for min_score, label, key in VERDICT_BANDS:
        if score >= min_score:
            return (label, key)
    return (VERDICT_BANDS[-1][1], VERDICT_BANDS[-1][2])


def risk_level(score: Optional[int]) -> str:
    """Risk level: low / medium / high based on score."""
    if score is None:
        return "unknown"
    if score >= 60:
        return "low"
    if score >= 40:
        return "medium"
    return "high"


def analyst_score(buy: int, hold: int, sell: int) -> Optional[int]:
    """Score from Buy/Hold/Sell consensus. %75+ → 92, %50+ → 74, %30+ → 55, %15+ → 38, else 18."""
    total = buy + hold + sell
    if total == 0:
        return None
    pct = buy / total * 100
    return 92 if pct >= 75 else 74 if pct >= 50 else 55 if pct >= 30 else 38 if pct >= 15 else 18
