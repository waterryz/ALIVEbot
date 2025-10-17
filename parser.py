from playwright.sync_api import sync_playwright
import os
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
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page()

            print("🌐 Открываю страницу логина...")
            page.goto(LOGIN_URL, timeout=60000)
            page.wait_for_selector("input[placeholder='ЖСН']", timeout=15000)

            # Вводим ИИН
            page.fill("input[placeholder='ЖСН']", iin)
            # Для пароля ищем по частичному совпадению, чтобы не зависеть от текста
            page.fill("input[placeholder*='Құпия']", password)

            print("🔐 Отправляю форму входа...")
            # Кликаем кнопку "Жүйеге кіру" (возможны разные языки)
            page.locator("button:has-text('Жүйеге кіру'), button:has-text('Войти')").click()
            page.wait_for_timeout(5000)

            print("📍 Текущий URL:", page.url)

            if "login" in page.url:
                print("❌ Неверный логин или пароль.")
                browser.close()
                return "login_failed"

            journal_url = JOURNAL_LINKS.get(subject)
            if not journal_url:
                print("❌ Предмет не найден:", subject)
                browser.close()
                return "wrong_subject"

            print("📘 Открываю журнал:", subject)
            page.goto(journal_url, timeout=60000)
            page.wait_for_timeout(5000)

            os.makedirs("screenshots", exist_ok=True)
            screenshot_path = f"screenshots/{subject}.png"
            page.screenshot(path=screenshot_path, full_page=True)

            print("✅ Скриншот сохранён:", screenshot_path)
            browser.close()
            return screenshot_path

    except Exception as e:
        print(f"🔥 Ошибка в get_screenshot(): {e}")
        return None
