import os
import smtplib
import requests
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def build_morning_message(report: dict) -> str:
    now    = datetime.now().strftime("%d %B %Y %H:%M")
    macro  = report.get("macro", {})
    stocks = {s["symbol"]: s for s in report.get("stocks", []) if "error" not in s}
    top3   = report.get("top3", [])
    alerts = report.get("risk_alerts", [])

    lines = [f"☀️ Sabah Raporu — {now}", ""]

    lines.append("📈 Top 3 Fırsat:")
    for i, sym in enumerate(top3[:3], 1):
        s = stocks.get(sym, {})
        chg  = s.get("change_pct") or 0
        sign = "+" if chg >= 0 else ""
        lines.append(f"{i}. {sym} — {s.get('score','?')}/100 {s.get('verdict','?')} ({sign}{chg:.1f}%)")

    if alerts:
        lines.append("")
        lines.append("⚠️ Risk Uyarısı:")
        for sym in alerts:
            s = stocks.get(sym, {})
            lines.append(f"• {sym} — {s.get('verdict','?')} ({s.get('score','?')}/100)")

    lines.append("")
    usd_try = macro.get("usd_try")
    gold    = macro.get("gold_usd")
    sp_chg  = macro.get("sp500_change_pct")
    if sp_chg is not None:
        sp_sign = "+" if sp_chg >= 0 else ""
        lines.append(f"💱 USD/TRY: {usd_try} | Altın: ${gold} | S&P500: {sp_sign}{sp_chg:.2f}%")
    else:
        lines.append(f"💱 USD/TRY: {usd_try} | Altın: ${gold}")

    return "\n".join(lines)


def send_telegram(message: str, bot_token: str, chat_id: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)


def send_gmail(subject: str, body: str, gmail_address: str, gmail_password: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_address
    msg["To"]      = gmail_address
    msg.attach(MIMEText(body, "plain", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, gmail_address, msg.as_string())


def notify_morning(report: dict) -> None:
    message  = build_morning_message(report)
    token    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id  = os.environ.get("TELEGRAM_CHAT_ID", "")
    gmail    = os.environ.get("GMAIL_ADDRESS", "")
    gmail_pw = os.environ.get("GMAIL_APP_PASSWORD", "")

    if token and chat_id:
        send_telegram(message, token, chat_id)
        print("✅ Telegram sent")
    if gmail and gmail_pw:
        send_gmail("☀️ Hisse Sabah Raporu", message, gmail, gmail_pw)
        print("✅ Gmail sent")
