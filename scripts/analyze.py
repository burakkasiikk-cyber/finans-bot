#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.fetch_history import fetch_trader_stock
from scripts.fetch_macro import fetch_macro
from scripts.technical import rescore_report, aggregate_backtest
from scripts.news_sentiment import fetch_news_sentiment
from scripts.track import update_track


def _index_context(yticker: str) -> dict:
    """Bir endeksin rejimini hesapla: MA50 üstünde mi, 1 aylık getiri, skor düzeltmesi.

    adj: yükseliş piyasası → +2 (alımlar lehine), düşüş → -3 (temkin), nötr → 0."""
    try:
        import yfinance as yf
        hist = yf.Ticker(yticker).history(period="6mo")
        closes = [float(c) for c in hist["Close"] if c == c and c > 0]
    except Exception:
        closes = []
    if len(closes) < 55:
        return {"trend": "bilinmiyor", "ret_1m": None, "adj": 0, "above_ma50": None}
    ma50 = sum(closes[-50:]) / 50
    above = closes[-1] > ma50
    ret_1m = round((closes[-1] / closes[-1 - 21] - 1) * 100, 1) if len(closes) > 21 else None
    if above and (ret_1m or 0) > 1:
        trend, adj = "yükseliş", 2
    elif (not above) and (ret_1m or 0) < -1:
        trend, adj = "düşüş", -3
    else:
        trend, adj = "yatay", 0
    return {"trend": trend, "ret_1m": ret_1m, "adj": adj, "above_ma50": above}


def compute_market_context() -> dict:
    """BIST100 (XU100.IS) rejim + 1 aylık getirisi. (Sadece BIST odağı.)"""
    return {"bist": _index_context("XU100.IS")}


def apply_market_context(report: dict, ctx: dict = None) -> dict:
    """Piyasa rejimi + endekse göreli güç hesaplar ve report'a yazar.

    analyze.py ve update_prices.py ORTAK kullanır → rejim her güncellemede taze
    kalır (yoksa gün içi güncelleme bayat rejimle çalışır ve fren yanlış basılı
    kalır). Endeks verisi çekilemezse ('bilinmiyor') eski sağlam rejim korunur."""
    if ctx is None:
        ctx = compute_market_context()
    bist = ctx.get("bist", {})
    if bist.get("trend") and bist["trend"] != "bilinmiyor":
        report["market_regime"] = {"bist": bist}
        report["regime_adj"] = {"BIST": bist["adj"]}
    idx = (report.get("market_regime") or {}).get("bist") or {}
    for s in report.get("stocks", []):
        if "error" in s:
            continue
        closes = [b["c"] for b in s.get("price_history", []) if b.get("c")]
        st_ret = round((closes[-1] / closes[-1 - 21] - 1) * 100, 1) if len(closes) > 21 else None
        if st_ret is not None and idx.get("ret_1m") is not None:
            rs = round(st_ret - idx["ret_1m"], 1)          # BIST100'ü ne kadar yendi
            s["rel_strength"] = rs
            s["rel_adj"] = 3 if rs > 5 else 1 if rs > 0 else -3 if rs < -5 else -1
        else:
            s["rel_strength"], s["rel_adj"] = None, 0
    return ctx

BIST_STOCKS = [
    # Bankalar  (QNBFB delisted/halka kapandı — çıkarıldı)
    "AKBNK", "GARAN", "HALKB", "ISCTR", "VAKBN", "YKBNK", "ALBRK", "SKBNK",
    # Holdingler
    "KCHOL", "SAHOL", "AGHOL", "DOHOL", "ECZYT",
    # Sanayi / Petrokimya / Demir-Çelik  (SODA Şişecam'a katıldı — çıkarıldı)
    "TUPRS", "EREGL", "KRDMD", "PETKM", "BRSAN", "GUBRF",
    # İnşaat / Çimento
    "AKCNS", "CIMSA", "BSOKE", "CEMTS", "ENKAI", "TKFEN",
    # Havacılık / Ulaşım
    "THYAO", "PGSUS", "TAVHL", "RYSAS",
    # Telekomünikasyon
    "TCELL", "TTKOM",
    # Teknoloji / Savunma / Yazılım  (EKDMR yeni listelendi, yeterli veri yok — çıkarıldı)
    "ASELS", "LOGO", "NETAS", "INDES",
    # Perakende  (MIGROS doğru ticker: MGROS)
    "BIMAS", "MGROS", "BIZIM", "SOKM",
    # Otomotiv
    "TOASO", "FROTO", "OTKAR", "DOAS",
    # Tüketim / Gıda / İçecek
    "ARCLK", "VESTL", "ULKER", "AEFES", "CCOLA", "KONTR", "MAVI",
    # Enerji
    "AKSEN", "ODAS", "AYEN", "ZOREN",
    # GYO / Gayrimenkul  (EMLAK doğru ticker: EKGYO = Emlak Konut GYO)
    "EKGYO", "ISGYO", "ALGYO", "AKFGY",
    # Madencilik  (KOZAL/KOZAA işlem durdurulmuş — çıkarıldı)
    "ALKIM", "KARSN",
    # Sigorta
    "ANHYT", "AKGRT",
    # Diğer  (IPEKE işlem durdurulmuş — çıkarıldı)
    "SISE", "EGEEN", "DEVA", "ECILC", "NTHOL", "KLNMA", "ISDMR", "GOLTS",
    "TURSG", "HURGZ", "REEDR", "FENER", "BJKAS", "GSRAY", "TSPOR",
]


def run() -> dict:
    key          = os.environ.get("FINNHUB_KEY", "")
    exchange_key = os.environ.get("EXCHANGE_API_KEY", "")

    print("Fetching macro data...")
    try:
        # Her durumda fetch_macro çağır: yfinance ile altın + BIST100 değişimini alır,
        # Finnhub key varsa döviz/S&P500/altın da Finnhub'dan gelir.
        macro = fetch_macro(key, exchange_key)
    except Exception as e:
        print(f"  ! macro fetch failed: {e}")
        macro = {}

    # Eski raporu yükle: Finnhub yoksa ABD verisini ve eski macro alanlarını korumak için
    old_report = {}
    old_path = Path("data/report.json")
    if old_path.exists():
        try:
            old_report = json.loads(old_path.read_text())
        except Exception:
            old_report = {}

    # Macro eksik alanları eski raporundan tamamla
    old_macro = old_report.get("macro", {}) or {}
    for k, v in old_macro.items():
        if not macro.get(k) and v is not None:
            macro[k] = v

    # "Dünkü" skor + karar haritası — "bugün ne değişti" ve değişim bildirimleri için
    prev_map = {
        s["symbol"]: {"score": s.get("score"), "verdict_key": s.get("verdict_key")}
        for s in old_report.get("stocks", []) if "error" not in s and s.get("symbol")
    }

    stocks = []

    # TRADER MODU: yalnızca BIST hisseleri — yfinance fiyat geçmişi.
    # Skorlama tamamen teknik olduğu için Finnhub/temel veriye gerek yok.
    print("BIST hisseleri (yfinance)...")
    for sym in BIST_STOCKS:
        print(f"  {sym}")
        try:
            stocks.append(fetch_trader_stock(sym, "BIST"))
        except Exception as e:
            stocks.append({"symbol": sym, "error": str(e)})
        time.sleep(0.4)  # yfinance 429 önlemi

    errors = [s for s in stocks if "error" in s]
    if errors:
        print(f"⚠️  {len(errors)} hisse atlandı: {[(e['symbol'], e['error']) for e in errors]}")

    # Haber duygu analizi — skoru olumlu/olumsuz etkiler (haberler gösterilmez)
    print("Haber duygu analizi...")
    for s in stocks:
        if "error" in s:
            continue
        yt = f"{s['symbol']}.IS" if s.get("exchange") == "BIST" else s["symbol"]
        try:
            s["news"] = fetch_news_sentiment(yt, s["symbol"], s.get("name", ""))
        except Exception:
            s["news"] = {"adjustment": 0, "sentiment": "nötr", "pos": 0, "neg": 0, "count": 0}
        # Dünkü skor/karar — "bugün ne değişti" karşılaştırması için
        if s["symbol"] in prev_map:
            s["prev"] = prev_map[s["symbol"]]
        time.sleep(0.25)

    report = {
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "macro":          macro,
        "stocks":         stocks,
        "top3":           [],
        "risk_alerts":    [],
        "weekly_summary": None,
        "mode":           "trader",
    }

    # Piyasa rejimi + endekse göreli güç (analyze ve update_prices ortak fonksiyon)
    print("Piyasa rejimi & göreli güç...")
    apply_market_context(report)

    # TRADER MODU: skoru teknik + haber + göreli güç + rejim ile üret.
    n = rescore_report(report)
    report["backtest"] = aggregate_backtest(report)
    # Öneri karnesi: bugünün sinyallerini kaydet, ufku dolanları ölç
    report["karne"] = update_track(report)
    k = report["karne"]["90g"]["overall"]["h10"]
    if k["n"]:
        print(f"📒 Karne (90g/10g): %{k['win_rate']} isabet, beklenti {k['avg_ret']:+}% ({k['n']} sinyal)")
    if report["backtest"]:
        b = report["backtest"]
        print(f"📊 Backtest: {b['trades']} işlem, başarı %{b['win_rate']}, ort {b['avg_ret']:+}% ({b['horizon']}g)")
    print(f"⚡ Trader modu: {n} hisse skorlandı, {len(report['stocks'])-n} atlandı.")
    return report


if __name__ == "__main__":
    report = run()
    out = Path("data/report.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"✅ report.json written: {len(report['stocks'])} stocks")
