"""Configuration management - loads environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Canvas API Configuration
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")
CANVAS_BASE_URL = os.getenv("CANVAS_BASE_URL", "https://canvas.instructure.com/api/v1/")
HEADERS = {
    "Authorization": f"Bearer {CANVAS_TOKEN}"
}

# Database Configuration (optional, has default in db_manager.py)
DB_PATH = os.getenv("DB_PATH")

# Weekly Notification Configuration
WEEKLY_NOTIFICATION_HOUR = int(os.getenv("WEEKLY_NOTIFICATION_HOUR", "9"))
WEEKLY_NOTIFICATION_MINUTE = int(os.getenv("WEEKLY_NOTIFICATION_MINUTE", "0"))
