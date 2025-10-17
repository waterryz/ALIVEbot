# Используем официальный Python slim образ
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Обновим и установим Chromium и шрифты
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      wget \
      unzip \
      fonts-liberation \
      libnss3 \
      libatk-bridge2.0-0 \
      libatk1.0-0 \
      libc6 \
      libx11-6 \
      libx11-xcb1 \
      libxcb1 \
      libxcomposite1 \
      libxdamage1 \
      libxrandr2 \
      libasound2 \
      libpangocairo-1.0-0 \
      libgtk-3-0 \
      chromium \
      chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Указываем бинарник chromium (webdriver использует этот путь)
ENV CHROME_BIN=/usr/bin/chromium
ENV PATH="/root/.local/bin:${PATH}"

# Порт, который Render будет слушать (или настрой Render на PORT)
EXPOSE 10000

# Команда запуска
CMD ["python", "bot.py"]
