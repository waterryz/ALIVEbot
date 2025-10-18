import os
import asyncio
import logging
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import subprocess

# ──────────────────────────────────────────────
# 🔧 Настройки
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook/{TOKEN}"
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ──────────────────────────────────────────────
# 📦 Подключение к базе данных
async def create_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            login TEXT,
            password TEXT
        )
    """)
    await conn.close()
    logger.info("✅ Таблица users создана или уже существует.")

async def get_user(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT login, password FROM users WHERE user_id=$1", user_id)
    await conn.close()
    return row

async def save_user(user_id, login, password):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        INSERT INTO users (user_id, login, password)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id) DO UPDATE SET login=$2, password=$3
    """, user_id, login, password)
    await conn.close()

async def delete_user(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM users WHERE user_id=$1", user_id)
    await conn.close()

# ──────────────────────────────────────────────
# ⚙️ Проверка и автоустановка Chromium
async def ensure_playwright_installed():
    chrome_path = "/opt/render/.cache/ms-playwright/chromium-1140/chrome-linux/chrome"
    if not os.path.exists(chrome_path):
        logger.warning("⚠️ Chromium не найден, устанавливаю автоматически...")
        try:
            subprocess.run(
                ["python", "-m", "playwright", "install", "chromium", "--with-deps"],
                check=True
            )
            logger.info("✅ Chromium установлен успешно.")
        except Exception as e:
            logger.error(f"❌ Ошибка при установке Chromium: {e}")

# ──────────────────────────────────────────────
# 📸 Скриншот страницы журнала
async def make_screenshot(login, password, url, path):
    await ensure_playwright_installed()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://college.snation.kz/kz/tko/login")
        await page.fill("#loginform-username", login)
        await page.fill("#loginform-password", password)
        await page.click("button[type=submit]")
        await page.wait_for_timeout(2000)
        await page.goto(url)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=path, full_page=True)
        await browser.close()

# ──────────────────────────────────────────────
# 🧠 Команды
@dp.message(CommandStart())
async def start(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔐 Войти", callback_data="login")
    kb.button(text="📘 Журналы", callback_data="journals")
    kb.button(text="👤 Аккаунт", callback_data="account")
    kb.button(text="🚪 Выйти", callback_data="logout")
    kb.adjust(1)

    await message.answer(
        "👋 Привет! Я бот ALIVE helper.\n"
        "Введи логин и пароль, чтобы получать скриншоты журналов.\n\n"
        "Команды:\n"
        "• /login — авторизация\n"
        "• /account — просмотр учётки\n"
        "• /journals — открыть журналы\n"
        "• /logout — удалить данные\n\n"
        "Создал: Сычёв Александр ПО2408",
        reply_markup=kb.as_markup()
    )

@dp.message(Command("login"))
async def cmd_login(message: types.Message):
    await message.answer("🧾 Введи логин SmartNation:")
    dp.data = {"state": "awaiting_login"}

@dp.message(Command("logout"))
async def cmd_logout(message: types.Message):
    await delete_user(message.from_user.id)
    await message.answer("🚪 Данные удалены. Чтобы снова войти — /login")

@dp.message(Command("account"))
async def cmd_account(message: types.Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Аккаунт не найден. Используй /login")
        return
    await message.answer(f"👤 SmartNation:\nЛогин: <code>{user['login']}</code>\nПароль: ••••••••", parse_mode="HTML")

@dp.message(Command("journals"))
async def cmd_journals(message: types.Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала авторизуйся через /login")
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="💻 Python", callback_data="journal_python")
    kb.button(text="🎨 Графика", callback_data="journal_graphics")
    kb.button(text="💾 БД", callback_data="journal_db")
    kb.button(text="🧠 ИКТ", callback_data="journal_ict")
    kb.button(text="🏃 Физра", callback_data="journal_pe")
    kb.adjust(1)

    await message.answer("📚 Выбери журнал:", reply_markup=kb.as_markup())

# ──────────────────────────────────────────────
# 🔘 Коллбэки
@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("❌ Сначала авторизуйся через /login")
        return

    journals = {
        "journal_python": "https://college.snation.kz/kz/tko/control/journals/873776",
        "journal_graphics": "https://college.snation.kz/kz/tko/control/journals/873751",
        "journal_db": "https://college.snation.kz/kz/tko/control/journals/873763",
        "journal_ict": "https://college.snation.kz/kz/tko/control/journals/873757",
        "journal_pe": "https://college.snation.kz/kz/tko/control/journals/873753",
    }

    if callback.data in journals:
        url = journals[callback.data]
        path = f"screenshot_{callback.from_user.id}.png"
        await callback.message.answer("⏳ Захожу в SmartNation...")

        try:
            await make_screenshot(user["login"], user["password"], url, path)
            await callback.message.answer_photo(open(path, "rb"))
            os.remove(path)
        except Exception as e:
            await callback.message.answer(f"⚠️ Ошибка при загрузке журнала:\n{e}")

# ──────────────────────────────────────────────
# 🌐 Webhook-сервер
async def on_start(app):
    await create_db()
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("✅ Webhook установлен и база готова!")

async def on_shutdown(app):
    await bot.delete_webhook()
    logger.info("🛑 Webhook удалён и сессия закрыта")

app = web.Application()
app.router.add_post(f"/webhook/{TOKEN}", dp.webhook_handler)
app.on_startup.append(on_start)
app.on_shutdown.append(on_shutdown)

def main():
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
