#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.fetch_history import fetch_trader_stock
from scripts.fetch_macro import fetch_macro
from scripts.technical import rescore_report
from scripts.news_sentiment import fetch_news_sentiment

US_STOCKS   = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AMD", "TSLA"]
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

    # TRADER MODU: tüm hisseler (ABD + BIST) tek kaynaktan — yfinance fiyat geçmişi.
    # Skorlama tamamen teknik olduğu için Finnhub/temel veriye gerek yok.
    print("ABD hisseleri (yfinance)...")
    for sym in US_STOCKS:
        print(f"  {sym}")
        try:
            stocks.append(fetch_trader_stock(sym, "NASDAQ"))
        except Exception as e:
            stocks.append({"symbol": sym, "error": str(e)})
        time.sleep(0.4)

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

    # TRADER MODU: skoru tamamen teknik göstergelere dayandır (price_history'den).
    # rescore_report skorlar, sıralar, top3 + risk_alerts'i tazeler.
    n = rescore_report(report)
    print(f"⚡ Trader modu: {n} hisse teknik göstergelerle skorlandı, {len(report['stocks'])-n} atlandı.")
    return report


if __name__ == "__main__":
    report = run()
    out = Path("data/report.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"✅ report.json written: {len(report['stocks'])} stocks")
