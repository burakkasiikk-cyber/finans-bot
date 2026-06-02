#!/usr/bin/env python3
"""
Grafik verisini güncelle — yfinance only, Finnhub key gerekmez.
Her hissenin price_history alanını (son 60 işlem günü OHLCV) yeniler.
"""
import json
import time
from pathlib import Path

import yfinance as yf

from scripts.technical import rescore_report


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
        yticker = sym if exc != "BIST" else f"{sym}.IS"
        try:
            hist = yf.Ticker(yticker).history(period="3mo")
            ph = [
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
            s["price_history"] = ph
            updated += 1
            print(f"  {sym}: {len(ph)} bar")
        except Exception as e:
            print(f"  {sym}: HATA {e}")
        time.sleep(0.35)   # yfinance 429 önlemi

    # Fiyat geçmişi tazelendi — trader skorlarını da güncelle
    n = rescore_report(report)
    print(f"⚡ Trader modu: {n} hisse yeniden skorlandı.")

    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n✅ {updated}/{len(stocks)} hisse güncellendi.")


if __name__ == "__main__":
    run()
