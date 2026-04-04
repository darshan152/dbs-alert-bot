import requests
import pandas as pd
from datetime import datetime
import json
from io import StringIO
import os
from bs4 import BeautifulSoup

HEADERS       = {"User-Agent": "Mozilla/5.0"}
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ── Telegram ──────────────────────────────────────────────────────────────────

def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

# ── Fetch latest close from web ───────────────────────────────────────────────

def get_latest_close(ticker) -> tuple:
    url = f"https://stockanalysis.com/quote/sgx/{ticker}/history/"
    r   = requests.get(url, headers=HEADERS)
    df  = pd.read_html(StringIO(r.text))[0]
    df.columns = [c.lower() for c in df.columns]
    date  = df.iloc[0, 0]
    close = float(df.iloc[0, 4])
    return date, close

# ── Fetch pb_1dn from calculate_metrics ──────────────────────────────────────

def get_latest_div_yield(ticker):
    url= f"https://stockanalysis.com/quote/sgx/{ticker}/dividend/"

    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(StringIO(response.text), "html.parser")

    # The page lists dividend info in a definition-list style block.
    # Look for the label "Dividend Yield" and grab the next sibling value.
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for i, line in enumerate(lines):
        if "Dividend Yield" in line:
            # The yield value is on the next non-empty line
            yield_value = lines[i + 1]
            return yield_value

    return None

# ── Main alert logic ──────────────────────────────────────────────────────────

def check_and_alert():
    tickers = ["D05","U11","O39"]
    for ticker in tickers:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Running check for {ticker}...")

        try:
            date, close   = get_latest_close(ticker)
            div_yield = get_latest_div_yield(ticker)
            with open("output.json", "r") as f:
                data = json.load(f)
            bps    = data[ticker]["bps"]
            pb     = close / bps
            pb_ave = data[ticker]["pb_ave"]
            pb_1dn = data[ticker]["pb_1dn"]
            pb_1up = data[ticker]["pb_1up"]

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
                f"Div Yield  : {div_yield}\n"
                f"BpS        : SGD {bps:.4f}\n"
                f"PB         : {pb:.4f}\n"
                f"────────────────────\n"
                f"PB 1up     : {pb_1up:.4f}\n"
                f"PB Ave     : {pb_ave:.4f}\n"
                f"PB 1dn     : {pb_1dn:.4f}\n"
                f"────────────────────\n"
                f"Dist to 1dn: {dist_to_1dn:+.4f} ({pct_from_1dn:.1f}% from bottom)\n"
            )
            print(msg)

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
