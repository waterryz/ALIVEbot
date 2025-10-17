import os
from functools import lru_cache

import psycopg
from psycopg.rows import dict_row


@lru_cache(maxsize=1)
def _require_db_url() -> str:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL environment variable is required")
    return db_url


def init_db():
    with psycopg.connect(_require_db_url(), sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    iin TEXT NOT NULL,
                    password TEXT NOT NULL
                )
                """
            )
        conn.commit()


def save_user(user_id: int, iin: str, password: str):
    with psycopg.connect(_require_db_url(), sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (user_id, iin, password)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET iin = EXCLUDED.iin, password = EXCLUDED.password
                """,
                (user_id, iin, password),
            )
        conn.commit()


def get_user(user_id: int):
    with psycopg.connect(_require_db_url(), sslmode="require") as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT iin, password FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
    if row:
        return row["iin"], row["password"]
    return None
