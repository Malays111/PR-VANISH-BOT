import os

BOT_TOKEN = os.environ.get("8398207757:AAHqH5mZSwL7rxx6FGZFu-0ZzfIHQ00_I7M")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в переменных окружения")

ADMIN_ID = int(os.environ.get("ADMIN_ID", 8217088275))
if not ADMIN_ID:
    raise ValueError("ADMIN_ID не установлен в переменных окружения")

PHOTO_URL = os.environ.get("https://www.dropbox.com/scl/fi/w58dqa8v3gypoyx26qgno/photo_2025-09-27_01-31-37-1.jpg?rlkey=s17vgnm63nu209hs7or0zilxr&st=9fejuodz&dl=1")
if not PHOTO_URL:
    raise ValueError("PHOTO_URL не установлен в переменных окружения")

CRYPTOBOT_TOKEN = os.environ.get("463340:AA7AujJqzBp7kIXfSpxXcGyaQtMXbgk8B4E")
if not CRYPTOBOT_TOKEN:
    raise ValueError("CRYPTOBOT_TOKEN не установлен в переменных окружения")

TON_API_KEY = os.environ.get("TON_API_KEY", "")