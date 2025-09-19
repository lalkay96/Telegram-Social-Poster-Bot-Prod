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
FB_PAGE_ID = os.getenv("FB_PAGE_ID") # Added for Facebook
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN") # Added for Facebook


# Cloudinary configuration
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# Global instances (to avoid re-initialization)
twitter_v1_api = None
if all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET
    )
    logger.info("☁️ Cloudinary configured.")
else:
    logger.warning("⚠️ Cloudinary credentials not fully set. Image uploads to Cloudinary will be skipped for Instagram/Facebook posts.")

# --- Global variables for media group handling ---
media_group_messages = collections.defaultdict(list)
last_message_time = {}
MEDIA_GROUP_TIMEOUT = 2 # Seconds to wait for all messages in a group

# --- Twitter Posting Functions ---

async def refresh_twitter_token():
    """Refreshes the Twitter API v2 bearer token using the refresh token."""
    try:
        async with httpx.AsyncClient() as client:
            auth_header = base64.b64encode(f"{TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}".encode()).decode()
            response = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                headers={"Authorization": f"Basic {auth_header}"},
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": TWITTER_REFRESH_TOKEN,
                    "client_id": TWITTER_CLIENT_ID,
                }
            )
            response.raise_for_status()
            token_data = response.json()
            new_access_token = token_data["access_token"]
            new_refresh_token = token_data["refresh_token"]
            os.environ["TWITTER_ACCESS_TOKEN"] = new_access_token
            os.environ["TWITTER_REFRESH_TOKEN"] = new_refresh_token
            logger.warning("🔑 Twitter tokens refreshed! PLEASE UPDATE YOUR .ENV FILE:")
            logger.warning("TWITTER_ACCESS_TOKEN=%s", new_access_token)
            logger.warning("TWITTER_REFRESH_TOKEN=%s", new_refresh_token)
            return new_access_token
    except httpx.HTTPStatusError as e:
        logger.error("Failed to refresh Twitter token: %s - Response: %s", e.response.status_code, e.response.text)
        return None
    except Exception as e:
        logger.error("Unexpected error while refreshing Twitter token: %s", e)
        return None

async def post_to_twitter(caption: str, image_paths: list = None):
    """Posts a text tweet or an image tweet (up to 4) to Twitter."""
    global twitter_v1_api
    if not all([TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_REFRESH_TOKEN, TWITTER_API_KEY_V1,
                TWITTER_API_SECRET_V1, TWITTER_ACCESS_TOKEN_V1, TWITTER_ACCESS_TOKEN_SECRET_V1]):
        logger.error("❌ One or more Twitter API credentials are not set. Skipping Twitter post.")
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
            logger.info("🐦 Uploading %d image(s) to Twitter media endpoint using V1.1 API...", len(image_paths))
            
            auth_v1 = tweepy.OAuth1UserHandler(
                TWITTER_API_KEY_V1, TWITTER_API_SECRET_V1, TWITTER_ACCESS_TOKEN_V1, TWITTER_ACCESS_TOKEN_SECRET_V1
            )
            api_v1 = tweepy.API(auth_v1)
            
            for path in image_paths:
                media = await asyncio.to_thread(api_v1.media_upload, filename=path)
                media_ids.append(media.media_id_string)
            logger.info("✅ All images uploaded to Twitter media. Media IDs: %s", media_ids)
        elif image_paths and len(image_paths) > 4:
            logger.warning("Twitter only supports up to 4 images. Skipping Twitter post for this media group.")
            return

        tweet_response = await asyncio.to_thread(client_v2.create_tweet, text=caption, media_ids=media_ids)
        logger.info("✅ Successfully posted to Twitter! Tweet ID: %s", tweet_response.data['id'])

    except tweepy.HTTPException as e:
        if e.response.status_code == 401:
            logger.info("🔄 Twitter Access Token unauthorized. Attempting to refresh token...")
            new_access_token = await refresh_twitter_token()
            if new_access_token:
                await post_to_twitter(caption, image_paths)
            else:
                logger.error("❌ Failed to refresh Twitter token. Please regenerate tokens.")
        else:
            logger.error("❌ Twitter post failed: %s - Response: %s", e.response.status_code, e.response.text)
    except Exception as e:
        logger.error("Unexpected error while posting to Twitter: %s", e)

# --- Facebook Posting Function --- [NEWLY ADDED] ---

async def post_to_facebook_page(message: str, image_url: str = None):
    """Posts text or image to a Facebook Page."""
    if not all([FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN]):
        logger.error("❌ Facebook Page ID or Access Token not set.")
        return

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if image_url:
                url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
                response = await client.post(url, data={
                    "url": image_url,
                    "caption": message,
                    "access_token": FB_PAGE_ACCESS_TOKEN
                })
            else:
                url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
                response = await client.post(url, data={
                    "message": message,
                    "access_token": FB_PAGE_ACCESS_TOKEN
                })

            data = response.json()
            if "id" in data:
                logger.info("✅ Successfully posted to Facebook Page! Post ID: %s", data["id"])
            else:
                logger.error("❌ Failed to post to Facebook Page: %s", data)
    except Exception:
        logger.exception("Error posting to Facebook Page")

# --- Instagram Posting Functions ---

async def post_to_instagram_feed(image_urls: list, caption: str):
    """Posts a single image or a carousel of images with a caption to Instagram Feed."""
    if not all([IG_ACCOUNT_ID, IG_ACCESS_TOKEN]):
        logger.error("❌ Instagram Account ID or Access Token not set. Cannot post to Instagram Feed.")
        return

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if len(image_urls) == 1:
                # Post a single image
                container_url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media"
                container_response = await client.post(container_url, data={
                    "image_url": image_urls[0],
                    "caption": caption,
                    "access_token": IG_ACCESS_TOKEN
                })
                container_data = container_response.json()
                if 'id' in container_data:
                    creation_id = container_data['id']
                    publish_url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media_publish"
                    publish_response = await client.post(publish_url, data={
                        "creation_id": creation_id,
                        "access_token": IG_ACCESS_TOKEN
                    })
                    publish_data = publish_response.json()
                    if 'id' in publish_data:
                        logger.info("✅ Successfully posted single image to Instagram Feed! Post ID: %s", publish_data['id'])
                    else:
                        logger.error("❌ Instagram Feed publish failed for single image: %s", publish_data)
                else:
                    logger.error("❌ Failed to create IG Feed container for single image. Error: %s", container_data.get('error', 'Unknown error'))
                return

            # Post a carousel for multiple images
            child_ids = []
            for url in image_urls:
                container_url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media"
                container_response = await client.post(container_url, data={
                    "image_url": url,
                    "access_token": IG_ACCESS_TOKEN
                })
                container_data = container_response.json()
                if 'id' in container_data:
                    child_ids.append(container_data['id'])
                else:
                    logger.error("❌ Failed to create IG Feed media container for %s. Error: %s", url, container_data.get('error', 'Unknown error'))
                    return # Stop if a single image fails
            
            carousel_url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media"
            carousel_response = await client.post(carousel_url, data={
                "caption": caption,
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "access_token": IG_ACCESS_TOKEN
            })
            carousel_data = carousel_response.json()

            if 'id' in carousel_data:
                carousel_id = carousel_data['id']
                publish_url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media_publish"
                publish_response = await client.post(publish_url, data={
                    "creation_id": carousel_id,
                    "access_token": IG_ACCESS_TOKEN
                })
                publish_data = publish_response.json()
                if 'id' in publish_data:
                    logger.info("✅ Successfully posted carousel to Instagram Feed! Post ID: %s", publish_data['id'])
                else:
                    logger.error("❌ Instagram Feed carousel publish failed: %s", publish_data)
            else:
                logger.error("❌ Failed to create IG carousel container. Error: %s", carousel_data.get('error', 'Unknown error'))
    except httpx.HTTPStatusError as e:
        logger.exception("Instagram Feed HTTP error: %s - Response: %s", e.response.status_code, e.response.text)
    except Exception as e:
        logger.exception("An unexpected error occurred while posting to Instagram Feed:")


async def post_to_instagram_story(image_url: str):
    """Posts an image to Instagram Stories."""
    if not all([IG_ACCOUNT_ID, IG_ACCESS_TOKEN]):
        logger.error("❌ Instagram Account ID or Access Token not set. Cannot post to Instagram Story.")
        return
    try:
        container_url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media"
        publish_url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media_publish"
        async with httpx.AsyncClient(timeout=30.0) as client:
            container_response = await client.post(container_url, data={
                "image_url": image_url,
                "media_type": "STORIES",
                "access_token": IG_ACCESS_TOKEN
            })
            container_data = container_response.json()
            if 'id' in container_data:
                container_id = container_data['id']
                publish_response = await client.post(publish_url, data={
                    "creation_id": container_id,
                    "access_token": IG_ACCESS_TOKEN
                })
                publish_data = publish_response.json()
                if 'id' in publish_data:
                    logger.info("✅ Successfully posted to Instagram Story! Story ID: %s", publish_data['id'])
                else:
                    logger.error("❌ Instagram Story publish failed: %s", publish_data)
            else:
                logger.error("❌ Failed to create IG Story media container. Error: %s", container_data.get('error', 'Unknown error'))
    except httpx.HTTPStatusError as e:
        logger.exception("Instagram Story HTTP error: %s - Response: %s", e.response.status_code, e.response.text)
    except Exception as e:
        logger.exception("An unexpected error occurred while posting to Instagram Story:")
        
# --- Telegram Channel Posting ---

async def post_to_telegram_channel(image_paths: list, caption: str, bot_instance: telegram.Bot):
    """Posts an image or a group of images with a caption to a specified Telegram channel."""
    if not TELEGRAM_CHANNEL_ID:
        logger.error("❌ TELEGRAM_CHANNEL_ID is not set. Cannot post to Telegram channel.")
        return
    try:
        logger.info("✈️ Posting to Telegram channel %s...", TELEGRAM_CHANNEL_ID)
        
        if len(image_paths) > 1:
            media = [telegram.InputMediaPhoto(media=open(path, 'rb')) for path in image_paths]
            # Find the caption and assign it to the first media item
            media[0].caption = caption
            await bot_instance.send_media_group(chat_id=TELEGRAM_CHANNEL_ID, media=media)
            logger.info("✅ Successfully posted media group to Telegram channel!")
        elif image_paths:
            with open(image_paths[0], 'rb') as photo_file:
                await bot_instance.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=photo_file, caption=caption)
            logger.info("✅ Successfully posted single photo to Telegram channel!")

    except Exception as e:
        logger.exception("❌ Error posting to Telegram channel:")

async def post_text_to_telegram_channel(text: str, bot_instance: telegram.Bot):
    """Posts a text message to a specified Telegram channel."""
    if not TELEGRAM_CHANNEL_ID:
        logger.error("❌ TELEGRAM_CHANNEL_ID is not set. Skipping text post to Telegram channel.")
        return
    try:
        logger.info("✈️ Posting text to Telegram channel %s...", TELEGRAM_CHANNEL_ID)
        await bot_instance.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=text)
        logger.info("✅ Successfully posted text to Telegram channel!")
    except Exception as e:
        logger.exception("❌ Error posting text to Telegram channel:")

# --- Helper Functions ---
async def upload_image_to_cloudinary(image_path):
    if CLOUDINARY_CLOUD_NAME:
        try:
            result = await asyncio.to_thread(cloudinary.uploader.upload, image_path)
            cloudinary_image_url = result['secure_url']
            logger.info("☁️ Uploaded to Cloudinary: %s", cloudinary_image_url)
            return cloudinary_image_url
        except Exception as e:
            logger.exception("❌ Failed to upload image to Cloudinary.")
    return None

def check_image_aspect_ratio(image_path):
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            aspect_ratio = width / height
            is_feed_compatible = (0.8 <= aspect_ratio <= 1.91)
            logger.info("Image dimensions: %dx%d, Aspect Ratio: %.2f. Feed compatible: %s", width, height, aspect_ratio, is_feed_compatible)
            return is_feed_compatible
    except Exception as e:
        logger.exception("Error checking image aspect ratio. Assuming not feed compatible.")
        return False

async def process_media_group(messages, bot_instance, caption):
    """Downloads all images from a media group, and posts them to all platforms."""
    local_image_paths = []
    cloudinary_urls = []

    # Ensure messages are sorted by message_id to maintain order
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
        # --- [MODIFICATION POINT 1] ---
        # Added Facebook posting for media groups
        posting_tasks.append(post_to_facebook_page(caption, cloudinary_urls[0]))

        if all(check_image_aspect_ratio(path) for path in local_image_paths):
            posting_tasks.append(post_to_instagram_feed(cloudinary_urls, caption))
        else:
            logger.info("At least one image in media group is not compatible with Instagram Feed. Skipping.")
        
        # Optionally, post the first image to story
        # posting_tasks.append(post_to_instagram_story(cloudinary_urls[0]))

    if posting_tasks:
        await asyncio.gather(*posting_tasks)
        # Reply to the first message in the group
        await sorted_messages[0].reply_text("✅ Your media group post has been sent to all configured social media platforms!")

    # Clean up temporary files
    for path in local_image_paths:
        if os.path.exists(path):
            os.remove(path)
            logger.info("🗑️ Cleaned up temporary file: %s", path)

# --- Telegram Bot Message Handler ---
async def handle_telegram_message(update: telegram.Update, bot_instance: telegram.Bot):
    """Handles incoming messages from Telegram and distributes to all social media platforms."""
    image_path = None
    try:
        if not update.message:
            logger.warning("Received update without a message object.")
            return

        message = update.message
        
        # --- THIS IS THE KEY FIX ---
        # If the message is part of a media group, just add it to our list and return.
        # The main loop will handle the processing after a timeout.
        if message.media_group_id:
            media_group_id = message.media_group_id
            media_group_messages[media_group_id].append(message)
            last_message_time[media_group_id] = time.time()
            # We return here to stop further processing for this single message
            return

        # The rest of the function now only handles SINGLE image or TEXT messages
        caption = message.caption or message.text or "No caption"
        posting_tasks = []
        
        if message.photo: # This will now only trigger for single photos
            file_id = message.photo[-1].file_id
            file_obj = await bot_instance.get_file(file_id)
            image_path = os.path.join(os.getcwd(), f"temp_{file_id}.jpg")
            await file_obj.download_to_drive(image_path)
            logger.info("📥 Single photo downloaded to %s", image_path)

            cloudinary_image_url = await upload_image_to_cloudinary(image_path)
            
            is_feed_compatible = check_image_aspect_ratio(image_path)
            
            posting_tasks.append(post_to_twitter(caption, [image_path]))
            posting_tasks.append(post_to_telegram_channel([image_path], caption, bot_instance))

            if cloudinary_image_url:
                # --- [MODIFICATION POINT 2] ---
                # Added Facebook posting for single images
                posting_tasks.append(post_to_facebook_page(caption, cloudinary_image_url))

                if is_feed_compatible:
                    # For a single image, post to feed instead of carousel
                    posting_tasks.append(post_to_instagram_feed([cloudinary_image_url], caption))
                else:
                    logger.info("Image not compatible with Instagram Feed. Skipping.")
                posting_tasks.append(post_to_instagram_story(cloudinary_image_url))

        elif message.text: # This handles text-only messages
            posting_tasks.append(post_to_twitter(message.text))
            posting_tasks.append(post_text_to_telegram_channel(message.text, bot_instance))
            # Also post text-only to Facebook
            posting_tasks.append(post_to_facebook_page(message.text))
            logger.info("Skipping Instagram posts for text-only message.")

        if posting_tasks:
            await asyncio.gather(*posting_tasks)
            await message.reply_text("✅ Your post has been sent to all configured social media platforms!")

    except Exception as e:
        logger.exception("Error handling Telegram message:")
        if update.message:
            await update.message.reply_text("❌ Failed to process your request. Please check logs for details.")
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
            logger.info("🗑️ Cleaned up temporary file: %s", image_path)

# --- Main Bot Function ---
async def main():
    """Initializes and runs the Telegram bot to handle messages and post to social media."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN is not set. Exiting.")
        return

    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        bot_info = await bot.get_me()
        logger.info("🚀 Telegram Bot is running as @%s.", bot_info.username)
        await bot.delete_webhook()
        logger.info("Webhook deleted to ensure polling mode.")
    except telegram.error.InvalidToken:
        logger.error("❌ Invalid Telegram Bot Token. Please check your .env file.")
        return
    except Exception as e:
        logger.error("❌ Error during bot initialization: %s", e)
        return

    update_id = 0
    while True:
        try:
            updates = await bot.get_updates(offset=update_id, timeout=10)
            for update in updates:
                if update.update_id >= update_id:
                    update_id = update.update_id + 1
                    await handle_telegram_message(update, bot)
            
            # This handles any media groups that have timed out
            for group_id in list(media_group_messages.keys()):
                if time.time() - last_message_time.get(group_id, 0) >= MEDIA_GROUP_TIMEOUT:
                    messages_to_post = media_group_messages.pop(group_id)
                    last_message_time.pop(group_id, None)
                    # Find the first message with a caption to use for all posts
                    caption = next((msg.caption for msg in messages_to_post if msg.caption), "No caption")
                    await process_media_group(messages_to_post, bot, caption)

            await asyncio.sleep(1)
        except telegram.error.TimedOut:
            pass
        except telegram.error.NetworkError as e:
            logger.error("Telegram Network Error: %s. Retrying in 5 seconds...", e)
            await asyncio.sleep(5)
        except Exception as e:
            logger.error("Error in main loop: %s. Retrying in 5 seconds...", e)
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.exception("An unhandled error occurred in the main execution:")