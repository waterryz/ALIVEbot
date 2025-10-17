import os
import logging
import time
import pg8000
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
from webdriver_manager.chrome import ChromeDriverManager

# ──────────────────────────────
# ЛОГИ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────
# ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", 10000))

PG_USER = "neondb_owner"
PG_PASSWORD = "npg_wh0zI9NHUVBe"
PG_HOST = "ep-lively-river-agz7orw8-pooler.c-2.eu-central-1.aws.neon.tech"
PG_DB = "neondb"

# ──────────────────────────────
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# ──────────────────────────────
# БАЗА ДАННЫХ
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
# FSM (логин и пароль)
class AuthForm(StatesGroup):
    login = State()
    password = State()

# ──────────────────────────────
# КЛАВИАТУРЫ
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
# КОМАНДЫ
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот SmartNation.\n"
        "Введи логин и пароль, чтобы получать скриншоты журналов.\n\n"
        "Команды:\n"
        "• /login — авторизация\n"
        "• /account — просмотр учётки\n"
        "• /journals — открыть журналы\n"
        "• /logout — удалить данные",
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
    await message.answer("✅ Данные сохранены! Теперь напиши /journals")

@dp.message(Command("account"))
async def account_cmd(message: types.Message):
    row = get_user(message.from_user.id)
    if not row:
        await message.answer("❌ Нет данных. Используй /login.")
    else:
        masked = "•" * max(8, len(row['password']) // 2)
        await message.answer(
            f"👤 <b>SmartNation аккаунт</b>\n"
            f"Логин: <code>{row['login']}</code>\n"
            f"Пароль: <code>{masked}</code>"
        )

@dp.message(Command("logout"))
async def logout_cmd(message: types.Message):
    delete_user(message.from_user.id)
    await message.answer("🚪 Данные удалены.")

@dp.message(Command("journals"))
async def journals_cmd(message: types.Message):
    await message.answer("📘 Выбери журнал:", reply_markup=journals_kb())

# ──────────────────────────────
# ССЫЛКИ НА ЖУРНАЛЫ
JOURNALS = {
    "python": "https://college.snation.kz/kz/tko/control/journals/873776",
    "graphics": "https://college.snation.kz/kz/tko/control/journals/873751",
    "bd": "https://college.snation.kz/kz/tko/control/journals/873763",
    "ikt": "https://college.snation.kz/kz/tko/control/journals/873757",
    "pe": "https://college.snation.kz/kz/tko/control/journals/873753"
}

# ──────────────────────────────
# ФУНКЦИЯ СКРИНШОТА
def make_screenshot(login, password, url, path):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    driver.get("https://college.snation.kz/kz/tko/login")

    # логин
    driver.find_element(By.NAME, "login").send_keys(login)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(4)

    # переход в журнал
    driver.get(url)
    time.sleep(5)
    driver.save_screenshot(path)
    driver.quit()

# ──────────────────────────────
# ВЫБОР ЖУРНАЛА
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

    await callback.message.answer("⏳ Загружаю журнал, подожди немного...")

    path = f"{callback.from_user.id}_{subj}.png"
    make_screenshot(login, password, url, path)

    await bot.send_photo(callback.from_user.id, open(path, "rb"))
    os.remove(path)
    await callback.answer()

# ──────────────────────────────
# ВЕБ-СЕРВЕР
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
    logger.info("🛑 Завершение процесса (Render control)")

def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)
    app.router.add_get("/", root)
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
