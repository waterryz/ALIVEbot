import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from flask import Flask, request
from users_db import init_db, save_credentials
from parser import parse_site  # если у тебя парсер называется иначе — поменяй
from dotenv import load_dotenv

# ───────────────────────────────
# Настройка окружения
# ───────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise Exception("❌ Не найден BOT_TOKEN в переменных окружения")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# ───────────────────────────────
# Инициализация базы данных
# ───────────────────────────────
try:
    init_db()
    logging.info("✅ База данных инициализирована")
except Exception as e:
    logging.error(f"❌ Ошибка инициализации базы: {e}")

# ───────────────────────────────
# Обработчики команд
# ───────────────────────────────
@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Привет 👋 Это ALIVE Bot!\n"
        "Отправь логин и пароль, чтобы получить данные из журнала."
    )

@dp.message()
async def credentials_handler(message: Message):
    try:
        creds = message.text.strip().split()
        if len(creds) != 2:
            await message.answer("❗ Введи логин и пароль через пробел.")
            return

        login, password = creds
        save_credentials(message.from_user.id, login, password)
        await message.answer("✅ Данные сохранены! Получаю информацию...")

        result = await parse_site(login, password)
        await message.answer(result or "Не удалось получить данные 😔")

    except Exception as e:
        logging.error(f"Ошибка при обработке сообщения: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуй снова.")

# ───────────────────────────────
# Flask webhook endpoints
# ───────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return "ALIVE Bot работает 🚀"

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    try:
        update = types.Update(**request.json)
        await dp.feed_update(bot, update)
        return "ok", 200
    except Exception as e:
        logging.error(f"Ошибка в webhook: {e}")
        return "error", 500

# ───────────────────────────────
# Запуск Flask + aiogram
# ───────────────────────────────
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    logging.info("🚀 Flask сервер запущен")
    try:
        app.run(host="0.0.0.0", port=10000)
    except Exception as e:
        logging.error(f"❌ Ошибка при запуске Flask: {e}")
