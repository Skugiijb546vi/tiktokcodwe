import os
import sys
import glob
import asyncio
import json
import base64
import urllib.request
from pyrogram import Client
from pyrogram.raw.functions.channels import GetChannels
from pyrogram.raw.types import InputChannel

async def resolve_channel(app, channel_id):
    cid = abs(int(channel_id))
    if cid > 1000000000000:
        cid = int(str(cid)[3:])
    try:
        await app.invoke(GetChannels(id=[InputChannel(channel_id=cid, access_hash=0)]))
        print("Channel peer resolved.")
    except Exception as e:
        print(f"Warning: Could not resolve channel peer: {e}")

async def download_video_telegram(app, channel_id, message_id, output_filename="input_movie.mp4"):
    print(f"Downloading video from Telegram channel {channel_id}, message {message_id}...")
    message = await app.get_messages(chat_id=int(channel_id), message_ids=int(message_id))
    if not message.video and not message.document:
        raise Exception("Message does not contain a video.")
    actual_path = await app.download_media(message, file_name=output_filename)
    return actual_path

async def process_and_split(input_file, app=None, user_chat_id=None, output_dir="clips"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    if app and user_chat_id:
        try:
            await app.send_message(chat_id=int(user_chat_id), text="✂️ مۆنتاژ و بڕینی ڤیدیۆکە دەستی پێکرد، ئەمە کەمێک کاتی دەوێت...")
        except: pass
        
    command = [
        "ffmpeg", "-i", input_file,
        "-vf", "setpts=0.95*PTS,hflip,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-af", "atempo=1.05",
        "-f", "segment", "-segment_time", "120",
        "-c:v", "libx264", "-preset", "fast", "-reset_timestamps", "1", "-map", "0",
        os.path.join(output_dir, "clip_%03d.mp4")
    ]
    
    process = await asyncio.create_subprocess_exec(*command)
    minutes_passed = 0
    while True:
        try:
            await asyncio.wait_for(process.wait(), timeout=600.0) # wait 10 mins
            break
        except asyncio.TimeoutError:
            minutes_passed += 10
            if app and user_chat_id:
                try:
                    await app.send_message(chat_id=int(user_chat_id), text=f"⏳ هێشتا خەریکی مۆنتاژم... (نزیکەی {minutes_passed} خولەک تێپەڕی)")
                except: pass
                
    if process.returncode != 0:
        if app and user_chat_id:
            try:
                await app.send_message(chat_id=int(user_chat_id), text="❌ هەڵەیەک لە کاتی مۆنتاژ ڕوویدا!")
            except: pass
        raise Exception("ffmpeg failed")
        
    clips = sorted(glob.glob(os.path.join(output_dir, "clip_*.mp4")))
    return clips

async def send_to_telegram(app, clips, channel_id):
    print(f"Sending {len(clips)} clips to channel {channel_id}...")
    message_ids = []
    for index, clip in enumerate(clips):
        part_number = index + 1
        caption = f"Part {part_number}"
        msg = await app.send_video(chat_id=int(channel_id), video=clip, caption=caption)
        message_ids.append(msg.id)
    return message_ids

def update_queue_on_github(message_ids):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "Skugiijb546vi/tiktokcodwe")
    if not token:
        print("No GITHUB_TOKEN. Cannot update queue on github.")
        return
        
    url = f"https://api.github.com/repos/{repo}/contents/queue.json"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    
    sha = None
    existing_queue = []
    try:
        res = urllib.request.urlopen(req)
        data = json.loads(res.read())
        sha = data.get("sha")
        content = base64.b64decode(data["content"]).decode("utf-8")
        existing_queue = json.loads(content)
    except Exception as e:
        print("No existing queue.json found, creating a new one.")
        pass
        
    existing_queue.extend(message_ids)
    
    put_data = {
        "message": "Update TikTok upload queue",
        "content": base64.b64encode(json.dumps(existing_queue).encode("utf-8")).decode("utf-8")
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
        print("Failed to update queue.json:", e)

async def main():
    video_data = sys.argv[1]
    input_vid = "input_movie.mp4"
    
    parts = video_data.split(":")
    channel_id = parts[1]
    message_id = parts[2]
    user_chat_id = parts[3] if len(parts) > 3 else None
    
    api_id = os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")
    bot_token = os.environ.get("BOT_TOKEN")
    
    app = Client("temp_worker", api_id=api_id, api_hash=api_hash, bot_token=bot_token, in_memory=True)
    await app.start()
    
    try:
        await resolve_channel(app, channel_id)
        
        # Download
        input_vid = await download_video_telegram(app, channel_id, message_id, input_vid)
        
        # Split (reports every 10 min)
        clips = await process_and_split(input_vid, app, user_chat_id)
        
        # Send to dump channel
        message_ids = await send_to_telegram(app, clips, channel_id)
        
        # Save message IDs to queue.json on GitHub!
        update_queue_on_github(message_ids)
        
        # Final success message
        if user_chat_id:
            try:
                await app.send_message(chat_id=int(user_chat_id), text="✅ تەواو بوو! ڤیدیۆکە بڕدرا بۆ چەند بەشێک. لە ماوەی چەند خولەکی داهاتوودا یەکەم پارچە پۆست دەبێت لە تیکتۆکەکەت، وە بەشەکانی تر هەر نیو کاتژمێر جارێک بە هەڕەمەکی خۆیان پۆست دەکرێن.")
            except: pass
            
    except Exception as e:
        print(f"Error: {e}")
        if user_chat_id:
            try:
                await app.send_message(chat_id=int(user_chat_id), text=f"❌ هەڵەیەک ڕوویدا: {str(e)}")
            except: pass
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
