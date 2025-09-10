import telegram
from binance.client import Client
import os
from dotenv import load_dotenv
import asyncio
import pandas as pd
import ta
import time
import schedule
import sys
import pytz
from datetime import datetime
import requests # NEW: For WordPress API calls
import json     # NEW: For handling JSON payloads

# --- Environment Setup ---
load_dotenv()

# --- Tee Class for Logging ---
class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

# --- API Credentials ---
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOTS_TOKEN")
TELEGRAM_GROUP_IDS_STR = os.getenv("TELEGRAM_GROUP_IDS")
WORDPRESS_API_USER = os.getenv("WORDPRESS_API_USER")
WORDPRESS_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD")

TELEGRAM_GROUP_IDS = TELEGRAM_GROUP_IDS_STR.split(',') if TELEGRAM_GROUP_IDS_STR else []

# --- Credential Validation ---
if not all([BINANCE_API_KEY, BINANCE_SECRET_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_GROUP_IDS, WORDPRESS_API_USER, WORDPRESS_APP_PASSWORD]):
    print("Error: One or more environment variables are missing.")
    print("Please check your .env file and ensure all credentials are set, including WordPress credentials.")
    exit()

# --- Service Clients ---
binance_client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
telegram_bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# --- General Configuration ---
watchlist = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
intervals_map = {
    '15m': Client.KLINE_INTERVAL_15MINUTE,
    '30m': Client.KLINE_INTERVAL_30MINUTE,
    '1H': Client.KLINE_INTERVAL_1HOUR,
    '4H': Client.KLINE_INTERVAL_4HOUR,
    '1D': Client.KLINE_INTERVAL_1DAY,
    '1W': Client.KLINE_INTERVAL_1WEEK,
    '1M': Client.KLINE_INTERVAL_1MONTH,
}
YOUR_TIMEZONE = "Africa/Lagos"

# --- WordPress Configuration ---
WORDPRESS_URL = "https://9jacashflow.com"
WORDPRESS_SCANNER_PAGE_ID = 26265
WORDPRESS_ARCHIVE_CATEGORY_ID = 767
WORDPRESS_DAILY_SCAN_TAG_ID = 779
WORDPRESS_FEATURED_IMAGE_ID = 26267

# --- Helper Functions for Data Analysis ---

def get_trend(symbol, interval):
    try:
        klines = binance_client.get_klines(symbol=symbol, interval=interval, limit=100)
        if len(klines) < 50:
            return "⚪️ N/A"

        df = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])

        ema_50 = ta.trend.ema_indicator(df['close'], window=50)
        adx_indicator = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=14)

        latest_close = df['close'].iloc[-1]
        latest_ema_50 = ema_50.iloc[-1]
        latest_plus_di = adx_indicator.adx_pos().iloc[-1]
        latest_minus_di = adx_indicator.adx_neg().iloc[-1]

        if latest_close > latest_ema_50 and latest_plus_di > latest_minus_di:
            return "🟢 Bullish"
        elif latest_close < latest_ema_50 and latest_minus_di > latest_plus_di:
            return "🔴 Bearish"
        else:
            return "⚪️ Neutral"

    except Exception as e:
        print(f"Error getting trend for {symbol} on {interval}: {e}")
        return "⚠️ Error"

def get_overall_trend(symbol):
    mtfa_intervals = {
        'W': Client.KLINE_INTERVAL_1WEEK,
        'D': Client.KLINE_INTERVAL_1DAY,
        '4H': Client.KLINE_INTERVAL_4HOUR,
    }
    bullish_count = 0
    bearish_count = 0

    for key, interval in mtfa_intervals.items():
        trend_result = get_trend(symbol, interval)
        if "Bullish" in trend_result:
            bullish_count += 1
        elif "Bearish" in trend_result:
            bearish_count += 1

    if bullish_count == 3: return "🟢 Strong Bullish"
    elif bearish_count == 3: return "🔴 Strong Bearish"
    elif bullish_count > bearish_count: return "🟢 Bullish"
    elif bearish_count > bullish_count: return "🔴 Bearish"
    else: return "⚪️ Sideways/Mixed"

def get_trending_markets():
    print("Scanning for trending markets...")
    trending_markets = []
    try:
        exchange_info = binance_client.get_exchange_info()
        all_usdt_pairs = [s['symbol'] for s in exchange_info['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
    except Exception as e:
        print(f"Failed to get exchange info: {e}")
        return []

    for symbol in all_usdt_pairs[:200]: # Limit scan time
        try:
            klines = binance_client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=100)
            if len(klines) < 100: continue

            df = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])

            adx = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
            roc = ta.momentum.roc(df['close'], window=12)
            rsi = ta.momentum.rsi(df['close'], window=14)

            if adx.iloc[-1] > 25 and roc.iloc[-1] > 0 and rsi.iloc[-1] > 60:
                trending_markets.append(symbol)
            time.sleep(0.1)
        except Exception as e:
            print(f"Failed to analyze {symbol}: {e}")
            continue

    print(f"Found {len(trending_markets)} trending markets.")
    return trending_markets

# --- NEW: WordPress Functions ---

def format_df_to_html(df):
    """Converts the results DataFrame to a styled HTML table."""
    def style_trend(val):
        if 'Bullish' in val:
            color = '#28a745' # Green
        elif 'Bearish' in val:
            color = '#dc3545' # Red
        else:
            color = '#6c757d' # Grey
        return f'color: {color}; font-weight: bold;'

    styled_df = df.style.apply(lambda col: col.map(style_trend), subset=pd.IndexSlice[:, df.columns != 'Coin'])
    # The 'market-scanner-table' class can be styled in your WordPress theme's CSS
    html_table = styled_df.to_html(classes='market-scanner-table', border=0, escape=False)
    return html_table

def update_wordpress_page(page_id, html_content):
    """Updates a specific WordPress page with the given HTML content."""
    print(f"Attempting to update WordPress page ID: {page_id}...")
    api_url = f"{WORDPRESS_URL}/wp-json/wp/v2/pages/{page_id}"
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({'content': html_content})

    try:
        response = requests.post(api_url, data=data, headers=headers, auth=(WORDPRESS_API_USER, WORDPRESS_APP_PASSWORD), timeout=20)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print(f"Successfully updated WordPress page ID: {page_id} ✅")
    except requests.exceptions.RequestException as e:
        print(f"Failed to update WordPress page ID: {page_id}. Error: {e} ❌")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response content: {e.response.text}")


def create_wordpress_post(title, html_content):
    """Creates a new WordPress post."""
    print("Attempting to create new WordPress post...")
    api_url = f"{WORDPRESS_URL}/wp-json/wp/v2/posts"
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({
        'title': title,
        'content': html_content,
        'status': 'publish',
        'categories': [WORDPRESS_ARCHIVE_CATEGORY_ID],
        'tags': [WORDPRESS_DAILY_SCAN_TAG_ID],
        'featured_media': WORDPRESS_FEATURED_IMAGE_ID
    })

    try:
        response = requests.post(api_url, data=data, headers=headers, auth=(WORDPRESS_API_USER, WORDPRESS_APP_PASSWORD), timeout=20)
        response.raise_for_status()
        print(f"Successfully created new WordPress post: '{title}' ✅")
    except requests.exceptions.RequestException as e:
        print(f"Failed to create WordPress post. Error: {e} ❌")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response content: {e.response.text}")

# --- Messaging & Reporting Functions ---

async def send_long_message(chat_id, text, parse_mode='HTML'):
    """Splits a long message into multiple smaller messages and sends them."""
    MAX_MESSAGE_LENGTH = 4096
    parts = []
    current_part = ""
    for line in text.split('\n'):
        if len(current_part) + len(line) + 1 > MAX_MESSAGE_LENGTH:
            parts.append(current_part)
            current_part = line + '\n'
        else:
            current_part += line + '\n'
    if current_part:
        parts.append(current_part)

    for part in parts:
        if not part.strip(): continue
        try:
            await telegram_bot.send_message(chat_id=chat_id, text=part, parse_mode=parse_mode)
            print(f"Sent a message chunk to group {chat_id} ✅")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Failed to send a message chunk to group {chat_id}: {e} ❌")

async def send_report(create_new_post=False):
    """
    Generates the market report, sends it to Telegram, and updates/creates WordPress content.
    """
    print("--- Generating New Report ---")
    all_symbols_to_scan = list(dict.fromkeys(get_trending_markets() + watchlist)) # Combine and remove duplicates

    if not all_symbols_to_scan:
        print("No trending markets found and watchlist is empty. Skipping report.")
        return

    report_data = []
    for symbol in all_symbols_to_scan:
        data_row = {'Coin': symbol}
        data_row['Overall'] = get_overall_trend(symbol)
        for name, interval in intervals_map.items():
            data_row[name] = get_trend(symbol, interval)
        report_data.append(data_row)

    # Create a DataFrame from the collected data
    df = pd.DataFrame(report_data)
    df.set_index('Coin', inplace=True)

    # 1. Generate Telegram Message
    message = "<b>Binance Market Trend Report</b>\n\n"
    message += f"<pre>{df.to_string()}</pre>" # Using pre-formatted tag for better alignment
    print("\n--- Report Generation Complete ---")

    # 2. Send to Telegram
    print(f"Sending report to {len(TELEGRAM_GROUP_IDS)} Telegram group(s)...")
    for group_id in TELEGRAM_GROUP_IDS:
        await send_long_message(chat_id=group_id.strip(), text=message)

    # 3. Generate HTML for WordPress
    html_table = format_df_to_html(df)

    # 4. Update the static WordPress page (happens every time)
    update_wordpress_page(WORDPRESS_SCANNER_PAGE_ID, html_table)

    # 5. Create a new WordPress post (only if flagged, e.g., at 8:05)
    if create_new_post:
        post_title = f"Daily Market Scan: {datetime.now(pytz.timezone(YOUR_TIMEZONE)).strftime('%B %d, %Y')}"
        create_wordpress_post(post_title, html_table)


def run_scanner_job(create_post=False):
    """Wrapper to run the async report function and pass the create_post flag."""
    print(f"\n--- SCHEDULER TRIGGERED at {datetime.now(pytz.timezone(YOUR_TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')} ({YOUR_TIMEZONE}) ---")
    print(f"Flag 'create_post' is set to: {create_post}")
    try:
        asyncio.run(send_report(create_new_post=create_post))
        print("--- Scheduled job finished successfully. ---\n")
    except Exception as e:
        print(f"An error occurred during the scheduled job run: {e}")

# --- Main Execution Block ---
if __name__ == "__main__":
    LOGS_DIR = "logs"
    LOG_FILE_PATH = os.path.join(LOGS_DIR, "binance", "trend.log")
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)

    log_file = open(LOG_FILE_PATH, 'a', encoding='utf-8')
    original_stdout = sys.stdout
    sys.stdout = Tee(original_stdout, log_file)

    print("======================================================")
    print(f"Bot starting up at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Server Time)")
    print("======================================================")

    # Run once immediately on startup and create a post
    run_scanner_job(create_post=True)

    # Schedule future runs
    schedule.every().day.at("08:05", YOUR_TIMEZONE).do(run_scanner_job, create_post=True)
    schedule.every().day.at("14:05", YOUR_TIMEZONE).do(run_scanner_job, create_post=False)
    schedule.every().day.at("23:05", YOUR_TIMEZONE).do(run_scanner_job, create_post=False)

    print("\nScheduler has been set up. Bot is now in running mode. ⏰")
    print(f"Schedules are set for {YOUR_TIMEZONE} timezone.")
    next_run = schedule.next_run
    if next_run:
        print(f"Next scheduled run is at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

    while True:
        schedule.run_pending()
        time.sleep(1)