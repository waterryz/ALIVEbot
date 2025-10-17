import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from parser import get_screenshot
from users_db import init_db, save_credentials
from dotenv import load_dotenv
import psycopg

# ───────────────────────────────
# ЗАГРУЖАЕМ ПЕРЕМЕННЫЕ
# ───────────────────────────────
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ───────────────────────────────
# ИНИЦИАЛИЗАЦИЯ БАЗЫ
# ───────────────────────────────
try:
    init_db()
    logging.info("✅ Таблица users готова к использованию")
except psycopg.Error as e:
    logging.error(f"❌ Ошибка инициализации базы: {e}")

# ───────────────────────────────
# ОБРАБОТЧИК КОМАНДЫ /start
# ───────────────────────────────
@dp.message(CommandStart())
async def start_command(message: types.Message):
    await message.answer(
        "Привет! 👋\n"
        "Я помогу тебе получить скриншоты с сайта колледжа.\n\n"
        "🔹 Отправь свой ИИН и пароль в формате:\n"
        "`123456789012 пароль123`\n\n"
        "🔹 Пример:\n"
        "`060420091234 qwerty123`\n\n"
        "_Все данные шифруются и не передаются третьим лицам._",
        parse_mode="Markdown"
    )

# ───────────────────────────────
# ОБРАБОТЧИК ВВОДА ИИН И ПАРОЛЯ
# ───────────────────────────────
@dp.message()
async def handle_login(message: types.Message):
    try:
        text = message.text.strip()
        if len(text.split()) != 2:
            await message.answer("❌ Неверный формат. Отправь в формате: `ИИН пароль`", parse_mode="Markdown")
            return

        iin, password = text.split()

        save_credentials(message.from_user.id, iin, password)
        await message.answer("✅ Данные сохранены! Теперь выбери предмет:")

        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="Python"), types.KeyboardButton(text="БД")],
                [types.KeyboardButton(text="ИКТ"), types.KeyboardButton(text="Графика")],
                [types.KeyboardButton(text="Физра"), types.KeyboardButton(text="Экономика")]
            ],
            resize_keyboard=True
        )
        await message.answer("📚 Выбери предмет:", reply_markup=keyboard)

    except Exception as e:
        logging.error(f"Ошибка при обработке логина: {e}")
        await message.answer("❌ Ошибка при сохранении данных. Попробуй снова.")

# ───────────────────────────────
# ПОЛУЧЕНИЕ СКРИНШОТА
# ───────────────────────────────
@dp.message(lambda msg: msg.text in ["Python", "БД", "ИКТ", "Графика", "Физра", "Экономика"])
async def handle_subject(message: types.Message):
    try:
        user_id = message.from_user.id
        subject = message.text
        iin, password = await get_user_credentials(user_id)

        if not iin or not password:
            await message.answer("❌ Сначала отправь свой ИИН и пароль.")
            return

        await message.answer("🕐 Подожди немного, получаю скриншот...")

        screenshot_path = get_screenshot(iin, password, subject)
        if screenshot_path:
            await message.answer_photo(types.FSInputFile(screenshot_path), caption=f"📄 {subject}")
        else:
            await message.answer("❌ Ошибка при получении скриншота. Проверь данные и попробуй снова.")

    except Exception as e:
        logging.error(f"Ошибка при получении скриншота: {e}")
        await message.answer("⚠️ Не удалось получить журнал. Попробуй позже.")

# ───────────────────────────────
# ЗАПУСК ПОЛЛИНГА
# ───────────────────────────────
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
