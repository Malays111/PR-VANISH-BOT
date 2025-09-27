import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
PHOTO_URL = os.environ.get("PHOTO_URL")
CRYPTOBOT_TOKEN = os.environ.get("CRYPTOBOT_TOKEN")
TON_API_KEY = os.environ.get("TON_API_KEY", "")