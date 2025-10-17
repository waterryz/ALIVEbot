from playwright.sync_api import sync_playwright
import time

LOGIN_URL = "https://college.snation.kz/kz/tko/login"
JOURNAL_LINKS = {
    "Python": "https://college.snation.kz/kz/tko/control/journals/873776",
    "БД": "https://college.snation.kz/kz/tko/control/journals/873763",
    "ИКТ": "https://college.snation.kz/kz/tko/control/journals/873757",
    "Графика": "https://college.snation.kz/kz/tko/control/journals/873751",
    "Физра": "https://college.snation.kz/kz/tko/control/journals/873753",
    "Экономика": "https://college.snation.kz/kz/tko/control/journals/873760",
}


def get_screenshot(iin, password, subject):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(LOGIN_URL)
        page.fill("input[name='iin']", iin)
        page.fill("input[name='password']", password)
        page.click("button[type='submit']")

        time.sleep(3)

        if "login" in page.url:
            browser.close()
            return None

        journal_url = JOURNAL_LINKS.get(subject)
        if not journal_url:
            browser.close()
            return None

        page.goto(journal_url)
        time.sleep(5)

        screenshot_path = f"screenshots/{subject}.png"
        page.screenshot(path=screenshot_path, full_page=True)

        browser.close()
        return screenshot_path

import asyncio

# ───────────────────────────────
# Асинхронная обёртка для бота
# ───────────────────────────────
async def parse_site(login: str, password: str):
    """
    Универсальная функция для Telegram-бота.
    Делает скриншоты всех журналов и возвращает ссылки.
    """
    subjects = list(JOURNAL_LINKS.keys())
    results = []

    for subject in subjects:
        screenshot_path = get_screenshot(login, password, subject)
        if screenshot_path:
            results.append(f"✅ {subject}: {screenshot_path}")
        else:
            results.append(f"❌ {subject}: ошибка входа или загрузки")

    return "\n".join(results)

