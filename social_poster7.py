import os
import asyncio
import logging
import base64
import time
from dotenv import load_dotenv
import httpx
import tweepy
import telegram
from PIL import Image
import cloudinary
import cloudinary.uploader
import collections

# --- Global Configuration from Environment Variables ---
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add this line to silence httpx's INFO logs
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Twitter (V2 for posting, V1.1 for media upload)
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_REFRESH_TOKEN = os.getenv("TWITTER_REFRESH_TOKEN")
TWITTER_API_KEY_V1 = os.getenv("TWITTER_API_KEY_V1")
TWITTER_API_SECRET_V1 = os.getenv("TWITTER_API_SECRET_V1")
TWITTER_ACCESS_TOKEN_V1 = os.getenv("TWITTER_ACCESS_TOKEN_V1")
TWITTER_ACCESS_TOKEN_SECRET_V1 = os.getenv("TWITTER_ACCESS_TOKEN_SECRET_V1")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Instagram (and Facebook Page)
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_PAGE_ID = os.getenv("IG_PAGE_ID")
IG_ACCOUNT_ID = os.getenv("IG_ACCOUNT_ID")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")

# Cloudinary configuration
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# Global instances (to avoid re-initialization)
if all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET
    )
    logger.info("☁️ Cloudinary configured.")
else:
    logger.warning("⚠️ Cloudinary credentials not fully set. Image uploads will be skipped for Instagram/Facebook.")

# --- Global variables for media group handling ---
media_group_messages = collections.defaultdict(list)
last_message_time = {}
MEDIA_GROUP_TIMEOUT = 2 # Seconds to wait for all messages in a group

# --- Twitter Posting Functions ---

async def post_to_twitter(caption: str, image_paths: list = None):
    """Posts a text tweet or an image tweet (up to 4) to Twitter."""
    if not all([TWITTER_API_KEY_V1, TWITTER_API_SECRET_V1, TWITTER_ACCESS_TOKEN_V1, TWITTER_ACCESS_TOKEN_SECRET_V1]):
        logger.error("❌ Twitter API v1.1 credentials are not set. Skipping Twitter post.")
        return

    try:
        client_v2 = tweepy.Client(
            consumer_key=TWITTER_API_KEY_V1,
            consumer_secret=TWITTER_API_SECRET_V1,
            access_token=TWITTER_ACCESS_TOKEN_V1,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET_V1
        )

        media_ids = []
        if image_paths and len(image_paths) <= 4:
            logger.info("🐦 Uploading %d image(s) to Twitter...", len(image_paths))
            auth_v1 = tweepy.OAuth1UserHandler(
                TWITTER_API_KEY_V1, TWITTER_API_SECRET_V1, TWITTER_ACCESS_TOKEN_V1, TWITTER_ACCESS_TOKEN_SECRET_V1
            )
            api_v1 = tweepy.API(auth_v1)
            for path in image_paths:
                media = await asyncio.to_thread(api_v1.media_upload, filename=path)
                media_ids.append(media.media_id_string)
            logger.info("✅ Twitter media uploaded. Media IDs: %s", media_ids)
        elif image_paths and len(image_paths) > 4:
            logger.warning("Twitter only supports up to 4 images. Skipping Twitter post.")
            return

        await asyncio.to_thread(client_v2.create_tweet, text=caption, media_ids=media_ids)
        logger.info("✅ Successfully posted to Twitter!")
    except Exception as e:
        logger.exception("❌ Error posting to Twitter:")

# --- Facebook Posting Functions ---

async def post_to_facebook_page(message: str, image_url: str = None):
    """Posts text or a single image to a Facebook Page."""
    if not all([FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN]):
        logger.error("❌ Facebook Page ID or Access Token not set.")
        return

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if image_url:
                url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
                response = await client.post(url, data={"url": image_url, "caption": message, "access_token": FB_PAGE_ACCESS_TOKEN})
            else:
                url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
                response = await client.post(url, data={"message": message, "access_token": FB_PAGE_ACCESS_TOKEN})

            data = response.json()
            if "id" in data:
                logger.info("✅ Successfully posted to Facebook Page! Post ID: %s", data["id"])
            else:
                logger.error("❌ Failed to post to Facebook Page: %s", data)
    except Exception:
        logger.exception("Error posting to Facebook Page")

async def post_album_to_facebook_page(caption: str, image_urls: list):
    """Uploads multiple images as a single album post to a Facebook Page."""
    if not all([FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN]):
        logger.error("❌ Facebook Page ID or Access Token not set.")
        return
    if not image_urls:
        return

    media_ids = []
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info("Uploading %d photos to Facebook for album post...", len(image_urls))
            # Step 1: Upload each photo with 'published=false' to get its ID
            for url in image_urls:
                upload_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
                response = await client.post(upload_url, data={"url": url, "published": "false", "access_token": FB_PAGE_ACCESS_TOKEN})
                data = response.json()
                if "id" in data:
                    media_ids.append(data["id"])
                else:
                    logger.error("❌ Failed to upload a photo for the Facebook album: %s", data)
                    return

            if not media_ids:
                logger.error("❌ No photos were successfully uploaded for Facebook album.")
                return

            logger.info("✅ All photos uploaded to Facebook. Creating feed post...")
            # Step 2: Create the feed post with all the uploaded photo IDs
            feed_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
            attached_media = [{"media_fbid": media_id} for media_id in media_ids]
            response = await client.post(feed_url, data={"message": caption, "attached_media": str(attached_media).replace("'", '"'), "access_token": FB_PAGE_ACCESS_TOKEN})
            
            data = response.json()
            if "id" in data:
                logger.info("✅ Successfully posted album to Facebook Page! Post ID: %s", data["id"])
            else:
                logger.error("❌ Failed to post album to Facebook Page: %s", data)
    except Exception:
        logger.exception("Error posting album to Facebook Page")

# --- Instagram Posting Functions ---

async def post_to_instagram_feed(image_urls: list, caption: str):
    """Posts a single image or a carousel to Instagram Feed."""
    if not all([IG_ACCOUNT_ID, IG_ACCESS_TOKEN]):
        logger.error("❌ Instagram credentials not set.")
        return

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if len(image_urls) == 1:
                # Post a single image
                container_url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media"
                container_response = await client.post(container_url, data={"image_url": image_urls[0], "caption": caption, "access_token": IG_ACCESS_TOKEN})
                container_data = container_response.json()
                if 'id' in container_data:
                    creation_id = container_data['id']
                    publish_url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media_publish"
                    publish_response = await client.post(publish_url, data={"creation_id": creation_id, "access_token": IG_ACCESS_TOKEN})
                    publish_data = publish_response.json()
                    if 'id' in publish_data:
                        logger.info("✅ Successfully posted single image to Instagram! Post ID: %s", publish_data['id'])
                    else:
                        logger.error("❌ Instagram single image publish failed: %s", publish_data)
                else:
                    logger.error("❌ Failed to create Instagram container for single image: %s", container_data.get('error', 'Unknown'))
                return

            # Post a carousel for multiple images
            child_ids = []
            logger.info("Uploading %d images for Instagram carousel...", len(image_urls))
            for url in image_urls:
                container_url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media"
                container_response = await client.post(container_url, data={"image_url": url, "access_token": IG_ACCESS_TOKEN})
                container_data = container_response.json()
                if 'id' in container_data:
                    child_ids.append(container_data['id'])
                else:
                    logger.error("❌ Failed to create Instagram media container for %s. Error: %s", url, container_data.get('error', 'Unknown'))
                    return
            
            carousel_url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media"
            carousel_response = await client.post(carousel_url, data={"caption": caption, "media_type": "CAROUSEL", "children": ",".join(child_ids), "access_token": IG_ACCESS_TOKEN})
            carousel_data = carousel_response.json()

            if 'id' in carousel_data:
                carousel_id = carousel_data['id']
                publish_url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media_publish"
                publish_response = await client.post(publish_url, data={"creation_id": carousel_id, "access_token": IG_ACCESS_TOKEN})
                publish_data = publish_response.json()
                if 'id' in publish_data:
                    logger.info("✅ Successfully posted carousel to Instagram! Post ID: %s", publish_data['id'])
                else:
                    logger.error("❌ Instagram carousel publish failed: %s", publish_data)
            else:
                logger.error("❌ Failed to create Instagram carousel container: %s", carousel_data.get('error', 'Unknown'))
    except Exception:
        logger.exception("Error posting to Instagram Feed:")

# --- Helper & Telegram Functions (No Changes Below This Line) ---

async def post_to_telegram_channel(image_paths: list, caption: str, bot_instance: telegram.Bot):
    """Posts one or more images to the configured Telegram channel."""
    if not TELEGRAM_CHANNEL_ID:
        logger.error("❌ TELEGRAM_CHANNEL_ID is not set.")
        return
    try:
        if len(image_paths) > 1:
            # Correctly create the media list, adding the caption only to the first item
            media = [
                telegram.InputMediaPhoto(media=open(path, 'rb'), caption=caption if i == 0 else None)
                for i, path in enumerate(image_paths)
            ]
            await bot_instance.send_media_group(chat_id=TELEGRAM_CHANNEL_ID, media=media)
        elif image_paths:
            # This part for single images is already correct
            with open(image_paths[0], 'rb') as photo_file:
                await bot_instance.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=photo_file, caption=caption)
    except Exception:
        logger.exception("❌ Error posting to Telegram channel:")

async def post_text_to_telegram_channel(text: str, bot_instance: telegram.Bot):
    if not TELEGRAM_CHANNEL_ID:
        logger.error("❌ TELEGRAM_CHANNEL_ID is not set.")
        return
    try:
        await bot_instance.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=text)
    except Exception:
        logger.exception("❌ Error posting text to Telegram channel:")

async def upload_image_to_cloudinary(image_path):
    if CLOUDINARY_CLOUD_NAME:
        try:
            result = await asyncio.to_thread(cloudinary.uploader.upload, image_path)
            return result.get('secure_url')
        except Exception:
            logger.exception("❌ Failed to upload image to Cloudinary.")
    return None

def check_image_aspect_ratio(image_path):
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            aspect_ratio = width / height
            return 0.8 <= aspect_ratio <= 1.91
    except Exception:
        logger.exception("Error checking image aspect ratio.")
        return False

async def process_media_group(messages, bot_instance, caption):
    local_image_paths, cloudinary_urls = [], []
    sorted_messages = sorted(messages, key=lambda m: m.message_id)

    for msg in sorted_messages:
        if msg.photo:
            file_id = msg.photo[-1].file_id
            file_obj = await bot_instance.get_file(file_id)
            image_path = os.path.join(os.getcwd(), f"temp_{file_id}.jpg")
            await file_obj.download_to_drive(image_path)
            local_image_paths.append(image_path)
            
            cloudinary_url = await upload_image_to_cloudinary(image_path)
            if cloudinary_url:
                cloudinary_urls.append(cloudinary_url)
    
    posting_tasks = []
    if local_image_paths:
        posting_tasks.append(post_to_twitter(caption, local_image_paths))
        posting_tasks.append(post_to_telegram_channel(local_image_paths, caption, bot_instance))

    if cloudinary_urls:
        # Conditional logic for Facebook single vs. album post
        if len(cloudinary_urls) > 1:
            posting_tasks.append(post_album_to_facebook_page(caption, cloudinary_urls))
        else:
            posting_tasks.append(post_to_facebook_page(caption, cloudinary_urls[0]))

        if all(check_image_aspect_ratio(path) for path in local_image_paths):
            posting_tasks.append(post_to_instagram_feed(cloudinary_urls, caption))
        else:
            logger.info("One or more images not compatible with Instagram Feed ratio. Skipping IG post.")

    if posting_tasks:
        await asyncio.gather(*posting_tasks)
        await sorted_messages[0].reply_text("✅ Post sent to all configured social media platforms!")

    for path in local_image_paths:
        if os.path.exists(path):
            os.remove(path)

async def handle_telegram_message(update: telegram.Update, bot_instance: telegram.Bot):
    image_path = None
    try:
        if not update.message: return
        message = update.message
        
        if message.media_group_id:
            media_group_messages[message.media_group_id].append(message)
            last_message_time[message.media_group_id] = time.time()
            return

        caption = message.caption or message.text or ""
        posting_tasks = []
        
        if message.photo:
            file_id = message.photo[-1].file_id
            file_obj = await bot_instance.get_file(file_id)
            image_path = os.path.join(os.getcwd(), f"temp_{file_id}.jpg")
            await file_obj.download_to_drive(image_path)

            cloudinary_image_url = await upload_image_to_cloudinary(image_path)
            
            posting_tasks.append(post_to_twitter(caption, [image_path]))
            posting_tasks.append(post_to_telegram_channel([image_path], caption, bot_instance))

            if cloudinary_image_url:
                posting_tasks.append(post_to_facebook_page(caption, cloudinary_image_url))
                if check_image_aspect_ratio(image_path):
                    posting_tasks.append(post_to_instagram_feed([cloudinary_image_url], caption))

        elif message.text:
            posting_tasks.append(post_to_twitter(message.text))
            posting_tasks.append(post_text_to_telegram_channel(message.text, bot_instance))
            posting_tasks.append(post_to_facebook_page(message.text))

        if posting_tasks:
            await asyncio.gather(*posting_tasks)
            await message.reply_text("✅ Post sent to all configured social media platforms!")

    except Exception:
        logger.exception("Error handling Telegram message:")
        if update.message:
            await update.message.reply_text("❌ Failed to process your request.")
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)

async def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN is not set. Exiting.")
        return

    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    logger.info("🚀 Telegram Bot is running...")
    await bot.delete_webhook()
    update_id = 0

    while True:
        try:
            updates = await bot.get_updates(offset=update_id, timeout=10)
            for update in updates:
                update_id = update.update_id + 1
                await handle_telegram_message(update, bot)
            
            for group_id in list(media_group_messages.keys()):
                if time.time() - last_message_time.get(group_id, 0) >= MEDIA_GROUP_TIMEOUT:
                    messages_to_post = media_group_messages.pop(group_id)
                    last_message_time.pop(group_id, None)
                    caption = next((msg.caption for msg in messages_to_post if msg.caption), "")
                    await process_media_group(messages_to_post, bot, caption)

            await asyncio.sleep(1)
        except telegram.error.NetworkError as e:
            logger.error("Telegram Network Error: %s. Retrying in 5s...", e)
            await asyncio.sleep(5)
        except Exception:
            logger.exception("Error in main loop. Retrying in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")