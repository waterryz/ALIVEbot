from playwright.sync_api import sync_playwright
import time
import os

# Ссылки
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
    """
    Авторизация на сайте колледжа и получение скриншота журнала по предмету.
    Возвращает путь к скриншоту или текст ошибки ("login_failed", "wrong_subject", None)
    """

    try:
        with sync_playwright() as p:
            print("🌐 Запуск браузера...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print("🔗 Открываю страницу логина...")
            page.goto(LOGIN_URL, timeout=60000)

            # Ждём появление формы входа
            page.wait_for_selector("input[placeholder='ЖСН']", timeout=15000)

            print("✏️ Ввожу данные пользователя...")
            page.fill("input[placeholder='ЖСН']", iin)
            page.fill("input[placeholder^='Құпия']", password)

            # Кнопка входа
            page.click("button:has-text('Жүйеге кіру')")

            print("🔐 Ожидание перехода после входа...")
            page.wait_for_timeout(5000)

            # Проверка успешного входа
            if "login" in page.url or "password" in page.url:
                print("❌ Ошибка: неверный логин или пароль.")
                browser.close()
                return "login_failed"

            # Проверка предмета
            journal_url = JOURNAL_LINKS.get(subject)
            if not journal_url:
                print("❌ Ошибка: предмет не найден.")
                browser.close()
                return "wrong_subject"

            print(f"📚 Открываю журнал по предмету: {subject}")
            page.goto(journal_url, timeout=60000)

            # Ждём загрузку страницы
            page.wait_for_timeout(5000)

            # Создание папки для скринов
            os.makedirs("screenshots", exist_ok=True)
            screenshot_path = f"screenshots/{subject}.png"

            # Сохраняем скриншот
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"✅ Скриншот сохранён: {screenshot_path}")

            browser.close()
            return screenshot_path

    except Exception as e:
        print(f"⚠️ Ошибка в get_screenshot(): {e}")
        return None
