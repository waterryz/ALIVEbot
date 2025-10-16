import os
import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# === Настройки окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL", "https://alivebot-9wc6.onrender.com")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в переменных окружения Render")

# === Инициализация Aiogram ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Обработчики ===
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "👋 Сәлем! Бұл бот SmartNation колледж сайтынан бағаларды көрсетеді.\n\n"
        "Пока в разработке разработчиком."
    )

@dp.message()
async def echo(message: types.Message):
    await message.answer(f"Ты написал: {message.text}")

# === Flask сервер ===
app = Flask(__name__)

@app.get("/")
def home():
    return "✅ Bot Alive and Running!"

@app.post(f"/webhook/{BOT_TOKEN}")
async def webhook():
    try:
        data = request.get_json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
    except Exception as e:
        print(f"⚠️ Ошибка при обработке вебхука: {e}")
    return {"ok": True}

# === Установка вебхука при запуске ===
async def on_startup():
    webhook_url = f"{APP_URL}/webhook/{BOT_TOKEN}"
    await bot.set_webhook(webhook_url)
    print(f"✅ Вебхук установлен: {webhook_url}")

def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(on_startup())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

if __name__ == "__main__":
    main()
