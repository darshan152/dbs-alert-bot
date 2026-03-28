import requests
import pandas as pd
import sqlite3
from datetime import datetime
#import schedule
import time

DB_PATH       = "../investment.db"
HEADERS       = {"User-Agent": "Mozilla/5.0"}
TELEGRAM_TOKEN   = "8698959116:AAErA5gdBVOUJSMtkute-nw0"
TELEGRAM_CHAT_ID = "102526"

# ── Telegram ──────────────────────────────────────────────────────────────────

def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

# ── Fetch latest close from web ───────────────────────────────────────────────

def get_latest_close() -> tuple:
    url = "https://stockanalysis.com/quote/sgx/D05/history/"
	print("hi")
    r   = requests.get(url, headers=HEADERS)
	print("hi1")
    df  = pd.read_html(r.text)[0]
	print("hi2")
    df.columns = [c.lower() for c in df.columns]
	print("hi3")
    date  = df.iloc[0, 0]
	print("hi4")
    close = float(df.iloc[0, 4])
	print("hi5")
    return date, close

# ── Fetch pb_1dn from calculate_metrics ──────────────────────────────────────


# ── Main alert logic ──────────────────────────────────────────────────────────

def check_and_alert():
    ticker = "D05"
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Running check for {ticker}...")

    try:
        date, close   = get_latest_close()

        bps    = 24.1966
        pb     = close / bps
        pb_ave = 1.2451
        pb_1dn = 0.9332
        pb_1up = 1.5569

        # Distance from PB to pb_1dn as % of the band width
        band_width   = pb_1up - pb_1dn
        dist_to_1dn  = pb - pb_1dn                       # positive = above, negative = below
        pct_from_1dn = (dist_to_1dn / band_width) * 100  # 0% = at 1dn, 100% = at 1up

        # Alert if PB is within the lower 25% of the band
        THRESHOLD_PCT = 25
        alert_triggered = pct_from_1dn <= THRESHOLD_PCT

        msg = (
            f"*DBS ({ticker}) Daily PB Alert*\n"
            f"Date       : {date}\n"
            f"Close      : SGD {close:.2f}\n"
            f"BpS        : SGD {bps:.4f}\n"
            f"PB         : {pb:.4f}\n"
            f"────────────────────\n"
            f"PB 1up     : {pb_1up:.4f}\n"
            f"PB Ave     : {pb_ave:.4f}\n"
            f"PB 1dn     : {pb_1dn:.4f}\n"
            f"────────────────────\n"
            f"Dist to 1dn: {dist_to_1dn:+.4f} ({pct_from_1dn:.1f}% from bottom)\n"
        )

        if alert_triggered:
            msg += f"\n*ALERT: PB is near 1dn — possible buy zone*"
            print("ALERT triggered!")
        else:
            msg += f"\nStatus: PB within normal range"

        send_telegram(msg)
        print("Alert sent.")

    except Exception as e:
        send_telegram(f"[{ticker}] Error during check: {e}")
        print(f"Error: {e}")

# ── Scheduler — runs at 8:30am daily (before SGX opens at 9am) ────────────────

if __name__ == "__main__":
    # Run once immediately on start so you can verify it works
	check_and_alert()
