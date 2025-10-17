# -*- coding: utf-8 -*-
import os
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.filters import Command
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

# --- Настройки из окружения ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан")

# Render предоставляет RENDER_EXTERNAL_URL. Если нет — поставь свой WEBHOOK_HOST, например https://myapp.onrender.com
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBHOOK_HOST")
if not WEBHOOK_HOST:
    raise RuntimeError("WEBHOOK_HOST или RENDER_EXTERNAL_URL не заданы")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.getenv("PORT", "10000"))

SMART_LOGIN = os.getenv("SMART_LOGIN")
SMART_PASSWORD = os.getenv("SMART_PASSWORD")
if not (SMART_LOGIN and SMART_PASSWORD):
    print("Warning: SMART_LOGIN/SMART_PASSWORD не заданы. /getscreens работать не будет пока их нет.")

# Журналы (через запятую) или дефолтный набор
JOURNAL_URLS = os.getenv("JOURNAL_URLS", "").strip()
if JOURNAL_URLS:
    JOURNAL_URLS = [u.strip() for u in JOURNAL_URLS.split(",") if u.strip()]
else:
    JOURNAL_URLS = [
        "https://college.snation.kz/kz/tko/control/journals/873776",
        "https://college.snation.kz/kz/tko/control/journals/873751",
    ]

OUTDIR = Path("screens")
OUTDIR.mkdir(exist_ok=True)

# --- Aiogram webhook setup ---
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

@dp.message(Command(commands=["start"]))
async def cmd_start(msg):
    await msg.answer("Привет! Отправь /getscreens чтобы получить скрины журналов SmartNation.")

@dp.message(Command(commands=["getscreens"]))
async def cmd_getscreens(msg):
    if not (SMART_LOGIN and SMART_PASSWORD):
        await msg.answer("Ошибка: SMART_LOGIN/SMART_PASSWORD не настроены в окружении.")
        return
    await msg.answer("Логинюсь в SmartNation и снимаю скриншоты... Это может занять ~10-30 секунд.")
    try:
        driver = create_logged_driver(headless=True)
    except Exception as e:
        await msg.answer(f"Не удалось запустить браузер: {e}")
        return

    sent = 0
    try:
        for idx, url in enumerate(JOURNAL_URLS, start=1):
            try:
                path = screenshot_url(driver, url, name_hint=f"journal_{idx}")
                with open(path, "rb") as f:
                    await bot.send_photo(chat_id=msg.chat.id, photo=f, caption=f"Журнал {idx}\n{url}")
                sent += 1
            except Exception as e:
                await msg.answer(f"Ошибка при скриншоте {url}: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    if sent:
        await msg.answer("Готово ✅")
    else:
        await msg.answer("Не удалось сделать ни одного скриншота.")

# --- webhook handler ---
async def handle(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="no json")
    update = Update(**data)
    await dp.process_update(update)
    return web.Response(status=200, text="ok")

async def on_startup(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook установлен:", WEBHOOK_URL)

async def on_cleanup(app: web.Application):
    await bot.delete_webhook()
    await bot.session.close()

def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    web.run_app(app, host="0.0.0.0", port=PORT)

# -------------------- Selenium helpers --------------------
def create_logged_driver(headless=True):
    """
    Запускает Chromium + chromedriver. Возвращает selenium webdriver,
    уже залогиненным в SmartNation (если удачно).
    """
    # Параметры браузера
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1200")
    chrome_options.add_argument("--lang=ru")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    # Если на системе есть chromium в нестандартном месте, можно указать BINARY_LOCATION через env
    chrome_bin = os.getenv("CHROME_BIN")  # например /usr/bin/chromium
    if chrome_bin:
        chrome_options.binary_location = chrome_bin

    # Устанавливаем chromedriver через webdriver_manager
    driver_path = ChromeDriverManager().install()
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(8)

    # Логинимся
    login_url = "https://college.snation.kz/kz/tko/login"
    driver.get(login_url)
    time.sleep(1.0)

    # Пытливые варианты селекторов — если первый не найден, пробуем другой
    try:
        # Вариант 1: name=username / name=password
        try:
            u = driver.find_element(By.NAME, "username")
            p = driver.find_element(By.NAME, "password")
            btn = driver.find_element(By.XPATH, "//button[@type='submit' or contains(., 'Кіру') or contains(., 'Войти')]")
        except Exception:
            # Вариант 2: id или placeholder
            u = driver.find_element(By.ID, "login")
            p = driver.find_element(By.ID, "password")
            btn = driver.find_element(By.XPATH, "//button[contains(.,'Кіру') or contains(.,'Войти') or @type='submit']")
    except NoSuchElementException:
        raise RuntimeError("Не удалось найти поля логина. Проверь селекторы на странице логина SmartNation.")

    # Заполняем и отправляем
    u.clear()
    u.send_keys(SMART_LOGIN)
    p.clear()
    p.send_keys(SMART_PASSWORD)
    try:
        btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", btn)
    # Ждём редирект/загрузку
    time.sleep(2.5)

    # Проверка успешного входа: попробуем найти кнопку выхода / профиль
    # (если не нашли — всё равно возвращаем драйвер, может быть требуется 2FA)
    return driver

def screenshot_url(driver, url: str, name_hint: str = "page"):
    driver.get(url)
    time.sleep(1.2)
    # Попытка получить полную высоту страницы и сделать полно-страничный скрин
    try:
        total_width = driver.execute_script("return document.documentElement.scrollWidth")
        total_height = driver.execute_script("return document.documentElement.scrollHeight")
        # Ограничим размеры, чтобы не выйти за пределы
        w = min(total_width, 4096)
        h = min(total_height, 20000)
        driver.set_window_size(w, h)
        time.sleep(0.5)
    except Exception:
        pass
    fname = OUTDIR / f"{int(time.time())}_{name_hint}.png"
    driver.save_screenshot(str(fname))
    return fname

# -------------------- Run --------------------
if __name__ == "__main__":
    main()
