import requests
from bs4 import BeautifulSoup

def login_and_get_grades(iin, password):
    session = requests.Session()
    login_url = "https://college.snation.kz/kz/tko/login"
    response = session.get(login_url)
    soup = BeautifulSoup(response.text, "html.parser")
    token = soup.find("meta", {"name": "csrf-token"})["content"]
    payload = {"_token": token, "login": iin, "password": password}
    login_response = session.post(login_url, data=payload)
    if "Журнал" not in login_response.text:
        return None
    journal_url = "https://college.snation.kz/ru/tko/control/journals/873776"
    journal_response = session.get(journal_url)
    return journal_response.text

def extract_grades_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="sc-journal__table--scroll-part")
    if not table:
        return "⚠️ Не удалось найти таблицу с оценками."
    headers = [th.text.strip() for th in table.find_all("th")]
    rows = table.find_all("tr")[1:]
    grades = []
    for td, date in zip(rows[0].find_all("td"), headers):
        grade = td.text.strip()
        grades.append(f"📅 {date}: {grade or '—'}")
    return "\n".join(grades)