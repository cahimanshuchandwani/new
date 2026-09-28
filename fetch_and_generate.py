import os
import json
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- Configuration & NSE Session Setup ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.nseindia.com/'
}

def get_nse_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get("https://www.nseindia.com", timeout=10)
    except Exception as e:
        print(f"[Warning] Failed to fetch NSE session cookies: {e}")
    return session

session = get_nse_session()

# --- Data Fetcher 1: Price Band Changes ---
def fetch_price_band_changes():
    url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500"
    band_changes = {}
    db_file = "price_bands_db.json"
    
    prev_bands = {}
    if os.path.exists(db_file):
        with open(db_file, "r") as f:
            prev_bands = json.load(f)

    current_bands = {}
    try:
        res = session.get(url, timeout=12)
        if res.status_code == 200:
            data = res.json().get('data', [])
            for item in data:
                symbol = item.get('symbol', '').strip().upper()
                band = item.get('meta', {}).get('band', '20')
                if symbol:
                    current_bands[symbol] = str(band).replace('%', '').strip()
    except Exception as e:
        print(f"[Error] Fetching Price Bands failed: {e}")

    if prev_bands:
        for sym, new_band in current_bands.items():
            old_band = prev_bands.get(sym)
            if old_band and old_band != new_band:
                band_changes[sym] = {"old": old_band, "new": new_band}

    if current_bands:
        with open(db_file, "w") as f:
            json.dump(current_bands, f, indent=2)

    return band_changes

# --- Data Fetcher 2: Earnings for Next Trading Day ---
def fetch_next_day_earnings():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d-%b-%Y")
    url = f"https://www.nseindia.com/api/event-calendar?index=equities&from_date={tomorrow}&to_date={tomorrow}"
    earnings_list = []

    try:
        res = session.get(url, timeout=12)
        if res.status_code == 200:
            events = res.json()
            for ev in events:
                desc = str(ev.get('purpose', '')).lower()
                if 'financial result' in desc or 'earnings' in desc or 'audited' in desc:
                    sym = ev.get('symbol', '').strip().upper()
                    if sym:
                        earnings_list.append(sym)
    except Exception as e:
        print(f"[Error] Fetching Earnings Calendar failed: {e}")

    return sorted(list(set(earnings_list)))

# --- Data Fetcher 3: IPOs Listed Today ---
def fetch_today_ipos():
    today_str = datetime.now().strftime("%d-%b-%Y")
    url = "https://www.nseindia.com/api/ipo-detail"
    today_ipos = []

    try:
        res = session.get(url, timeout=12)
        if res.status_code == 200:
            ipo_data = res.json()
            for item in ipo_data:
                listing_date = item.get('listingDate', '')
                if listing_date == today_str:
                    sym = item.get('symbol', '').strip().upper()
                    company = item.get('companyName', sym)
                    if sym:
                        today_ipos.append({"symbol": sym, "name": company})
    except Exception as e:
        print(f"[Error] Fetching IPO Listings failed: {e}")

    return today_ipos

# --- Pine Script Generator ---
def generate_pine_script(band_changes, earnings, ipos):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M IST")

    band_cases = ""
    for sym, change in band_changes.items():
        band_cases += f'        "{sym}" => "{change["old"]}% → {change["new"]}%"\n'
    if not band_cases:
        band_cases = '        => "None"\n'

    earnings_cases = ""
    for sym in earnings:
        earnings_cases += f'        "{sym}" => true\n'
    if not earnings_cases:
        earnings_cases = '        => false\n'

    ipo_cases = ""
    for ipo in ipos:
        ipo_cases += f'        "{ipo["symbol"]}" => true\n'
    if not ipo_cases:
        ipo_cases = '        => false\n'

    pine_template = f"""//@version=5
indicator("NSE Market Insights HUD (Auto-Updated)", overlay = true)

// --- Generated On: {now_str} ---

// Lookup 1: Next-Day Circuit Band Changes
get_band_change(ticker) =>
    switch ticker
{band_cases}

// Lookup 2: Next-Day Earnings Announcements
has_earnings_tomorrow(ticker) =>
    switch ticker
{earnings_cases}

// Lookup 3: IPOs Listed Today
is_ipo_today(ticker) =>
    switch ticker
{ipo_cases}

// --- Active Symbol Data Extraction ---
curr_sym     = syminfo.ticker
band_status  = get_band_change(curr_sym)
has_earnings = has_earnings_tomorrow(curr_sym)
is_ipo       = is_ipo_today(curr_sym)

// --- On-Chart HUD Display Table ---
var table hud = table.new(position.top_right, 2, 4, bgcolor=color.rgb(19, 23, 34, 15), border_color=color.rgb(41, 98, 255), border_width=1)

if barstate.islast
    table.cell(hud, 0, 0, "NSE Market Alert", text_color=color.white, bgcolor=color.rgb(41, 98, 255), text_size=size.small)
    table.cell(hud, 1, 0, curr_sym, text_color=color.white, bgcolor=color.rgb(41, 98, 255), text_size=size.small)

    table.cell(hud, 0, 1, "Next-Day UC Revision", text_color=color.gray, text_size=size.small)
    table.cell(hud, 1, 1, band_status, text_color=band_status != "None" ? color.red : color.green, text_size=size.small)

    table.cell(hud, 0, 2, "Earnings Tomorrow", text_color=color.gray, text_size=size.small)
    table.cell(hud, 1, 2, has_earnings ? "YES 📊" : "No", text_color=has_earnings ? color.orange : color.white, text_size=size.small)

    table.cell(hud, 0, 3, "New IPO Listing", text_color=color.gray, text_size=size.small)
    table.cell(hud, 1, 3, is_ipo ? "FRESH LISTING 🚀" : "No", text_color=is_ipo ? color.teal : color.white, text_size=size.small)

// --- Candle Callout Badges ---
if barstate.islast
    if band_status != "None"
        label.new(bar_index, high, "UC REVISION: " + band_status, style=label.style_label_down, color=color.red, textcolor=color.white)
    if has_earnings
        label.new(bar_index, low, "EARNINGS TOMORROW 📊", style=label.style_label_up, color=color.orange, textcolor=color.white)
    if is_ipo
        label.new(bar_index, high, "NEW IPO LISTING 🚀", style=label.style_label_down, color=color.teal, textcolor=color.white)
"""
    with open("generated_indicator.pine", "w", encoding="utf-8") as f:
        f.write(pine_template)

    print("[Success] Generated 'generated_indicator.pine' successfully.")

if __name__ == "__main__":
    bands = fetch_price_band_changes()
    earnings = fetch_next_day_earnings()
    ipos = fetch_today_ipos()
    generate_pine_script(bands, earnings, ipos)
