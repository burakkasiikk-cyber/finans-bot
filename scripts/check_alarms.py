#!/usr/bin/env python3
"""
Runs every 30 minutes via GitHub Actions. Reads alarm rules from ALARMS env var (JSON array).
Format: [{"symbol":"NVDA","dir":"below","price":900,"label":"NVDA 900 below"},...]
Sends Telegram notification when a rule triggers.
"""
import json
import os
import time
from scripts.notify import send_telegram


def get_price(symbol: str, exchange: str = ""):
    """Güncel fiyat — yfinance (Finnhub bağımlılığı kaldırıldı).

    BIST sembolleri için '.IS' eklenir. Sembol zaten '.IS' içeriyorsa dokunulmaz."""
    try:
        import yfinance as yf
        yt = symbol
        if exchange == "BIST" and not symbol.endswith(".IS"):
            yt = f"{symbol}.IS"
        price = yf.Ticker(yt).fast_info.last_price
        time.sleep(0.3)
        return float(price) if price else None
    except Exception:
        return None


def check_alarms() -> None:
    alarms_json = os.environ.get("ALARMS", "[]")
    try:
        alarms = json.loads(alarms_json)
    except json.JSONDecodeError:
        print("Invalid ALARMS JSON, skipping.")
        return

    if not alarms:
        print("No active alarms.")
        return

    token   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    triggered = []
    for alarm in alarms:
        symbol    = alarm.get("symbol", "")
        target    = alarm.get("price", 0)
        direction = alarm.get("dir", "below")
        exchange  = alarm.get("exchange", "")
        price     = get_price(symbol, exchange)
        if price is None:
            continue
        hit = (direction == "below" and price < target) or \
              (direction == "above" and price > target)
        if hit:
            sign = "<" if direction == "below" else ">"
            triggered.append(f"🔔 ALARM: {symbol} {sign} {target:.2f} (şu an: {price:.2f})")

    if not triggered:
        print(f"Tetiklenen alarm yok ({len(alarms)} kural kontrol edildi)")
    elif token and chat_id:
        send_telegram("\n".join(triggered), token, chat_id)
        print(f"✅ {len(triggered)} alarm gönderildi")
    else:
        print(f"⚠️  {len(triggered)} alarm tetiklendi ama Telegram secret yok — gönderilemedi")
        for t in triggered:
            print("  ", t)


if __name__ == "__main__":
    check_alarms()
