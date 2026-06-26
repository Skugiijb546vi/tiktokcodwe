import os
import asyncio
import time
import random
from pyrogram import Client
from pyrogram.raw.functions.channels import GetChannels
from pyrogram.raw.types import InputChannel
from tiktok_uploader.upload import upload_video

COOKIES_FILE = "cookies.txt"

async def resolve_channel(app, channel_id):
    cid = abs(int(channel_id))
    if cid > 1000000000000:
        cid = int(str(cid)[3:])
    try:
        await app.invoke(GetChannels(id=[InputChannel(channel_id=cid, access_hash=0)]))
    except Exception as e:
        pass

async def process_next_clip():
    api_id = os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")
    bot_token = os.environ.get("BOT_TOKEN")
    channel_id = os.environ.get("CHANNEL_ID")
    
    app = Client("temp_downloader", api_id=api_id, api_hash=api_hash, bot_token=bot_token, in_memory=True)
    await app.start()
    
    chat_id = int(channel_id)
    await resolve_channel(app, channel_id)
    
    messages = []
    async for msg in app.get_chat_history(chat_id):
        if msg.video:
            messages.append(msg)
            
    if not messages:
        print("No clips left.")
        await app.stop()
        return
        
    oldest_message = messages[-1]
    file_path = await app.download_media(oldest_message)
    
    caption = oldest_message.caption if oldest_message.caption else "Movie Clip"
    description = f"{caption} #movie #foryou #clips"
    
    # RANDOM DELAY FOR TIKTOK SAFETY
    delay = random.randint(10, 180)
    print(f"Waiting {delay} seconds before uploading to mimic human behavior...")
    time.sleep(delay)
    
    try:
        upload_video(file_path, description=description, cookies=COOKIES_FILE)
        await oldest_message.delete()
    except Exception as e:
        print(f"Failed: {e}")
        
    if os.path.exists(file_path):
        os.remove(file_path)
        
    await app.stop()

if __name__ == "__main__":
    if os.path.exists(COOKIES_FILE):
        asyncio.run(process_next_clip())