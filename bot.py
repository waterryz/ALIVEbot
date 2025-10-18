import os
import logging
import asyncio
import pg8000
import subprocess
import aiohttp
import zipfile
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from html import escape

# ──────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", 10000))

PG_USER = "neondb_owner"
PG_PASSWORD = "npg_wh0zI9NHUVBe"
PG_HOST = "ep-lively-river-agz7orw8-pooler.c-2.eu-central-1.aws.neon.tech"
PG_DB = "neondb"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# ──────────────────────────────
def get_conn():
    return pg8000.connect(
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST,
        database=PG_DB,
        port=5432,
        ssl_context=True
    )

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            login TEXT,
            password TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def save_user(user_id, login, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, login, password)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET login = EXCLUDED.login, password = EXCLUDED.password;
    """, (user_id, login, password))
    conn.commit()
    cur.close()
    conn.close()

def get_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT login, password FROM users WHERE user_id = %s;", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {"login": row[0], "password": row[1]}

def delete_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id = %s;", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

# ──────────────────────────────
def menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Войти", callback_data="login")],
        [InlineKeyboardButton(text="📘 Журналы", callback_data="journals")],
        [InlineKeyboardButton(text="👤 Аккаунт", callback_data="account")],
        [InlineKeyboardButton(text="🚪 Выйти", callback_data="logout")]
    ])

def journals_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💻 Python", callback_data="journal_python")],
        [InlineKeyboardButton(text="🎨 Графика", callback_data="journal_graphics")],
        [InlineKeyboardButton(text="🗄️ БД", callback_data="journal_bd")],
        [InlineKeyboardButton(text="🧠 ИКТ", callback_data="journal_ikt")],
        [InlineKeyboardButton(text="🏃 Физ-ра", callback_data="journal_pe")]
    ])

# ──────────────────────────────
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
        "Создал: Cычёв Александр ПО2408",
        reply_markup=menu_kb()
    )

# ──────────────────────────────
JOURNALS = {
    "python": "https://college.snation.kz/kz/tko/control/journals/873776",
    "graphics": "https://college.snation.kz/kz/tko/control/journals/873751",
    "bd": "https://college.snation.kz/kz/tko/control/journals/873763",
    "ikt": "https://college.snation.kz/kz/tko/control/journals/873757",
    "pe": "https://college.snation.kz/kz/tko/control/journals/873753"
}

# ──────────────────────────────
CHROME_PATH = "./chrome/chrome-linux/chrome"
CHROME_ZIP = "https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/1140/chrome-linux.zip"

async def ensure_chromium():
    """Скачивает portable Chromium при первом запуске."""
    if os.path.exists(CHROME_PATH):
        return
    os.makedirs("chrome", exist_ok=True)
    zip_path = "chrome/chrome.zip"

    logger.info("⬇️ Скачиваю Chromium portable...")
    async with aiohttp.ClientSession() as session:
        async with session.get(CHROME_ZIP) as resp:
            with open(zip_path, "wb") as f:
                while True:
                    chunk = await resp.content.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall("chrome")
    os.remove(zip_path)
    logger.info("✅ Chromium готов!")

async def make_screenshot(login, password, url, path):
    await ensure_chromium()
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=CHROME_PATH
        )
        page = await browser.new_page()

        await page.goto("https://college.snation.kz/kz/tko/login")
        await page.fill("input[aria-label='ЖСН']", login)
        await page.fill("input[aria-label='Құпия сөз']", password)
        await page.click("button:has-text('Жүйеге кіру')")

        await page.wait_for_load_state("networkidle")
        await page.goto(url)
        await page.wait_for_timeout(2000)

        await page.screenshot(path=path, full_page=True)
        await browser.close()

# ──────────────────────────────
@dp.callback_query(F.data.startswith("journal_"))
async def cb_journal(callback: types.CallbackQuery):
    subj = callback.data.replace("journal_", "")
    row = get_user(callback.from_user.id)
    if not row:
        await callback.message.answer("❌ Сначала введи логин и пароль: /login")
        return

    login = row["login"]
    password = row["password"]
    url = JOURNALS[subj]
    path = f"{callback.from_user.id}_{subj}.png"

    await callback.message.answer("⏳ Захожу в SmartNation...")

    try:
        await make_screenshot(login, password, url, path)
        await bot.send_photo(callback.from_user.id, open(path, "rb"))
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка при загрузке журнала:\n<code>{escape(str(e))}</code>")
    finally:
        if os.path.exists(path):
            os.remove(path)

# ──────────────────────────────
async def handle(request: web.Request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception("Ошибка webhook: %s", e)
        return web.Response(status=500, text="Internal Server Error")
    return web.Response(status=200, text="ok")

async def root(request):
    return web.Response(text="Bot is running ✅")

async def on_start(app: web.Application):
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("✅ Webhook установлен и база готова!")
    await ensure_chromium()

def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)
    app.router.add_get("/", root)
    app.on_startup.append(on_start)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
