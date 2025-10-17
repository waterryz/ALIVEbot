import os
import psycopg
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# ───────────────────────────────
# Загрузка .env
# ───────────────────────────────
load_dotenv()

# ───────────────────────────────
# Настройка ключа шифрования
# ───────────────────────────────
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print("⚠️  Не найден ENCRYPTION_KEY — создан временный. Сохрани его в Render Settings!")

fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

# ───────────────────────────────
# Подключение к базе данных
# ───────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("❌ Не найдена переменная окружения DATABASE_URL!")

def _test_connection():
    """Проверка подключения к базе"""
    try:
        with psycopg.connect(DATABASE_URL, sslmode="require") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()
                print(f"🟢 Подключено к PostgreSQL: {version[0]}")
    except Exception as e:
        print(f"🔴 Ошибка подключения к БД: {e}")

# ───────────────────────────────
# Инициализация таблицы пользователей
# ───────────────────────────────
def init_db():
    """Создание таблицы users"""
    try:
        with psycopg.connect(DATABASE_URL, sslmode="require") as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        login TEXT NOT NULL,
                        password TEXT NOT NULL
                    )
                """)
                conn.commit()
        print("✅ Таблица users готова к использованию")
        _test_connection()
    except Exception as e:
        print(f"❌ Ошибка инициализации базы: {e}")

# ───────────────────────────────
# Сохранение логина и пароля
# ───────────────────────────────
def save_credentials(user_id: int, login: str, password: str):
    """Сохраняет или обновляет зашифрованные данные пользователя"""
    encrypted_login = fernet.encrypt(login.encode()).decode()
    encrypted_password = fernet.encrypt(password.encode()).decode()

    with psycopg.connect(DATABASE_URL, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (user_id, login, password)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET login = EXCLUDED.login, password = EXCLUDED.password
            """, (user_id, encrypted_login, encrypted_password))
            conn.commit()
    print(f"💾 Данные пользователя {user_id} сохранены")

# ───────────────────────────────
# Получение логина и пароля
# ───────────────────────────────
def get_credentials(user_id: int):
    """Возвращает расшифрованные данные пользователя"""
    with psycopg.connect(DATABASE_URL, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT login, password FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if not row:
                return None
            login = fernet.decrypt(row[0].encode()).decode()
            password = fernet.decrypt(row[1].encode()).decode()
            return login, password
