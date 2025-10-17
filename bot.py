import os
import logging
import psycopg
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from cryptography.fernet import Fernet
from aiohttp import web
from parser import get_screenshot

# Настройка логов
logging.basicConfig(level=logging.INFO)

# ─────────────────────────────────────────────
# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")  # https://alivebot-9bjd.onrender.com

if not all([BOT_TOKEN, DATABASE_URL, ENCRYPTION_KEY, WEBHOOK_BASE_URL]):
    raise Exception("❌ Не заданы обязательные переменные окружения")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
fernet = Fernet(ENCRYPTION_KEY)

# ─────────────────────────────────────────────
# Инициализация базы
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
    logging.info("✅ Таблица users готова")

asyncio.run(init_db())

# ─────────────────────────────────────────────
# Команда /start
@dp.message(CommandStart())
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📘 Пример IIN и пароля", callback_data="example")]
    ])
    await message.answer(
        "👋 Привет! Отправь свой ИИН и пароль через пробел\n(пример: `123456789012 1234`)",
        parse_mode="Markdown",
        reply_markup=kb
    )

@dp.callback_query()
async def example(callback: types.CallbackQuery):
    await callback.message.answer("📘 Пример: `123456789012 1234` (IIN и пароль через пробел)", parse_mode="Markdown")
    await callback.answer()

# ─────────────────────────────────────────────
# Основная логика
@dp.message()
async def handle_message(message: types.Message):
    text = message.text.strip()
    parts = text.split()

    # Проверяем, есть ли пользователь в БД
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT login, password FROM users WHERE user_id = %s", (message.from_user.id,))
            user = await cur.fetchone()

    if not user:
        if len(parts) != 2:
            await message.answer("❌ Формат неверный. Введи так: `ИИН пароль`", parse_mode="Markdown")
            return

        iin, password = parts
        enc_login = fernet.encrypt(iin.encode()).decode()
        enc_pass = fernet.encrypt(password.encode()).decode()

        async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO users (user_id, login, password)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        login = EXCLUDED.login,
                        password = EXCLUDED.password;
                """, (message.from_user.id, enc_login, enc_pass))
                await conn.commit()

        await message.answer("✅ Данные сохранены! Теперь выбери предмет:")
        await message.answer("📚 Доступные журналы:\nPython, БД, ИКТ, Графика, Физра, Экономика")
        return

    # Если пользователь уже в БД
    subject = text.strip()
    login = fernet.decrypt(user[0].encode()).decode()
    password = fernet.decrypt(user[1].encode()).decode()

    await message.answer("⌛ Получаю скриншот, подожди немного...")

    path = get_screenshot(login, password, subject)
    if path == "login_failed":
        await message.answer("❌ Неверный ИИН или пароль. Попробуй снова.")
    elif path == "wrong_subject":
        await message.answer("⚠️ Такого предмета нет. Проверь название.")
    elif not path:
        await message.answer("⚠️ Ошибка при получении данных. Попробуй позже.")
    else:
        await message.answer_photo(open(path, "rb"), caption=f"📸 Журнал по предмету {subject}")

# ─────────────────────────────────────────────
# Вебхук
async def on_startup(app):
    webhook_url = f"{WEBHOOK_BASE_URL}/webhook/{BOT_TOKEN}"
    await bot.set_webhook(webhook_url)
    logging.info(f"🌐 Webhook установлен: {webhook_url}")

async def on_shutdown(app):
    await bot.delete_webhook()
    logging.info("🛑 Webhook удалён")

# aiohttp сервер
async def handle_webhook(request):
    update = await request.json()
    await dp.feed_update(bot, types.Update(**update))
    return web.Response()

app = web.Application()
app.router.add_post(f"/webhook/{BOT_TOKEN}", handle_webhook)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
