import os
import asyncio
import logging
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================
# КНОПКИ
# ==========================
def menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Войти", callback_data="login")],
        [InlineKeyboardButton(text="📚 Журналы", callback_data="journals")],
        [InlineKeyboardButton(text="👤 Аккаунт", callback_data="account")],
        [InlineKeyboardButton(text="📩 Выйти", callback_data="logout")]
    ])

# ==========================
# БАЗА
# ==========================
async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        login TEXT,
        password TEXT
    )
    """)
    await conn.close()

async def save_user(user_id, login, password):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
    INSERT INTO users (user_id, login, password)
    VALUES ($1, $2, $3)
    ON CONFLICT (user_id) DO UPDATE SET login = EXCLUDED.login, password = EXCLUDED.password
    """, user_id, login, password)
    await conn.close()

async def get_user(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
    await conn.close()
    return user

async def delete_user(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM users WHERE user_id=$1", user_id)
    await conn.close()

# ==========================
# СТАРТ
# ==========================
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

# ==========================
# ЛОГИН
# ==========================
@dp.message(Command("login"))
async def ask_login(message: types.Message):
    await message.answer("🔑 Введи ИИН:")
    dp.login_step = True
    dp.password_step = False

@dp.message()
async def handle_input(message: types.Message):
    user_id = message.from_user.id

    if getattr(dp, "login_step", False):
        dp.temp_login = message.text.strip()
        dp.login_step = False
        dp.password_step = True
        await message.answer("🔒 Теперь введи пароль:")
        return

    if getattr(dp, "password_step", False):
        dp.temp_password = message.text.strip()
        dp.password_step = False
        await save_user(user_id, dp.temp_login, dp.temp_password)
        await message.answer("✅ Логин и пароль сохранены!", reply_markup=menu_kb())

# ==========================
# АККАУНТ
# ==========================
@dp.message(Command("account"))
async def account_info(message: types.Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("⚠️ Ты ещё не вошёл! Используй /login.")
    else:
        masked = user["password"][:2] + "•" * (len(user["password"]) - 2)
        await message.answer(f"👤 SmartNation аккаунт:\nЛогин: `{user['login']}`\nПароль: `{masked}`", parse_mode="Markdown")

# ==========================
# УДАЛЕНИЕ ДАННЫХ
# ==========================
@dp.message(Command("logout"))
async def logout(message: types.Message):
    await delete_user(message.from_user.id)
    await message.answer("🗑️ Данные удалены!", reply_markup=menu_kb())

# ==========================
# ЗАГРУЗКА ЖУРНАЛА
# ==========================
@dp.message(Command("journals"))
async def journals(message: types.Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("⚠️ Сначала войди через /login.")
        return

    await message.answer("⏳ Загружаю журнал, подожди немного...")

    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
        driver.get("https://college.snation.kz/kz/tko/login")

        driver.find_element("id", "loginform-username").send_keys(user["login"])
        driver.find_element("id", "loginform-password").send_keys(user["password"])
        driver.find_element("name", "login-button").click()

        await asyncio.sleep(5)
        driver.get("https://college.snation.kz/kz/tko/control/journals/873776")
        await asyncio.sleep(5)

        screenshot_path = f"screenshot_{message.from_user.id}.png"
        driver.save_screenshot(screenshot_path)
        driver.quit()

        with open(screenshot_path, "rb") as photo:
            await message.answer_photo(photo, caption="📄 Вот твой журнал!")
        os.remove(screenshot_path)

    except Exception as e:
        await message.answer(f"⚠️ Ошибка при загрузке журнала: {e}")

# ==========================
# ВЕБ-СЕРВЕР
# ==========================
async def on_startup(app):
    await init_db()
    webhook_url = f"{BASE_URL}/webhook/{BOT_TOKEN}"
    await bot.set_webhook(webhook_url)
    logging.info("✅ Вебхук установлен")

async def on_shutdown(app):
    await bot.delete_webhook()
    logging.info("🛑 Вебхук удалён")

app = web.Application()
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)
app.router.add_post(f"/webhook/{BOT_TOKEN}", dp.startup_webhook)
app.router.add_get("/", lambda _: web.Response(text="ALIVE helper is running ✅"))

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
