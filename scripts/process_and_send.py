import os
import sys
import subprocess
import glob
import asyncio
from pyrogram import Client
from pyrogram.raw.functions.channels import GetChannels
from pyrogram.raw.types import InputChannel

async def resolve_channel(app, channel_id):
    """Resolve channel peer for fresh bot sessions on GitHub Actions."""
    cid = abs(int(channel_id))
    if cid > 1000000000000:
        cid = int(str(cid)[3:])  # Remove "100" prefix
    try:
        await app.invoke(GetChannels(id=[InputChannel(channel_id=cid, access_hash=0)]))
        print(f"Channel peer resolved successfully.")
    except Exception as e:
        print(f"Warning: Could not resolve channel peer: {e}")

def download_video_http(url, output_filename="input_movie.mp4"):
    print(f"Downloading video from {url}...")
    subprocess.run(["yt-dlp", "-o", output_filename, url], check=True)
    return output_filename

async def download_video_telegram(channel_id, message_id, output_filename="input_movie.mp4"):
    print(f"Downloading video from Telegram channel {channel_id}, message {message_id}...")
    api_id = os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")
    bot_token = os.environ.get("BOT_TOKEN")
    
    app = Client("temp_downloader", api_id=api_id, api_hash=api_hash, bot_token=bot_token, in_memory=True)
    await app.start()
    
    # Resolve the channel peer first (needed for fresh sessions)
    await resolve_channel(app, channel_id)
    
    message = await app.get_messages(chat_id=int(channel_id), message_ids=int(message_id))
    if not message.video and not message.document:
        raise Exception("Message does not contain a video.")
        
    actual_path = await app.download_media(message, file_name=output_filename)
    await app.stop()
    return actual_path

def process_and_split(input_file, output_dir="clips"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    print("Processing and splitting video...")
    command = [
        "ffmpeg", "-i", input_file,
        "-vf", "setpts=0.95*PTS,hflip,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-af", "atempo=1.05",
        "-f", "segment", "-segment_time", "120",
        "-c:v", "libx264", "-preset", "fast", "-reset_timestamps", "1", "-map", "0",
        os.path.join(output_dir, "clip_%03d.mp4")
    ]
    subprocess.run(command, check=True)
    clips = sorted(glob.glob(os.path.join(output_dir, "clip_*.mp4")))
    return clips

async def send_to_telegram(clips):
    api_id = os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")
    bot_token = os.environ.get("BOT_TOKEN")
    channel_id = os.environ.get("CHANNEL_ID")
    
    app = Client("temp_uploader", api_id=api_id, api_hash=api_hash, bot_token=bot_token, in_memory=True)
    await app.start()
    
    # Resolve the channel peer first
    await resolve_channel(app, channel_id)
    
    print(f"Sending {len(clips)} clips to channel {channel_id}...")
    for index, clip in enumerate(clips):
        part_number = index + 1
        caption = f"Part {part_number}"
        print(f"Uploading {clip}...")
        await app.send_video(chat_id=int(channel_id), video=clip, caption=caption)
        
    await app.stop()

async def main():
    video_data = sys.argv[1]
    input_vid = "input_movie.mp4"
    
    if video_data.startswith("tg_message:"):
        parts = video_data.split(":")
        channel_id = parts[1]
        message_id = parts[2]
        input_vid = await download_video_telegram(channel_id, message_id, input_vid)
    else:
        download_video_http(video_data, input_vid)
        
    clips = process_and_split(input_vid)
    await send_to_telegram(clips)

if __name__ == "__main__":
    asyncio.run(main())
