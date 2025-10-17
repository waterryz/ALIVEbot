from playwright.sync_api import sync_playwright
import time
import os

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
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print("🌐 Переход на сайт...")
            page.goto(LOGIN_URL, timeout=60000)

            # Заполняем форму
            page.fill("input[name='iin']", iin)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")

            # Ждем перехода после логина
            page.wait_for_timeout(5000)

            if "login" in page.url or "error" in page.url:
                print("❌ Не удалось войти в аккаунт — проверь ИИН и пароль")
                browser.close()
                return None

            # Проверяем предмет
            journal_url = JOURNAL_LINKS.get(subject)
            if not journal_url:
                print("❌ Неверный предмет:", subject)
                browser.close()
                return None

            print("📖 Открываю журнал:", subject)
            page.goto(journal_url, timeout=60000)
            page.wait_for_timeout(5000)

            # Создаём папку, если нет
            os.makedirs("screenshots", exist_ok=True)
            screenshot_path = f"screenshots/{subject}.png"

            page.screenshot(path=screenshot_path, full_page=True)
            browser.close()

            print("✅ Скриншот сохранен:", screenshot_path)
            return screenshot_path

    except Exception as e:
        print(f"⚠️ Ошибка в get_screenshot(): {e}")
        return None
