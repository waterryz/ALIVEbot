from playwright.sync_api import sync_playwright
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
        print(f"🚀 Старт Playwright для {subject}")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page()

            print("🌐 Открываю страницу логина...")
            page.goto(LOGIN_URL, timeout=60000)

            # Проверяем наличие формы
            page.wait_for_selector("input[placeholder='ЖСН']", timeout=15000)
            print("✅ Форма найдена — ввожу данные...")

            page.fill("input[placeholder='ЖСН']", iin)
            page.fill("input[placeholder^='Құпия']", password)
            page.click("button:has-text('Жүйеге кіру')")
            print("🔐 Нажата кнопка входа, жду переход...")

            page.wait_for_timeout(6000)
            print("📍 Текущий URL после входа:", page.url)

            # Проверяем успешность входа
            if "login" in page.url or "password" in page.url:
                print("❌ Ошибка входа — неверный логин или пароль.")
                browser.close()
                return "login_failed"

            # Проверяем предмет
            journal_url = JOURNAL_LINKS.get(subject)
            if not journal_url:
                print("❌ Неверный предмет:", subject)
                browser.close()
                return "wrong_subject"

            print("📖 Открываю журнал:", journal_url)
            page.goto(journal_url, timeout=60000)
            page.wait_for_timeout(5000)

            # Проверяем, загрузился ли журнал
            if "control/journals" not in page.url:
                print("⚠️ Переход к журналу не удался.")
                browser.close()
                return None

            # Делаем скриншот
            os.makedirs("screenshots", exist_ok=True)
            screenshot_path = f"screenshots/{subject}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"✅ Скриншот сохранён: {screenshot_path}")

            browser.close()
            return screenshot_path

    except Exception as e:
        print(f"🔥 Исключение в get_screenshot(): {type(e).__name__} — {e}")
        return None
