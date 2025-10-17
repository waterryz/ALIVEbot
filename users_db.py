import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv("DATABASE_URL")

def init_db():
    conn = psycopg2.connect(DB_URL, sslmode="require")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            iin TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def save_user(user_id: int, iin: str, password: str):
    conn = psycopg2.connect(DB_URL, sslmode="require")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, iin, password)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET iin = EXCLUDED.iin, password = EXCLUDED.password
    """, (user_id, iin, password))
    conn.commit()
    cur.close()
    conn.close()

def get_user(user_id: int):
    conn = psycopg2.connect(DB_URL, sslmode="require")
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT iin, password FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return row["iin"], row["password"]
    return None
