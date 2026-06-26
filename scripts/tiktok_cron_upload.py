import os
import asyncio
import time
import random
import json
import base64
import urllib.request
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

def get_queue_from_github():
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "Skugiijb546vi/tiktokcodwe")
    if not token:
        return [], None
    url = f"https://api.github.com/repos/{repo}/contents/queue.json"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    try:
        res = urllib.request.urlopen(req)
        data = json.loads(res.read())
        sha = data.get("sha")
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), sha
    except Exception as e:
        print("Failed to get queue.json", e)
        return [], None

def save_queue_to_github(queue, sha):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "Skugiijb546vi/tiktokcodwe")
    if not token:
        return
    url = f"https://api.github.com/repos/{repo}/contents/queue.json"
    put_data = {
        "message": "Update TikTok upload queue",
        "content": base64.b64encode(json.dumps(queue).encode("utf-8")).decode("utf-8")
    }
    if sha:
        put_data["sha"] = sha
        
    req_put = urllib.request.Request(url, data=json.dumps(put_data).encode("utf-8"), method="PUT")
    req_put.add_header("Authorization", f"Bearer {token}")
    req_put.add_header("Accept", "application/vnd.github+json")
    req_put.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req_put)
        print("Successfully updated queue.json on GitHub.")
    except Exception as e:
        print("Failed to save queue.json", e)

async def process_next_clip():
    api_id = os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")
    bot_token = os.environ.get("BOT_TOKEN")
    channel_id = os.environ.get("CHANNEL_ID")
    
    queue, sha = get_queue_from_github()
    if not queue:
        print("Queue is empty. Nothing to post.")
        return
        
    # Get the oldest clip (first item)
    message_id_to_post = queue[0]
    print(f"Going to post message ID: {message_id_to_post}")
    
    app = Client("temp_downloader", api_id=api_id, api_hash=api_hash, bot_token=bot_token, in_memory=True)
    await app.start()
    
    chat_id = int(channel_id)
    await resolve_channel(app, channel_id)
    
    message = await app.get_messages(chat_id=chat_id, message_ids=int(message_id_to_post))
    if not message or (not message.video and not message.document):
        print(f"Message {message_id_to_post} is not a valid video or deleted. Removing from queue.")
        queue.pop(0)
        save_queue_to_github(queue, sha)
        await app.stop()
        return
        
    file_path = await app.download_media(message)
    
    caption = message.caption if message.caption else "Movie Clip"
    description = f"{caption} #movie #foryou #clips"
    
    # RANDOM DELAY FOR TIKTOK SAFETY
    if not os.environ.get("IMMEDIATE"):
        delay = random.randint(60, 2400)
        print(f"Waiting {delay} seconds before uploading to mimic human behavior...")
        time.sleep(delay)
    else:
        print("IMMEDIATE flag set. Uploading right now without delay.")
    
    success = False
    try:
        upload_video(file_path, description=description, cookies=COOKIES_FILE)
        success = True
    except Exception as e:
        print(f"Failed to upload: {e}")
        
    if os.path.exists(file_path):
        os.remove(file_path)
        
    if success:
        # Delete from telegram channel
        try:
            await message.delete()
        except: pass
        # Remove from queue
        queue.pop(0)
        save_queue_to_github(queue, sha)
        
    await app.stop()

if __name__ == "__main__":
    if os.path.exists(COOKIES_FILE):
        asyncio.run(process_next_clip())
