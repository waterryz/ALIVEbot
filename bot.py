import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from flask import Flask, request

TOKEN = "8438829706:AAHiv7tHdDBMR3UoGXn3CcUHWuuIVFBAvU0"
WEBHOOK_URL = f"https://alivebot-7pa2.onrender.com/webhook/{TOKEN}"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# === Flask app ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ SmartNation бот активен!"

@app.post(f"/webhook/{TOKEN}")
async def webhook():
    try:
        update = types.Update.model_validate(request.json, strict=False)
        await dp.feed_update(bot, update)
        return "ok"
    except Exception as e:
        print(f"❌ Ошибка в webhook: {e}")
        return "error", 500

# === Aiogram handlers ===
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот колледжа SmartNation.\n"
        "Введи свой ИИН и пароль для входа в журнал 📘"
    )

# === Функция запуска ===
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Вебхук установлен: {WEBHOOK_URL}")

# === Основной запуск ===
def run():
    loop = asyncio.get_event_loop()
    loop.create_task(on_startup())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

if __name__ == "__main__":
    run()
