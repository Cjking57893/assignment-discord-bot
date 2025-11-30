"""
Configuration Management for Canvas Assignment Bot
Loads environment variables and provides application-wide settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Canvas API Configuration
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")
CANVAS_BASE_URL = "https://canvas.instructure.com/api/v1/"
HEADERS = {
    "Authorization": f"Bearer {CANVAS_TOKEN}"
}

# Database Configuration (optional, has default in db_manager.py)
DB_PATH = os.getenv("DB_PATH")