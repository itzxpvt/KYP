#  config.py

from dotenv import load_dotenv
import os

# Load .env file explicitly
load_dotenv(dotenv_path="config.env")

# Telegram API credentials
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Allowed chat IDs (individual users or groups)
ALLOWED_CHAT_IDS = [
    6397654988,         # Individual user
    -1002344515129      # Example group/channel
]

# Mapping of batches to their respective group chat IDs
BATCH_GROUPS = {
    "January":  [-1002428161649],
    "February": [-1002563300801],
    "March":    [-1002578015396],
    "April":    [-1002325824742]
}

# Time zone setting
TIME_ZONE = "Asia/Kolkata"
