import os
import asyncio
from pyrogram import Client
from tiktok_uploader.upload import upload_video

COOKIES_FILE = "cookies.txt"

async def process_next_clip():
    api_id = os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")
    bot_token = os.environ.get("BOT_TOKEN")
    channel_id = os.environ.get("CHANNEL_ID")
    
    app = Client("temp_downloader", api_id=api_id, api_hash=api_hash, bot_token=bot_token, in_memory=True)
    await app.start()
    
    chat_id = int(channel_id)
    
    messages = []
    async for msg in app.get_chat_history(chat_id):
        if msg.video:
            messages.append(msg)
            
    if not messages:
        print("No clips left in the channel to upload.")
        await app.stop()
        return
        
    oldest_message = messages[-1]
    
    print(f"Downloading clip {oldest_message.id}...")
    file_path = await app.download_media(oldest_message)
    
    caption = oldest_message.caption if oldest_message.caption else "Movie Clip"
    description = f"{caption} #movie #foryou #clips"
    
    print(f"Uploading to TikTok: {description}")
    try:
        upload_video(file_path, description=description, cookies=COOKIES_FILE)
        print("Upload successful! Deleting message from Telegram...")
        await oldest_message.delete()
    except Exception as e:
        print(f"Failed to upload: {e}")
        
    if os.path.exists(file_path):
        os.remove(file_path)
        
    await app.stop()

if __name__ == "__main__":
    if not os.path.exists(COOKIES_FILE):
        print("Cookies file not found! Upload aborted.")
    else:
        asyncio.run(process_next_clip())
