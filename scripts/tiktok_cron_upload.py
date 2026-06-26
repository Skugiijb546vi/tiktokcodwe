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

def download_clip(api_id, api_hash, bot_token, channel_id, message_id):
    """Download a clip from Telegram synchronously."""
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
    """Delete a message from Telegram synchronously."""
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
    asyncio.run(_delete())

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

def upload_to_tiktok_with_login(file_path, description):
    """Upload video to TikTok using Playwright with email/password login."""
    from playwright.sync_api import sync_playwright
    
    email = os.environ.get("TIKTOK_EMAIL")
    password = os.environ.get("TIKTOK_PASSWORD")
    
    if not email or not password:
        print("ERROR: TIKTOK_EMAIL or TIKTOK_PASSWORD not set!")
        return False
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        try:
            # Go to TikTok login
            print("Navigating to TikTok login page...")
            page.goto("https://www.tiktok.com/login/phone-or-email/email", timeout=60000)
            page.wait_for_timeout(3000)
            
            # Login with email
            print("Logging in with email...")
            email_input = page.locator('input[name="username"]')
            if email_input.count() == 0:
                email_input = page.locator('input[type="text"]').first
            email_input.fill(email)
            page.wait_for_timeout(1000)
            
            password_input = page.locator('input[type="password"]')
            password_input.fill(password)
            page.wait_for_timeout(1000)
            
            # Click login button
            login_btn = page.locator('button[data-e2e="login-button"]')
            if login_btn.count() == 0:
                login_btn = page.locator('button:has-text("Log in")').first
            login_btn.click()
            page.wait_for_timeout(10000)
            
            # Check if CAPTCHA appears
            if "captcha" in page.content().lower() or "verify" in page.url.lower():
                print("WARNING: CAPTCHA detected! Login may fail.")
                page.wait_for_timeout(15000)
            
            # Navigate to upload page
            print("Going to TikTok upload page...")
            page.goto("https://www.tiktok.com/creator#/upload?scene=creator_center", timeout=60000)
            page.wait_for_timeout(5000)
            
            # Upload the video file
            print(f"Uploading video: {file_path}")
            file_input = page.locator('input[type="file"]')
            if file_input.count() > 0:
                file_input.set_input_files(file_path)
            else:
                # Try iframe approach
                iframe = page.frame_locator("iframe").first
                file_input = iframe.locator('input[type="file"]')
                file_input.set_input_files(file_path)
            
            page.wait_for_timeout(10000)
            
            # Add description/caption
            print("Adding description...")
            caption_editor = page.locator('div[contenteditable="true"]').first
            if caption_editor.count() > 0:
                caption_editor.click()
                # Clear existing text
                page.keyboard.press("Control+a")
                page.keyboard.press("Backspace")
                page.keyboard.type(description, delay=50)
            
            page.wait_for_timeout(5000)
            
            # Wait for video to process
            print("Waiting for video to process...")
            page.wait_for_timeout(30000)
            
            # Click Post button
            print("Clicking Post button...")
            post_btn = page.locator('button:has-text("Post")').last
            if post_btn.count() == 0:
                post_btn = page.locator('div[class*="btn-post"]').first
            if post_btn.count() > 0:
                post_btn.click()
                page.wait_for_timeout(15000)
                print("Video posted successfully!")
                browser.close()
                return True
            else:
                print("Could not find Post button!")
                # Take screenshot for debugging
                page.screenshot(path="debug_screenshot.png")
                browser.close()
                return False
                
        except Exception as e:
            print(f"Upload error: {e}")
            try:
                page.screenshot(path="debug_screenshot.png")
            except:
                pass
            browser.close()
            return False

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
        delay = random.randint(60, 1200)
        print(f"Waiting {delay} seconds before uploading...")
        time.sleep(delay)
    else:
        print("IMMEDIATE flag set. Uploading now.")
    
    # Step 3: Upload to TikTok with email/password login
    success = upload_to_tiktok_with_login(file_path, description)
        
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
    main()
