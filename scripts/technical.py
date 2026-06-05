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

# "Giriş zamanı" (timing) ana boyut: aşırı alımı cezalandırıp iyi girişi ödüllendirir.
# Böylece skor "en çok pumplanmış" değil, "şu an girmek için iyi konumda" olanı öne çıkarır.
WEIGHTS = {"trend": 0.30, "timing": 0.30, "momentum": 0.20, "setup": 0.20}


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


def atr(bars: list, period: int = 14) -> Optional[float]:
    """Average True Range — stop/hedef mesafesi için oynaklık ölçüsü."""
    if len(bars) < period + 1:
        return None
    trs = []
    for i in range(1, len(bars)):
        h, l, pc = bars[i]["h"], bars[i]["l"], bars[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    recent = trs[-period:]
    return sum(recent) / len(recent)


def stochastic(bars: list, k_period: int = 14, d_period: int = 3) -> Optional[dict]:
    """Stochastic osilatörü (%K, %D). >80 aşırı alım, <20 aşırı satım."""
    if len(bars) < k_period:
        return None
    ks = []
    for i in range(k_period - 1, len(bars)):
        window = bars[i - k_period + 1:i + 1]
        hh = max(b["h"] for b in window)
        ll = min(b["l"] for b in window)
        c = bars[i]["c"]
        ks.append(100 * (c - ll) / (hh - ll) if hh != ll else 50.0)
    k_last = ks[-1]
    d_last = sum(ks[-d_period:]) / min(d_period, len(ks))
    return {"k": round(k_last, 1), "d": round(d_last, 1)}


def support_resistance(bars: list, lookback: int = 20) -> tuple:
    """Son `lookback` günün en düşük (destek) / en yüksek (direnç) seviyeleri."""
    window = bars[-lookback:]
    return (min(b["l"] for b in window), max(b["h"] for b in window))


def volume_trend(bars: list, short: int = 5, long: int = 20) -> Optional[float]:
    """Kısa/uzun ortalama hacim oranı. >1 = artan hacim (hareketi teyit eder)."""
    vols = [b.get("v") for b in bars if b.get("v")]
    if len(vols) < long:
        return None
    sv = sum(vols[-short:]) / short
    lv = sum(vols[-long:]) / long
    return round(sv / lv, 2) if lv else None


def trade_setup(bars: list) -> Optional[dict]:
    """Long (alım) kurulumu: giriş / stop / hedef / risk-ödül + destek-direnç.

    Stop  = yakın dip (son 10 gün) altı  → her hissede farklı mesafe
    Hedef = direnç (son 20 gün tepesi); fiyat dirençteyse kırılım hedefi
    Böylece risk/ödül oranı fiyatın destek-dirence göre konumuna bağlı,
    her hissede gerçekten değişir."""
    if len(bars) < 15:
        return None
    last = bars[-1]["c"]
    a = atr(bars)
    if a is None or a <= 0:
        return None
    sup, res = support_resistance(bars, 20)          # 20 günlük destek/direnç
    recent_low = min(b["l"] for b in bars[-10:])     # yakın dip → stop referansı

    # Stop: yakın dibin biraz altı (0.25×ATR tampon)
    stop = round(recent_low - 0.25 * a, 2)
    if stop >= last:                                  # güvenlik: stop girişin altında olmalı
        stop = round(last - 1.0 * a, 2)

    # Hedef: direnç belirgin şekilde yukarıdaysa oraya; değilse (zirvede/kırılımda)
    # risk kadar ölçülü hareket projeksiyonu (measured move)
    risk = last - stop
    if res > last * 1.01:
        target = round(res, 2)
    else:
        target = round(last + 1.5 * risk, 2)

    reward = target - last
    rr = round(reward / risk, 2) if risk > 0 else None
    return {
        "entry": round(last, 2),
        "stop": stop,
        "target": target,
        "rr": rr,
        "support": round(sup, 2),
        "resistance": round(res, 2),
        "atr": round(a, 2),
    }


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


def _stoch_score(st: Optional[dict]) -> Optional[int]:
    if not st:
        return None
    k = st["k"]
    # Yükselen momentum (K>D) ve sağlıklı bölge iyi; >80 aşırı alım, <20 aşırı satım
    rising = k >= st["d"]
    if k > 80:
        base = 50          # aşırı alım — temkinli
    elif k > 60:
        base = 80
    elif k > 40:
        base = 62
    elif k > 20:
        base = 46
    else:
        base = 40          # aşırı satım — tepki ihtimali
    return min(100, base + (8 if rising else -8))


def _momentum_score(closes: List[float], bars: Optional[list] = None) -> Optional[int]:
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
    if bars:
        ss = _stoch_score(stochastic(bars))
        if ss is not None:
            parts.append(ss)
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


def timing_state(closes: List[float], bars: Optional[list] = None) -> dict:
    """İYİ GİRİŞ ZAMANI değerlendirmesi.

    Mantık: "en çok yükselmiş" değil, "şu an girmek için iyi konumda" olanı ödüllendirir.
    - Yükseliş trendinde + aşırı alımda DEĞİL + geri çekilmiş → en iyi giriş (yüksek puan)
    - Aşırı alım / parabolik / üst banda yapışık → kovalama, cezalandırılır (GÜÇLÜ AL olmaz)
    - Düşüş trendinde aşırı satım + dipten dönüş → 'izle' (tepki ihtimali)
    Döndürür: {score, durum, gerilim}
    """
    if len(closes) < 20:
        return {"score": None, "durum": "—", "gerilim": None}
    last = closes[-1]
    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else ma20
    r = rsi(closes)
    st = stochastic(bars) if bars else None
    k = st["k"] if st else None
    boll = bollinger_pos(closes)
    ext = round((last / ma20 - 1) * 100, 1) if ma20 else 0.0     # MA20 üstündeki gerilim %
    uptrend = last > ma50
    rising = len(closes) >= 2 and closes[-1] > closes[-2]

    overbought = ((r is not None and r >= 72) or (k is not None and k >= 85)
                  or (boll is not None and boll > 0.92) or ext > 12)

    if uptrend:
        if overbought:
            return {"score": 32, "durum": "Aşırı alım — kovalama riski", "gerilim": ext}
        if r is not None and 40 <= r <= 58 and ext < 7:
            return {"score": 86, "durum": "Sağlıklı geri çekilme — iyi giriş", "gerilim": ext}
        if r is not None and r < 40:
            return {"score": 74, "durum": "Derin geri çekilme — uptrend sürüyor", "gerilim": ext}
        if r is not None and 58 < r < 72:
            return {"score": 58, "durum": "Yükselişte, biraz yüksek", "gerilim": ext}
        return {"score": 56, "durum": "Yükseliş trendi", "gerilim": ext}
    else:
        oversold = ((r is not None and r <= 30) or (k is not None and k <= 15)
                    or (boll is not None and boll < 0.08))
        if oversold and rising:
            return {"score": 56, "durum": "Dipten dönüş başlıyor? — izle", "gerilim": ext}
        if oversold:
            return {"score": 44, "durum": "Aşırı satım — dönüş teyidi bekle", "gerilim": ext}
        return {"score": 26, "durum": "Düşüş trendi — uzak dur", "gerilim": ext}


def _setup_score(rr: Optional[float]) -> Optional[int]:
    """Risk/ödül oranını 0-100 skora çevirir — iyi kurulum yüksek puan."""
    if rr is None:
        return None
    if rr >= 2.5:
        return 92
    if rr >= 2.0:
        return 84
    if rr >= 1.5:
        return 74
    if rr >= 1.0:
        return 58
    if rr >= 0.7:
        return 44
    if rr >= 0.4:
        return 32
    return 18


def _risk_from_vol(vol: Optional[float]) -> str:
    if vol is None:
        return "medium"
    if vol >= 4.0:
        return "high"
    if vol >= 2.0:
        return "medium"
    return "low"


def simple_signal(closes: List[float], bars: list, score: Optional[int]) -> dict:
    """Trend + aşırı alım/satım durumundan basit AL/SAT/BEKLE sinyali üretir.

    Hem sinyal kutusu metnini hem de rozet etiketini (verdict) tek kaynaktan verir,
    böylece ikisi asla çelişmez."""
    ma = ma_signal(closes)
    m = macd(closes)
    r = rsi(closes)
    st = stochastic(bars)
    boll = boll_label(bollinger_pos(closes))
    macd_sig = m["sig"] if m else "—"

    overbought = (r is not None and r >= 75) or (st and st["k"] >= 85) or boll == "Üst Band"
    oversold = (r is not None and 0 < r <= 30) or (st and st["k"] <= 15) or boll == "Alt Band"
    death_cross = ma == "Death Cross"

    # ANA KARAR doğrudan SKORDAN gelir → en yüksek skorlu hisse her zaman en olumlu
    # etiketi alır (rozet = sinyal = skor, hepsi tutarlı). Aşırı alım/satım gibi
    # nüanslar yalnızca açıklama metnine eklenir, kararı değiştirmez.
    s = score if score is not None else 50
    if s >= 75:
        action, key, head = "AL", "strong_buy", "🟢 GÜÇLÜ AL"
        base = "Teknik tablo güçlü — alım için en olumlu grup."
    elif s >= 60:
        action, key, head = "AL", "buy", "🟢 AL"
        base = "Teknik görünüm olumlu."
    elif s >= 45:
        action, key, head = "BEKLE", "hold", "🟡 TUT / NÖTR"
        base = "Kararsız bölge — net bir sinyal yok, kenarda kalmak mantıklı."
    elif s >= 32:
        action, key, head = "SAT", "sell", "🔴 SAT"
        base = "Teknik görünüm zayıf — alım için uygun değil."
    else:
        action, key, head = "SAT", "strong_sell", "🔴 GÜÇLÜ SAT"
        base = "Teknik tablo çok zayıf."

    notes = []
    if overbought and key in ("strong_buy", "buy"):
        notes.append("Ancak hisse AŞIRI ALIMDA — şu an tepe bölgesinde; geri çekilmede "
                     "(destek yakınında) girmek daha mantıklı, elindekinde kâr-al düşünülebilir.")
    if oversold and key in ("sell", "strong_sell"):
        notes.append("Hisse aşırı satımda — kısa vadeli tepki yükselişi gelebilir.")
    if death_cross and key in ("strong_buy", "buy"):
        notes.append("Dikkat: hareketli ortalamalar düşüş kesişiminde (Death Cross).")
    detail = base + (" " + " ".join(notes) if notes else "")

    LABELS = {"strong_buy": "GÜÇLÜ AL", "buy": "AL", "hold": "TUT / NÖTR",
              "sell": "SAT", "strong_sell": "GÜÇLÜ SAT"}
    return {"action": action, "key": key, "headline": head, "detail": detail,
            "verdict": LABELS[key]}


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
    bars = [b for b in (price_history or []) if b.get("c")]
    closes = [b["c"] for b in bars]
    if len(closes) < 20:
        return None

    trend = _trend_score(closes)
    mom = _momentum_score(closes, bars)
    tim = timing_state(closes, bars)             # GİRİŞ ZAMANI — aşırı alımı cezalandırır
    vol_pct = volatility_pct(closes)

    # Hacim onayı: artan hacim yükseliş trendini güçlendirir
    vt = volume_trend(bars)
    if trend is not None and vt is not None:
        if vt >= 1.3:
            trend = min(100, trend + 6)
        elif vt < 0.7:
            trend = max(0, trend - 6)

    m = macd(closes)
    st = stochastic(bars)
    ts = trade_setup(bars)                       # risk/ödül → kurulum skoru için erken hesapla
    rr = ts["rr"] if ts else None
    dims = {
        "trend": {
            "score": trend,
            "metrics": {"ma": ma_signal(closes), "macd": m["sig"] if m else "—",
                        "vol_x": vt},
        },
        "timing": {
            "score": tim["score"],
            "metrics": {"durum": tim["durum"], "rsi": rsi(closes),
                        "boll": boll_label(bollinger_pos(closes)), "gerilim": tim["gerilim"]},
        },
        "momentum": {
            "score": mom,
            "metrics": {
                "stoch": st["k"] if st else None,
                "ret_1w": pct_return(closes, 5),
                "ret_1m": pct_return(closes, 21),
            },
        },
        "setup": {
            "score": _setup_score(rr),
            "metrics": {"rr": rr},
        },
    }

    weighted, total_w = 0.0, 0.0
    for key, w in WEIGHTS.items():
        s = dims[key]["score"]
        if s is not None:
            weighted += s * w
            total_w += w
    overall = round(weighted / total_w) if total_w else None

    # Rozet (verdict) basit sinyalle AYNI kaynaktan gelir → çelişmez.
    # NOT: haber düzeltmesi varsa rescore_report nihai skora göre yeniden hesaplar.
    sig = simple_signal(closes, bars, overall)

    return {
        "score": overall,
        "verdict": sig["verdict"],
        "verdict_key": sig["key"],
        "risk": _risk_from_vol(vol_pct),
        "dimensions": dims,
        "trade_setup": ts,
        "signal": sig,
    }


def backtest_signals(bars: list, horizon: int = 10) -> Optional[dict]:
    """Geçmiş 'iyi giriş' sinyallerinin gerçekte nasıl sonuçlandığını ölçer.

    Strateji (sistemin mantığını yansıtır): yükseliş trendinde (fiyat>MA20>MA50)
    + aşırı alımda değil (RSI 40-70) iken AL; `horizon` gün sonraki getiriyi ölç.
    Döndürür: {n, win_rate, avg_ret, horizon} — yeterli işlem yoksa None."""
    closes = [b["c"] for b in (bars or []) if b.get("c")]
    if len(closes) < 60 + horizon:
        return None
    wins = 0
    rets = []
    i = 50
    while i < len(closes) - horizon:
        w = closes[: i + 1]
        ma20 = sum(w[-20:]) / 20
        ma50 = sum(w[-50:]) / 50
        r = rsi(w)
        last = w[-1]
        if last > ma50 and last > ma20 and r is not None and 40 <= r < 70:
            fwd = (closes[i + horizon] / closes[i] - 1) * 100
            rets.append(fwd)
            if fwd > 0:
                wins += 1
            i += horizon          # bir işlemden sonra ileri atla (çakışmasın)
        else:
            i += 1
    if len(rets) < 3:
        return None
    return {
        "n": len(rets),
        "win_rate": round(wins / len(rets) * 100),
        "avg_ret": round(sum(rets) / len(rets), 1),
        "horizon": horizon,
    }


def aggregate_backtest(report: dict) -> Optional[dict]:
    """Tüm hisselerin backtest sonuçlarını birleştir → sistem geneli başarı."""
    n = wins_w = 0
    all_ret = 0.0
    cnt = 0
    for s in report.get("stocks", []):
        bt = s.get("backtest")
        if not bt:
            continue
        n += bt["n"]
        wins_w += bt["win_rate"] * bt["n"]
        all_ret += bt["avg_ret"] * bt["n"]
        cnt += 1
    if n == 0:
        return None
    return {
        "trades": n,
        "stocks": cnt,
        "win_rate": round(wins_w / n),
        "avg_ret": round(all_ret / n, 1),
        "horizon": 10,
    }


def rescore_report(report: dict) -> int:
    """Rapordaki her hisseyi price_history'den teknik olarak yeniden skorla.

    score / verdict / verdict_key / risk / dimensions alanlarını günceller.
    Döndürür: yeniden skorlanan hisse sayısı."""
    # Piyasa rejimi düzeltmesi (borsa bazında) — analyze.py doldurur
    regime = report.get("regime_adj", {}) or {}
    n = 0
    for s in report.get("stocks", []):
        if "error" in s:
            continue
        res = score_from_history(s.get("price_history"))
        if res:
            base = res["score"]
            # Skoru etkileyen düzeltmeler: haber + endekse göreli güç + piyasa rejimi
            news_adj = (s.get("news") or {}).get("adjustment", 0) or 0
            rel_adj  = s.get("rel_adj", 0) or 0
            reg_adj  = regime.get(s.get("exchange", ""), 0) or 0
            total = news_adj + rel_adj + reg_adj
            res["adjustments"] = {"news": news_adj, "rel": rel_adj, "regime": reg_adj}
            if base is not None and total:
                final = max(0, min(100, base + total))
                res["score"] = final
                res["score_base"] = base   # düzeltme öncesi teknik skor (şeffaflık)
                # Rozet/sinyali NİHAİ skora göre yeniden hesapla (band değişmiş olabilir)
                bars = [b for b in s.get("price_history", []) if b.get("c")]
                closes = [b["c"] for b in bars]
                sig = simple_signal(closes, bars, final)
                res["signal"] = sig
                res["verdict"] = sig["verdict"]
                res["verdict_key"] = sig["key"]
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
