from playwright.async_api import async_playwright
import asyncio
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

async def get_screenshot(iin, password, subject):
    os.makedirs("screenshots", exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Вход на сайт
            await page.goto(LOGIN_URL, timeout=20000)
            await page.fill("input[name='iin']", iin)
            await page.fill("input[name='password']", password)
            await page.click("button[type='submit']")
            await asyncio.sleep(3)

            # Проверка успешного входа
            if "login" in page.url.lower():
                await browser.close()
                return {"success": False, "error": "Неверный логин или пароль"}

            journal_url = JOURNAL_LINKS.get(subject)
            if not journal_url:
                await browser.close()
                return {"success": False, "error": f"Предмет {subject} не найден"}

            await page.goto(journal_url, timeout=20000)
            await asyncio.sleep(5)

            screenshot_path = f"screenshots/{subject}.png"
            await page.screenshot(path=screenshot_path, full_page=True)

            await browser.close()
            return {"success": True, "path": screenshot_path}

        except Exception as e:
            await browser.close()
            return {"success": False, "error": str(e)}
