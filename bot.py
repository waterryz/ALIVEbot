import os
import logging
import asyncio
import asyncpg
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
BASE_URL = os.getenv("BASE_URL", "https://alivebot-production.up.railway.app")
PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# ──────────────────────────────
# Инициализация базы данных
# ──────────────────────────────
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
        ON CONFLICT (user_id) DO UPDATE
        SET login = EXCLUDED.login, password = EXCLUDED.password
    """, user_id, login, password)
    await conn.close()

async def get_user(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT login, password FROM users WHERE user_id=$1", user_id)
    await conn.close()
    return user

async def delete_user(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM users WHERE user_id=$1", user_id)
    await conn.close()

# ──────────────────────────────
# Кнопки меню
# ──────────────────────────────
def menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Войти", callback_data="login")],
        [InlineKeyboardButton(text="📚 Журналы", callback_data="journals")],
        [InlineKeyboardButton(text="👤 Аккаунт", callback_data="account")],
        [InlineKeyboardButton(text="📤 Выйти", callback_data="logout")]
    ])

# ──────────────────────────────
# Приветственное сообщение
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
        "Создал: Сычёв Александр ПО2408",
        reply_markup=menu_kb()
    )

# ──────────────────────────────
# Авторизация: ввод ИИН и пароля
# ──────────────────────────────
user_temp = {}

@dp.message(Command("login"))
async def cmd_login(message: types.Message):
    await message.answer("🔑 Введи ИИН:")
    user_temp[message.from_user.id] = {"step": "login"}

@dp.message()
async def handle_input(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_temp:
        return

    step = user_temp[user_id].get("step")

    if step == "login":
        user_temp[user_id]["login"] = message.text.strip()
        user_temp[user_id]["step"] = "password"
        await message.answer("🔒 Теперь введи пароль:")

    elif step == "password":
        login = user_temp[user_id]["login"]
        password = message.text.strip()
        await save_user(user_id, login, password)
        user_temp.pop(user_id)
        await message.answer("✅ Логин и пароль сохранены!", reply_markup=menu_kb())

# ──────────────────────────────
# Просмотр аккаунта
# ──────────────────────────────
@dp.message(Command("account"))
async def cmd_account(message: types.Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Ты ещё не вошёл. Напиши /login.")
    else:
        await message.answer(
            f"👤 SmartNation аккаунт:\nЛогин: {user['login']}\nПароль: {'*' * len(user['password'])}"
        )

# ──────────────────────────────
# Выход из аккаунта
# ──────────────────────────────
@dp.message(Command("logout"))
async def cmd_logout(message: types.Message):
    await delete_user(message.from_user.id)
    await message.answer("📤 Данные удалены.", reply_markup=menu_kb())

# ──────────────────────────────
# Скриншот журнала через Playwright
# ──────────────────────────────
async def make_screenshot(login, password, url, path):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto("https://college.snation.kz/kz/tko/login", timeout=60000)

        # заполняем поля
        selectors_login = [
            "#loginform-username",
            "input[name='LoginForm[username]']",
            "input[name='username']",
            "input[type='text']"
        ]
        selectors_pass = [
            "#loginform-password",
            "input[name='LoginForm[password]']",
            "input[name='password']",
            "input[type='password']"
        ]

        for sel in selectors_login:
            try:
                await page.fill(sel, login, timeout=5000)
                break
            except Exception:
                pass

        for sel in selectors_pass:
            try:
                await page.fill(sel, password, timeout=5000)
                break
            except Exception:
                pass

        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")
        await page.goto(url, timeout=60000)
        await page.screenshot(path=path, full_page=True)
        await browser.close()

# ──────────────────────────────
# Команда /journals
# ──────────────────────────────
@dp.message(Command("journals"))
async def cmd_journals(message: types.Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("⚠️ Сначала войди с помощью /login.")
        return

    journals = {
        "Python": "https://college.snation.kz/kz/tko/control/journals/873776",
        "Графика": "https://college.snation.kz/kz/tko/control/journals/873751",
        "БД": "https://college.snation.kz/kz/tko/control/journals/873763",
        "ИКТ": "https://college.snation.kz/kz/tko/control/journals/873757",
        "Физра": "https://college.snation.kz/kz/tko/control/journals/873753",
    }

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"journal:{url}")]
        for name, url in journals.items()
    ])

    await message.answer("📚 Выбери журнал:", reply_markup=kb)

@dp.callback_query()
async def cb_journal(callback: types.CallbackQuery):
    if not callback.data.startswith("journal:"):
        return

    url = callback.data.split(":", 1)[1]
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("⚠️ Сначала войди с помощью /login.")
        return

    await callback.message.answer("⏳ Захожу в SmartNation и загружаю журнал...")
    path = f"screenshot_{callback.from_user.id}.png"

    try:
        await make_screenshot(user["login"], user["password"], url, path)
        await callback.message.answer_photo(types.FSInputFile(path))
        os.remove(path)
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка при загрузке журнала:\n{e}")

# ──────────────────────────────
# Webhook & запуск
# ──────────────────────────────
async def on_startup(app):
    await init_db()
    await bot.delete_webhook()
    await bot.set_webhook(f"{BASE_URL}/webhook/{BOT_TOKEN}", drop_pending_updates=True)
    logging.info("✅ Вебхук установлен и база готова!")

async def on_shutdown(app):
    await bot.delete_webhook()
    logging.info("🛑 Вебхук удалён.")

# создаём aiohttp приложение
app = web.Application()
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

# новый хендлер вебхука (без приватных методов)
async def handle_webhook(request):
    update = await request.json()
    await dp.feed_update(bot, types.Update(**update))
    return web.Response(text="ok")

app.router.add_post(f"/webhook/{BOT_TOKEN}", handle_webhook)

# новый хендлер вебхука (без приватных методов)
async def handle_webhook(request):
    update = await request.json()
    await dp.feed_update(bot, types.Update(**update))
    return web.Response(text="ok")

app.router.add_post(f"/webhook/{BOT_TOKEN}", handle_webhook)

# важно зарегистрировать хендлеры колбэков
dp.callback_query.register(cb_journal)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)

