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
    os.makedirs("screenshots", exist_ok=True)
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

        link = JOURNAL_LINKS.get(subject)
        if not link:
            browser.close()
            return None

        page.goto(link)
        time.sleep(5)

        path = f"screenshots/{subject}.png"
        page.screenshot(path=path, full_page=True)
        browser.close()
        return path
