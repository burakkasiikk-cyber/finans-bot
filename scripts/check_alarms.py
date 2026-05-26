#!/usr/bin/env python3
"""
Runs every 30 minutes via GitHub Actions. Reads alarm rules from ALARMS env var (JSON array).
Format: [{"symbol":"NVDA","dir":"below","price":900,"label":"NVDA 900 below"},...]
Sends Telegram notification when a rule triggers.
"""
import json
import os
import time
import requests
from scripts.notify import send_telegram

BASE = "https://finnhub.io/api/v1"


def get_price(symbol: str, api_key: str):
    try:
        r = requests.get(f"{BASE}/quote?symbol={symbol}&token={api_key}", timeout=8)
        time.sleep(0.3)
        return r.json().get("c")
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

    api_key = os.environ["FINNHUB_KEY"]
    token   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    triggered = []
    for alarm in alarms:
        symbol    = alarm.get("symbol", "")
        target    = alarm.get("price", 0)
        direction = alarm.get("dir", "below")
        price     = get_price(symbol, api_key)
        if price is None:
            continue
        hit = (direction == "below" and price < target) or \
              (direction == "above" and price > target)
        if hit:
            sign = "<" if direction == "below" else ">"
            triggered.append(f"🔔 ALARM: {symbol} {sign} ${target:.2f} (şu an: ${price:.2f})")

    if triggered and token and chat_id:
        send_telegram("\n".join(triggered), token, chat_id)
        print(f"✅ {len(triggered)} alarm(s) sent")
    else:
        print(f"No alarms triggered ({len(alarms)} rules checked)")


if __name__ == "__main__":
    check_alarms()
