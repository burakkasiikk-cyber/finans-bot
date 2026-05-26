#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.fetch_us import fetch_us_stock
from scripts.fetch_bist import fetch_bist_stock
from scripts.fetch_macro import fetch_macro

US_STOCKS   = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AMD", "TSLA"]
BIST_STOCKS = ["THYAO", "GARAN", "KCHOL", "TUPRS", "EREGL", "SISE", "ASELS"]


def run() -> dict:
    key          = os.environ["FINNHUB_KEY"]
    exchange_key = os.environ.get("EXCHANGE_API_KEY", "")

    print("Fetching macro data...")
    macro = fetch_macro(key, exchange_key)

    print("Analyzing US stocks...")
    stocks = []
    for sym in US_STOCKS:
        print(f"  {sym}")
        stocks.append(fetch_us_stock(sym, key))
        time.sleep(1)

    print("Analyzing BIST stocks...")
    for sym in BIST_STOCKS:
        print(f"  {sym}")
        stocks.append(fetch_bist_stock(sym))

    valid  = [s for s in stocks if "error" not in s and s.get("score") is not None]
    errors = [s for s in stocks if "error" in s]
    valid.sort(key=lambda s: s["score"], reverse=True)

    if errors:
        print(f"⚠️  {len(errors)} stocks failed: {[e['symbol'] for e in errors]}")

    top3        = [s["symbol"] for s in valid[:3]]
    risk_alerts = [s["symbol"] for s in valid if s.get("risk") == "high"]

    return {
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "macro":          macro,
        "stocks":         valid + errors,
        "top3":           top3,
        "risk_alerts":    risk_alerts,
        "weekly_summary": None,
    }


if __name__ == "__main__":
    report = run()
    out = Path("data/report.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"✅ report.json written: {len(report['stocks'])} stocks")
