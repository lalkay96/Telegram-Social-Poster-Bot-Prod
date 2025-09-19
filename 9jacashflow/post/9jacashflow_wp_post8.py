# NEWS AGGREGATOR (Ultimate Hybrid/Fallback Edition with Rotating Images - FULLY POPULATED)
# + Binance Weekly Telegram Roundup

import feedparser
import requests
import schedule
import time
from datetime import datetime, timedelta
import os
import sys
from dotenv import load_dotenv
import random
from urllib.parse import quote_plus

# Load environment variables from .env file
load_dotenv()

# --- Tee Class for Logging (No changes needed) ---
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

# --- WordPress API Configuration (No changes needed) ---
WORDPRESS_URL = "https://9jacashflow.com/wp-json/wp/v2/posts"
WORDPRESS_API_USER = os.getenv("WORDPRESS_API_USER")
WORDPRESS_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD")

# --- Telegram API Configuration (NEW) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
# Combine group IDs and user IDs into a single list for sending messages
_group_ids = os.getenv("TELEGRAM_GROUP_IDS", "").split(',')
_user_ids = os.getenv("TELEGRAM_USER_IDS", "").split(',')
TELEGRAM_CHAT_IDS = [chat_id for chat_id in _group_ids + _user_ids if chat_id] # Filter out empty strings

# --- Bot Settings (No changes needed) ---
POST_TIME = "08:05"
MAX_ITEMS = 20

# --- Tag ID Mapping (No changes needed) ---
TAG_IDS = {
    "daily_digest": 776, "crypto_trading": 777, "forex_trading": 540,
    "stock_trading": 778, "real_estate": 422, "agriculture": 544,
    "online_business": 389,
}

# --- Binance Weekly News Configuration (NEW) ---
BINANCE_WEEKLY_CONFIG = {
    "max_items": 15,
    "keywords": ["binance", "bnb", "bnb chain"],
    "intro": "🔥 <b>Binance Weekly News Roundup</b> 🔥\n\nHere are the top stories about Binance, BNB, and BNB Chain from the past week:",
    "sources":  [
                # --- Original Sources ---
                {"direct_rss": "https://cointelegraph.com/rss", "google_query": "site:cointelegraph.com crypto", "use_google_fallback": True, "local": False},
                {"direct_rss": "https://www.coindesk.com/arc/outboundfeeds/rss/", "google_query": "site:coindesk.com crypto", "use_google_fallback": True, "local": False},
                {"direct_rss": "https://decrypt.co/feed", "google_query": "site:decrypt.co crypto", "use_google_fallback": True, "local": False},
                
                # --- Newly Added Tier 1 Sources ---
                {"direct_rss": "https://www.theblock.co/rss.xml", "google_query": "site:theblock.co crypto", "use_google_fallback": True, "local": False},
                {"direct_rss": "https://blockworks.co/feed", "google_query": "site:blockworks.co crypto", "use_google_fallback": True, "local": False},
                {"direct_rss": "https://beincrypto.com/feed/", "google_query": "site:beincrypto.com crypto", "use_google_fallback": True, "local": False},

                # --- Original Sources Continued ---
                {"direct_rss": "https://bitcoinist.com/feed/", "google_query": "site:bitcoinist.com crypto", "use_google_fallback": True, "local": False},
                {"direct_rss": "https://www.newsbtc.com/feed/", "google_query": "site:newsbtc.com crypto", "use_google_fallback": True, "local": False},
                {"direct_rss": "https://cryptoslate.com/feed/", "google_query": "site:cryptoslate.com crypto", "use_google_fallback": True, "local": False},
                {"direct_rss": "https://bitcoinmagazine.com/feed", "google_query": "site:bitcoinmagazine.com bitcoin", "use_google_fallback": True, "local": False},
                
                # --- Newly Added Niche & Mainstream Sources ---
                {"direct_rss": "https://thedefiant.io/feed", "google_query": "site:thedefiant.io defi", "use_google_fallback": True, "local": False},
                {"direct_rss": "https://u.today/rss", "google_query": "site:u.today crypto", "use_google_fallback": True, "local": False},
                {"direct_rss": "https://feeds.bloomberg.com/crypto/source/crypto.rss", "google_query": "site:bloomberg.com/crypto", "use_google_fallback": True, "local": False},
                {"direct_rss": "https://www.forbes.com/crypto-blockchain/feed/", "google_query": "site:forbes.com crypto", "use_google_fallback": True, "local": False},

                # --- Newly Added Local Nigerian Source ---
                {"direct_rss": "https://nairametrics.com/category/cryptocurrency/feed/", "google_query": "site:nairametrics.com crypto", "use_google_fallback": True, "local": True},
            ]
}

# --- Category Configurations (Unchanged) ---
CATEGORIES = {
    "stock_trading": {
        "id": 341, "featured_media_ids": [25057, 24276, 25382],
        "intro": "Today’s <strong>Stock Market</strong> update 📈. Catch the top movers across Nigeria, Africa, and global equities.",
        "cta": "That’s it for today’s stock market roundup! Which market do you think will rally next? 🚀",
        "sources": [
            {"direct_rss": "https://nairametrics.com/category/stock-market/feed/", "google_query": "site:nairametrics.com stocks", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://businessday.ng/category/markets/feed/", "google_query": "site:businessday.ng stocks", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "google_query": "site:cnbc.com stocks", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "google_query": "site:marketwatch.com stocks", "use_google_fallback": True, "local": False},
        ]
    },
    "forex_trading": {
        "id": 539, "featured_media_ids": [24978, 25005, 24942],
        "intro": "Here’s your <strong>Forex Trading</strong> daily digest 📊. Stay ahead of the FX market with today’s top news.",
        "cta": "That’s a wrap on forex news today 🌍. Drop a comment on which currency pair you’re watching!",
        "sources": [
            {"direct_rss": "https://www.dailyfx.com/feeds/top", "google_query": "site:dailyfx.com forex", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.forexlive.com/feed", "google_query": "site:forexlive.com forex", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.fxstreet.com/rss/news", "google_query": "site:fxstreet.com forex", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://nairametrics.com/category/currency/feed/", "google_query": "site:nairametrics.com forex", "use_google_fallback": True, "local": True},
        ]
    },
    "crypto_trading": {
        "id": 305, "featured_media_ids": [25124, 25057, 25159],
        "intro": "Welcome to today’s <strong>Crypto Trading</strong> roundup 🚀. Here are the top stories shaping the crypto markets today.",
        "cta": "That’s it for today’s crypto highlights! Which trade setup caught your attention? Share in the comments below 💬",
        "sources": BINANCE_WEEKLY_CONFIG["sources"] # Re-using the same sources for daily crypto digest
    },
    # ... your other categories (real_estate, agriculture, online_business) remain unchanged ...
    "real_estate": {
        "id": 309, "featured_media_ids": [26216, 26217, 26218, 26219, 26220],
        "intro": "Welcome to today’s <strong>Real Estate</strong> roundup 🏠. Stay updated on property, housing, and infrastructure news.",
        "cta": "That’s the latest in real estate 🌍. Planning your next investment? Let’s talk in the comments 👇",
        "sources": [
            {"direct_rss": "https://nairametrics.com/category/real-estate/feed/", "google_query": "site:nairametrics.com real estate", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://businessday.ng/category/real-estate/feed/", "google_query": "site:businessday.ng real estate", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://www.housingwire.com/feed", "google_query": "site:housingwire.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.inman.com/feed/", "google_query": "site:inman.com real estate", "use_google_fallback": True, "local": False},
        ]
    },
    "agriculture": {
        "id": 303, "featured_media_ids": [26210, 26211, 22711],
        "intro": "Your daily <strong>Agriculture & Agribusiness</strong> digest 🌱. From crops to livestock, here are today’s top updates.",
        "cta": "That’s it for agriculture today 🚜. What sector excites you most — crops, livestock, or exports? 💬",
        "sources": [
            {"direct_rss": "https://nairametrics.com/category/agriculture/feed/", "google_query": "site:nairametrics.com agriculture", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://businessday.ng/category/agriculture/feed/", "google_query": "site:businessday.ng agriculture", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://guardian.ng/category/business-services/agriculture/feed/", "google_query": "site:guardian.ng agriculture", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://www.agriculturedive.com/feeds/news/", "google_query": "site:agriculturedive.com", "use_google_fallback": True, "local": False},
        ]
    },
    "online_business": {
        "id": 308, "featured_media_ids": [26212, 26213, 26214, 26215],
        "intro": "Here’s today’s <strong>Online Business</strong> roundup 💻. From freelancing to e-commerce, these are the key updates.",
        "cta": "That’s all for online business today 🚀. Are you building a side hustle or scaling up? Share below!",
        "sources": [
            {"direct_rss": "https://techcrunch.com/feed/", "google_query": "site:techcrunch.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.entrepreneur.com/latest.rss", "google_query": "site:entrepreneur.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://techcabal.com/feed/", "google_query": "site:techcabal.com", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://www.wired.com/feed/category/business/latest/rss", "google_query": "site:wired.com business", "use_google_fallback": True, "local": False},
        ]
    },
}

# --- Telegram Sender Function (NEW) ---
def send_telegram_message(message):
    """Sends a message to all configured Telegram chat IDs."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not configured. Skipping.")
        return
    if not TELEGRAM_CHAT_IDS:
        print("❌ No TELEGRAM_GROUP_IDS or TELEGRAM_USER_IDS configured. Skipping.")
        return

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {
            'chat_id': chat_id.strip(),
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        try:
            r = requests.post(api_url, data=payload, timeout=10)
            if r.status_code == 200:
                print(f"✅ Telegram message sent successfully to Chat ID: {chat_id.strip()}")
            else:
                print(f"❌ Failed to send Telegram message to {chat_id.strip()}. Status: {r.status_code}, Response: {r.text}")
        except requests.exceptions.RequestException as e:
            print(f"❌ An error occurred while sending message to {chat_id.strip()}: {e}")
        time.sleep(1) # Sleep briefly to avoid rate limiting


# --- News Fetching Functions (MODIFIED & NEW) ---

def _get_feed_from_source(src):
    """Helper function to get a feed using direct RSS with a Google News fallback."""
    feed = None
    # Attempt direct RSS feed
    try:
        direct_feed = feedparser.parse(src["direct_rss"])
        if direct_feed and direct_feed.entries:
            feed = direct_feed
            print(f"   -> Fetched DIRECTLY from: {src['direct_rss']}")
    except Exception as e:
        print(f"   -> Direct feed failed for {src['direct_rss']}. Error: {e}")

    # If direct fails and fallback is enabled, try Google News
    if not feed and src.get("use_google_fallback", False):
        print(f"   -> Direct feed empty/failed. Trying GOOGLE FALLBACK for query: '{src['google_query']}'")
        try:
            encoded_query = quote_plus(f"{src['google_query']} when:7d") # Add time filter to google query
            google_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            google_feed = feedparser.parse(google_url)
            if google_feed and google_feed.entries:
                feed = google_feed
        except Exception as e:
            print(f"   -> Google fallback also failed. Error: {e}")
    return feed

def fetch_binance_news(sources, keywords, max_items):
    """Fetches news from the last week that matches specific keywords."""
    stories = []
    used_links = set()
    one_week_ago = datetime.now() - timedelta(days=7)

    for src in sources:
        feed = _get_feed_from_source(src)
        if not feed:
            continue

        for entry in feed.entries:
            # 1. Check for valid link and title
            if not hasattr(entry, 'link') or not hasattr(entry, 'title'):
                continue

            # 2. Check for keywords
            title_lower = entry.title.lower()
            if not any(keyword.lower() in title_lower for keyword in keywords):
                continue
            
            # 3. Check publication date (must be within the last week)
            published_dt = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published_dt = datetime.fromtimestamp(time.mktime(entry.updated_parsed))

            if published_dt and published_dt >= one_week_ago:
                if entry.link not in used_links:
                    # Format for Telegram: <a href='...'>Title</a>
                    html_story = f'<a href="{entry.link}">{entry.title}</a>'
                    stories.append(html_story)
                    used_links.add(entry.link)
            
            if len(stories) >= max_items:
                break
        if len(stories) >= max_items:
            break
            
    print(f"   -> Fetched {len(stories)} unique stories for the Binance digest.")
    return stories[:max_items]

def fetch_top_stories(sources, max_items=MAX_ITEMS):
    """Original function for fetching general news for WordPress."""
    stories = []
    used_links = set()
    all_articles_by_source = []
    random.shuffle(sources)

    for src in sources:
        feed = _get_feed_from_source(src)
        if feed:
            all_articles_by_source.append((feed.entries, src.get("local", False)))

    # Pass 1 & 2: Collate and de-duplicate articles (no changes needed here)
    for source_articles, is_local in all_articles_by_source:
        count = 0
        for entry in source_articles:
            if len(stories) >= max_items: break
            if hasattr(entry, 'link') and entry.link not in used_links:
                flag = "🇳🇬 " if is_local else ""
                html_story = f'{flag}<a href="{entry.link}" target="_blank" rel="noopener noreferrer">{entry.title}</a>'
                stories.append(html_story)
                used_links.add(entry.link)
                count += 1
            if count >= 2: break
        if len(stories) >= max_items: break

    if len(stories) < max_items:
        for source_articles, is_local in all_articles_by_source:
            for entry in source_articles:
                if len(stories) >= max_items: break
                if hasattr(entry, 'link') and entry.link not in used_links:
                    flag = "🇳🇬 " if is_local else ""
                    html_story = f'<a href="{entry.link}" target="_blank" rel="noopener noreferrer">{entry.title}</a>'
                    stories.append(html_story)
                    used_links.add(entry.link)
            if len(stories) >= max_items: break
            
    print(f"   -> Fetched {len(stories)} unique stories for the digest.")
    return stories[:max_items]

# --- Post to WordPress (Unchanged) ---
def post_to_wordpress(category_key, cfg):
    print(f"Fetching stories for WordPress category: {category_key}...")
    stories = fetch_top_stories(cfg["sources"])
    if not stories:
        print(f"⚠️ No stories found for {category_key}")
        return

    content_parts = [f"<p>{cfg['intro']}</p>", f"<ol>{''.join([f'<li>{s}</li>' for s in stories])}</ol>", f"<p>{cfg['cta']}</p>"]
    content = "".join(content_parts)
    category_title = category_key.replace('_', ' ').title()
    post_title = f"{category_title} Daily Digest – {datetime.now().strftime('%B %d, %Y')}"
    selected_media_id = random.choice(cfg["featured_media_ids"])

    data = {
        "title": post_title, "content": content, "status": "publish",
        "categories": [cfg["id"]], "featured_media": selected_media_id,
        "tags": [TAG_IDS["daily_digest"], TAG_IDS.get(category_key)]
    }

    print(f"Attempting to post to WordPress: '{post_title}' with image ID: {selected_media_id}")
    try:
        r = requests.post(
            WORDPRESS_URL, auth=(WORDPRESS_API_USER, WORDPRESS_APP_PASSWORD), json=data, timeout=30
        )
        if r.status_code == 201:
            print(f"✅ {category_key} digest posted successfully! URL: {r.json().get('link', 'N/A')}")
        else:
            print(f"❌ Failed to post {category_key}. Status: {r.status_code}, Response: {r.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred while posting {category_key}: {e}")

# --- Master Run & Schedule Functions ---

def run_binance_weekly_roundup():
    """Job to fetch and send the weekly Binance news to Telegram."""
    print(f"\n--- Starting Binance Weekly Roundup job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    cfg = BINANCE_WEEKLY_CONFIG
    stories = fetch_binance_news(cfg["sources"], cfg["keywords"], cfg["max_items"])

    if not stories:
        print("⚠️ No relevant Binance news found for the past week. Skipping Telegram message.")
        return

    # Build the message as an ordered list for Telegram
    message_lines = [cfg["intro"]]
    for i, story in enumerate(stories, 1):
        message_lines.append(f"{i}. {story}")
    
    final_message = "\n\n".join(message_lines)
    
    send_telegram_message(final_message)
    print("--- Binance Weekly Roundup job finished. ---\n")

def run_all_wordpress():
    """Original function to run all WordPress posts."""
    if not WORDPRESS_API_USER or not WORDPRESS_APP_PASSWORD:
        print("❌ CRITICAL ERROR: WordPress credentials are not set.")
        return
    print(f"\n--- Starting WordPress job run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    for key, cfg in list(CATEGORIES.items()):
        post_to_wordpress(key, cfg)
        time.sleep(10)
    print("--- WordPress job run finished. ---\n")

if __name__ == "__main__":
    LOGS_DIR = "logs"
    LOG_FILE_PATH = os.path.join(LOGS_DIR, "9jacashflow", "post.log")
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    log_file = open(LOG_FILE_PATH, 'a', encoding='utf-8')
    sys.stdout = Tee(sys.stdout, log_file)
    print("=" * 50 + f"\nSCRIPT STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" + "=" * 50)
    
    # --- Scheduling ---
    print("🗓️  Setting up schedules...")
    
    # Schedule 1: Daily WordPress Posts
    schedule.every().day.at(POST_TIME).do(run_all_wordpress)
    print(f"   -> Daily WordPress digests scheduled for {POST_TIME} (Server Time).")
    
    # Schedule 2: Weekly Binance Telegram Roundup (NEW)
    schedule.every().saturday.at("10:05").do(run_binance_weekly_roundup)
    print("   -> Weekly Binance Telegram roundup scheduled for Saturday at 10:05 (Server Time).")
    
    # --- Initial Run for Testing ---
    # Uncomment the lines below if you want to test them immediately upon starting the script
    # print("\n🚀 Running initial jobs immediately for testing...")
    # run_all_wordpress() 
    run_binance_weekly_roundup()

    print("\n✅ All jobs scheduled. Bot is now running. Waiting for pending jobs...")
    while True:
        schedule.run_pending()
        time.sleep(60)