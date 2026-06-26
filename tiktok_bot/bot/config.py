import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "22697853"))
API_HASH = os.getenv("API_HASH", "4801319a0aeb52817bc01d3cc60bb245")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8648125101:AAFkU3zC0-WbfRMysznRP_eswbEDeDi-PiM")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
REPO_OWNER = os.getenv("REPO_OWNER", "Skugiijb546vi")
REPO_NAME = os.getenv("REPO_NAME", "tiktok_bot")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1004487037289")
