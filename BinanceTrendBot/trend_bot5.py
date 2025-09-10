import telegram
from binance.client import Client
import os
from dotenv import load_dotenv
import asyncio
import pandas as pd
import ta
import time
import schedule
import sys          # For logging
import pytz         # For timezone handling
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth

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

# --- Binance & Telegram Configuration ---
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOTS_TOKEN")
TELEGRAM_GROUP_IDS_STR = os.getenv("TELEGRAM_GROUP_IDS")
TELEGRAM_GROUP_IDS = TELEGRAM_GROUP_IDS_STR.split(',') if TELEGRAM_GROUP_IDS_STR else []

if not all([BINANCE_API_KEY, BINANCE_SECRET_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_GROUP_IDS]):
    print("Error: One or more environment variables are missing.")
    exit()

binance_client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
telegram_bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# --- WordPress API Configuration ---
WORDPRESS_URL = "https://9jacashflow.com"
WORDPRESS_API_USER = os.getenv("WORDPRESS_API_USER")
WORDPRESS_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD")

WORDPRESS_PAGE_ID = 26265   # Scanner page
WORDPRESS_POST_CATEGORY_ID = 767
WORDPRESS_POST_TAG_ID = 779
WORDPRESS_POST_FEATURED_IMAGE_ID = 26267

# --- Config ---
watchlist = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
intervals = [
    Client.KLINE_INTERVAL_15MINUTE,
    Client.KLINE_INTERVAL_30MINUTE,
    Client.KLINE_INTERVAL_1HOUR,
    Client.KLINE_INTERVAL_4HOUR,
    Client.KLINE_INTERVAL_1DAY,
    Client.KLINE_INTERVAL_1WEEK,
    Client.KLINE_INTERVAL_1MONTH,
]
YOUR_TIMEZONE = "Africa/Lagos"


# --- Helper Functions for Data Analysis ---
def get_trend(symbol, interval):
    try:
        klines = binance_client.get_klines(symbol=symbol, interval=interval, limit=100)
        if len(klines) < 50:
            return "⚪️ N/A (Not enough data)"
        
        df = pd.DataFrame(klines, columns=[
            'open_time','open','high','low','close','volume','close_time',
            'quote_asset_volume','number_of_trades','taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume','ignore'
        ])
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
            return "⚪️ Neutral / Mixed"
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
    for _, interval in mtfa_intervals.items():
        trend_result = get_trend(symbol, interval)
        if "Bullish" in trend_result:
            bullish_count += 1
        elif "Bearish" in trend_result:
            bearish_count += 1
    if bullish_count == 3:
        return "🟢 Strong Bullish"
    elif bearish_count == 3:
        return "🔴 Strong Bearish"
    elif bullish_count > bearish_count:
        return "🟢 Bullish"
    elif bearish_count > bullish_count:
        return "🔴 Bearish"
    else:
        return "⚪️ Sideways/Mixed"


def get_trending_markets():
    print("Scanning for trending markets...")
    trending_markets = []
    try:
        exchange_info = binance_client.get_exchange_info()
        all_usdt_pairs = [s['symbol'] for s in exchange_info['symbols'] if 'USDT' in s['symbol'] and s['status'] == 'TRADING']
    except Exception as e:
        print(f"Failed to get exchange info: {e}")
        return []
    filtered_pairs = all_usdt_pairs[:200]
    for symbol in filtered_pairs:
        try:
            klines = binance_client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=100)
            if len(klines) < 100:
                continue
            df = pd.DataFrame(klines, columns=[
                'open_time','open','high','low','close','volume','close_time',
                'quote_asset_volume','number_of_trades','taker_buy_base_asset_volume',
                'taker_buy_quote_asset_volume','ignore'
            ])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            adx = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
            roc = ta.momentum.roc(df['close'], window=12)
            rsi = ta.momentum.rsi(df['close'], window=14)
            if adx.iloc[-1] > 25 and roc.iloc[-1] > 0 and rsi.iloc[-1] > 60:
                trending_markets.append({
                    'symbol': symbol,
                    'adx': adx.iloc[-1],
                    'roc': roc.iloc[-1],
                    'rsi': rsi.iloc[-1]
                })
            time.sleep(0.1)
        except Exception as e:
            print(f"Failed to analyze {symbol}: {e}")
            continue
    print(f"Found {len(trending_markets)} trending markets.")
    return trending_markets


async def send_long_message(chat_id, text, parse_mode='HTML'):
    MAX_MESSAGE_LENGTH = 4096
    parts = []
    lines = text.split('\n')
    current_part = ""
    for line in lines:
        if len(current_part) + len(line) + 1 > MAX_MESSAGE_LENGTH:
            parts.append(current_part)
            current_part = line + '\n'
        else:
            current_part += line + '\n'
    if current_part:
        parts.append(current_part)
    for part in parts:
        if not part.strip():
            continue
        try:
            await telegram_bot.send_message(chat_id=chat_id, text=part, parse_mode=parse_mode)
            print(f"Sent chunk to group {chat_id} ✅")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Failed to send chunk to group {chat_id}: {e} ❌")


# --- Report Generation ---
async def generate_report_text():
    tz = pytz.timezone(YOUR_TIMEZONE)
    now = datetime.now(tz)
    scan_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    message = (
        f"<b>Binance Market Trend Report</b>\n\n"
        f"<i>Scan time: {scan_time_str}</i>\n\n"
    )
    trending_markets = get_trending_markets()
    if trending_markets:
        message += "<b>🔥 Trending & Momentum Markets</b>\n\n"
        for i, market in enumerate(trending_markets, start=1):
            symbol = market['symbol']
            message += f"<b>{i}. {symbol}</b> (ADX: {market['adx']:.2f}, ROC: {market['roc']:.2f}, RSI: {market['rsi']:.2f})\n"
            message += f"  - Overall Trend: {get_overall_trend(symbol)}\n"
            for interval in intervals:
                trend = get_trend(symbol, interval)
                message += f"  - Trend ({interval}): {trend}\n"
            message += "\n"
    else:
        message += "<b>🔥 No significant trending markets found.</b>\n\n"
    message += "<b>📊 Watchlist Markets</b>\n\n"
    for i, coin in enumerate(watchlist, start=1):
        message += f"<b>{i}. {coin}</b>\n"
        message += f"  - Overall Trend: {get_overall_trend(coin)}\n"
        for interval in intervals:
            trend = get_trend(coin, interval)
            message += f"  - Trend ({interval}): {trend}\n"
        message += "\n"
    return message


async def send_report():
    message = await generate_report_text()
    for group_id in TELEGRAM_GROUP_IDS:
        await send_long_message(chat_id=group_id.strip(), text=message)
    return message


# --- WordPress Functions ---
def format_for_wordpress(report_text):
    html = report_text.replace("<b>", "<strong>").replace("</b>", "</strong>")
    html = html.replace("\n", "<br>")
    return f"<div class='market-scanner-report'>{html}</div>"

def update_wordpress_page(content_html):
    url = f"{WORDPRESS_URL}/wp-json/wp/v2/pages/{WORDPRESS_PAGE_ID}"
    payload = {"content": content_html}
    response = requests.post(
        url, auth=HTTPBasicAuth(WORDPRESS_API_USER, WORDPRESS_APP_PASSWORD), json=payload
    )
    if response.status_code == 200:
        print("✅ WordPress page updated.")
    else:
        print(f"❌ Page update failed: {response.status_code} {response.text}")

def create_wordpress_post(content_html, title):
    url = f"{WORDPRESS_URL}/wp-json/wp/v2/posts"
    payload = {
        "title": title,
        "status": "publish",
        "content": content_html,
        "categories": [WORDPRESS_POST_CATEGORY_ID],
        "tags": [WORDPRESS_POST_TAG_ID],
        "featured_media": WORDPRESS_POST_FEATURED_IMAGE_ID,
    }
    response = requests.post(
        url, auth=HTTPBasicAuth(WORDPRESS_API_USER, WORDPRESS_APP_PASSWORD), json=payload
    )
    if response.status_code == 201:
        print("✅ WordPress post created.")
    else:
        print(f"❌ Post creation failed: {response.status_code} {response.text}")


# --- Scheduler Job ---
def run_scanner_job():
    tz = pytz.timezone(YOUR_TIMEZONE)
    now = datetime.now(tz)
    current_time_str = now.strftime("%H:%M")
    print(f"\n--- SCHEDULER TRIGGERED at {now.strftime('%Y-%m-%d %H:%M:%S')} ({YOUR_TIMEZONE}) ---")
    try:
        message = asyncio.run(send_report())
        wp_html = format_for_wordpress(message)
        update_wordpress_page(wp_html)
        if current_time_str == "08:05":
            title = f"Binance Daily Market Scan – {now.strftime('%B %d, %Y')}"
            create_wordpress_post(wp_html, title)
        print("--- Job finished successfully. ---\n")
    except Exception as e:
        print(f"Job error: {e}")


# --- Main ---
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

    # Run once immediately
    run_scanner_job()

    # Scheduler
    schedule.every().day.at("08:05", YOUR_TIMEZONE).do(run_scanner_job)
    schedule.every().day.at("14:05", YOUR_TIMEZONE).do(run_scanner_job)
    schedule.every().day.at("23:05", YOUR_TIMEZONE).do(run_scanner_job)

    print("\nScheduler set. Bot running... ⏰")
    while True:
        schedule.run_pending()
        time.sleep(60)
