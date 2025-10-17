import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from flask import Flask, request
from playwright.async_api import async_playwright
from users_db import init_db, save_user, get_user

TOKEN = "8438829706:AAHiv7tHdDBMR3UoGXn3CcUHWuuIVFBAvU0"
WEBHOOK_URL = f"https://alivebot-7pa2.onrender.com/webhook/{TOKEN}"

# путь к базе (учтён persistent диск)
DB_PATH = os.getenv("DB_PATH", "users.db")

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

init_db()

# Ссылки на журналы
JOURNAL_LINKS = {
    "Пайтон 🐍": "https://college.snation.kz/kz/tko/control/journals/873776",
    "Графика 🎨": "https://college.snation.kz/kz/tko/control/journals/873751",
    "Физра 🏃": "https://college.snation.kz/kz/tko/control/journals/873753",
    "БД 💾": "https://college.snation.kz/kz/tko/control/journals/873763",
    "ИКТ 💻": "https://college.snation.kz/kz/tko/control/journals/873757"
}


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
        print(f"❌ Ошибка при апдейте: {e}")
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
    iin, password = message.text.split(maxsplit=1)
    save_user(message.from_user.id, iin.strip(), password.strip())

    # Создаём кнопки
    keyboard = types.InlineKeyboardMarkup()
    for subj in JOURNAL_LINKS.keys():
        keyboard.add(types.InlineKeyboardButton(text=subj, callback_data=f"subject_{subj}"))

    await message.answer("✅ Авторизация сохранена!\nТеперь выбери предмет:", reply_markup=keyboard)


# Обработка выбора предмета
@dp.callback_query(F.data.startswith("subject_"))
async def handle_subject(callback: types.CallbackQuery):
    subj = callback.data.replace("subject_", "")
    user = get_user(callback.from_user.id)

    if not user:
        await callback.message.answer("⚠️ Сначала введи свой ИИН и пароль.")
        return

    iin, password = user
    await callback.message.answer(f"📸 Загружаю журнал *{subj}*...", parse_mode="Markdown")

    link = JOURNAL_LINKS.get(subj)
    if not link:
        await callback.message.answer("❌ Ошибка: ссылка на предмет не найдена.")
        return

    screenshot_path = f"screenshots/{callback.from_user.id}_{subj}.png"
    os.makedirs("screenshots", exist_ok=True)

    try:
        await take_screenshot(iin, password, link, screenshot_path)
        await callback.message.answer_photo(photo=open(screenshot_path, "rb"))
    except Exception as e:
        print(f"Ошибка скриншота: {e}")
        await callback.message.answer("❌ Не удалось загрузить журнал. Проверь логин и пароль.")


# Функция скриншота Playwright
async def take_screenshot(iin, password, journal_url, save_path):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://college.snation.kz/kz/tko/login", timeout=60000)

        # Вводим логин/пароль (подстрой под реальные селекторы)
        await page.fill('input[name="iin"]', iin)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')

        await page.wait_for_timeout(3000)
        await page.goto(journal_url)
        await page.wait_for_timeout(5000)

        await page.screenshot(path=save_path, full_page=True)
        await browser.close()


# Проверка данных
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
