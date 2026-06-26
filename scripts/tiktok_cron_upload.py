import os
import sys
import time
import random
import json
import base64
import urllib.request
import asyncio
import threading
from pyrogram import Client
from pyrogram.raw.functions.channels import GetChannels
from pyrogram.raw.types import InputChannel

COOKIES_FILE = "cookies.txt"

def upload_screenshot_to_fileio(filepath):
    try:
        import requests
        with open(filepath, 'rb') as f:
            response = requests.post('https://tmpfiles.org/api/v1/upload', files={'file': f})
        data = response.json()
        if data.get('status') == 'success':
            url = data['data']['url']
            return url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
    except Exception as e:
        print("Screenshot upload failed:", e)
    
    # Fallback to bashupload
    try:
        import subprocess
        result = subprocess.run(['curl', '-s', '-T', filepath, 'https://bashupload.com/'], capture_output=True, text=True)
        import re
        match = re.search(r'https?://bashupload\.com/[^\s]+', result.stdout)
        if match:
            return match.group(0)
    except:
        pass
    return None

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
    def _run():
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

def parse_cookies(cookies_file):
    cookies = []
    with open(cookies_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 7:
                cookie = {
                    'name': parts[5],
                    'value': parts[6],
                    'domain': parts[0],
                    'path': parts[2],
                }
                try:
                    exp = int(parts[4])
                    if exp > 0:
                        cookie['expires'] = exp
                except:
                    pass
                cookies.append(cookie)
    return cookies

def upload_to_tiktok(file_path, description):
    from playwright.sync_api import sync_playwright
    
    cookies = parse_cookies(COOKIES_FILE)
    if not cookies:
        print("ERROR: No cookies found!")
        return False
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        for cookie in cookies:
            try:
                c = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain'],
                    'path': cookie.get('path', '/'),
                }
                if 'expires' in cookie:
                    c['expires'] = cookie['expires']
                context.add_cookies([c])
            except Exception as e:
                pass
        
        page = context.new_page()
        
        try:
            print("Navigating to TikTok upload page...")
            page.goto("https://www.tiktok.com/upload", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            
            # Check what account we are logged into
            page.screenshot(path="login_status.png")
            link = upload_screenshot_to_fileio("login_status.png")
            print(f"Screenshot at upload page: {link}")
            
            try:
                # Try to get the username from the profile picture or URL
                profile_link = page.locator('a[href^="/@"]').first
                if profile_link.is_visible(timeout=3000):
                    href = profile_link.get_attribute("href")
                    print(f"Logged in as: {href}")
                else:
                    print("Could not find profile link on page. Is user fully logged in?")
            except Exception as e:
                print("Error finding profile:", e)
                
            if "/login" in page.url:
                print("ERROR: Cookies are invalid. Redirected to login page.")
                browser.close()
                return False
            
            print("Uploading video file...")
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(file_path)
            
            print("Waiting for video to upload and process...")
            page.wait_for_timeout(15000)
            
            page.screenshot(path="after_upload.png")
            link = upload_screenshot_to_fileio("after_upload.png")
            print(f"Screenshot after video upload: {link}")
            
            for _ in range(5):
                try:
                    for selector in [
                        "button:has-text('Got it')",
                        "button:has-text('Close')", 
                        "button:has-text('Dismiss')",
                        "button:has-text('OK')",
                        "div[class*='modal'] button",
                        "[data-e2e='modal-close-button']",
                    ]:
                        try:
                            btn = page.locator(selector).first
                            if btn.is_visible(timeout=1000):
                                btn.click(force=True)
                                page.wait_for_timeout(1000)
                        except:
                            pass
                except:
                    pass
            
            print("Setting description...")
            try:
                caption_editor = page.locator("div[contenteditable='true']").first
                if caption_editor.is_visible(timeout=5000):
                    caption_editor.click(force=True)
                    page.wait_for_timeout(500)
                    page.keyboard.press("Control+a")
                    page.keyboard.press("Backspace")
                    page.wait_for_timeout(500)
                    for char in description:
                        page.keyboard.type(char, delay=20)
                    print("Description set!")
            except Exception as e:
                print(f"Could not set description: {e}")
            
            page.wait_for_timeout(5000)
            
            page.screenshot(path="before_post.png")
            link = upload_screenshot_to_fileio("before_post.png")
            print(f"Screenshot before posting: {link}")
            
            for selector in ["button:has-text('Got it')", "button:has-text('Close')", "button:has-text('Dismiss')"]:
                try:
                    btn = page.locator(selector)
                    if btn.is_visible(timeout=1000):
                        btn.click(force=True)
                        page.wait_for_timeout(1000)
                except:
                    pass
            
            print("Looking for Post button...")
            posted = False
            
            post_selectors = [
                "button:has-text('Post')",
                "button[data-e2e='post-button']",
                "div[class*='btn-post']",
                "button:has-text('Publish')",
            ]
            
            for selector in post_selectors:
                try:
                    post_btn = page.locator(selector).last
                    if post_btn.is_visible(timeout=3000):
                        post_btn.click(force=True)
                        print(f"Clicked post button with selector: {selector}")
                        posted = True
                        break
                except:
                    continue
            
            if not posted:
                try:
                    page.evaluate("""
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            if (btn.textContent.trim() === 'Post' || btn.textContent.trim() === 'Publish') {
                                btn.click();
                                break;
                            }
                        }
                    """)
                    posted = True
                    print("Clicked post button via JavaScript")
                except Exception as e:
                    print(f"JS click failed: {e}")
            
            if posted:
                print("Wait 20 seconds after posting...")
                page.wait_for_timeout(20000)
                
                page.screenshot(path="after_post.png")
                link = upload_screenshot_to_fileio("after_post.png")
                print(f"Screenshot after posting: {link}")
                
                current_url = page.url
                page_content = page.content()
                
                if "manage" in current_url or "Your video is being uploaded" in page_content or "uploaded" in page_content.lower() or "post" not in current_url:
                    print("SUCCESS: Video posted to TikTok!")
                    browser.close()
                    return True
                else:
                    print(f"Post button clicked but unclear if successful. URL: {current_url}")
                    browser.close()
                    return False
            else:
                print("ERROR: Could not find post button!")
                browser.close()
                return False
                
        except Exception as e:
            print(f"Upload error: {e}")
            browser.close()
            return False

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
    
    file_path, caption = download_clip(api_id, api_hash, bot_token, channel_id, message_id_to_post)
    
    if not file_path:
        print(f"Message {message_id_to_post} is not valid. Removing from queue.")
        queue.pop(0)
        save_queue_to_github(queue, sha)
        return
    
    print(f"Downloaded: {file_path}")
    description = f"{caption} #movie #foryou #clips"
    
    if not os.environ.get("IMMEDIATE"):
        delay = random.randint(30, 300)
        print(f"Waiting {delay} seconds before uploading...")
        time.sleep(delay)
    else:
        print("IMMEDIATE flag set. Uploading now.")
    
    success = upload_to_tiktok(file_path, description)
        
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
    # Ensure requests library is installed for screenshot uploads
    os.system("pip install requests > /dev/null 2>&1")
    main()
