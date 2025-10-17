import os
import logging
import time
import pg8000
import asyncio
import chromedriver_autoinstaller
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from html import escape

# ──────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────
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
class AuthForm(StatesGroup):
    login = State()
    password = State()

# ──────────────────────────────
def menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Войти", callback_data="login")],
        [InlineKeyboardButton(text="📘 Журналы", callback_data="journals")],
        [InlineKeyboardButton(text="👤 Аккаунт", callback_data="account")],
        [InlineKeyboardButton(text="🚪 Выйти", callback_data="logout")]
    ])

def journals_kb():
    buttons = [
        [InlineKeyboardButton(text="💻 Python", callback_data="journal_python")],
        [InlineKeyboardButton(text="🎨 Графика", callback_data="journal_graphics")],
        [InlineKeyboardButton(text="🗄️ БД", callback_data="journal_bd")],
        [InlineKeyboardButton(text="🧠 ИКТ", callback_data="journal_ikt")],
        [InlineKeyboardButton(text="🏃 Физ-ра", callback_data="journal_pe")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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
@dp.callback_query(F.data == "login")
async def cb_login(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Введи логин (ЖСН):")
    await state.set_state(AuthForm.login)
    await callback.answer()

@dp.callback_query(F.data == "journals")
async def cb_journals(callback: types.CallbackQuery):
    await callback.message.answer("📘 Выбери журнал:", reply_markup=journals_kb())
    await callback.answer()

@dp.callback_query(F.data == "account")
async def cb_account(callback: types.CallbackQuery):
    row = get_user(callback.from_user.id)
    if not row:
        await callback.message.answer("❌ Нет данных. Используй /login.")
    else:
        masked = "•" * max(8, len(row['password']) // 2)
        await callback.message.answer(
            f"👤 <b>SmartNation аккаунт</b>\n"
            f"Логин: <code>{row['login']}</code>\n"
            f"Пароль: <code>{masked}</code>"
        )
    await callback.answer()

@dp.callback_query(F.data == "logout")
async def cb_logout(callback: types.CallbackQuery):
    delete_user(callback.from_user.id)
    await callback.message.answer("🚪 Данные удалены.")
    await callback.answer()

# ──────────────────────────────
JOURNALS = {
    "python": "https://college.snation.kz/kz/tko/control/journals/873776",
    "graphics": "https://college.snation.kz/kz/tko/control/journals/873751",
    "bd": "https://college.snation.kz/kz/tko/control/journals/873763",
    "ikt": "https://college.snation.kz/kz/tko/control/journals/873757",
    "pe": "https://college.snation.kz/kz/tko/control/journals/873753"
}

# ──────────────────────────────
def make_screenshot(login, password, url, path):
    # Устанавливаем chromium автоматически
    chromedriver_autoinstaller.install()

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)

    driver.get("https://college.snation.kz/kz/tko/login")

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[aria-label='ЖСН']"))
        )

        driver.find_element(By.CSS_SELECTOR, "input[aria-label='ЖСН']").send_keys(login)
        driver.find_element(By.CSS_SELECTOR, "input[aria-label='Құпия сөз']").send_keys(password)
        driver.find_element(By.XPATH, "//button[contains(., 'Жүйеге кіру')]").click()

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "sn-page"))
        )

        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )

        time.sleep(2)
        driver.save_screenshot(path)

    except Exception as e:
        driver.save_screenshot("error.png")
        raise e
    finally:
        driver.quit()

# ──────────────────────────────
@dp.callback_query(F.data.startswith("journal_"))
async def cb_journal(callback: types.CallbackQuery):
    await callback.answer("⏳ Загрузка...")
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
        await asyncio.to_thread(make_screenshot, login, password, url, path)
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
    await bot.set_webhook(f"{WEBHOOK_URL}")
    logger.info("✅ Webhook установлен и база готова!")

def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)
    app.router.add_get("/", root)
    app.on_startup.append(on_start)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
