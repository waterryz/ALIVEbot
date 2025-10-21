import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL")  # например, https://parser-production.up.railway.app/parse
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://your-bot-production.up.railway.app/webhook
PORT = int(os.getenv("PORT", 8080))
