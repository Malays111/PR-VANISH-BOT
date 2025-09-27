import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в переменных окружения")

ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
if not ADMIN_ID:
    raise ValueError("ADMIN_ID не установлен в переменных окружения")

PHOTO_URL = os.environ.get("PHOTO_URL")
if not PHOTO_URL:
    raise ValueError("PHOTO_URL не установлен в переменных окружения")

CRYPTOBOT_TOKEN = os.environ.get("CRYPTOBOT_TOKEN")
if not CRYPTOBOT_TOKEN:
    raise ValueError("CRYPTOBOT_TOKEN не установлен в переменных окружения")

TON_API_KEY = os.environ.get("TON_API_KEY", "")