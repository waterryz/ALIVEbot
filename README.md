
# SmartNation Bot (Render Ready)

Бот для SmartNation, который логинится по ИИН и паролю, делает скриншоты журналов и отправляет их в Telegram.

## 🚀 Деплой на Render
1. Залей проект на GitHub.
2. Создай новый **Web Service** на [render.com](https://render.com).
3. Укажи buildCommand и startCommand как в `render.yaml`.
4. В настройках сервиса создай переменные окружения:
   - `BOT_TOKEN` — токен твоего Telegram-бота.
   - `DATABASE_URL` — строка подключения к PostgreSQL (например, из Neon.tech). Render автоматически подставит `sslmode=require`.
   - `WEBHOOK_BASE_URL` — внешний URL сервиса на Render (например, `https://smartnation-bot.onrender.com`). Если Render уже задаёт `RENDER_EXTERNAL_URL`, можно пропустить.
5. После деплоя вебхук установится автоматически, т.к. бот использует `WEBHOOK_BASE_URL`.
