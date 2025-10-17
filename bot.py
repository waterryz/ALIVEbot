import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from flask import Flask, request
from users_db import init_db, save_user, get_user

TOKEN = "8438829706:AAHiv7tHdDBMR3UoGXn3CcUHWuuIVFBAvU0"
WEBHOOK_URL = f"https://alivebot-7pa2.onrender.com/webhook/{TOKEN}"

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# Инициализация базы при старте
init_db()

@app.route('/')
def home():
    return "✅ SmartNation бот активен!"

@app.post(f"/webhook/{TOKEN}")
async def webhook():
    try:
        data = request.json
        if not data:
            return "no data", 400
        update = types.Update.model_validate(data, strict=False)
        await dp.feed_update(bot, update)
        return "ok"
    except Exception as e:
        print(f"❌ Ошибка при обработке апдейта: {e}")
        return "error", 500

# /start
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот колледжа SmartNation.\n"
        "Введи свой ИИН и пароль для входа в журнал 📘\n\n"
        "Пример: `090120555841 555841abc`",
        parse_mode="Markdown"
    )

# Принимаем ИИН и пароль
@dp.message(F.text.regexp(r"^\d{12}\s+\S+$"))
async def handle_credentials(message: types.Message):
    try:
        iin, password = message.text.split(maxsplit=1)
        save_user(message.from_user.id, iin.strip(), password.strip())
        await message.answer("✅ Авторизация сохранена!\nТеперь выбери предмет:")
        # Здесь позже добавим inline-кнопки с предметами
    except Exception as e:
        print(f"⚠️ Ошибка сохранения: {e}")
        await message.answer("❌ Ошибка при сохранении данных. Попробуй снова.")

# Для теста — проверить сохранённые данные
@dp.message(Command("me"))
async def show_user_data(message: types.Message):
    user = get_user(message.from_user.id)
    if user:
        await message.answer(f"🔐 Твои данные:\nИИН: {user[0]}\nПароль: {user[1]}")
    else:
        await message.answer("ℹ️ Ты ещё не вводил свои данные.")

async def setup_webhook():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Вебхук установлен: {WEBHOOK_URL}")

def main():
    loop = asyncio.get_event_loop()
    loop.create_task(setup_webhook())
    print("🚀 Flask сервер запущен")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

if __name__ == "__main__":
    main()
