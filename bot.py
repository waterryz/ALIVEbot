import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from parser import login_and_get_grades, extract_grades_from_html

# 🔐 Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")  # без https:// в коде не вставляй

if not BOT_TOKEN or not APP_URL:
    raise ValueError("❌ Не найдены переменные BOT_TOKEN или APP_URL!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Введи ИИН и пароль через пробел:\nПример: 123456789012 1234pass")

async def handle_creds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        iin, password = update.message.text.strip().split()
        await update.message.reply_text("🔐 Входим в журнал...")
        html = login_and_get_grades(iin, password)
        if not html:
            await update.message.reply_text("❌ Неверный ИИН или пароль.")
            return
        grades = extract_grades_from_html(html)
        await update.message.reply_text(grades)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_creds))

    print("🚀 Устанавливаем Webhook...")

    # Запуск с Webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=f"{APP_URL}/webhook/{BOT_TOKEN}",
    )
