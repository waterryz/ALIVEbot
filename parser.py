import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://college.snation.kz/kz/tko/control/journals"

async def fetch_subject_grades(subj_id: str, cookie: str):
    months = ["09/2025", "10/2025", "11/2025", "12/2025"]
    points, ro1, ro2 = [], [], []

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": cookie
    }

    async with httpx.AsyncClient(headers=headers, timeout=20) as client:
        for month in months:
            url = f"{BASE_URL}/{subj_id}/load-table?year_month={month.replace('/', '%2F')}"
            try:
                r = await client.get(url)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "html.parser")

                points += [td.text.strip() for td in soup.select("td.points") if td.text.strip()]
                ro1 += [td.text.strip() for td in soup.select("td.ro1") if td.text.strip()]
                ro2 += [td.text.strip() for td in soup.select("td.ro2") if td.text.strip()]
            except Exception:
                continue

    def fmt(arr): return ", ".join(arr) if arr else "—"

    return (
        f"📘 *Оценки за семестр*"
        f"━━━━━━━━━━━━━━━━━━━"
        f"Оценки: {fmt(points)}"
        f"РО1: {fmt(ro1)}"
        f"РО2: {fmt(ro2)}"
    )
