#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.fetch_us import fetch_us_stock
from scripts.fetch_bist import fetch_bist_stock
from scripts.fetch_macro import fetch_macro
from scripts.technical import rescore_report

US_STOCKS   = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AMD", "TSLA"]
BIST_STOCKS = [
    # Bankalar
    "AKBNK", "GARAN", "HALKB", "ISCTR", "VAKBN", "YKBNK", "QNBFB", "ALBRK", "SKBNK",
    # Holdingler
    "KCHOL", "SAHOL", "AGHOL", "DOHOL", "ECZYT",
    # Sanayi / Petrokimya / Demir-Çelik
    "TUPRS", "EREGL", "KRDMD", "PETKM", "SODA", "BRSAN", "GUBRF",
    # İnşaat / Çimento
    "AKCNS", "CIMSA", "BSOKE", "CEMTS", "ENKAI", "TKFEN",
    # Havacılık / Ulaşım
    "THYAO", "PGSUS", "TAVHL", "RYSAS",
    # Telekomünikasyon
    "TCELL", "TTKOM",
    # Teknoloji / Savunma / Yazılım
    "ASELS", "EKDMR", "LOGO", "NETAS", "INDES",
    # Perakende
    "BIMAS", "MIGROS", "BIZIM", "SOKM",
    # Otomotiv
    "TOASO", "FROTO", "OTKAR", "DOAS",
    # Tüketim / Gıda / İçecek
    "ARCLK", "VESTL", "ULKER", "AEFES", "CCOLA", "KONTR", "MAVI",
    # Enerji
    "AKSEN", "ODAS", "AYEN", "ZOREN",
    # GYO / Gayrimenkul
    "EMLAK", "ISGYO", "ALGYO", "AKFGY",
    # Madencilik
    "KOZAL", "KOZAA", "ALKIM", "KARSN",
    # Sigorta
    "ANHYT", "AKGRT",
    # Diğer
    "SISE", "EGEEN", "DEVA", "ECILC", "NTHOL", "KLNMA", "ISDMR", "GOLTS",
    "TURSG", "HURGZ", "REEDR", "IPEKE", "FENER", "BJKAS", "GSRAY", "TSPOR",
]


def run() -> dict:
    key          = os.environ.get("FINNHUB_KEY", "")
    exchange_key = os.environ.get("EXCHANGE_API_KEY", "")
    has_finnhub  = bool(key)

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

    stocks = []

    if has_finnhub:
        print("Analyzing US stocks...")
        for sym in US_STOCKS:
            print(f"  {sym}")
            try:
                stocks.append(fetch_us_stock(sym, key))
            except Exception as e:
                stocks.append({"symbol": sym, "error": str(e)})
            time.sleep(1)
    else:
        print("FINNHUB_KEY yok — ABD verisi eski rapordan korunuyor.")
        for s in old_report.get("stocks", []):
            if s.get("exchange") and s["exchange"] != "BIST":
                stocks.append(s)

    print("Analyzing BIST stocks...")
    for sym in BIST_STOCKS:
        print(f"  {sym}")
        try:
            stocks.append(fetch_bist_stock(sym))
        except Exception as e:
            stocks.append({"symbol": sym, "error": str(e)})
        time.sleep(0.5)  # yfinance 429 önlemi

    valid  = [s for s in stocks if "error" not in s and s.get("score") is not None]
    errors = [s for s in stocks if "error" in s]
    valid.sort(key=lambda s: s["score"], reverse=True)

    if errors:
        print(f"⚠️  {len(errors)} stocks failed: {[e['symbol'] for e in errors]}")

    top3        = [s["symbol"] for s in valid[:3]]
    risk_alerts = [s["symbol"] for s in valid if s.get("risk") == "high"]

    report = {
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "macro":          macro,
        "stocks":         valid + errors,
        "top3":           top3,
        "risk_alerts":    risk_alerts,
        "weekly_summary": None,
        "mode":           "trader",
    }

    # TRADER MODU: skoru tamamen teknik göstergelere dayandır (price_history'den)
    n = rescore_report(report)
    print(f"⚡ Trader modu: {n} hisse teknik göstergelerle yeniden skorlandı.")
    return report


if __name__ == "__main__":
    report = run()
    out = Path("data/report.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"✅ report.json written: {len(report['stocks'])} stocks")
