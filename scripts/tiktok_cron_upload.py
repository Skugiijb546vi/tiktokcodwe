import os
import sys
import time
import random
import json
import base64
import urllib.request
import asyncio
from pyrogram import Client
from pyrogram.raw.functions.channels import GetChannels
from pyrogram.raw.types import InputChannel
from tiktok_uploader.upload import upload_video

COOKIES_FILE = "cookies.txt"

def download_clip(api_id, api_hash, bot_token, channel_id, message_id):
    async def _download():
        app = Client("temp_dl", api_id=api_id, api_hash=api_hash, bot_token=bot_token, in_memory=True)
        await app.start()
        cid = abs(int(channel_id))
        if cid > 1000000000000:
            cid = int(str(cid)[3:])
        try:
            await app.invoke(GetChannels(id=[InputChannel(channel_id=cid, access_hash=0)]))
        except:
            pass
        message = await app.get_messages(chat_id=int(channel_id), message_ids=int(message_id))
        if not message or (not message.video and not message.document):
            await app.stop()
            return None, None
        file_path = await app.download_media(message)
        caption = message.caption if message.caption else "Movie Clip"
        await app.stop()
        return file_path, caption
    return asyncio.run(_download())

def delete_message(api_id, api_hash, bot_token, channel_id, message_id):
    import threading
    def _run():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def _delete():
            app = Client("temp_del", api_id=api_id, api_hash=api_hash, bot_token=bot_token, in_memory=True)
            await app.start()
            cid = abs(int(channel_id))
            if cid > 1000000000000:
                cid = int(str(cid)[3:])
            try:
                await app.invoke(GetChannels(id=[InputChannel(channel_id=cid, access_hash=0)]))
            except:
                pass
            try:
                await app.delete_messages(chat_id=int(channel_id), message_ids=int(message_id))
            except:
                pass
            await app.stop()
        loop.run_until_complete(_delete())
        loop.close()
    t = threading.Thread(target=_run)
    t.start()
    t.join(timeout=30)

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

def main():
    api_id = os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")
    bot_token = os.environ.get("BOT_TOKEN")
    channel_id = os.environ.get("CHANNEL_ID")
    
    queue, sha = get_queue_from_github()
    if not queue:
        print("Queue is empty. Nothing to post.")
        return
        
    message_id_to_post = queue[0]
    print(f"Going to post message ID: {message_id_to_post}")
    
    # Step 1: Download from Telegram
    file_path, caption = download_clip(api_id, api_hash, bot_token, channel_id, message_id_to_post)
    
    if not file_path:
        print(f"Message {message_id_to_post} is not valid. Removing from queue.")
        queue.pop(0)
        save_queue_to_github(queue, sha)
        return
    
    print(f"Downloaded: {file_path}")
    description = f"{caption} #movie #foryou #clips"
    
    # Step 2: Random delay
    if not os.environ.get("IMMEDIATE"):
        delay = random.randint(30, 300)
        print(f"Waiting {delay} seconds before uploading...")
        time.sleep(delay)
    else:
        print("IMMEDIATE flag set. Uploading now.")
    
    # Step 3: Upload to TikTok using tiktok-uploader with cookies
    success = False
    try:
        upload_video(file_path, description=description, cookies=COOKIES_FILE)
        success = True
        print("Successfully uploaded to TikTok!")
    except Exception as e:
        print(f"Failed to upload: {e}")
        
    if os.path.exists(file_path):
        os.remove(file_path)
        
    if success:
        delete_message(api_id, api_hash, bot_token, channel_id, message_id_to_post)
        queue.pop(0)
        save_queue_to_github(queue, sha)
        print(f"Done! Remaining in queue: {len(queue)}")
    else:
        print("Upload failed. Will retry next time.")

if __name__ == "__main__":
    if not os.path.exists(COOKIES_FILE):
        print("No cookies.txt found. Exiting.")
        sys.exit(0)
    main()
