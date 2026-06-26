import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
import config

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

# Start dummy server for Render
threading.Thread(target=run_dummy_server, daemon=True).start()

app = Client(
    "tiktok_bot_session",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    await message.reply_text("Ø³ÚµØ§Ùˆ! Ù…Ù† Ø¨Û†ØªÛŒ ØªØ§ÛŒØ¨Û•ØªÛŒ ØªÛ†Ù… Ø¨Û† Ø¦Ø§Ù…Ø§Ø¯Û•Ú©Ø±Ø¯Ù†ÛŒ Ú¤ÛŒØ¯ÛŒÛ† Ø¨Û† ØªÛŒÚ©ØªÛ†Ú©. Ú¤ÛŒØ¯ÛŒÛ†Ú©Û•Øª Ù„ÛŽØ±Û• ÙÛ†Ø±ÙˆØ§Ø±Ø¯ Ø¨Ú©Û• ØªØ§ Ø¯Û•Ø³Øª Ù¾ÛŽ Ø¨Ú©Û•Ù….")

def trigger_github(video_data):
    url = f"https://api.github.com/repos/{config.REPO_OWNER}/{config.REPO_NAME}/actions/workflows/process_movie.yml/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {
        "ref": "main",
        "inputs": {
            "video_url": video_data
        }
    }
    return requests.post(url, headers=headers, json=data)

@app.on_message(filters.text & ~filters.command("start"))
async def process_video_link(client: Client, message: Message):
    video_url = message.text.strip()
    
    if not video_url.startswith("http"):
        await message.reply_text("Tkaye linkeky drwst bnera yan flmek forward bka.")
        return
    
    msg = await message.reply_text(f"Linkekem wergert. Hewldadem bnerem bo GitHub Actions...\nLink: {video_url}")
    
    if not config.GITHUB_TOKEN or not config.REPO_OWNER or not config.REPO_NAME:
        await msg.edit_text("Keshaya: GitHub Token yan zanyary GitHub nadrwta. Tkaye .env file chak bka.")
        return
        
    try:
        response = trigger_github(video_url)
        if response.status_code == 204:
            await msg.edit_text("Sarkawtuw bu! GitHub Actions karesakay destpekr. Tik tokakant chawere bka.")
        else:
            await msg.edit_text(f"Kesha drwst bu la nardny bo GitHub:\nCode: {response.status_code}\nResponse: {response.text}")
    except Exception as e:
        await msg.edit_text(f"Hala ruyda: {str(e)}")

@app.on_message(filters.video | filters.document)
async def process_telegram_video(client: Client, message: Message):
    msg = await message.reply_text("ðŸ“¥ Ú¤ÛŒØ¯ÛŒÛ†Ú©Û• ÙˆÛ•Ø±Ú¯ÛŒØ±Ø§ØŒ Ø®Û•Ø±ÛŒÚ©ÛŒ Ø¦Ø§Ù…Ø§Ø¯Û•Ú©Ø±Ø¯Ù†ÛŒÙ…...")
    
    if not config.CHANNEL_ID:
        await msg.edit_text("Keshaya: CHANNEL_ID diari nakrawa!")
        return
        
    try:
        # Forward the video to the dump channel
        forwarded_msg = await message.copy(chat_id=int(config.CHANNEL_ID))
        
        # Create the special data string for github (includes chat_id for reporting)
        video_data = f"tg_message:{config.CHANNEL_ID}:{forwarded_msg.id}:{message.chat.id}"
        
        response = trigger_github(video_data)
        if response.status_code == 204:
            await msg.edit_text("âœ… Ú¤ÛŒØ¯ÛŒÛ†Ú©Û• ÙˆÛ•Ø±Ú¯ÛŒØ±Ø§ Ùˆ Ø®Û•Ø±ÛŒÚ©ÛŒ Ù…Û†Ù†ØªØ§Ú˜ Ùˆ Ø¨Ú•ÛŒÙ†Ù…ØŒ ØªÚ©Ø§ÛŒÛ• Ú†Ø§ÙˆÛ•Ú•ÛŽ Ø¨Ú©Û• Ø¦Û•Ù… Ù¾Ø±Û†Ø³Û•ÛŒÛ• Ù¾ÛŽÙˆÛŒØ³ØªÛŒ Ø¨Û• Ú©Ø§ØªÛ•ØŒ Ù‡Û•Ø± Ù¡Ù  Ø®ÙˆÙ„Û•Ú© Ø¬Ø§Ø±ÛŽÚ© Ú•Ø§Ù¾Û†Ø±ØªÛŽÚ©Øª Ø¨Û† Ø¯Û•Ù†ÛŽØ±Ù… Ú©Û• Ú†Û•Ù†Ø¯Ù… Ù„ÛŽ ØªÛ•ÙˆØ§Ùˆ Ú©Ø±Ø¯ÙˆÙˆÛ•...")
        else:
            await msg.edit_text(f"Kesha drwst bu la nardny bo GitHub:\nCode: {response.status_code}\nResponse: {response.text}")
            
    except Exception as e:
        await msg.edit_text(f"Hala ruyda: {str(e)}")

if __name__ == "__main__":
    print("Bot started...")
    app.run()
