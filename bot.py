import os
import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from parser import get_screenshot
from db import init_db, save_user, get_user

BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_TOKEN_HERE"
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL", "https://botalive.onrender.com")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

SUBJECTS = ["Python", "БД", "ИКТ", "Графика", "Физра", "Экономика"]

@app.route("/")
def home():
    return "✅ SmartNation Bot работает!"

@app.route(WEBHOOK_PATH, methods=["POST"])
async def webhook():
    update = types.Update.model_validate(request.json, strict=False)
    await dp.feed_update(bot, update)
    return "ok"

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Привет! Введи свой *ИИН и пароль* через пробел:\n\n`123456789012 12345678`",
        parse_mode="Markdown"
    )

@dp.message()
async def handle_login(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()
    user_data = get_user(user_id)

    if not user_data:
        try:
            iin, password = text.split()
            save_user(user_id, iin, password)
            builder = InlineKeyboardBuilder()
            for subj in SUBJECTS:
                builder.button(text=subj, callback_data=subj)
            builder.adjust(2)
            await message.answer("✅ Сохранено! Теперь выбери предмет:", reply_markup=builder.as_markup())
        except ValueError:
            await message.answer("⚠️ Введи ИИН и пароль через пробел.")
    else:
        await message.answer("📚 Выбери предмет из списка ниже:")

@dp.callback_query()
async def handle_subject(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    if not user:
        await callback.message.answer("⚠️ Сначала введи ИИН и пароль.")
        return

    iin, password = user
    subject = callback.data
    await callback.message.answer(f"📸 Загружаю журнал: {subject}...")

    path = get_screenshot(iin, password, subject)
    if not path:
        await callback.message.answer("❌ Не удалось войти или загрузить журнал.")
        return

    await bot.send_photo(chat_id=user_id, photo=open(path, "rb"))
    await callback.message.answer("✅ Готово!")

async def on_startup():
    init_db()
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Вебхук установлен: {WEBHOOK_URL}")

if __name__ == "__main__":
    asyncio.run(on_startup())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
