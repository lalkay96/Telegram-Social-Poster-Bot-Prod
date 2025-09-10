import telegram
from binance.client import Client
import os
from dotenv import load_dotenv
import asyncio
import pandas as pd
import ta
import time
import schedule
import sys          # NEW: For logging
import pytz         # NEW: For timezone handling
from datetime import datetime # NEW: For diagnostic time logging

# --- Environment Setup ---
load_dotenv()

# --- Tee Class for Logging ---
# NEW: This class redirects print statements to both the console and a file
class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()  # Ensure content is written immediately
    def flush(self):
        for f in self.files:
            f.flush()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOTS_TOKEN")

TELEGRAM_GROUP_IDS_STR = os.getenv("TELEGRAM_GROUP_IDS")
TELEGRAM_GROUP_IDS = TELEGRAM_GROUP_IDS_STR.split(',') if TELEGRAM_GROUP_IDS_STR else []

if not all([BINANCE_API_KEY, BINANCE_SECRET_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_GROUP_IDS]):
    print("Error: One or more environment variables are missing.")
    print("Please check your .env file and ensure all credentials are set, including TELEGRAM_GROUP_IDS.")
    exit()

binance_client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
telegram_bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# --- Configuration ---
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
YOUR_TIMEZONE = "Africa/Lagos" # NEW: Define your timezone

# --- Helper Functions for Data Analysis ---

def get_trend(symbol, interval):
    """
    Determines the trend using the 50 EMA and the ADX's +DI/-DI lines.
    """
    try:
        klines = binance_client.get_klines(symbol=symbol, interval=interval, limit=100)
        if len(klines) < 50:
            return "⚪️ N/A (Not enough data)"
            
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
            return "⚪️ Neutral / Mixed"
            
    except Exception as e:
        print(f"Error getting trend for {symbol} on {interval}: {e}")
        return "⚠️ Error"

def get_overall_trend(symbol):
    """
    Performs a detailed Multiple Time Frame Analysis (MTFA).
    Returns 'Strong Bullish', 'Bullish', 'Strong Bearish', 'Bearish', or 'Sideways/Mixed'.
    """
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
    """Scans all USDT markets to find trending and momentum markets based on H1 indicators."""
    print("Scanning for trending markets...")
    trending_markets = []
    
    try:
        exchange_info = binance_client.get_exchange_info()
        all_usdt_pairs = [s['symbol'] for s in exchange_info['symbols'] if 'USDT' in s['symbol'] and s['status'] == 'TRADING']
    except Exception as e:
        print(f"Failed to get exchange info: {e}")
        return []

    # Limit to the first 200 pairs to keep the scan time reasonable
    filtered_pairs = all_usdt_pairs[:200]
    
    for symbol in filtered_pairs:
        try:
            klines = binance_client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=100)
            if len(klines) < 100:
                continue

            df = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])

            adx = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
            roc = ta.momentum.roc(df['close'], window=12)
            rsi = ta.momentum.rsi(df['close'], window=14)

            latest_adx = adx.iloc[-1]
            latest_roc = roc.iloc[-1]
            latest_rsi = rsi.iloc[-1]
            
            # Find markets with strong trend (ADX > 25), bullish momentum (ROC > 0), and strength (RSI > 60)
            if latest_adx > 25 and latest_roc > 0 and latest_rsi > 60:
                trending_markets.append({
                    'symbol': symbol,
                    'adx': latest_adx,
                    'roc': latest_roc,
                    'rsi': latest_rsi
                })
            
            time.sleep(0.1) # Small delay to be safe with API rate limits
            
        except Exception as e:
            print(f"Failed to analyze {symbol}: {e}")
            continue

    print(f"Found {len(trending_markets)} trending markets.")
    return trending_markets

async def send_long_message(chat_id, text, parse_mode='HTML'):
    """Splits a long message into multiple smaller messages and sends them."""
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
            await telegram_bot.send_message(
                chat_id=chat_id,
                text=part,
                parse_mode=parse_mode
            )
            print(f"Sent a message chunk to group {chat_id} ✅")
            await asyncio.sleep(1) 
        except Exception as e:
            print(f"Failed to send a message chunk to group {chat_id}: {e} ❌")


# --- Main Report Generation and Sending ---
async def send_report():
    """Generates the full market report and sends it to multiple Telegram groups."""
    print("--- Generating New Report ---")
    message = "<b>Binance Market Trend Report</b>\n\n"
    
    trending_markets = get_trending_markets()
    
    if trending_markets:
        message += "<b>🔥 Trending & Momentum Markets</b>\n\n"
        for i, market in enumerate(trending_markets, start=1):
            symbol = market['symbol']
            message += f"<b>{i}. {symbol}</b> (ADX: {market['adx']:.2f}, ROC: {market['roc']:.2f}, RSI: {market['rsi']:.2f})\n"
            message += f"  - Overall Trend: {get_overall_trend(symbol)}\n"
            for interval in intervals:
                trend = get_trend(symbol, interval)
                message += f"  - Trend ({interval}): {trend}\n"
            message += "\n"
    else:
        message += "<b>🔥 No significant trending markets found.</b>\n\n"
    
    message += "<b>📊 Watchlist Markets</b>\n\n"
    for i, coin in enumerate(watchlist, start=1):
        message += f"<b>{i}. {coin}</b>\n"
        message += f"  - Overall Trend: {get_overall_trend(coin)}\n"
        for interval in intervals:
            trend = get_trend(coin, interval)
            message += f"  - Trend ({interval}): {trend}\n"
        message += "\n"
    
    print("\n--- Report Generation Complete ---")
    
    print(f"Sending report to {len(TELEGRAM_GROUP_IDS)} group(s)...")
    for group_id in TELEGRAM_GROUP_IDS:
        await send_long_message(chat_id=group_id.strip(), text=message)

def run_scanner_job():
    """A simple wrapper to run the asynchronous send_report function."""
    print(f"\n--- SCHEDULER TRIGGERED at {datetime.now(pytz.timezone(YOUR_TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')} ({YOUR_TIMEZONE}) ---")
    try:
        asyncio.run(send_report())
        print("--- Scheduled job finished successfully. ---\n")
    except Exception as e:
        print(f"An error occurred during the scheduled job run: {e}")

# --- Main execution block ---
if __name__ == "__main__":
    # --- NEW: Logging Setup ---
    LOGS_DIR = "logs"
    LOG_FILE_PATH = os.path.join(LOGS_DIR, "binance", "trend.log")
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    
    log_file = open(LOG_FILE_PATH, 'a', encoding='utf-8')
    original_stdout = sys.stdout
    sys.stdout = Tee(original_stdout, log_file)
    
    print("======================================================")
    print(f"Bot starting up at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Server Time)")
    print("======================================================")
    
    # Run once immediately on startup
    run_scanner_job()

    # --- MODIFIED: Schedule with specified timezone ---
    schedule.every().day.at("08:00", YOUR_TIMEZONE).do(run_scanner_job)
    schedule.every().day.at("14:00", YOUR_TIMEZONE).do(run_scanner_job)
    schedule.every().day.at("23:00", YOUR_TIMEZONE).do(run_scanner_job)

    print("\nScheduler has been set up. Bot is now in running mode. ⏰")
    print(f"Schedules are set for {YOUR_TIMEZONE} timezone.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)