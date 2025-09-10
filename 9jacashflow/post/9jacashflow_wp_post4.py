import feedparser
import requests
import schedule
import time
from datetime import datetime
import os
import sys
from dotenv import load_dotenv
import random

# Load environment variables from .env file
load_dotenv()

# --- Tee Class for Logging ---
# This class redirects print statements to both the console and a file
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

# --- WordPress API Configuration ---
WORDPRESS_URL = "https://9jacashflow.com/wp-json/wp/v2/posts"
# Safely load credentials from environment variables
WORDPRESS_API_USER = os.getenv("WORDPRESS_API_USER")
WORDPRESS_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD")

# --- Bot Settings ---
POST_TIME = "08:05"
MAX_ITEMS = 20
ALLOW_FEWER = False
HIGHLIGHT_LOCAL = True

# --- Tag ID Mapping ---
TAG_IDS = {
    "daily_digest": 776,
    "crypto_trading": 777,
    "forex_trading": 540,
    "stock_trading": 778,
    "real_estate": 422,
    "agriculture": 544,
    "online_business": 389,
}

# --- Category Configurations ---
CATEGORIES = {
    "crypto_trading": {
        "id": 305,
        "featured_media_id": 25124,
        "intro": "Welcome to today’s <strong>Crypto Trading</strong> roundup 🚀. Here are the top stories shaping the crypto markets today.",
        "cta": "That’s it for today’s crypto highlights! Which trade setup caught your attention? Share below 💬",
        "sources": [
            {"url": "https://cointelegraph.com/rss", "local": False},
            {"url": "https://www.coindesk.com/arc/outboundfeeds/rss", "local": False},
            {"url": "https://cryptoslate.com/feed", "local": False},
            {"url": "https://bitcoinmagazine.com/feed", "local": False},
            {"url": "https://nairametrics.com/category/cryptocurrency/feed", "local": True},
            {"url": "https://decrypt.co/feed", "local": False}
        ] 
    },
    "forex_trading": {
        "id": 539,
        "featured_media_id": 25005,
        "intro": "Here’s your <strong>Forex Trading</strong> daily digest 📊. Stay ahead of the FX market with today’s top news.",
        "cta": "That’s a wrap on forex news today 🌍. Drop a comment on which currency pair you’re watching!",
        "sources": [
            {"url": "https://www.forexlive.com/feed", "local": False},
            {"url": "https://www.dailyfx.com/feeds", "local": False},
            {"url": "https://www.investing.com/rss/news_1.rss", "local": False},
            {"url": "https://nairametrics.com/category/currency/feed", "local": True},
            {"url": "https://businessday.ng/category/banking/feed/", "local": True},
            {"url": "https://investinglive.com/feed/news", "local": False},
            {"url": "https://www.fxstreet.com/rss", "local": False},
            {"url": "https://investinglive.com/feed/centralbank", "local": False}
        ]
    },
    "stock_trading": {
        "id": 341,
        "featured_media_id": 25057,
        "intro": "Today’s <strong>Stock Market</strong> update 📈. Catch the top movers across Nigeria, Africa, and global equities.",
        "cta": "That’s it for today’s stock market roundup! Which market do you think will rally next? 🚀",
        "sources": [
            {"url": "https://www.bloomberg.com/feeds/podcasts/etf-report.xml", "local": False},
            {"url": "https://www.cnbc.com/id/10001147/device/rss/rss.xml", "local": False},
            {"url": "https://www.reuters.com/finance/markets/rss", "local": False},
            {"url": "https://nairametrics.com/category/stock-market/feed", "local": True},
            {"url": "https://businessday.ng/markets/feed", "local": True}
        ]
    },
    "real_estate": {
        "id": 309,
        "featured_media_id": 26216,
        "intro": "Welcome to today’s <strong>Real Estate</strong> roundup 🏠. Stay updated on property, housing, and infrastructure news.",
        "cta": "That’s the latest in real estate 🌍. Planning your next investment? Let’s talk in the comments 👇",
        "sources": [
            {"url": "https://businessday.ng/category/real-estate/feed/", "local": False},
            {"url": "https://kenmcelroy.com/feed/", "local": False},
            {"url": "https://www.stuartchng.com/blog-feed.xml", "local": False},
            {"url": "https://www.housingwire.com/feed", "local": False},
            {"url": "https://www.bisnow.com/rss", "local": False},
            {"url": "https://www.realtor.com/news/rss", "local": False},
            {"url": "https://nairametrics.com/category/real-estate/feed", "local": True},
            {"url": "https://businessday.ng/real-estate/feed", "local": True}
        ]
    },
    "agriculture": {
        "id": 303,
        "featured_media_id": 26210,
        "intro": "Your daily <strong>Agriculture & Agribusiness</strong> digest 🌱. From crops to livestock, here are today’s top updates.",
        "cta": "That’s it for agriculture today 🚜. What sector excites you most — crops, livestock, or exports? 💬",
        "sources": [
            {"url": "https://businessday.ng/category/agriculture/feed/", "local": False},
            {"url": "https://www.agriculturedive.com/feeds/news/", "local": False},
            {"url": "https://allafrica.com/tools/headlines/rdf/agriculture/headlines.rdf", "local": True},
            {"url": "https://www.agri-pulse.com/rss", "local": False},
            {"url": "https://nairametrics.com/category/agriculture/feed", "local": True},
            {"url": "https://guardian.ng/category/business-services/agriculture/feed", "local": True}
        ]
    },
    "online_business": {
        "id": 308,
        "featured_media_id": 26212,
        "intro": "Here’s today’s <strong>Online Business</strong> roundup 💻. From freelancing to e-commerce, these are the key updates.",
        "cta": "That’s all for online business today 🚀. Are you building a side hustle or scaling up? Share below!",
        "sources": [
            {"url": "https://www.entrepreneur.com/latest.rss", "local": False},
            {"url": "https://www.wired.com/feed/category/business/latest/rss", "local": False},
            {"url": "https://techcrunch.com/feed/", "local": False},
            {"url": "https://thenextweb.com/feed", "local": False},
            {"url": "https://www.businessinsider.com/rss", "local": True},
            {"url": "https://disruptafrica.com/feed", "local": False},
            {"url": "https://www.socialmediaexaminer.com/feed", "local": False},
            {"url": "https://www.contentmarketinginstitute.com/feed", "local": False},
            {"url": "https://technext24.com/feed", "local": True},
            {"url": "https://nairametrics.com/category/technology/feed", "local": True},
            {"url": "https://www.wired.com/feed/tag/ai/latest/rss", "local": False}
        ]
    }
}

# --- Fetch & Format News ---
def fetch_top_stories(sources, max_items=MAX_ITEMS):
    """
    Fetches stories with a two-pass approach to ensure source diversity.
    Also prepends a flag emoji for local sources.
    """
    stories = []
    used_links = set()
    all_articles_by_source = []

    shuffled_sources = list(sources)
    random.shuffle(shuffled_sources)

    # Pre-fetch articles and store them with their "local" status
    for src in shuffled_sources:
        try:
            feed = feedparser.parse(src["url"])
            if feed.entries:
                # Store a tuple: (list_of_entries, is_local_boolean)
                all_articles_by_source.append((feed.entries, src["local"]))
        except Exception as e:
            print(f"   -> Could not fetch from {src['url']}. Error: {e}")

    # Pass 1: Round-robin to get one story from each source
    for source_articles, is_local in all_articles_by_source:
        if len(stories) >= max_items:
            break
        for entry in source_articles:
            if entry.link not in used_links:
                # Add flag if the source is local
                flag = "🇳🇬 " if is_local else ""
                html_story = f'{flag}<a href="{entry.link}" target="_blank" rel="noopener noreferrer">{entry.title}</a>'
                stories.append(html_story)
                used_links.add(entry.link)
                break

    # Pass 2: Fill up the remaining slots
    if len(stories) < max_items:
        for source_articles, is_local in all_articles_by_source:
            if len(stories) >= max_items:
                break
            for entry in source_articles:
                if len(stories) >= max_items:
                    break
                if entry.link not in used_links:
                    # Add flag if the source is local
                    flag = "🇳🇬 " if is_local else ""
                    html_story = f'{flag}<a href="{entry.link}" target="_blank" rel="noopener noreferrer">{entry.title}</a>'
                    stories.append(html_story)
                    used_links.add(entry.link)

    print(f"   -> Fetched {len(stories)} unique stories for the digest.")
    return stories[:max_items]

# --- Post to WordPress ---
def post_to_wordpress(category_key, cfg):
    print(f"Fetching stories for {category_key}...")
    stories = fetch_top_stories(cfg["sources"])
    if not stories:
        print(f"⚠️ No stories found for {category_key}")
        return

    content_parts = [f"<p>{cfg['intro']}</p>"]
    list_items = "".join([f"<li>{story}</li>" for story in stories])
    content_parts.append(f"<ol>{list_items}</ol>")
    content_parts.append(f"<p>{cfg['cta']}</p>")
    content = "".join(content_parts)
    
    category_title = category_key.replace('_',' ').title()
    post_title = f"{category_title} Daily Digest – {datetime.now().strftime('%B %d, %Y')}"
    
    data = {
        "title": post_title,
        "content": content,
        "status": "publish",
        "categories": [cfg["id"]],
        "featured_media": cfg["featured_media_id"],
        "tags": [TAG_IDS["daily_digest"], TAG_IDS[category_key]]
    }

    print(f"Attempting to post: '{post_title}'")
    try:
        r = requests.post(
            WORDPRESS_URL,
            auth=(WORDPRESS_API_USER, WORDPRESS_APP_PASSWORD),
            json=data,
            timeout=30
        )

        if r.status_code == 201:
            post_url = r.json().get('link', 'N/A')
            print(f"✅ {category_key} digest posted successfully! URL: {post_url}")
        else:
            print(f"❌ Failed to post {category_key}. Status: {r.status_code}, Response: {r.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred while posting {category_key}: {e}")

# --- Master Run ---
def run_all():
    if not WORDPRESS_API_USER or not WORDPRESS_APP_PASSWORD:
        print("❌ CRITICAL ERROR: WordPress credentials are not set.")
        print("Please check your .env file and ensure WORDPRESS_API_USER and WORDPRESS_APP_PASSWORD are defined.")
        return

    print(f"\n--- Starting job run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    for key, cfg in CATEGORIES.items():
        post_to_wordpress(key, cfg)
    print("--- Job run finished. ---\n")

# --- Run Immediately + Schedule ---
if __name__ == "__main__":
    LOGS_DIR = "logs"
    LOG_FILE_PATH = os.path.join(LOGS_DIR, "9jacashflow", "post.log")
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    
    log_file = open(LOG_FILE_PATH, 'a', encoding='utf-8')
    original_stdout = sys.stdout
    sys.stdout = Tee(original_stdout, log_file)

    print("=========================================================")
    print(f"SCRIPT STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=========================================================")

    print("🚀 Running first digest immediately...")
    run_all()
    
    print(f"🚀 Bot scheduled. Will post daily digests at {POST_TIME} (Server Time).")
    schedule.every().day.at(POST_TIME).do(run_all)

    while True:
        schedule.run_pending()
        time.sleep(60)