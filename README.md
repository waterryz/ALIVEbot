# SmartNation Bot (Render Ready)

Бот для SmartNation, который логинится по ИИН и паролю, делает скриншоты журналов и отправляет их в Telegram.

## 🚀 Деплой на Render
1. Залей проект на GitHub.
2. Создай новый **Web Service** на [render.com](https://render.com).
3. Укажи buildCommand и startCommand как в `render.yaml`.
4. После запуска установи вебхук:
   https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://<YOUR_RENDER_URL>/webhook/<YOUR_TOKEN>
