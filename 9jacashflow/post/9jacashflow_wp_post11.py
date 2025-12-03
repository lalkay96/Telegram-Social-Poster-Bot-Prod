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

# --- Telegram API Configuration (No changes needed) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
_group_ids = os.getenv("TELEGRAM_GROUP_IDS", "").split(',')
_user_ids = os.getenv("TELEGRAM_USER_IDS", "").split(',')
TELEGRAM_CHAT_IDS = [chat_id for chat_id in _group_ids + _user_ids if chat_id]

# --- Bot Settings (No changes needed) ---
POST_TIME = "08:05"
MAX_ITEMS = 20

# --- Tag ID Mapping (No changes needed) ---
TAG_IDS = {
    "daily_digest": 776, "crypto_trading": 777, "forex_trading": 540,
    "stock_trading": 778, "real_estate": 422, "agriculture": 544,
    "online_business": 389,
}

# --- Binance Weekly News Configuration (No changes needed) ---
BINANCE_WEEKLY_CONFIG = {
    "max_items": 15,
    "keywords": ["binance", "bnb", "bnb chain"],
    "intro": "🔥 <b>Binance Weekly News Roundup</b> 🔥\n\nHere are the top stories about Binance, BNB, and BNB Chain from the past week:",
    "sources":  [
        {"direct_rss": "https://cointelegraph.com/rss", "google_query": "site:cointelegraph.com crypto", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://www.coindesk.com/arc/outboundfeeds/rss/", "google_query": "site:coindesk.com crypto", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://decrypt.co/feed", "google_query": "site:decrypt.co crypto", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://www.theblock.co/rss.xml", "google_query": "site:theblock.co crypto", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://blockworks.co/feed", "google_query": "site:blockworks.co crypto", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://beincrypto.com/feed/", "google_query": "site:beincrypto.com crypto", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://bitcoinist.com/feed/", "google_query": "site:bitcoinist.com crypto", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://www.newsbtc.com/feed/", "google_query": "site:newsbtc.com crypto", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://cryptoslate.com/feed/", "google_query": "site:cryptoslate.com crypto", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://bitcoinmagazine.com/feed", "google_query": "site:bitcoinmagazine.com bitcoin", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://thedefiant.io/feed", "google_query": "site:thedefiant.io defi", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://u.today/rss", "google_query": "site:u.today crypto", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://feeds.bloomberg.com/crypto/source/crypto.rss", "google_query": "site:bloomberg.com/crypto", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://www.forbes.com/crypto-blockchain/feed/", "google_query": "site:forbes.com crypto", "use_google_fallback": True, "local": False},
        {"direct_rss": "https://nairametrics.com/category/cryptocurrency/feed/", "google_query": "site:nairametrics.com crypto", "use_google_fallback": True, "local": True},
    ]
}

# --- Category Configurations (No changes needed) ---
CATEGORIES = {
    "stock_trading": {
        "id": 341, "featured_media_ids": [25057, 24276, 25382],
        "intro": "Today’s <strong>Stock Market</strong> update 📈. Catch the top movers across Nigeria, Africa, and global equities.",
        "cta": "That’s it for today’s stock market roundup! Which market do you think will rally next? 🚀",
        "sources": [
            { "direct_rss": "https://nairametrics.com/category/stock-market/feed/", "google_query": "site:nairametrics.com stocks", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://businessday.ng/category/markets/feed/", "google_query": "site:businessday.ng stocks OR equities", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://www.proshareng.com/rss/", "google_query": "site:proshareng.com capital market", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://punchng.com/topics/business/capital-market/feed/", "google_query": "site:punchng.com stock market", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "google_query": "site:cnbc.com markets", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "google_query": "site:marketwatch.com stocks", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.reuters.com/markets/stocks/rss/", "google_query": "site:reuters.com stocks", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.bloomberg.com/opinion/authors/ARbTQlO_kkg/matthew-a-levine.rss", "google_query": "site:bloomberg.com money stuff", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://finance.yahoo.com/rss/", "google_query": "site:finance.yahoo.com market news", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.ft.com/markets?format=rss", "google_query": "site:ft.com markets", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.wsj.com/xml/rss/3_7031.xml", "google_query": "site:wsj.com markets", "use_google_fallback": True, "local": False }
        ]
    },
    "forex_trading": {
        "id": 539, "featured_media_ids": [24978, 25005, 24942],
        "intro": "Here’s your <strong>Forex Trading</strong> daily digest 📊. Stay ahead of the FX market with today’s top news.",
        "cta": "That’s a wrap on forex news today 🌍. Drop a comment on which currency pair you’re watching!",
        "sources": [
            { "direct_rss": "https://nairametrics.com/category/currency/feed/", "google_query": "site:nairametrics.com forex OR naira", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://businessday.ng/category/banking/feed/", "google_query": "site:businessday.ng forex OR currency", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://www.proshareng.com/rss/markets.php?market=FX", "google_query": "site:proshareng.com forex", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://www.dailyfx.com/feeds/top", "google_query": "site:dailyfx.com forex", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.forexlive.com/feed", "google_query": "site:forexlive.com forex", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.fxstreet.com/rss/news", "google_query": "site:fxstreet.com forex", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.investing.com/rss/news_2.rss", "google_query": "site:investing.com forex", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.babypips.com/feed", "google_query": "site:babypips.com forex news", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.reuters.com/markets/currencies/rss/", "google_query": "site:reuters.com currencies", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.bloomberg.com/professional/feed/insights/topics/foreign-exchange/", "google_query": "site:bloomberg.com forex", "use_google_fallback": True, "local": False }
        ]
    },
    "crypto_trading": {
        "id": 305, "featured_media_ids": [25124, 25057, 25159],
        "intro": "Welcome to today’s <strong>Crypto Trading</strong> roundup 🚀. Here are the top stories shaping the crypto markets today.",
        "cta": "That’s it for today’s crypto highlights! Which trade setup caught your attention? Share in the comments below 💬",
        "sources": BINANCE_WEEKLY_CONFIG["sources"]
    },
    "real_estate": {
        "id": 309, "featured_media_ids": [26216, 26217, 26218, 26219, 26220],
        "intro": "Welcome to today’s <strong>Real Estate</strong> roundup 🏠. Stay updated on property, housing, and infrastructure news.",
        "cta": "That’s the latest in real estate 🌍. Planning your next investment? Let’s talk in the comments 👇",
        "sources": [
            { "direct_rss": "https://nairametrics.com/category/real-estate/feed/", "google_query": "site:nairametrics.com real estate", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://businessday.ng/category/real-estate/feed/", "google_query": "site:businessday.ng real estate", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://guardian.ng/category/property/feed/", "google_query": "site:guardian.ng property OR \"real estate\"", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://punchng.com/topics/business/homes-property/feed/", "google_query": "site:punchng.com property", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://estateintel.com/feed", "google_query": "site:estateintel.com research", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://www.housingwire.com/feed", "google_query": "site:housingwire.com", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.inman.com/feed/", "google_query": "site:inman.com real estate", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.realtor.com/news/feed/", "google_query": "site:realtor.com news", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.bisnow.com/rss", "google_query": "site:bisnow.com commercial real estate", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://therealdeal.com/feed/", "google_query": "site:therealdeal.com", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.biggerpockets.com/blog/feed", "google_query": "site:biggerpockets.com/blog", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.wsj.com/xml/rss/3_7021.xml", "google_query": "site:wsj.com real estate", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.zillow.com/research/feed/", "google_query": "site:zillow.com/research", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.curbed.com/rss/index.xml", "google_query": "site:curbed.com real estate", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://kenmcelroy.com/feed/", "google_query": "site:kenmcelroy.com real estate", "use_google_fallback": True, "local": False }
        ]
    },
    "agriculture": {
        "id": 303, "featured_media_ids": [26210, 26211, 22711],
        "intro": "Your daily <strong>Agriculture & Agribusiness</strong> digest 🌱. From crops to livestock, here are today’s top updates.",
        "cta": "That’s it for agriculture today 🚜. What sector excites you most — crops, livestock, or exports? 💬",
        "sources": [
            { "direct_rss": "https://nairametrics.com/category/agriculture/feed/", "google_query": "site:nairametrics.com agriculture", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://businessday.ng/category/agriculture/feed/", "google_query": "site:businessday.ng agriculture", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://guardian.ng/category/business-services/agribusiness/feed/", "google_query": "site:guardian.ng agriculture OR agribusiness", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://punchng.com/topics/business/agro-business/feed/", "google_query": "site:punchng.com agriculture", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://allafrica.com/tools/headlines/rdf/agriculture/headlines.rdf", "google_query": "site:allafrica.com agriculture", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://www.premiumtimesng.com/category/agriculture/feed", "google_query": "site:premiumtimesng.com agriculture", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://www.agriculturedive.com/feeds/news/", "google_query": "site:agriculturedive.com", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.agri-pulse.com/rss", "google_query": "site:agri-pulse.com", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.agriculture.com/feed", "google_query": "site:agriculture.com news", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.agweb.com/rss", "google_query": "site:agweb.com", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.reuters.com/business/aerospace-defense/rss/", "google_query": "site:reuters.com agriculture", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.fao.org/news/rss/en/", "google_query": "site:fao.org news agriculture", "use_google_fallback": True, "local": False }
        ]
    },
    "online_business": {
        "id": 308, "featured_media_ids": [26212, 26213, 26214, 26215],
        "intro": "Here’s today’s <strong>Online Business</strong> roundup 💻. From freelancing to e-commerce, these are the key updates.",
        "cta": "That’s all for online business today 🚀. Are you building a side hustle or scaling up? Share below!",
        "sources": [
            { "direct_rss": "https://techcabal.com/feed/", "google_query": "site:techcabal.com", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://technext.ng/feed/", "google_query": "site:technext.ng", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://www.benjamindada.com/rss/", "google_query": "site:benjamindada.com", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://disrupt-africa.com/feed/", "google_query": "site:disrupt-africa.com nigeria", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://techpoint.africa/feed/", "google_query": "site:techpoint.africa", "use_google_fallback": True, "local": True },
            { "direct_rss": "https://techcrunch.com/feed/", "google_query": "site:techcrunch.com startup OR business", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.entrepreneur.com/latest.rss", "google_query": "site:entrepreneur.com online business", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.wired.com/feed/category/business/latest/rss", "google_query": "site:wired.com business", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://feeds.businessinsider.com/custom/all", "google_query": "site:businessinsider.com tech OR strategy", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.socialmediaexaminer.com/feed/", "google_query": "site:socialmediaexaminer.com", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.fastcompany.com/latest/rss", "google_query": "site:fastcompany.com tech business", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://www.inc.com/rss/", "google_query": "site:inc.com online business", "use_google_fallback": True, "local": False },
            { "direct_rss": "https://feeds.mashable.com/Mashable", "google_query": "site:mashable.com business", "use_google_fallback": True, "local": False }
        ]
    },
}

# --- NEW: URL Redirect Resolver ---
def resolve_redirect_url(url):
    """
    Follows a URL's redirect and returns the final destination URL.
    Especially useful for Google News links.
    """
    if "news.google.com" in url:
        try:
            # Use a HEAD request for efficiency; we only need the headers, not the content.
            response = requests.head(url, allow_redirects=True, timeout=10)
            return response.url # This will be the final URL after all redirects.
        except requests.RequestException as e:
            print(f"      -> ⚠️  Could not resolve redirect for {url}. Error: {e}")
            return url # Fallback to the original URL if resolution fails.
    return url

# --- Telegram Sender Function (No changes needed) ---
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
        time.sleep(1)

# --- News Fetching Functions ---

def _get_feed_from_source(src):
    """Helper function to get a feed using direct RSS with a Google News fallback."""
    feed = None
    try:
        direct_feed = feedparser.parse(src["direct_rss"])
        if direct_feed and direct_feed.entries:
            feed = direct_feed
            print(f"   -> Fetched DIRECTLY from: {src['direct_rss']}")
    except Exception as e:
        print(f"   -> Direct feed failed for {src['direct_rss']}. Error: {e}")

    if not feed and src.get("use_google_fallback", False):
        print(f"   -> Direct feed empty/failed. Trying GOOGLE FALLBACK for query: '{src['google_query']}'")
        try:
            encoded_query = quote_plus(f"{src['google_query']} when:7d")
            google_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            google_feed = feedparser.parse(google_url)
            if google_feed and google_feed.entries:
                feed = google_feed
        except Exception as e:
            print(f"   -> Google fallback also failed. Error: {e}")
    return feed

# --- MODIFIED: This function now resolves links for WordPress posts ---
def fetch_top_stories(sources, max_items=MAX_ITEMS):
    """Fetches top stories for WordPress, resolving Google News links."""
    stories = []
    used_links = set()
    all_articles_by_source = []
    random.shuffle(sources)

    for src in sources:
        feed = _get_feed_from_source(src)
        if feed:
            all_articles_by_source.append((feed.entries, src.get("local", False)))

    # Pass 1 & 2: Collate and de-duplicate articles
    for source_articles, is_local in all_articles_by_source:
        count = 0
        for entry in source_articles:
            if len(stories) >= max_items: break
            if hasattr(entry, 'link') and entry.link not in used_links:
                
                original_link = entry.link
                # --- MODIFIED: Resolve the URL before creating the HTML string ---
                final_link = resolve_redirect_url(original_link)
                # -----------------------------------------------------------------

                flag = "🇳🇬 " if is_local else ""
                html_story = f'{flag}<a href="{final_link}" target="_blank" rel="noopener noreferrer">{entry.title}</a>'
                stories.append(html_story)
                
                used_links.add(original_link)
                used_links.add(final_link) # Add both to avoid duplicates
                count += 1
            if count >= 2: break
        if len(stories) >= max_items: break

    if len(stories) < max_items:
        for source_articles, is_local in all_articles_by_source:
            for entry in source_articles:
                if len(stories) >= max_items: break
                if hasattr(entry, 'link') and entry.link not in used_links:
                    
                    original_link = entry.link
                    # --- MODIFIED: Resolve the URL before creating the HTML string ---
                    final_link = resolve_redirect_url(original_link)
                    # -----------------------------------------------------------------
                    
                    flag = "🇳🇬 " if is_local else ""
                    html_story = f'<a href="{final_link}" target="_blank" rel="noopener noreferrer">{entry.title}</a>'
                    stories.append(html_story)

                    used_links.add(original_link)
                    used_links.add(final_link)
            if len(stories) >= max_items: break
            
    print(f"   -> Fetched {len(stories)} unique stories for the digest.")
    return stories[:max_items]

# --- Post to WordPress (No changes needed) ---
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

# --- MODIFIED: This function now resolves links for Telegram ---
def run_binance_weekly_roundup_google_only():
    """
    Job to fetch and send the weekly Binance news to Telegram using a single Google News query.
    """
    print(f"\n--- Starting Binance Weekly Roundup (Google News) at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    keywords = '"Binance" OR "BNB" OR "BNB Chain"'
    max_items = 15
    intro_message = "🔥 <b>Binance Weekly News Roundup</b> 🔥\n\nHere are the top stories about Binance, BNB, and BNB Chain from the past week, powered by Google News:"

    query = f'({keywords}) when:7d'
    encoded_query = quote_plus(query)
    google_news_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    print(f"   -> Fetching from Google News URL: {google_news_url}")

    stories = []
    used_links = set()
    try:
        feed = feedparser.parse(google_news_url)
        if not feed.entries:
            print("   -> No entries found in Google News feed.")
        
        for entry in feed.entries:
            if len(stories) >= max_items:
                break
            
            original_link = entry.link
            if hasattr(entry, 'link') and original_link not in used_links:
                print(f"      -> Resolving: {original_link[:70]}...")
                # --- MODIFIED: Resolve the redirect here ---
                final_link = resolve_redirect_url(original_link)
                # ----------------------------------------
                
                html_story = f'<a href="{final_link}">{entry.title}</a>'
                stories.append(html_story)
                
                used_links.add(original_link)
                used_links.add(final_link)

    except Exception as e:
        print(f"❌ An error occurred while fetching the Google News feed: {e}")
        return

    if not stories:
        print("⚠️ No relevant Binance news found for the past week. Skipping Telegram message.")
        return

    message_lines = [intro_message]
    for i, story in enumerate(stories, 1):
        message_lines.append(f"{i}. {story}")
    
    final_message = "\n\n".join(message_lines)
    
    send_telegram_message(final_message)
    print("--- Binance Weekly Roundup (Google News) job finished. ---\n")

def run_all_wordpress():
    """Original function to run all WordPress posts."""
    if not WORDPRESS_API_USER or not WORDPRESS_APP_PASSWORD:
        print("❌ CRITICAL ERROR: WordPress credentials are not set.")
        return
    print(f"\n--- Starting WordPress job run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    # Convert to list to avoid "dictionary changed size during iteration" if CATEGORIES is modified
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
    
    print("🗓️   Setting up schedules...")
    
    schedule.every().day.at(POST_TIME).do(run_all_wordpress)
    print(f"   -> Daily WordPress digests scheduled for {POST_TIME} (Server Time).")
    
    schedule.every().saturday.at("10:05").do(run_binance_weekly_roundup_google_only)
    print("   -> Weekly Binance Telegram roundup (Google News) scheduled for Saturday at 10:05.")

    # --- Initial Run for Testing ---
    # Uncomment the lines below to test immediately
    # print("\n🚀 Running initial jobs immediately for testing...")
    # run_all_wordpress() 
    # run_binance_weekly_roundup_google_only()

    print("\n✅ All jobs scheduled. Bot is now running. Waiting for pending jobs...")
    while True:
        schedule.run_pending()
        time.sleep(60)