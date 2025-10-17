import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Загрузка переменных окружения
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", 10000))

if not TOKEN:
    raise Exception("❌ BOT_TOKEN не найден в Render Environment")

# 👇 Новый стиль инициализации бота для aiogram 3.13+
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# ──────────────────────────────────────────────
# Хэндлер /start
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer("👋 Привет! Я бот SmartNation.\nРаботаю через вебхук и полностью готов ✅")

# ──────────────────────────────────────────────
# Обработчик webhook
async def handle(request: web.Request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)  # ✅ новый метод
    except Exception as e:
        logger.exception("❌ Ошибка при обработке webhook запроса: %s", e)
        return web.Response(status=500, text="Internal Server Error")
    return web.Response(status=200, text="ok")

# ──────────────────────────────────────────────
# Проверочный маршрут
async def root(request):
    return web.Response(text="Bot is running ✅")

# ──────────────────────────────────────────────
async def on_start(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("✅ Webhook установлен: %s", WEBHOOK_URL)

async def on_stop(app: web.Application):
    await bot.delete_webhook()
    await bot.session.close()
    logger.info("🛑 Webhook удалён и сессия закрыта")

# ──────────────────────────────────────────────
def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)
    app.router.add_get("/", root)
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    logger.info("🚀 Бот запускается на порту %d", PORT)
    web.run_app(app, host="0.0.0.0", port=PORT)

# ──────────────────────────────────────────────
if __name__ == "__main__":
    main()
