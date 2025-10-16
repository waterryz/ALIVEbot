import os
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from parser import get_cookie, get_journal_with_cookie, extract_grades_from_html

# Переменные окружения Render
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")

if not BOT_TOKEN or not APP_URL:
    raise ValueError("❌ BOT_TOKEN или APP_URL не заданы!")

# Простое хранилище cookie (можно заменить на Redis/БД)
COOKIE_FILE = "cookies.json"
if not os.path.exists(COOKIE_FILE):
    with open(COOKIE_FILE, "w") as f:
        json.dump({}, f)


def save_cookie(iin, cookies):
    with open(COOKIE_FILE, "r+") as f:
        data = json.load(f)
        data[iin] = cookies
        f.seek(0)
        json.dump(data, f)
        f.truncate()


def load_cookie(iin):
    with open(COOKIE_FILE, "r") as f:
        data = json.load(f)
        return data.get(iin)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Введи ИИН и пароль через пробел:\nПример: 123456789012 1234pass"
    )


async def handle_creds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip()
        if " " not in text:
            await update.message.reply_text("⚠️ Формат: ИИН пароль (через пробел)")
            return

        iin, password = text.split()

        await update.message.reply_text("🔐 Входим в систему...")

        # 1️⃣ Пробуем использовать сохранённую cookie
        cookies = load_cookie(iin)
        if cookies:
            html = await get_journal_with_cookie(cookies)
            if html:
                grades = extract_grades_from_html(html)
                await update.message.reply_text(grades, parse_mode="Markdown")
                return
            else:
                await update.message.reply_text("♻️ Сессия истекла, пробую войти заново...")

        # 2️⃣ Логинимся и сохраняем cookie
        cookies = await get_cookie(iin, password)
        if not cookies:
            await update.message.reply_text("❌ Неверный ИИН или пароль.")
            return

        save_cookie(iin, cookies)

        html = await get_journal_with_cookie(cookies)
        if not html:
            await update.message.reply_text("⚠️ Не удалось получить журнал.")
            return

        grades = extract_grades_from_html(html)
        await update.message.reply_text(grades, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {e}")


if __name__ == "__main__":
    print("🚀 Запуск Telegram-бота через Webhook на Render...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_creds))

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=f"{APP_URL}/webhook/{BOT_TOKEN}",
        drop_pending_updates=True,
    )
