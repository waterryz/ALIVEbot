import httpx
from bs4 import BeautifulSoup

# URL для входа и журнала
LOGIN_URL = "https://college.snation.kz/kz/tko/login"
JOURNAL_URL = "https://college.snation.kz/ru/tko/control/journals"


async def get_cookie(iin: str, password: str) -> dict | None:
    """
    Авторизация и получение cookie (без хранения пароля)
    """
    async with httpx.AsyncClient(follow_redirects=True) as client:
        headers = {"User-Agent": "Mozilla/5.0"}
        data = {"iin": iin, "password": password}

        resp = await client.post(LOGIN_URL, data=data, headers=headers)
        # Проверяем успешный вход
        if "Құпия сөз" in resp.text or "Жүйеге кіру" in resp.text or resp.status_code != 200:
            return None

        # Возвращаем словарь cookie
        return {c.name: c.value for c in client.cookies.jar}


async def get_journal_with_cookie(cookies: dict) -> str | None:
    """
    Получение HTML журнала, используя cookie сессии
    """
    async with httpx.AsyncClient(follow_redirects=True, cookies=cookies) as client:
        resp = await client.get(JOURNAL_URL)
        if resp.status_code != 200 or "Журнал" not in resp.text:
            return None
        return resp.text


def extract_grades_from_html(html: str) -> str:
    """
    Парсинг HTML журнала и извлечение оценок
    """
    soup = BeautifulSoup(html, "html.parser")

    header_cells = soup.select(".sc-journal__table--scroll-part th.sc-journal__table--cell-value")
    grade_cells = soup.select(".sc-journal__table--scroll-part td.sc-journal__table--cell-value")

    if not header_cells or not grade_cells:
        return "⚠️ Оценки не найдены."

    dates = [h.get_text(strip=True) for h in header_cells]
    grades = [g.get_text(strip=True) for g in grade_cells]

    numeric = [int(g) for g in grades if g.isdigit()]
    avg = sum(numeric) / len(numeric) if numeric else 0

    result = "📘 *Журнал:*\n" + "\n".join(
        f"{d}: {g or '—'}" for d, g in zip(dates, grades)
    ) + f"\n\n📊 Средний балл: {avg:.1f}"
    return result
