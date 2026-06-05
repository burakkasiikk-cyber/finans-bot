#!/usr/bin/env python3
"""
Fiyat geçmişini ve teknik skorları tazele — yfinance only, Finnhub gerekmez.
fetch_trader_stock'u yeniden kullanır (90 bar + backtest + likidite tutarlı kalır).
Haber duygusu (news) ve dünkü skor (prev) korunur.
"""
import json
import time
from pathlib import Path

from scripts.fetch_history import fetch_trader_stock
from scripts.technical import rescore_report, aggregate_backtest


def run():
    out = Path("data/report.json")
    if not out.exists():
        print("⚠️  data/report.json bulunamadı, atlıyor.")
        return

    report = json.loads(out.read_text())
    stocks = [s for s in report.get("stocks", []) if "error" not in s]
    print(f"Fiyat geçmişi güncelleniyor: {len(stocks)} hisse…")

    updated = 0
    for s in stocks:
        sym = s["symbol"]
        exc = s.get("exchange", "BIST")
        fresh = fetch_trader_stock(sym, exc)
        if "error" not in fresh:
            # Haber ve prev'i koru; gerisini tazele
            for k in ("price", "change_pct", "price_history", "backtest",
                      "liquidity", "turnover", "name"):
                if k in fresh:
                    s[k] = fresh[k]
            updated += 1
            print(f"  {sym}: {len(fresh['price_history'])} bar")
        else:
            print(f"  {sym}: {fresh['error']}")
        time.sleep(0.35)   # yfinance 429 önlemi

    n = rescore_report(report)
    report["backtest"] = aggregate_backtest(report)
    print(f"⚡ Trader modu: {n} hisse yeniden skorlandı.")

    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n✅ {updated}/{len(stocks)} hisse güncellendi.")


if __name__ == "__main__":
    run()
