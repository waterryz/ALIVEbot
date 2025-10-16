import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from flask import Flask, request
from parser import fetch_subject_grades

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")
PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

COOKIE_FILE = "cookies.json"
if not os.path.exists(COOKIE_FILE):
    with open(COOKIE_FILE, "w") as f:
        json.dump({}, f)

def save_cookie(user_id, cookie_str):
    with open(COOKIE_FILE, "r+") as f:
        data = json.load(f)
        data[str(user_id)] = cookie_str
        f.seek(0)
        json.dump(data, f)
        f.truncate()

def load_cookie(user_id):
    with open(COOKIE_FILE, "r") as f:
        data = json.load(f)
        return data.get(str(user_id))

subjects = {
    "Python 🐍": "873776",
    "Графика 🎨": "873751",
    "Физра 🏋️": "873753",
    "Базы данных 💾": "873763",
    "ИКТ 💻": "873757"
}

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Привет! Это бот SmartNation College.

"
        "Отправь cookie строкой:
"
        "`college_session=...; XSRF-TOKEN=...; region_id=...`

"
        "После этого выбери предмет из меню.",
        parse_mode="Markdown"
    )

@dp.message()
async def handle_cookie(message: types.Message):
    cookie_str = message.text.strip()
    user_id = message.from_user.id
    save_cookie(user_id, cookie_str)

    builder = InlineKeyboardBuilder()
    for name in subjects.keys():
        builder.button(text=name, callback_data=name)
    builder.adjust(1)

    await message.answer("✅ Cookie сохранены!
Выбери предмет:", reply_markup=builder.as_markup())

@dp.callback_query()
async def handle_subject(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cookie_str = load_cookie(user_id)

    if not cookie_str:
        await callback.message.answer("⚠️ Отправь cookie сначала командой /start.")
        return

    subj_name = callback.data
    subj_id = subjects[subj_name]

    await callback.message.answer(f"📡 Загружаю оценки по предмету *{subj_name}*...", parse_mode="Markdown")

    grades_text = await fetch_subject_grades(subj_id, cookie_str)
    await callback.message.answer(grades_text, parse_mode="Markdown")

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = types.Update.model_validate(await request.get_json())
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.route("/")
def index():
    return "✅ SmartNation Bot работает!"

async def on_startup():
    await bot.set_webhook(f"{APP_URL}/webhook/{BOT_TOKEN}")
    print(f"✅ Webhook установлен: {APP_URL}/webhook/{BOT_TOKEN}")

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(on_startup())
    run_flask()
