import os
import psycopg
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# ───────────────────────────────
# Настройка окружения
# ───────────────────────────────
load_dotenv()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # если ключ не задан, создаём новый (для локального запуска)
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print("⚠️  Создан временный ключ шифрования (сохрани его в ENV как ENCRYPTION_KEY)")

fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("❌ Переменная окружения DATABASE_URL не найдена")

# ───────────────────────────────
# Создание таблицы пользователей
# ───────────────────────────────
def init_db():
    """Создание таблицы users, если её ещё нет"""
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
    print(f"✅ Данные пользователя {user_id} сохранены")

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
