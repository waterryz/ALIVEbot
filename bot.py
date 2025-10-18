import os
import logging
import asyncpg
from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from playwright.async_api import async_playwright

# ---------------------- ENV / BASE ----------------------
load_dotenv()

BOT_TOKEN   = os.getenv("BOT_TOKEN")
DATABASE_URL= os.getenv("DATABASE_URL")
BASE_URL    = os.getenv("BASE_URL")  # публичный URL Railway
PORT        = int(os.getenv("PORT", 8080))

logging.basicConfig(level=logging.INFO)
bot = Bot(BOT_TOKEN)
dp  = Dispatcher()

# ---------------------- DB ----------------------
async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            login   TEXT,
            password TEXT
        );
    """)
    await conn.close()

async def save_user(user_id: int, login: str, password: str):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        INSERT INTO users (user_id, login, password)
        VALUES ($1,$2,$3)
        ON CONFLICT (user_id)
        DO UPDATE SET login = EXCLUDED.login, password = EXCLUDED.password;
    """, user_id, login, password)
    await conn.close()

async def get_user(user_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT login, password FROM users WHERE user_id=$1", user_id)
    await conn.close()
    return row

async def delete_user(user_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM users WHERE user_id=$1", user_id)
    await conn.close()

# ---------------------- UI ----------------------
def menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Войти",    callback_data="cb_login")],
        [InlineKeyboardButton(text="📚 Журналы",  callback_data="cb_journals")],
        [InlineKeyboardButton(text="👤 Аккаунт",  callback_data="cb_account")],
        [InlineKeyboardButton(text="📩 Выйти",    callback_data="cb_logout")],
    ])

def journals_kb() -> InlineKeyboardMarkup:
    # при необходимости добавишь другие журналы/урлы
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💻 Python", callback_data="jrnl|https://college.snation.kz/kz/tko/control/journals/873776")],
    ])

# ---------------------- FSM ----------------------
class LoginFSM(StatesGroup):
    waiting_login   = State()  # ИИН
    waiting_password= State()  # Пароль

# ---------------------- START ----------------------
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

# ---------------------- LOGIN (команда) ----------------------
@dp.message(Command("login"))
async def cmd_login(message: types.Message, state: FSMContext):
    await state.set_state(LoginFSM.waiting_login)
    await message.answer("🔑 Введи ИИН:")

@dp.message(LoginFSM.waiting_login)
async def login_step_login(message: types.Message, state: FSMContext):
    await state.update_data(login=message.text.strip())
    await state.set_state(LoginFSM.waiting_password)
    await message.answer("🔒 Теперь введи пароль:")

@dp.message(LoginFSM.waiting_password)
async def login_step_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    login = data.get("login", "").strip()
    password = message.text.strip()
    await save_user(message.from_user.id, login, password)
    await state.clear()
    await message.answer("✅ Логин и пароль сохранены!", reply_markup=menu_kb())

# ---------------------- LOGIN (кнопка) ----------------------
@dp.callback_query(F.data == "cb_login")
async def cb_login(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("🔑 Введи ИИН:")
    await state.set_state(LoginFSM.waiting_login)
    await call.answer()

# ---------------------- ACCOUNT ----------------------
@dp.message(Command("account"))
async def cmd_account(message: types.Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("⚠️ Ты ещё не вошёл. Нажми «🔐 Войти» или команда /login.")
        return
    masked = "•" * max(0, len(user["password"]) - 2)
    pwd_view = (user["password"][:2] + masked) if user["password"] else "—"
    await message.answer(
        f"👤 SmartNation аккаунт:\nЛогин: <code>{user['login']}</code>\nПароль: <code>{pwd_view}</code>",
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "cb_account")
async def cb_account(call: types.CallbackQuery):
    user = await get_user(call.from_user.id)
    if not user:
        await call.message.answer("⚠️ Ты ещё не вошёл. Нажми «🔐 Войти» или команда /login.")
    else:
        masked = "•" * max(0, len(user["password"]) - 2)
        pwd_view = (user["password"][:2] + masked) if user["password"] else "—"
        await call.message.answer(
            f"👤 SmartNation аккаунт:\nЛогин: <code>{user['login']}</code>\nПароль: <code>{pwd_view}</code>",
            parse_mode="HTML"
        )
    await call.answer()

# ---------------------- LOGOUT ----------------------
@dp.message(Command("logout"))
async def cmd_logout(message: types.Message):
    await delete_user(message.from_user.id)
    await message.answer("🗑️ Данные удалены.", reply_markup=menu_kb())

@dp.callback_query(F.data == "cb_logout")
async def cb_logout(call: types.CallbackQuery):
    await delete_user(call.from_user.id)
    await call.message.answer("🗑️ Данные удалены.", reply_markup=menu_kb())
    await call.answer()

# ---------------------- JOURNALS ----------------------
@dp.message(Command("journals"))
async def cmd_journals(message: types.Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("⚠️ Сначала войди: /login или кнопка «🔐 Войти».")
        return
    await message.answer("📚 Выбери журнал:", reply_markup=journals_kb())

@dp.callback_query(F.data == "cb_journals")
async def cb_journals(call: types.CallbackQuery):
    user = await get_user(call.from_user.id)
    if not user:
        await call.message.answer("⚠️ Сначала войди: /login или кнопка «🔐 Войти».")
    else:
        await call.message.answer("📚 Выбери журнал:", reply_markup=journals_kb())
    await call.answer()

@dp.callback_query(F.data.startswith("jrnl|"))
async def cb_open_journal(call: types.CallbackQuery):
    _, url = call.data.split("|", 1)
    user = await get_user(call.from_user.id)
    if not user:
        await call.message.answer("⚠️ Сначала войди: /login.")
        await call.answer()
        return

    await call.message.answer("⏳ Захожу в SmartNation и загружаю журнал...")
    try:
        photo_path = await make_screenshot_with_playwright(
            login=user["login"], password=user["password"], journal_url=url,
            user_id=call.from_user.id
        )
        with open(photo_path, "rb") as ph:
            await call.message.answer_photo(ph, caption="📄 Готово!")
    except Exception as e:
        await call.message.answer(f"⚠️ Ошибка при загрузке журнала:\n<code>{e}</code>", parse_mode="HTML")
        logging.exception("Journal error")
    finally:
        try:
            if os.path.exists(photo_path):
                os.remove(photo_path)
        except Exception:
            pass
    await call.answer()

# ---------------------- PLAYWRIGHT SCRAPER ----------------------
LOGIN_URL = "https://college.snation.kz/kz/tko/login"

async def make_screenshot_with_playwright(login: str, password: str, journal_url: str, user_id: int) -> str:
    """
    Логинится на SmartNation и делает скрин указанного журнала.
    Требует: playwright install chromium --with-deps
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox", "--disable-setuid-sandbox",
                "--disable-dev-shm-usage", "--disable-gpu",
            ],
        )
        ctx = await browser.new_context(viewport={"width":1280,"height":900})
        page = await ctx.new_page()

        # Login page
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)
        await page.fill("#loginform-username", login, timeout=30_000)
        await page.fill("#loginform-password", password, timeout=30_000)
        # есть разные верстки — пробуем по name/role/css
        clicked = False
        for sel in [
            "button[name='login-button']",
            "button[type='submit']",
            "text=Кіру",
            "text=Войти",
        ]:
            try:
                await page.click(sel, timeout=2_000)
                clicked = True
                break
            except Exception:
                pass
        if not clicked:
            raise RuntimeError("Не найден submit на форме логина")

        # даем времени на редирект
        await page.wait_for_timeout(2500)

        # журнал
        await page.goto(journal_url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(2000)

        out_path = f"journal_{user_id}.png"
        await page.screenshot(path=out_path, full_page=True)

        await ctx.close()
        await browser.close()
        return out_path

# ---------------------- WEBHOOK SERVER ----------------------
async def on_startup(app: web.Application):
    await init_db()
    webhook_url = f"{BASE_URL}/webhook/{BOT_TOKEN}"
    await bot.set_webhook(webhook_url)
    logging.info(f"✅ Вебхук установлен: {webhook_url}")

async def on_shutdown(app: web.Application):
    await bot.delete_webhook()
    logging.info("🛑 Вебхук удалён")

async def handle_webhook(request: web.Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return web.Response(text="ok")

app = web.Application()
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)
app.router.add_post(f"/webhook/{BOT_TOKEN}", handle_webhook)
app.router.add_get("/", lambda _: web.Response(text="ALIVE helper is running ✅"))

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
