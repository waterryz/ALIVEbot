import asyncio
import logging
import os
import psycopg
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from cryptography.fernet import Fernet
from parser import get_screenshot

# Логирование
logging.basicConfig(level=logging.INFO)

# ──────────────────────────────────────────────
# Настройки окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not BOT_TOKEN or not DATABASE_URL:
    raise Exception("❌ BOT_TOKEN или DATABASE_URL не заданы!")

fernet = Fernet(ENCRYPTION_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ──────────────────────────────────────────────
# Инициализация базы данных
async def init_db():
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    login TEXT,
                    password TEXT
                );
            """)
            await conn.commit()
    logging.info("✅ Таблица users готова к использованию")

asyncio.run(init_db())

# ──────────────────────────────────────────────
# Хэндлеры команд

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📘 Пример IIN и пароля", callback_data="example")],
    ])
    await message.answer(
        "👋 Привет! Отправь свой ИИН и пароль через пробел\n(пример: `123456789012 1234`)",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query()
async def example_callback(callback: types.CallbackQuery):
    await callback.message.answer("📘 Пример: `123456789012 1234` (IIN и пароль через пробел)", parse_mode="Markdown")
    await callback.answer()

# ──────────────────────────────────────────────
# Основная логика (ИИН/пароль → предмет)
@dp.message()
async def handle_message(message: types.Message):
    text = message.text.strip()
    parts = text.split()

    # Проверяем, есть ли пользователь в базе
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT login, password FROM users WHERE user_id = %s", (message.from_user.id,))
            row = await cur.fetchone()

    # Если пользователя нет — сохраняем ИИН и пароль
    if not row:
        if len(parts) != 2:
            await message.answer("❌ Формат неверный. Введи так: `ИИН пароль`", parse_mode="Markdown")
            return

        iin, password = parts
        encrypted_login = fernet.encrypt(iin.encode()).decode()
        encrypted_pass = fernet.encrypt(password.encode()).decode()

        async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO users (user_id, login, password)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        login = EXCLUDED.login,
                        password = EXCLUDED.password;
                """, (message.from_user.id, encrypted_login, encrypted_pass))
                await conn.commit()

        await message.answer("✅ Данные сохранены! Теперь выбери предмет:")
        await message.answer(
            "📚 Доступные журналы:\nPython, БД, ИКТ, Графика, Физра, Экономика\n\n✏️ Напиши предмет, чтобы получить скриншот."
        )
        return

    # Если пользователь уже есть — обрабатываем как предмет
    subject = text.strip()
    login = fernet.decrypt(row[0].encode()).decode()
    password = fernet.decrypt(row[1].encode()).decode()

    await message.answer("⌛ Получаю скриншот, подожди немного...")

    try:
        path = get_screenshot(login, password, subject)
        
        if path == "login_failed":
            await message.answer("❌ Неверный ИИН или пароль. Проверь и попробуй снова.")
            return
        elif path == "wrong_subject":
            await message.answer("⚠️ Такого предмета нет. Проверь название.")
            return
        elif not path:
            await message.answer("⚠️ Ошибка при получении данных. Попробуй позже.")
            return


        await message.answer_photo(photo=open(path, "rb"), caption=f"📸 Журнал по предмету {subject}")
    except Exception as e:
        logging.error(f"Ошибка при получении скриншота: {e}")
        await message.answer("⚠️ Произошла ошибка при загрузке журнала.")

# ──────────────────────────────────────────────
# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
