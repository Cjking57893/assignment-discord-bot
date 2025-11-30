import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")
CANVAS_BASE_URL = "https://canvas.instructure.com/api/v1/"
DB_PATH = os.getenv("DB_PATH")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Discord channel ID for weekly notifications
HEADERS = {
    "Authorization": f"Bearer {CANVAS_TOKEN}"
}