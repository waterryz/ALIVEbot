# -*- coding: utf-8 -*-
import os, time, asyncio, sqlite3
import logging
logging.basicConfig(level=logging.INFO)
from pathlib import Path
from dotenv import load_dotenv
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise Exception("BOT_TOKEN не задан")

WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.getenv("PORT", "10000"))

OUTDIR = Path("screens"); OUTDIR.mkdir(exist_ok=True)

# --- ЖУРНАЛЫ SmartNation (можно добавлять свои) ---
JOURNALS = {
    "Python": "https://college.snation.kz/kz/tko/control/journals/873776",
    "Графика": "https://college.snation.kz/kz/tko/control/journals/873751",
    "Физ-ра": "https://college.snation.kz/kz/tko/control/journals/873753",
    "Базы данных": "https://college.snation.kz/kz/tko/control/journals/873763",
    "ИКТ": "https://college.snation.kz/kz/tko/control/journals/873757",
}

# --- SQLite база для логинов ---
DB = "users.db"
conn = sqlite3.connect(DB, check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    login TEXT,
    password TEXT
)""")
conn.commit()

def save_user(uid, login, password):
    cur.execute("REPLACE INTO users(user_id, login, password) VALUES (?, ?, ?)", (uid, login, password))
    conn.commit()

def get_user(uid):
    cur.execute("SELECT login, password FROM users WHERE user_id=?", (uid,))
    return cur.fetchone()

# --- Telegram бот ---
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(m: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Войти", callback_data="login")],
        [InlineKeyboardButton(text="📚 Показать журналы", callback_data="show_journals")]
    ])
    await m.answer("👋 Привет! Я бот SmartNation.\n\n"
                   "• /login — ввести логин и пароль\n"
                   "• /getscreens — получить скриншот журнала\n\n"
                   "Или выбери действие:", reply_markup=kb)

# --- Авторизация ---
@dp.message(Command("login"))
async def login_cmd(m: types.Message):
    await m.answer("Введи логин SmartNation:")
    dp.message.register(get_login_step, lambda msg: msg.from_user.id == m.from_user.id)

async def get_login_step(m: types.Message):
    login = m.text.strip()
    await m.answer("Теперь введи пароль:")
    dp.message.register(lambda msg: save_login_pass(msg, login), lambda msg: msg.from_user.id == m.from_user.id)

async def save_login_pass(m: types.Message, login):
    password = m.text.strip()
    save_user(m.from_user.id, login, password)
    await m.answer("✅ Логин и пароль сохранены! Теперь используй /getscreens")

# --- Выбор журнала ---
@dp.message(Command("getscreens"))
async def getscreens(m: types.Message):
    creds = get_user(m.from_user.id)
    if not creds:
        await m.answer("⚠️ Сначала введи /login")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=title, callback_data=f"journal|{key}")] for key, title in enumerate(JOURNALS.keys())]
    )
    await m.answer("📘 Выбери журнал:", reply_markup=kb)

# --- Callback: показать выбранный журнал ---
@dp.callback_query(lambda c: c.data.startswith("journal|"))
async def send_journal(c: types.CallbackQuery):
    creds = get_user(c.from_user.id)
    if not creds:
        await c.message.answer("⚠️ Сначала введи /login")
        return
    login, password = creds
    idx = int(c.data.split("|")[1])
    name = list(JOURNALS.keys())[idx]
    url = list(JOURNALS.values())[idx]

    await c.message.answer(f"📄 Загружаю журнал *{name}*...", parse_mode="Markdown")
    try:
        driver = create_logged_driver(login, password)
        path = screenshot_url(driver, url, name)
        driver.quit()
        with open(path, "rb") as f:
            await bot.send_photo(c.from_user.id, f, caption=f"Журнал: {name}")
    except Exception as e:
        await c.message.answer(f"❌ Ошибка: {e}")

# --- Webhook / aiohttp ---
async def handle(req: web.Request):
    data = await req.json()
    await dp.process_update(types.Update(**data))
    return web.Response(status=200)

async def on_start(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print("✅ Webhook установлен:", WEBHOOK_URL)

async def on_stop(app):
    await bot.delete_webhook()
    await bot.session.close()

def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)

    # ✅ добавь GET / чтобы Render и Telegram не ловили 404
    async def root(request):
        return web.Response(text="Bot is running ✅")

    app.router.add_get("/", root)

    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)

    print("🚀 Bot starting on port", PORT)
    web.run_app(app, host="0.0.0.0", port=PORT)


# --- Selenium ---
def create_logged_driver(login, password):
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1200")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    driver.get("https://college.snation.kz/kz/tko/login")
    time.sleep(1)
    driver.find_element(By.NAME, "username").send_keys(login)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    time.sleep(2)
    return driver

def screenshot_url(driver, url, name):
    driver.get(url)
    time.sleep(1.2)
    path = OUTDIR / f"{int(time.time())}_{name}.png"
    driver.save_screenshot(str(path))
    return path

if __name__ == "__main__":
    print("🚀 Запуск бота...")
    main()
