import os
import logging
import asyncpg
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# Логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# ENV
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")
DATABASE_URL = os.getenv("DATABASE_URL")
PORT = int(os.getenv("PORT", 10000))

if not TOKEN:
    raise Exception("❌ BOT_TOKEN не найден")
if not DATABASE_URL:
    raise Exception("❌ DATABASE_URL не найден (Neon connection string)")

# ──────────────────────────────────────────────
# Aiogram
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# ──────────────────────────────────────────────
# FSM для авторизации
class AuthForm(StatesGroup):
    login = State()
    password = State()

# ──────────────────────────────────────────────
# Подключение к Neon PostgreSQL
async def create_db_pool():
    pool = await asyncpg.create_pool(DATABASE_URL, ssl="require")
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            login TEXT,
            password TEXT
        );
        """)
    return pool

pool: asyncpg.Pool = None

# ──────────────────────────────────────────────
# Работа с БД
async def save_user(user_id: int, login: str, password: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, login, password)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id)
            DO UPDATE SET login=$2, password=$3;
        """, user_id, login, password)

async def get_user(user_id: int):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT login, password FROM users WHERE user_id=$1;", user_id)

async def delete_user(user_id: int):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE user_id=$1;", user_id)

# ──────────────────────────────────────────────
# Интерфейс
def menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Войти", callback_data="login")],
        [InlineKeyboardButton(text="👤 Аккаунт", callback_data="account")],
        [InlineKeyboardButton(text="🚪 Выйти", callback_data="logout")]
    ])

# ──────────────────────────────────────────────
# Команды
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот SmartNation.\n"
        "Здесь ты можешь сохранить логин и пароль от SmartNation, чтобы потом бот мог делать скриншоты журналов.\n\n"
        "Команды:\n"
        "• /login — ввести логин и пароль\n"
        "• /account — посмотреть сохранённые данные\n"
        "• /logout — удалить учётку",
        reply_markup=menu_kb()
    )

@dp.message(Command("login"))
async def login_cmd(message: types.Message, state: FSMContext):
    await state.set_state(AuthForm.login)
    await message.answer("✍️ Введи логин SmartNation:")

@dp.message(AuthForm.login)
async def step_login(message: types.Message, state: FSMContext):
    await state.update_data(login=message.text.strip())
    await state.set_state(AuthForm.password)
    await message.answer("🔒 Теперь введи пароль:")

@dp.message(AuthForm.password)
async def step_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    login = data.get("login")
    password = message.text.strip()
    await save_user(message.from_user.id, login, password)
    await state.clear()
    await message.answer("✅ Логин и пароль сохранены!")

@dp.message(Command("account"))
async def account_cmd(message: types.Message):
    row = await get_user(message.from_user.id)
    if not row:
        await message.answer("❌ Данные не найдены. Нажми /login.")
    else:
        masked = "•" * max(8, len(row['password']) // 2)
        await message.answer(
            f"👤 <b>Аккаунт SmartNation</b>\n"
            f"Логин: <code>{row['login']}</code>\nПароль: <code>{masked}</code>"
        )

@dp.message(Command("logout"))
async def logout_cmd(message: types.Message):
    await delete_user(message.from_user.id)
    await message.answer("🚪 Учётка удалена.")

# ──────────────────────────────────────────────
# Inline callbacks
@dp.callback_query(F.data == "login")
async def cb_login(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Введи логин SmartNation:")
    await state.set_state(AuthForm.login)
    await callback.answer()

@dp.callback_query(F.data == "account")
async def cb_account(callback: types.CallbackQuery):
    row = await get_user(callback.from_user.id)
    if not row:
        await callback.message.answer("❌ Нет данных. Используй /login.")
    else:
        masked = "•" * max(8, len(row['password']) // 2)
        await callback.message.answer(
            f"👤 <b>Аккаунт SmartNation</b>\n"
            f"Логин: <code>{row['login']}</code>\nПароль: <code>{masked}</code>"
        )
    await callback.answer()

@dp.callback_query(F.data == "logout")
async def cb_logout(callback: types.CallbackQuery):
    await delete_user(callback.from_user.id)
    await callback.message.answer("🚪 Данные удалены.")
    await callback.answer()

# ──────────────────────────────────────────────
# Webhook и сервер
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
    global pool
    pool = await create_db_pool()
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("✅ Webhook установлен и подключен к БД.")

async def on_stop(app: web.Application):
    await bot.delete_webhook()
    await bot.session.close()
    await pool.close()
    logger.info("🛑 Всё закрыто.")

def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)
    app.router.add_get("/", root)
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
