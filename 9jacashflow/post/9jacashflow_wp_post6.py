# NEWS AGGREGATOR (Ultimate Hybrid/Fallback Edition with Rotating Images - FULLY POPULATED)

import feedparser
import requests
import schedule
import time
from datetime import datetime
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

# --- Bot Settings (No changes needed) ---
POST_TIME = "08:05"
MAX_ITEMS = 20

# --- Tag ID Mapping (No changes needed) ---
TAG_IDS = {
    "daily_digest": 776, "crypto_trading": 777, "forex_trading": 540,
    "stock_trading": 778, "real_estate": 422, "agriculture": 544,
    "online_business": 389,
}

# --- Category Configurations (Fully Populated with Fallback Logic) ---
# Each source now has a direct RSS feed, a Google query, and a 'use_google_fallback' switch.
# The script will ALWAYS try the 'direct_rss' first.
# If it fails AND 'use_google_fallback' is True, it will try the 'google_query'.
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
            {"direct_rss": "https://www.reuters.com/markets/rss/", "google_query": "site:reuters.com stocks", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.bloomberg.com/opinion/authors/ARbTQlO_kkg/matthew-a-levine.rss", "google_query": "site:bloomberg.com stocks", "use_google_fallback": True, "local": False},
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
            {"direct_rss": "https://www.investing.com/rss/news.rss", "google_query": "site:investing.com forex", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://nairametrics.com/category/currency/feed/", "google_query": "site:nairametrics.com forex", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://businessday.ng/category/banking/feed/", "google_query": "site:businessday.ng forex", "use_google_fallback": True, "local": True},
        ]
    },
    "crypto_trading": {
        "id": 305, "featured_media_ids": [25124, 25057, 25159],
        "intro": "Welcome to today’s <strong>Crypto Trading</strong> roundup 🚀. Here are the top stories shaping the crypto markets today.",
        "cta": "That’s it for today’s crypto highlights! Which trade setup caught your attention? Share in the comments below 💬",
        "sources": [
            {"direct_rss": "https://cointelegraph.com/rss", "google_query": "site:cointelegraph.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.coindesk.com/arc/outboundfeeds/rss/", "google_query": "site:coindesk.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://decrypt.co/feed", "google_query": "site:decrypt.co", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://nairametrics.com/category/cryptocurrency/feed/", "google_query": "site:nairametrics.com crypto", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://bitcoinist.com/feed/", "google_query": "site:bitcoinist.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.newsbtc.com/feed/", "google_query": "site:newsbtc.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://cryptoslate.com/feed/", "google_query": "site:cryptoslate.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://bitcoinmagazine.com/feed", "google_query": "site:bitcoinmagazine.com", "use_google_fallback": True, "local": False},
        ]
    },
    "real_estate": {
        "id": 309, "featured_media_ids": [26216, 26217, 26218, 26219, 26220],
        "intro": "Welcome to today’s <strong>Real Estate</strong> roundup 🏠. Stay updated on property, housing, and infrastructure news.",
        "cta": "That’s the latest in real estate 🌍. Planning your next investment? Let’s talk in the comments 👇",
        "sources": [
            {"direct_rss": "https://nairametrics.com/category/real-estate/feed/", "google_query": "site:nairametrics.com real estate", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://businessday.ng/category/real-estate/feed/", "google_query": "site:businessday.ng real estate", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://www.housingwire.com/feed", "google_query": "site:housingwire.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.inman.com/feed/", "google_query": "site:inman.com real estate", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.realtor.com/news/feed/", "google_query": "site:realtor.com news", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.bisnow.com/rss", "google_query": "site:bisnow.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://kenmcelroy.com/feed/", "google_query": "site:kenmcelroy.com real estate", "use_google_fallback": True, "local": False},
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
            {"direct_rss": "https://www.agri-pulse.com/rss", "google_query": "site:agri-pulse.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.agriculture.com/feed", "google_query": "site:agriculture.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.agweb.com/rss", "google_query": "site:agweb.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://allafrica.com/tools/headlines/rdf/agriculture/headlines.rdf", "google_query": "site:allafrica.com agriculture", "use_google_fallback": True, "local": True},
        ]
    },
    "online_business": {
        "id": 308, "featured_media_ids": [26212, 26213, 26214, 26215],
        "intro": "Here’s today’s <strong>Online Business</strong> roundup 💻. From freelancing to e-commerce, these are the key updates.",
        "cta": "That’s all for online business today 🚀. Are you building a side hustle or scaling up? Share below!",
        "sources": [
            {"direct_rss": "https://techcrunch.com/feed/", "google_query": "site:techcrunch.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.entrepreneur.com/latest.rss", "google_query": "site:entrepreneur.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://technext24.com/feed/", "google_query": "site:technext24.com", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://techcabal.com/feed/", "google_query": "site:techcabal.com", "use_google_fallback": True, "local": True},
            {"direct_rss": "https://www.wired.com/feed/category/business/latest/rss", "google_query": "site:wired.com business", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://feeds.businessinsider.com/custom/all", "google_query": "site:businessinsider.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://disrupt-africa.com/feed/", "google_query": "site:disrupt-africa.com", "use_google_fallback": True, "local": False},
            {"direct_rss": "https://www.socialmediaexaminer.com/feed/", "google_query": "site:socialmediaexaminer.com", "use_google_fallback": True, "local": False},
        ]
    },
}


# --- Fetch & Format News (MODIFIED FOR FALLBACK LOGIC) ---
def fetch_top_stories(sources, max_items=MAX_ITEMS):
    stories = []
    used_links = set()
    all_articles_by_source = []
    random.shuffle(sources)

    for src in sources:
        feed = None
        # --- Step 1: Attempt to fetch from the direct RSS feed FIRST ---
        try:
            direct_feed = feedparser.parse(src["direct_rss"])
            if direct_feed and direct_feed.entries:
                feed = direct_feed
                print(f"   -> Fetched DIRECTLY from: {src['direct_rss']}")
        except Exception as e:
            print(f"   -> Direct feed failed for {src['direct_rss']}. Error: {e}")

        # --- Step 2: If direct feed fails AND fallback is enabled, try Google News ---
        if not feed and src.get("use_google_fallback", False):
            print(f"   -> Direct feed empty/failed. Trying GOOGLE FALLBACK for query: '{src['google_query']}'")
            try:
                encoded_query = quote_plus(src['google_query'])
                google_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
                google_feed = feedparser.parse(google_url)
                if google_feed and google_feed.entries:
                    feed = google_feed
            except Exception as e:
                print(f"   -> Google fallback also failed. Error: {e}")

        # --- Step 3: If a feed was successfully fetched (either direct or fallback), add its articles ---
        if feed:
            all_articles_by_source.append((feed.entries, src["local"]))

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
                    html_story = f'{flag}<a href="{entry.link}" target="_blank" rel="noopener noreferrer">{entry.title}</a>'
                    stories.append(html_story)
                    used_links.add(entry.link)
            if len(stories) >= max_items: break
            
    print(f"   -> Fetched {len(stories)} unique stories for the digest.")
    return stories[:max_items]

# --- Post to WordPress (With image rotation - no changes needed) ---
def post_to_wordpress(category_key, cfg):
    print(f"Fetching stories for {category_key}...")
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

    print(f"Attempting to post: '{post_title}' with image ID: {selected_media_id}")
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

# --- Master Run & Schedule (No changes needed) ---
def run_all():
    if not WORDPRESS_API_USER or not WORDPRESS_APP_PASSWORD:
        print("❌ CRITICAL ERROR: WordPress credentials are not set.")
        return
    print(f"\n--- Starting job run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    for key, cfg in list(CATEGORIES.items()):
        post_to_wordpress(key, cfg)
        time.sleep(10)
    print("--- Job run finished. ---\n")

if __name__ == "__main__":
    LOGS_DIR = "logs"
    LOG_FILE_PATH = os.path.join(LOGS_DIR, "9jacashflow", "post.log")
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    log_file = open(LOG_FILE_PATH, 'a', encoding='utf-8')
    sys.stdout = Tee(sys.stdout, log_file)
    print("=" * 50 + f"\nSCRIPT STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" + "=" * 50)
    print("🚀 Running first digest immediately...")
    run_all()
    print(f"🚀 Bot scheduled. Will post daily digests at {POST_TIME} (Server Time).")
    schedule.every().day.at(POST_TIME).do(run_all)
    while True:
        schedule.run_pending()
        time.sleep(60)