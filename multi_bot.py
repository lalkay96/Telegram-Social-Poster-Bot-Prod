import subprocess
import time
import os

# === List of all Python bot files to run ===
BOTS = [
    "social_poster2.py",
    "9jacashflow_wp_post5.py",
    "BinanceTrendBot/trend_bot4.py",
]

# Twitter Poster
BOTS1 = [
    "social_poster_twitter.py",
]

# Instagram & Telegram Poster
BOTS2 = [
    "social_poster_tg_ig_fb.py",
]

# Twitter, Instagram, Telegram
BOT3 = [
    "social_poster3_multi_images.py",
    "BinanceTrendBot/trend_bot.py",
]

# Social Poster, 9CF Post Aggregate, Binance Trend Bot, 9CF Trend Scanner
BOTS4 = [
    "social_poster2.py",
    "9jacashflow_wp_post5.py",
    "BinanceTrendBot/trend_bot4.py",
    "9jacashflow/scanner/trend_ema.py",
]


# Social Poster, 9CF Post Aggregate, Binance Trend Bot, 9CF Trend Scanner
BOTS5 = [
    "social_poster7.py",
    "SocialPoster/coinoyo.py",
    "SocialPoster/filtang.py",
    "9jacashflow/post/9jacashflow_wp_post10.py",
    "BinanceTrendBot/trend_bot6.py",
    "9jacashflow/scanner/trend_ema.py",
]


# === Launch each bot in a separate subprocess with a 1-minute interval ===
processes = []
for bot in BOTS5:
    if os.path.exists(bot):
        print(f"🚀 Starting {bot}...")
        p = subprocess.Popen(["python", bot])
        processes.append(p)
        print("Waiting for 1 minute before starting the next bot...")
        time.sleep(60)  # Wait for 60 seconds (1 minute)
    else:
        print(f"❌ File not found: {bot}")

# === Keep main script alive while subprocesses run ===
try:
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    print("\n🛑 Shutting down all bots...")
    for p in processes:
        p.terminate()