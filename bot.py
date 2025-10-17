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
async def credentials_handler(message: types.Message):
    try:
        creds = message.text.strip().split()
        if len(creds) != 2:
            await message.answer("❗ Введи логин и пароль через пробел.")
            return

        login, password = creds
        save_credentials(message.from_user.id, login, password)
        await message.answer("✅ Данные сохранены! Получаю скриншоты журналов...")

        # Импортируем функцию
        from parser import JOURNAL_LINKS, get_screenshot

        for subject in JOURNAL_LINKS.keys():
            await message.answer(f"📘 Загружаю журнал: {subject}...")

            screenshot_path = get_screenshot(login, password, subject)
            if screenshot_path and os.path.exists(screenshot_path):
                with open(screenshot_path, "rb") as photo:
                    await message.answer_photo(photo, caption=f"✅ {subject}")
            else:
                await message.answer(f"❌ Не удалось загрузить {subject}")

        await message.answer("✅ Все доступные журналы загружены!")

    except Exception as e:
        logging.error(f"Ошибка при обработке сообщения: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуй позже.")


# ───────────────────────────────
# Flask webhook endpoints
# ───────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return "ALIVE Bot работает 🚀"

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = types.Update(**request.json)

        # создаём новый event loop для каждого запроса
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(dp.feed_update(bot, update))

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
