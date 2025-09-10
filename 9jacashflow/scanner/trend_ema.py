import schedule
import time
import MetaTrader5 as mt5
import pandas as pd
import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- WordPress API Configuration ---
WORDPRESS_URL = "https://9jacashflow.com"
WORDPRESS_API_USER = os.getenv("WORDPRESS_API_USER")
WORDPRESS_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD")

# IDs for the two static scanner pages
WORDPRESS_SCANNER_PAGE_ID = 26093  # The main scanner page
WORDPRESS_ARCHIVE_CATEGORY_ID = 767  # The category for the daily scan posts
WORDPRESS_DAILY_SCAN_TAG_ID = 771  # The tag ID for "Daily Market Scan"
WORDPRESS_FEATURED_IMAGE_ID = 26119 # The ID for the featured image to be used

# --- Consolidated MT5 Scanner Functions ---

def write_to_log(log_file, message):
    """Appends a message to the log file with a timestamp."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "a", encoding='utf-8') as f:
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        f.write(f"{timestamp} {message}\n")

def send_telegram_message(message, log_file):
    """Sends a potentially long message to Telegram."""
    TELEGRAM_MESSAGE_LIMIT = 4096
    
    if len(message) <= TELEGRAM_MESSAGE_LIMIT:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            log_message = f"❌ Failed to send Telegram message: {response.text}"
            print(log_message)
            write_to_log(log_file, log_message)
        else:
            log_message = "✅ Telegram message sent."
            print(log_message)
            write_to_log(log_file, log_message)
    else:
        while message:
            split_index = message.rfind('\n', 0, TELEGRAM_MESSAGE_LIMIT)
            if split_index == -1:
                split_index = TELEGRAM_MESSAGE_LIMIT
            chunk = message[:split_index]
            message = message[split_index:].lstrip()

            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                log_message = f"❌ Failed to send Telegram message chunk: {response.text}"
                print(log_message)
                write_to_log(log_file, log_message)
                break
            else:
                log_message = f"✅ Telegram message chunk sent (length: {len(chunk)})."
                print(log_message)
                write_to_log(log_file, log_message)

def get_historical_data(symbol, timeframe, count):
    """Retrieves historical data for a symbol."""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def calculate_adx_full(df, period):
    """
    Calculates the ADX indicator and returns ADX, +DI, and -DI values.
    """
    if len(df) < period * 2: return None, None, None
    df['high_low'] = df['high'] - df['low']
    df['high_prev_close'] = abs(df['high'] - df['close'].shift(1))
    df['low_prev_close'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['high_low', 'high_prev_close', 'low_prev_close']].max(axis=1)
    df['up_move'] = df['high'] - df['high'].shift(1)
    df['down_move'] = df['low'].shift(1) - df['low']
    
    df['+dm'] = 0.0
    df['-dm'] = 0.0
    
    df.loc[(df['up_move'] > df['down_move']) & (df['up_move'] > 0), '+dm'] = df['up_move']
    df.loc[(df['down_move'] > df['up_move']) & (df['down_move'] > 0), '-dm'] = df['down_move']
    
    df['atr'] = df['tr'].ewm(span=period, adjust=False).mean()
    df['+di'] = (df['+dm'].ewm(span=period, adjust=False).mean() / df['atr']) * 100
    df['-di'] = (df['-dm'].ewm(span=period, adjust=False).mean() / df['atr']) * 100
    df['dx'] = abs(df['+di'] - df['-di']) / (df['+di'] + df['-di']) * 100
    df['adx'] = df['dx'].ewm(span=period, adjust=False).mean()
    
    return df['adx'].iloc[-1], df['+di'].iloc[-1], df['-di'].iloc[-1]

# --- NEW FUNCTION TO CALCULATE EMA ---
def calculate_ema(df, period):
    """Calculates the Exponential Moving Average."""
    if len(df) < period:
        return None
    ema = df['close'].ewm(span=period, adjust=False).mean()
    return ema.iloc[-1]

# --- MODIFIED FUNCTION FOR TREND CALCULATION ---
def get_timeframe_trend(symbol, timeframe, candle_count, adx_period, ema_period):
    """Determines the trend for a single timeframe based on EMA(50) and DMI."""
    df = get_historical_data(symbol, timeframe, candle_count)
    if df is None or len(df) < candle_count:
        return "N/A"

    # Calculate required indicators
    _, plus_di, minus_di = calculate_adx_full(df, adx_period)
    ema_value = calculate_ema(df, ema_period)
    
    if ema_value is None or plus_di is None or minus_di is None:
        return "N/A"

    latest_close = df['close'].iloc[-1]
    
    # Apply the new trend logic
    is_bullish = latest_close > ema_value and plus_di > minus_di
    is_bearish = latest_close < ema_value and minus_di > plus_di

    if is_bullish:
        return "Bullish"
    elif is_bearish:
        return "Bearish"
    else:
        return "Neutral"

def calculate_roc(df, period):
    """Calculates the ROC indicator."""
    if len(df) < period: return None
    return ((df['close'].iloc[-1] - df['close'].iloc[-period]) / df['close'].iloc[-period]) * 100

def calculate_rsi(df, period):
    """Calculates the RSI indicator."""
    if len(df) < period * 2: return None
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    
    if avg_loss.iloc[-1] == 0:
        rs = 1000000 if avg_gain.iloc[-1] > 0 else 0
    else:
        rs = avg_gain.iloc[-1] / avg_loss.iloc[-1]
    
    rsi = 100 - (100 / (1 + rs))
    return rsi

def send_to_wordpress(title, content, log_file, page_id=None, post_categories=None, post_tags=None, featured_image_id=None):
    """
    Sends or updates content on a WordPress page or post using the REST API.
    - If page_id is provided, it updates that page.
    - If no page_id is provided, it creates a new post.
    - post_categories can be used to assign the new post to categories.
    """
    auth = (WORDPRESS_API_USER, WORDPRESS_APP_PASSWORD)
    headers = {
        "Content-Type": "application/json"
    }

    if page_id:
        endpoint = f"{WORDPRESS_URL}/wp-json/wp/v2/pages/{page_id}"
        payload = {
            "title": title,
            "content": content,
            "status": "publish"
        }
        method = "PUT"
    else:
        endpoint = f"{WORDPRESS_URL}/wp-json/wp/v2/posts"
        payload = {
            "title": title,
            "content": content,
            "status": "publish"
        }
        if post_categories:
            payload["categories"] = post_categories
        if post_tags:
            payload["tags"] = post_tags
        if featured_image_id:
            payload["featured_media"] = featured_image_id
        method = "POST"
    
    try:
        response = requests.request(method, endpoint, headers=headers, auth=auth, json=payload)
        response.raise_for_status()
        
        if page_id:
            log_message = f"✅ Successfully updated WordPress page (ID: {page_id}): {response.status_code}"
        else:
            log_message = f"✅ Successfully created WordPress post (ID: {response.json().get('id')}, Category: {post_categories}): {response.status_code}"
        
        print(log_message)
        write_to_log(log_file, log_message)
    except requests.exceptions.HTTPError as errh:
        error_message = f"❌ HTTP Error for WordPress: {errh} - {errh.response.text}"
        print(error_message)
        write_to_log(log_file, error_message)
    except requests.exceptions.ConnectionError as errc:
        error_message = f"❌ Error Connecting to WordPress: {errc}"
        print(error_message)
        write_to_log(log_file, error_message)
    except requests.exceptions.Timeout as errt:
        error_message = f"❌ Timeout Error for WordPress: {errt}"
        print(error_message)
        write_to_log(log_file, error_message)
    except requests.exceptions.RequestException as err:
        error_message = f"❌ Something went wrong with WordPress request: {err}"
        print(error_message)
        write_to_log(log_file, error_message)

# --- Configuration for each broker ---
BROKER_CONFIGS = [
    {"name": "Bybit", "path": r"C:/Program Files/Bybit MT5 Terminal Demo 1/terminal64.exe", "major_markets": ["GBPUSD+", "EURUSD+", "AUDUSD+", "USDJPY+", "GBPJPY+", "XAUUSD+", "XAGUSD", "USOUSD", "DJ30", "NAS100", "SP500", "UK100", "GER40", "Nikkei225"]},
    {"name": "Exness", "path": r"C:/Program Files/MetaTrader 5 EXNESS Demo 1/terminal64.exe", "major_markets": ["BTCUSD", "BCHUSD", "ETHUSD", "SOLUSD", "XRPUSD", "GBPUSD", "EURUSD", "US30", "USTEC", "US500", "USDJPY", "XAUUSD"]},
    {"name": "Deriv", "path": r"C:/Program Files/MetaTrader 5 Terminal/terminal64.exe", "major_markets": ['Volatility 10 Index', 'Volatility 25 Index', 'Volatility 50 Index', 'Volatility 75 Index', 'Volatility 100 Index', 'Crash 1000 Index', 'Crash 500 Index', 'Crash 300 Index', 'Crash 900 Index', 'Crash 600 Index', 'Boom 1000 Index', 'Boom 500 Index', 'Boom 300 Index']},
    {"name": "Weltrade", "path": r"C:/Program Files/MT5 Weltrade Synthetic Demo 1/terminal64.exe", "major_markets": [ 'FX Vol 20', 'FX Vol 40', 'FX Vol 60', 'FX Vol 80', 'FX Vol 99', 'SFX Vol 20', 'SFX Vol 40', 'SFX Vol 60', 'SFX Vol 80', 'SFX Vol 99' ]}
]

def scan_markets(broker_name, mt5_path, symbols_to_scan, scan_type, filter_results=True):
    """
    Executes a market scan for a given broker and list of symbols.
    - `filter_results`: If True, only returns markets meeting trending/momentum criteria.
      If False, returns all markets from the list with their data.
    """
    log_file = os.path.join("logs", "market-scanner", "market_scanner.log")
    
    start_message = f"Starting {scan_type} scan for {broker_name} at {datetime.now()}..."
    print(start_message)
    write_to_log(log_file, start_message)

    if not mt5.initialize(path=mt5_path):
        error_message = f"initialize() failed for {broker_name}, error code: {mt5.last_error()}"
        print(error_message)
        write_to_log(log_file, error_message)
        return []

    all_scanned_markets = []

    # --- Indicator Config ---
    CANDLE_COUNT = 100
    ADX_PERIOD = 14
    EMA_PERIOD = 50  # --- ADDED EMA PERIOD ---
    ADX_TRENDING_THRESHOLD = 25
    ROC_PERIOD = 14
    ROC_POSITIVE_MOMENTUM_THRESHOLD = 0.5
    RSI_PERIOD = 14
    RSI_MOMENTUM_CONFIRMATION_THRESHOLD = 55

    for symbol in symbols_to_scan:
        df_h1 = get_historical_data(symbol, mt5.TIMEFRAME_H1, CANDLE_COUNT)
        
        # Initialize values
        adx_value_h1, roc_value_h1, rsi_value_h1, is_trending, has_momentum = "N/A", "N/A", "N/A", False, False
        
        if df_h1 is not None and len(df_h1) >= CANDLE_COUNT:
            adx_value_h1, _, _ = calculate_adx_full(df_h1, ADX_PERIOD)
            roc_value_h1 = calculate_roc(df_h1, ROC_PERIOD)
            rsi_value_h1 = calculate_rsi(df_h1, RSI_PERIOD)

            if adx_value_h1 is not None:
                is_trending = adx_value_h1 >= ADX_TRENDING_THRESHOLD
            if roc_value_h1 is not None and rsi_value_h1 is not None:
                has_momentum = (roc_value_h1 > ROC_POSITIVE_MOMENTUM_THRESHOLD) and (rsi_value_h1 >= RSI_MOMENTUM_CONFIRMATION_THRESHOLD)

        # Build the market data dict
        market_data = {
            "Broker": broker_name,
            "Symbol": symbol,
            "ADX": round(adx_value_h1, 2) if isinstance(adx_value_h1, (float, int)) else "N/A",
            "ROC": round(roc_value_h1, 2) if isinstance(roc_value_h1, (float, int)) else "N/A",
            "RSI": round(rsi_value_h1, 2) if isinstance(rsi_value_h1, (float, int)) else "N/A",
            "IsTrendingMomentum": is_trending and has_momentum,
            "Timeframe_Trends": {},
            "Overall_Trend": "N/A",
            "Last Candle": df_h1['time'].iloc[-1].strftime('%Y-%m-%d %H:%M') if df_h1 is not None and len(df_h1) > 0 else "N/A"
        }
        
        # Only get timeframe trends if criteria are met or if we're not filtering
        if market_data["IsTrendingMomentum"] or not filter_results:
            TIMEFRAMES = {
                "15m": mt5.TIMEFRAME_M15,
                "30m": mt5.TIMEFRAME_M30,
                "1h": mt5.TIMEFRAME_H1,
                "4hr": mt5.TIMEFRAME_H4,
                "1d": mt5.TIMEFRAME_D1,
                "1w": mt5.TIMEFRAME_W1,
            }
            if df_h1 is not None and len(df_h1) >= CANDLE_COUNT:
                for tf_name, tf_mt5 in TIMEFRAMES.items():
                    # --- UPDATED FUNCTION CALL ---
                    market_data["Timeframe_Trends"][tf_name] = get_timeframe_trend(
                        symbol, tf_mt5, CANDLE_COUNT, ADX_PERIOD, EMA_PERIOD
                    )

                bullish_count = list(market_data["Timeframe_Trends"].values()).count("Bullish")
                bearish_count = list(market_data["Timeframe_Trends"].values()).count("Bearish")

                if bullish_count > bearish_count:
                    market_data["Overall_Trend"] = "Bullish"
                elif bearish_count > bullish_count:
                    market_data["Overall_Trend"] = "Bearish"
                else:
                    market_data["Overall_Trend"] = "Mixed"
            
        # Decide whether to include this market in the final list
        if filter_results:
            if market_data["IsTrendingMomentum"]:
                all_scanned_markets.append(market_data)
        else:
            all_scanned_markets.append(market_data)

    mt5.shutdown() # Shutdown MT5 for this broker instance

    return all_scanned_markets

def generate_output_content_for_broker(broker_name, scan_results, scan_type):
    """Generates formatted WordPress and Telegram content for a single broker."""
    scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- Added Emoji mapping for cleaner display ---
    TREND_EMOJIS = {
        "Bullish": "🟢 Bullish",
        "Bearish": "🔴 Bearish",
        "Neutral": "⚪️ Neutral",
        "N/A": "N/A"
    }

    telegram_content = f"*{scan_type.title()} Markets ({broker_name}) - Scanned at: {scan_time}*\n\n"
    wordpress_content = f"<h4>{scan_type.title()} Markets ({broker_name})</h4>"
    wordpress_content += '<div style="overflow-x: auto;">'
    wordpress_content += """
    <table border="1" style="width:100%; border-collapse: collapse; text-align: center;">
        <thead>
            <tr style="background-color:#f2f2f2;">
                <th style="padding: 8px;">Symbol</th>
                <th style="padding: 8px;">Overall Trend</th>
                <th style="padding: 8px;">H1 ADX</th>
                <th style="padding: 8px;">H1 ROC %</th>
                <th style="padding: 8px;">H1 RSI</th>
                <th style="padding: 8px;">15m</th>
                <th style="padding: 8px;">30m</th>
                <th style="padding: 8px;">1h</th>
                <th style="padding: 8px;">4hr</th>
                <th style="padding: 8px;">1d</th>
                <th style="padding: 8px;">1w</th>
            </tr>
        </thead>
        <tbody>
    """
    if scan_results:
        for market in scan_results:
            wordpress_content += f"""
            <tr>
                <td style="padding: 8px; text-align: left;">{market['Symbol']}</td>
                <td style="padding: 8px;">{TREND_EMOJIS.get(market['Overall_Trend'], market['Overall_Trend'])}</td>
                <td style="padding: 8px;">{market['ADX']}</td>
                <td style="padding: 8px;">{market['ROC']}</td>
                <td style="padding: 8px;">{market['RSI']}</td>
                <td style="padding: 8px;">{TREND_EMOJIS.get(market['Timeframe_Trends'].get('15m'), 'N/A')}</td>
                <td style="padding: 8px;">{TREND_EMOJIS.get(market['Timeframe_Trends'].get('30m'), 'N/A')}</td>
                <td style="padding: 8px;">{TREND_EMOJIS.get(market['Timeframe_Trends'].get('1h'), 'N/A')}</td>
                <td style="padding: 8px;">{TREND_EMOJIS.get(market['Timeframe_Trends'].get('4hr'), 'N/A')}</td>
                <td style="padding: 8px;">{TREND_EMOJIS.get(market['Timeframe_Trends'].get('1d'), 'N/A')}</td>
                <td style="padding: 8px;">{TREND_EMOJIS.get(market['Timeframe_Trends'].get('1w'), 'N/A')}</td>
            </tr>
            """
            line = f"`{market['Symbol']:<10} | Overall: {market['Overall_Trend']} | ADX: {market['ADX']} | ROC: {market['ROC']}% | RSI: {market['RSI']} | ⏱ {market['Last Candle']}`"
            telegram_content += line + "\n"

        wordpress_content += "</tbody></table>"
        wordpress_content += "</div>" # Close overflow-x div
        
    else:
        telegram_content += f"⚠️ No markets found with strong trend and momentum for {broker_name}." if scan_type == "Trending" else "No markets found in this list."
        wordpress_content += f"<p>No markets found with strong trend and momentum for {broker_name} at {scan_time}.</p>" if scan_type == "Trending" else f"<p>No markets found in this list at {scan_time}.</p>"
        wordpress_content += "</div>" # Close overflow-x div

    return telegram_content, wordpress_content


def run_main_scanner():
    """
    Runs the consolidated scan for all brokers and updates WordPress.
    """
    log_file_overall = os.path.join("logs", "market-scanner", "overall_wordpress.log")
    
    print(f"\n--- Starting Main Market Scanner ---")
    write_to_log(log_file_overall, f"--- Starting Main Market Scanner at {datetime.now()} ---")

    all_wordpress_content = []
    current_time = datetime.now()
    scan_start_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    main_telegram_message_parts = []
    all_trending_symbols = []
    
    wordpress_title_prefix = "Live Market Scanner"
    all_wordpress_content.append(f"<h1>{wordpress_title_prefix} Results - {scan_start_time}</h1>")
    
    # --- Section 1: Trending Markets ---
    all_wordpress_content.append("<h2>Trending Markets</h2>")
    
    for config in BROKER_CONFIGS:
        broker_name = config["name"]
        mt5_path = config["path"]

        if not mt5.initialize(path=mt5_path):
            write_to_log(log_file_overall, f"initialize() failed for {broker_name}, error code: {mt5.last_error()}")
            continue
        all_symbols = [s.name for s in mt5.symbols_get() if s.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED]
        mt5.shutdown()

        trending_results = scan_markets(broker_name, mt5_path, all_symbols, "Trending", filter_results=True)
        telegram_trending, wordpress_trending = generate_output_content_for_broker(broker_name, trending_results, "Trending")
        
        main_telegram_message_parts.append(telegram_trending)
        all_wordpress_content.append(wordpress_trending)
        all_wordpress_content.append("<hr>")

        # Collect symbols for the final JSON array
        all_trending_symbols.extend([m['Symbol'] for m in trending_results])


    # --- Section 2: Watchlist Markets ---
    all_wordpress_content.append("<h2>Watchlist Markets</h2>")
    
    for config in BROKER_CONFIGS:
        broker_name = config["name"]
        mt5_path = config["path"]
        major_markets = config["major_markets"]

        watchlist_results = scan_markets(broker_name, mt5_path, major_markets, "Watchlist", filter_results=False)
        telegram_watchlist, wordpress_watchlist = generate_output_content_for_broker(broker_name, watchlist_results, "Watchlist")

        main_telegram_message_parts.append(telegram_watchlist)
        all_wordpress_content.append(wordpress_watchlist)
        all_wordpress_content.append("<hr>")


    final_wordpress_content = "\n".join(all_wordpress_content)

    # Add the trending markets array to the final Telegram message
    markets_array_str = f"MARKETS = {json.dumps(all_trending_symbols)}"
    final_telegram_message = f"--- Cumulative Scan Results at {scan_start_time} ---\n\n" + "\n".join(main_telegram_message_parts) + f"\n`{markets_array_str}`"
    
    # --- Logging the full content sent to the static WordPress page ---
    log_message_wp_content = f"--- Content to be sent to Live Market Scanner page (ID: {WORDPRESS_SCANNER_PAGE_ID}) at {scan_start_time} ---\n{final_wordpress_content}\n"
    write_to_log(log_file_overall, log_message_wp_content)

    # --- Update the Static WordPress Page ---
    send_to_wordpress(wordpress_title_prefix, final_wordpress_content, log_file_overall, page_id=WORDPRESS_SCANNER_PAGE_ID)

    # --- Create a New Post for Archive (Only at the final scheduled time) ---
    if current_time.hour == 8 and current_time.minute <= 5: 
        archive_post_title = f"Daily Market Scan Results - {current_time.strftime('%B %d, %Y')}"
        send_to_wordpress(
            archive_post_title, 
            final_wordpress_content, 
            log_file_overall, 
            post_categories=[WORDPRESS_ARCHIVE_CATEGORY_ID], 
            post_tags=[WORDPRESS_DAILY_SCAN_TAG_ID],
            featured_image_id=WORDPRESS_FEATURED_IMAGE_ID
        )
        
    # --- Send a Cumulative Telegram message ---
    send_telegram_message(final_telegram_message, log_file_overall)

    print(f"--- Main scanner finished ---")
    write_to_log(log_file_overall, f"--- Main scanner finished ---")

# --- Main execution block ---
if __name__ == "__main__":
    # Initial run when the script starts
    run_main_scanner()

    # Schedule the scanner
    schedule.every().day.at("08:04").do(run_main_scanner)
    schedule.every().day.at("14:04").do(run_main_scanner)
    schedule.every().day.at("23:04").do(run_main_scanner)

    print("\nScheduler initialized. Waiting for the next scheduled run.")

    while True:
        schedule.run_pending()
        time.sleep(1)