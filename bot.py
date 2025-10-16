import os
import json
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)
from parser import get_journal_with_cookie, extract_grades_from_html

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")

if not BOT_TOKEN or not APP_URL:
    raise ValueError("❌ BOT_TOKEN или APP_URL не заданы!")

COOKIE_FILE = "cookies.json"
if not os.path.exists(COOKIE_FILE):
    with open(COOKIE_FILE, "w") as f:
        json.dump({}, f)

def save_cookie(user_id, cookie):
    with open(COOKIE_FILE, "r+") as f:
        data = json.load(f)
        data[str(user_id)] = cookie
        f.seek(0)
        json.dump(data, f)
        f.truncate()

def load_cookie(user_id):
    with open(COOKIE_FILE, "r") as f:
        data = json.load(f)
        return data.get(str(user_id))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Отправь свою cookie (например, `laravel_session=...; XSRF-TOKEN=...`), "
        "и я покажу твои оценки."
    )

async def handle_cookie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cookie_string = update.message.text.strip()

    # Сохраняем cookie
    save_cookie(user_id, cookie_string)
    await update.message.reply_text("✅ Cookie сохранена! Загружаю журнал...")

    html = await get_journal_with_cookie(cookie_string)
    if not html:
        await update.message.reply_text("❌ Не удалось войти с этой cookie. Возможно, она устарела.")
        return

    grades = extract_grades_from_html(html)
    await update.message.reply_text(grades, parse_mode="Markdown")

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cookie = load_cookie(user_id)

    if not cookie:
        await update.message.reply_text("⚠️ У тебя нет сохранённой cookie. Отправь её снова.")
        return

    await update.message.reply_text("♻️ Обновляю данные журнала...")

    html = await get_journal_with_cookie(cookie)
    if not html:
        await update.message.reply_text("❌ Cookie устарела, отправь новую.")
        return

    grades = extract_grades_from_html(html)
    await update.message.reply_text(grades, parse_mode="Markdown")

if __name__ == "__main__":
    print("🚀 Запуск Telegram-бота на Render...")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("refresh", refresh))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_cookie))

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=f"{APP_URL}/webhook/{BOT_TOKEN}",
        drop_pending_updates=True,
    )
