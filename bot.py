import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
from users_db import init_db, save_credentials
from dotenv import load_dotenv

# ───────────────────────────────
# НАСТРОЙКА ОКРУЖЕНИЯ
# ───────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise Exception("❌ BOT_TOKEN не найден в Render Settings")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# ───────────────────────────────
# ИНИЦИАЛИЗАЦИЯ БАЗЫ
# ───────────────────────────────
try:
    init_db()
except Exception as e:
    logging.error(f"❌ Ошибка инициализации базы данных: {e}")

# ───────────────────────────────
# КНОПКА ПРИМЕРА
# ───────────────────────────────
example_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📖 Пример формата", callback_data="example")]
])

# ───────────────────────────────
# ОБРАБОТЧИК /start
# ───────────────────────────────
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    text = (
        "Привет 👋 Это *ALIVE Bot!*\n\n"
        "📘 Я помогу тебе получить скриншоты журналов с сайта колледжа.\n\n"
        "🔐 Отправь свои данные в формате:\n"
        "`ИИН ПАРОЛЬ`\n\n"
        "После этого я начну загрузку твоих журналов 📊"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=example_button)

# ───────────────────────────────
# КОЛБЭК ПРИ НАЖАТИИ НА КНОПКУ "ПРИМЕР"
# ───────────────────────────────
@dp.callback_query()
async def show_example(callback: types.CallbackQuery):
    if callback.data == "example":
        example_text = (
            "🧩 *Пример правильного ввода:*\n"
            "`123456888999 888999abc`\n\n"
            "📌 Первое — ИИН, второе — пароль от сайта колледжа.\n"
            "⚠️ Не пиши запятые, точки и лишние символы!"
        )
        await callback.message.answer(example_text, parse_mode="Markdown")
        await callback.answer()

# ───────────────────────────────
# ОБРАБОТКА ДАННЫХ (ИИН + ПАРОЛЬ)
# ───────────────────────────────
@dp.message()
async def credentials_handler(message: types.Message):
    try:
        creds = message.text.strip().split()
        if len(creds) != 2:
            await message.answer("❗ Введи логин и пароль через пробел.\n\nПример: `090120555841 555841abc`", parse_mode="Markdown")
            return

        login, password = creds
        save_credentials(message.from_user.id, login, password)
        await message.answer("✅ Данные сохранены! Загружаю журналы...")

        from parser import JOURNAL_LINKS, get_screenshot
        import os

        os.makedirs("screenshots", exist_ok=True)

        for subject in JOURNAL_LINKS.keys():
            await message.answer(f"📘 Загружаю журнал: {subject}...")
            screenshot_path = get_screenshot(login, password, subject)
            if screenshot_path and os.path.exists(screenshot_path):
                with open(screenshot_path, "rb") as photo:
                    await message.answer_photo(photo, caption=f"✅ {subject}")
            else:
                await message.answer(f"❌ Не удалось загрузить {subject}")

        await message.answer("✅ Все доступные журналы отправлены!")

    except Exception as e:
        logging.error(f"Ошибка при обработке сообщения: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуй позже.")

# ───────────────────────────────
# FLASK WEBHOOK ENDPOINTS
# ───────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return "ALIVE Bot работает 🚀"

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = types.Update(**request.json)
        asyncio.run(dp.feed_update(bot, update))  # ✅ стабильный запуск
        return "ok", 200
    except Exception as e:
        logging.error(f"Ошибка в webhook: {e}")
        return "error", 500

# ───────────────────────────────
# ЗАПУСК FLASK СЕРВЕРА
# ───────────────────────────────
if __name__ == "__main__":
    logging.info("🚀 Flask сервер запущен и ожидает обновления Telegram...")
    app.run(host="0.0.0.0", port=10000)
