import os
import asyncio
import logging
import asyncpg
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# ──────────────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")  # например: https://your-app-name.up.railway.app
DB_URL = os.getenv("DATABASE_URL")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ──────────────────────────────────────
# Подключение к базе данных PostgreSQL (Neon.tech)
async def init_db():
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            login TEXT,
            password TEXT
        )
    """)
    await conn.close()

asyncio.run(init_db())

# ──────────────────────────────────────
# Меню клавиатура
def menu_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Журналы", callback_data="journals")],
        [InlineKeyboardButton(text="🔐 Аккаунт", callback_data="account")],
        [InlineKeyboardButton(text="🚪 Выйти", callback_data="logout")]
    ])
    return kb

# ──────────────────────────────────────
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот ALIVE helper.\n"
        "Введи логин и пароль, чтобы получать скриншоты журналов.\n\n"
        "Команды:\n"
        "• /login — авторизация\n"
        "• /account — просмотр учётки\n"
        "• /journals — открыть журналы\n"
        "• /logout — удалить данные\n\n"
        "Создал: Сычёв Александр ПО2408",
        reply_markup=menu_kb()
    )

# ──────────────────────────────────────
@dp.message(Command("login"))
async def login_cmd(message: types.Message):
    await message.answer("🔑 Введи логин (в формате: логин пароль):")

@dp.message()
async def save_login(message: types.Message):
    try:
        login, password = message.text.split(" ")
        conn = await asyncpg.connect(DB_URL)
        await conn.execute("""
            INSERT INTO users (user_id, login, password)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE SET login=$2, password=$3
        """, message.from_user.id, login, password)
        await conn.close()
        await message.answer("✅ Логин и пароль сохранены!")
    except Exception:
        await message.answer("⚠️ Неверный формат. Введи: логин пароль")

# ──────────────────────────────────────
@dp.callback_query(lambda c: c.data == "journals")
async def journals(callback: types.CallbackQuery):
    await callback.message.answer("🕐 Загружаю журнал...")
    await take_screenshot(callback)

async def take_screenshot(callback: types.CallbackQuery):
    conn = await asyncpg.connect(DB_URL)
    user = await conn.fetchrow("SELECT login, password FROM users WHERE user_id=$1", callback.from_user.id)
    await conn.close()
    if not user:
        await callback.message.answer("❌ Ты не авторизован. Используй /login")
        return

    login, password = user["login"], user["password"]
    screenshot_path = f"screenshot_{callback.from_user.id}.png"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto("https://college.snation.kz/kz/tko/login")
            await page.fill("#loginform-username", login)
            await page.fill("#loginform-password", password)
            await page.click("button[type=submit]")
            await page.wait_for_timeout(4000)
            await page.screenshot(path=screenshot_path)
            await browser.close()

        await callback.message.answer_photo(photo=open(screenshot_path, "rb"), caption="📸 Журнал успешно загружен!")
        os.remove(screenshot_path)
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка при загрузке журнала:\n{e}")

# ──────────────────────────────────────
# Веб-сервер и вебхук
app = web.Application()

async def on_startup(app):
    await bot.set_webhook(f"{BASE_URL}/webhook/{TOKEN}")
    print("✅ Webhook установлен и база готова!")

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()
    print("🛑 Webhook удалён и сессия закрыта")

app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=f"/webhook/{TOKEN}")
setup_application(app, dp, bot=bot)

PORT = int(os.getenv("PORT", 8080))
web.run_app(app, host="0.0.0.0", port=PORT)
