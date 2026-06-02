#!/usr/bin/env python3
"""
Teknik skorlama motoru — TRADER MODU.

Kısa vadeli alım-satım için hisseleri yalnızca fiyat geçmişinden (price_history)
hesaplanan teknik göstergelerle puanlar. Temel veriler (F/K, ROE vb.) kullanılmaz.

Boyutlar:
  • trend       (40%) — MA20/MA50 yapısı + MACD yönü
  • momentum    (40%) — RSI + 1 hafta / 1 ay getiri
  • volatilite  (20%) — Bollinger bandı konumu

Frontend'deki (index.html) gösterge matematiğiyle BİREBİR aynıdır ki
ekranda görünen RSI/MACD/Bollinger ile skor tutarlı olsun.

⚠️ Yatırım tavsiyesi değildir — kural tabanlı bir teknik sinyal hesaplayıcıdır.
"""
from typing import Optional, List

# Verdict bantları — artık "teknik sinyal gücü" etiketleri
VERDICT_BANDS = [
    (75, "GÜÇLÜ AL",  "strong_buy"),
    (60, "AL",         "buy"),
    (45, "TUT / NÖTR", "hold"),
    (32, "SAT",        "sell"),
    (0,  "GÜÇLÜ SAT",  "strong_sell"),
]

WEIGHTS = {"trend": 0.40, "momentum": 0.40, "volatility": 0.20}


# ──────────────────────────── Göstergeler ────────────────────────────
def _ema_series(data: List[float], period: int) -> List[float]:
    k = 2 / (period + 1)
    out = [data[0]]
    e = data[0]
    for x in data[1:]:
        e = x * k + e * (1 - k)
        out.append(e)
    return out


def rsi(closes: List[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains = losses = 0.0
    for i in range(len(closes) - period, len(closes)):
        d = closes[i] - closes[i - 1]
        if d > 0:
            gains += d
        else:
            losses -= d
    ag, al = gains / period, losses / period
    if al == 0:
        return 100.0
    return round(100 - 100 / (1 + ag / al), 1)


def macd(closes: List[float]) -> Optional[dict]:
    """MACD(12,26,9). Döndürür: {macd, signal, hist, sig: AL/SAT/NÖTR}."""
    if len(closes) < 26:
        return None
    e12 = _ema_series(closes, 12)
    e26 = _ema_series(closes, 26)
    macd_line = [a - b for a, b in zip(e12, e26)]
    signal = _ema_series(macd_line, 9)
    hist = macd_line[-1] - signal[-1]
    if hist > 0:
        sig = "AL"
    elif hist < 0:
        sig = "SAT"
    else:
        sig = "NÖTR"
    return {"macd": macd_line[-1], "signal": signal[-1], "hist": hist, "sig": sig}


def bollinger_pos(closes: List[float], period: int = 20) -> Optional[float]:
    """Fiyatın Bollinger bandı içindeki konumu (0=alt band, 1=üst band)."""
    if len(closes) < period:
        return None
    sl = closes[-period:]
    sma = sum(sl) / period
    var = sum((x - sma) ** 2 for x in sl) / period
    std = var ** 0.5
    if std == 0:
        return 0.5
    return (closes[-1] - (sma - 2 * std)) / (4 * std)


def boll_label(pos: Optional[float]) -> str:
    if pos is None:
        return "—"
    if pos > 0.9:
        return "Üst Band"
    if pos > 0.7:
        return "Orta-Üst"
    if pos > 0.3:
        return "Orta"
    if pos > 0.1:
        return "Orta-Alt"
    return "Alt Band"


def ma_signal(closes: List[float]) -> str:
    if len(closes) < 20:
        return "Veri Yok"
    last = closes[-1]
    if len(closes) >= 50:
        ma20 = sum(closes[-20:]) / 20
        ma50 = sum(closes[-50:]) / 50
        if last > ma20 > ma50:
            return "Golden Cross"
        if last < ma20 < ma50:
            return "Death Cross"
        return "Yükseliş" if last > ma20 else "Düşüş"
    ma20 = sum(closes[-20:]) / 20
    return "Yükseliş" if last > ma20 else "Düşüş"


def pct_return(closes: List[float], n: int) -> Optional[float]:
    if len(closes) > n and closes[-1 - n]:
        return round((closes[-1] / closes[-1 - n] - 1) * 100, 2)
    return None


def volatility_pct(closes: List[float], n: int = 20) -> Optional[float]:
    """Son n günün günlük getiri standart sapması (% cinsinden)."""
    if len(closes) < n + 1:
        n = len(closes) - 1
    if n < 2:
        return None
    rets = [(closes[i] / closes[i - 1] - 1) for i in range(len(closes) - n, len(closes)) if closes[i - 1]]
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / len(rets)
    return round((var ** 0.5) * 100, 2)


# ──────────────────────────── Alt skorlar ────────────────────────────
def _ret_score(v: Optional[float], t: List[float]) -> Optional[int]:
    if v is None:
        return None
    a, b, c, d = t
    return 92 if v >= a else 74 if v >= b else 55 if v >= c else 38 if v >= d else 18


def _trend_score(closes: List[float]) -> Optional[int]:
    if len(closes) < 20:
        return None
    last = closes[-1]
    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
    if ma50:
        if last > ma20 > ma50:
            score = 88
        elif last > ma20 and ma20 <= ma50:
            score = 64
        elif last <= ma20 and last > ma50:
            score = 46
        else:
            score = 22
    else:
        score = 70 if last > ma20 else 35
    m = macd(closes)
    if m:
        if m["hist"] > 0 and m["macd"] > 0:
            score = min(100, score + 10)
        elif m["hist"] < 0 and m["macd"] < 0:
            score = max(0, score - 10)
    return round(score)


def _momentum_score(closes: List[float]) -> Optional[int]:
    parts = []
    r = rsi(closes)
    if r is not None:
        # Trend takipçisi için ideal bölge 55–70; >80 aşırı alım (riskli), <30 aşırı satım
        if 55 <= r <= 70:
            parts.append(84)
        elif 70 < r <= 80:
            parts.append(62)
        elif r > 80:
            parts.append(42)
        elif 45 <= r < 55:
            parts.append(64)
        elif 35 <= r < 45:
            parts.append(48)
        elif 30 <= r < 35:
            parts.append(44)
        else:  # <30 aşırı satım — tepki yükselişi ihtimali
            parts.append(52)
    s1w = _ret_score(pct_return(closes, 5), [4, 1, -1, -4])
    s1m = _ret_score(pct_return(closes, 21), [10, 3, -3, -10])
    parts += [p for p in (s1w, s1m) if p is not None]
    return round(sum(parts) / len(parts)) if parts else None


def _volatility_score(closes: List[float]) -> Optional[int]:
    """Bollinger konumu — momentum bağlamında bant pozisyonu."""
    pos = bollinger_pos(closes)
    if pos is None:
        return None
    if pos > 0.95:
        return 58   # üst banda yapışık — aşırı uzamış
    if pos > 0.75:
        return 80
    if pos > 0.55:
        return 68
    if pos > 0.35:
        return 52
    if pos > 0.15:
        return 42
    return 34


def _risk_from_vol(vol: Optional[float]) -> str:
    if vol is None:
        return "medium"
    if vol >= 4.0:
        return "high"
    if vol >= 2.0:
        return "medium"
    return "low"


def verdict_of(score: Optional[int]) -> tuple:
    if score is None:
        return ("VERİ YETERSİZ", "insufficient")
    for min_score, label, key in VERDICT_BANDS:
        if score >= min_score:
            return (label, key)
    return (VERDICT_BANDS[-1][1], VERDICT_BANDS[-1][2])


# ──────────────────────────── Ana fonksiyon ────────────────────────────
def score_from_history(price_history: list) -> Optional[dict]:
    """price_history (OHLC bar listesi) → teknik skor + boyutlar.

    Yeterli veri yoksa None döner (çağıran eski skoru korumalı)."""
    closes = [b["c"] for b in (price_history or []) if b.get("c")]
    if len(closes) < 20:
        return None

    trend = _trend_score(closes)
    mom = _momentum_score(closes)
    vol_sc = _volatility_score(closes)
    vol_pct = volatility_pct(closes)

    m = macd(closes)
    dims = {
        "trend": {
            "score": trend,
            "metrics": {"ma": ma_signal(closes), "macd": m["sig"] if m else "—"},
        },
        "momentum": {
            "score": mom,
            "metrics": {
                "rsi": rsi(closes),
                "ret_1w": pct_return(closes, 5),
                "ret_1m": pct_return(closes, 21),
            },
        },
        "volatility": {
            "score": vol_sc,
            "metrics": {"boll": boll_label(bollinger_pos(closes)), "vol": vol_pct},
        },
    }

    weighted, total_w = 0.0, 0.0
    for key, w in WEIGHTS.items():
        s = dims[key]["score"]
        if s is not None:
            weighted += s * w
            total_w += w
    overall = round(weighted / total_w) if total_w else None
    label, key = verdict_of(overall)

    return {
        "score": overall,
        "verdict": label,
        "verdict_key": key,
        "risk": _risk_from_vol(vol_pct),
        "dimensions": dims,
    }


def rescore_report(report: dict) -> int:
    """Rapordaki her hisseyi price_history'den teknik olarak yeniden skorla.

    score / verdict / verdict_key / risk / dimensions alanlarını günceller.
    Döndürür: yeniden skorlanan hisse sayısı."""
    n = 0
    for s in report.get("stocks", []):
        if "error" in s:
            continue
        res = score_from_history(s.get("price_history"))
        if res:
            s.update(res)
            s["pros"] = []
            s["cons"] = []
            n += 1
    # En yüksek skora göre sırala, top3 / risk uyarılarını tazele
    valid = [s for s in report["stocks"] if "error" not in s and s.get("score") is not None]
    errors = [s for s in report["stocks"] if "error" in s or s.get("score") is None]
    valid.sort(key=lambda s: s["score"], reverse=True)
    report["stocks"] = valid + errors
    report["top3"] = [s["symbol"] for s in valid[:3]]
    report["risk_alerts"] = [s["symbol"] for s in valid if s.get("risk") == "high"]
    return n


if __name__ == "__main__":
    import json
    from pathlib import Path

    p = Path("data/report.json")
    report = json.loads(p.read_text())
    n = rescore_report(report)
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"✅ {n} hisse teknik olarak yeniden skorlandı (trader modu).")
