import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
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
# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Загрузка .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")
DATABASE_URL = os.getenv("DATABASE_URL")
PORT = int(os.getenv("PORT", 10000))

if not TOKEN:
    raise Exception("❌ BOT_TOKEN не найден в Render Environment")
if not DATABASE_URL:
    raise Exception("❌ DATABASE_URL не найден (строка из Neon.tech)")

# ──────────────────────────────────────────────
# Aiogram 3
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# ──────────────────────────────────────────────
# PostgreSQL helpers
def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require", cursor_factory=RealDictCursor)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    login TEXT,
                    password TEXT
                );
            """)
            conn.commit()

def save_user(user_id, login, password):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (user_id, login, password)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET login = EXCLUDED.login, password = EXCLUDED.password;
            """, (user_id, login, password))
            conn.commit()

def get_user(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT login, password FROM users WHERE user_id = %s;", (user_id,))
            return cur.fetchone()

def delete_user(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id = %s;", (user_id,))
            conn.commit()

# ──────────────────────────────────────────────
# FSM для авторизации
class AuthForm(StatesGroup):
    login = State()
    password = State()

# ──────────────────────────────────────────────
# Меню
def menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Войти", callback_data="login")],
        [InlineKeyboardButton(text="👤 Аккаунт", callback_data="account")],
        [InlineKeyboardButton(text="🚪 Выйти", callback_data="logout")]
    ])

# ──────────────────────────────────────────────
# Команды
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот SmartNation.\n"
        "Сохрани логин и пароль, чтобы потом получать скрины журналов.\n\n"
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
async def login_step(message: types.Message, state: FSMContext):
    await state.update_data(login=message.text.strip())
    await state.set_state(AuthForm.password)
    await message.answer("🔒 Теперь введи пароль:")

@dp.message(AuthForm.password)
async def password_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    login = data.get("login")
    password = message.text.strip()
    save_user(message.from_user.id, login, password)
    await state.clear()
    await message.answer("✅ Данные сохранены!")

@dp.message(Command("account"))
async def account_cmd(message: types.Message):
    row = get_user(message.from_user.id)
    if not row:
        await message.answer("❌ Данные не найдены. Используй /login.")
    else:
        masked = "•" * max(8, len(row['password']) // 2)
        await message.answer(
            f"👤 <b>Аккаунт SmartNation</b>\n"
            f"Логин: <code>{row['login']}</code>\n"
            f"Пароль: <code>{masked}</code>"
        )

@dp.message(Command("logout"))
async def logout_cmd(message: types.Message):
    delete_user(message.from_user.id)
    await message.answer("🚪 Данные удалены.")

# ──────────────────────────────────────────────
# Callback кнопки
@dp.callback_query(F.data == "login")
async def cb_login(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Введи логин SmartNation:")
    await state.set_state(AuthForm.login)
    await callback.answer()

@dp.callback_query(F.data == "account")
async def cb_account(callback: types.CallbackQuery):
    row = get_user(callback.from_user.id)
    if not row:
        await callback.message.answer("❌ Нет данных. Используй /login.")
    else:
        masked = "•" * max(8, len(row['password']) // 2)
        await callback.message.answer(
            f"👤 <b>Аккаунт SmartNation</b>\n"
            f"Логин: <code>{row['login']}</code>\n"
            f"Пароль: <code>{masked}</code>"
        )
    await callback.answer()

@dp.callback_query(F.data == "logout")
async def cb_logout(callback: types.CallbackQuery):
    delete_user(callback.from_user.id)
    await callback.message.answer("🚪 Данные удалены.")
    await callback.answer()

# ──────────────────────────────────────────────
# Webhook / сервер
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

async def on_stop(app: web.Application):
    await bot.delete_webhook()
    await bot.session.close()
    logger.info("🛑 Webhook удалён, бот остановлен")

def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)
    app.router.add_get("/", root)
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
