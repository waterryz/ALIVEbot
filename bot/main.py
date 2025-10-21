import base64
import io
import asyncio
import requests
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.filters import CommandStart
from config import BOT_TOKEN, API_URL, WEBHOOK_URL, PORT

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
user_data = {}

@dp.message(CommandStart())
async def start(message: types.Message):
    user_data[message.from_user.id] = {"step": "login"}
    await message.answer("👋 Привет! Введи логин SmartNation:")

@dp.message()
async def handle_msg(message: types.Message):
    uid = message.from_user.id
    data = user_data.get(uid, {})

    if data.get("step") == "login":
        data["login"] = message.text.strip()
        data["step"] = "password"
        await message.answer("🔑 Теперь введи пароль:")
    elif data.get("step") == "password":
        data["password"] = message.text.strip()
        await message.answer("⏳ Загружаю журнал...")
        try:
            r = requests.post(API_URL, json={
                "login": data["login"],
                "password": data["password"]
            }, timeout=60)
            if r.status_code == 200:
                img_b64 = r.json().get("image")
                img = base64.b64decode(img_b64)
                await bot.send_photo(
                    message.chat.id,
                    io.BytesIO(img),
                    caption="✅ Вот твой журнал!"
                )
            else:
                await message.answer("❌ Ошибка парсинга. Проверь данные.")
        except Exception as e:
            await message.answer(f"⚠️ Ошибка: {e}")
        user_data[uid] = {}
    else:
        await message.answer("Отправь /start чтобы начать.")

async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()

async def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.on_startup.append(lambda _: on_startup(bot))
    app.on_shutdown.append(lambda _: on_shutdown(bot))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ Webhook запущен на порту {PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
