import os
import asyncio
import logging
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ───────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", 8080))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db_pool = None

# ───────────────────────────────
# База данных
async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                login TEXT,
                password TEXT
            )
        """)

# ───────────────────────────────
# Клавиатура
def menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔐 Войти", callback_data="login")
    kb.button(text="📚 Журналы", callback_data="journals")
    kb.button(text="👤 Аккаунт", callback_data="account")
    kb.button(text="📤 Выйти", callback_data="logout")
    kb.adjust(1)
    return kb.as_markup()

# ───────────────────────────────
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

# ───────────────────────────────
# Логин
@dp.message(Command("login"))
async def cmd_login(message: types.Message):
    await message.answer("🔑 Введи логин и пароль (через пробел):")

@dp.message()
async def handle_login(message: types.Message):
    parts = message.text.strip().split()
    if len(parts) != 2:
        return
    login, password = parts
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, login, password)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id)
            DO UPDATE SET login=$2, password=$3
        """, message.from_user.id, login, password)
    await message.answer("✅ Логин и пароль сохранены!")

# ───────────────────────────────
# Просмотр учётки
@dp.message(Command("account"))
async def account(message: types.Message):
    async with db_pool.acquire() as conn:
        data = await conn.fetchrow("SELECT login, password FROM users WHERE user_id=$1", message.from_user.id)
        if data:
            await message.answer(f"👤 SmartNation аккаунт:\nЛогин: {data['login']}\nПароль: {'*' * len(data['password'])}")
        else:
            await message.answer("⚠️ Ты ещё не вошёл! Используй /login")

# ───────────────────────────────
# Удаление данных
@dp.message(Command("logout"))
async def logout(message: types.Message):
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE user_id=$1", message.from_user.id)
    await message.answer("📤 Данные удалены!")

# ───────────────────────────────
# Скрин журналов
@dp.message(Command("journals"))
async def journals(message: types.Message):
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT login, password FROM users WHERE user_id=$1", message.from_user.id)
        if not user:
            await message.answer("⚠️ Сначала войди через /login")
            return

    await message.answer("⏳ Загружаю журнал...")
    screenshot_path = f"screenshot_{message.from_user.id}.png"

    try:
        await asyncio.to_thread(make_screenshot, user["login"], user["password"], screenshot_path)
        await message.answer_photo(photo=open(screenshot_path, "rb"), caption="📸 Готово!")
        os.remove(screenshot_path)
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при загрузке журнала: {e}")

# ───────────────────────────────
# Selenium логин и скрин
def make_screenshot(login, password, path):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get("https://college.snation.kz/kz/tko/login")
        driver.find_element("name", "LoginForm[username]").send_keys(login)
        driver.find_element("name", "LoginForm[password]").send_keys(password)
        driver.find_element("xpath", "//button[@type='submit']").click()
        asyncio.sleep(2)
        driver.get("https://college.snation.kz/kz/tko/control/journals")
        asyncio.sleep(2)
        driver.save_screenshot(path)
    finally:
        driver.quit()

# ───────────────────────────────
# Webhook сервер
async def on_startup(app):
    await init_db()
    await bot.set_webhook(f"{BASE_URL}/webhook/{BOT_TOKEN}")
    logging.info("✅ Webhook установлен и база готова!")

async def on_shutdown(app):
    await bot.delete_webhook()
    await db_pool.close()
    logging.info("🛑 Webhook удалён и база закрыта!")

async def handle_webhook(request):
    data = await request.json()
    await dp.feed_update(bot, types.Update(**data))
    return web.Response()

# ───────────────────────────────
app = web.Application()
app.router.add_post(f"/webhook/{BOT_TOKEN}", handle_webhook)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

# ───────────────────────────────
if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
