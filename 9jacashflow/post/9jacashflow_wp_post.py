import feedparser
import requests
import schedule
import time
from datetime import datetime
import os
import sys
from dotenv import load_dotenv

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
MAX_ITEMS = 10
ALLOW_FEWER = False      # toggle fewer posts (True = allow less than 10, False = always 10)
HIGHLIGHT_LOCAL = True   # toggle highlighting local sources

# --- Category Configurations ---
CATEGORIES = {
    "crypto_trading": {
        "id": 305,
        "featured_media_id": 25124,
        "intro": "Welcome to today’s **Crypto Trading** roundup 🚀. Here are the top stories shaping the crypto markets today.",
        "cta": "That’s it for today’s crypto highlights! Which trade setup caught your attention? Share below 💬",
        "sources": [
            {"url": "https://cointelegraph.com/rss", "local": False},
            {"url": "https://cryptoslate.com/feed", "local": False},
            {"url": "https://bitcoinmagazine.com/feed", "local": False},
            {"url": "https://nairametrics.com/category/cryptocurrency/feed", "local": True},
            {"url": "https://technext24.com/feed", "local": True}
        ]
    },
    "forex_trading": {
        "id": 539,
        "featured_media_id": 25005,
        "intro": "Here’s your **Forex Trading** daily digest 📊. Stay ahead of the FX market with today’s top news.",
        "cta": "That’s a wrap on forex news today 🌍. Drop a comment on which currency pair you’re watching!",
        "sources": [
            {"url": "https://www.forexlive.com/feed", "local": False},
            {"url": "https://www.dailyfx.com/feeds", "local": False},
            {"url": "https://www.investing.com/rss/news_1.rss", "local": False},
            {"url": "https://nairametrics.com/category/currency/feed", "local": True},
            {"url": "https://businessday.ng/feed", "local": True}
        ]
    },
    "stock_trading": {
        "id": 341,
        "featured_media_id": 25057,
        "intro": "Today’s **Stock Market** update 📈. Catch the top movers across Nigeria, Africa, and global equities.",
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
        "intro": "Welcome to today’s **Real Estate** roundup 🏠. Stay updated on property, housing, and infrastructure news.",
        "cta": "That’s the latest in real estate 🌍. Planning your next investment? Let’s talk in the comments 👇",
        "sources": [
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
        "intro": "Your daily **Agriculture & Agribusiness** digest 🌱. From crops to livestock, here are today’s top updates.",
        "cta": "That’s it for agriculture today 🚜. What sector excites you most — crops, livestock, or exports? 💬",
        "sources": [
            {"url": "https://www.agriculture.com/rss", "local": False},
            {"url": "https://www.farmafrica.org/latest/news/rss", "local": False},
            {"url": "https://www.thecattlesite.com/rss/news/", "local": False},
            {"url": "https://nairametrics.com/category/agriculture/feed", "local": True},
            {"url": "https://guardian.ng/category/business-services/agriculture/feed", "local": True}
        ]
    },
    "online_business": {
        "id": 308,
        "featured_media_id": 26212,
        "intro": "Here’s today’s **Online Business** roundup 💻. From freelancing to e-commerce, these are the key updates.",
        "cta": "That’s all for online business today 🚀. Are you building a side hustle or scaling up? Share below!",
        "sources": [
            {"url": "https://www.entrepreneur.com/latest.rss", "local": False},
            {"url": "https://www.socialmediaexaminer.com/feed", "local": False},
            {"url": "https://www.contentmarketinginstitute.com/feed", "local": False},
            {"url": "https://technext24.com/feed", "local": True},
            {"url": "https://nairametrics.com/category/technology/feed", "local": True}
        ]
    }
}

# --- Fetch & Format News ---
def fetch_top_stories(sources, max_items=MAX_ITEMS):
    stories = []
    used_links = set() # Use links to avoid duplicate stories

    # Simplified fetching logic
    for src in sources:
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries:
                if len(stories) >= max_items:
                    break
                if entry.link not in used_links:
                    summary = getattr(entry, "summary", "")[:200]
                    label = " 🇳🇬" if HIGHLIGHT_LOCAL and src["local"] else ""
                    stories.append(f"**[{entry.title}]({entry.link})**{label}\n📌 {summary}...")
                    used_links.add(entry.link)
        except Exception as e:
            print(f"Could not fetch from {src['url']}. Error: {e}")
        if len(stories) >= max_items:
            break

    return stories[:max_items]

# --- Post to WordPress ---
def post_to_wordpress(category_key, cfg):
    print(f"Fetching stories for {category_key}...")
    stories = fetch_top_stories(cfg["sources"])
    if not stories:
        print(f"⚠️ No stories found for {category_key}")
        return

    content = (
        f"{cfg['intro']}\n\n" +
        "\n\n".join([f"{i+1}. {story}" for i, story in enumerate(stories)]) +
        f"\n\n{cfg['cta']}"
    )
    
    post_title = f"Top {len(stories)} {category_key.replace('_',' ').title()} News - {datetime.now().strftime('%B %d, %Y')}"
    
    data = {
        "title": post_title,
        "content": content,
        "status": "publish",
        "categories": [cfg["id"]],
        "featured_media": cfg["featured_media_id"],
        "tags": ["daily-digest", category_key]
    }

    print(f"Attempting to post: '{post_title}'")
    try:
        r = requests.post(
            WORDPRESS_URL,
            auth=(WORDPRESS_API_USER, WORDPRESS_APP_PASSWORD),
            json=data,
            timeout=30 # Add a timeout
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
    # --- Pre-run check for credentials ---
    if not WORDPRESS_API_USER or not WORDPRESS_APP_PASSWORD:
        print("❌ CRITICAL ERROR: WordPress API credentials are not set.")
        print("Please check your .env file and ensure WORDPRESS_API_USER and WORDPRESS_APP_PASSWORD are defined.")
        return # Stop execution if credentials are not found

    print(f"\n--- Starting job run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    for key, cfg in CATEGORIES.items():
        post_to_wordpress(key, cfg)
    print("--- Job run finished. ---\n")

# --- Run Immediately + Schedule ---
if __name__ == "__main__":
    # --- Logging Setup ---
    LOGS_DIR = "logs"
    LOG_FILE_PATH = os.path.join(LOGS_DIR, "9jacashflow", "post.log")
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    
    log_file = open(LOG_FILE_PATH, 'a', encoding='utf-8')
    original_stdout = sys.stdout
    sys.stdout = Tee(original_stdout, log_file)

    # --- Script Execution ---
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
