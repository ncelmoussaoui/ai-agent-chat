import psycopg
from app.config import DATABASE_URL


def get_connection():
    return psycopg.connect(DATABASE_URL)


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nachrichten (
                id SERIAL PRIMARY KEY,
                frage TEXT NOT NULL,
                antwort TEXT NOT NULL,
                erstellt_am TIMESTAMP DEFAULT now()
            )
            """
        )


def get_nachrichten(limit: int = 100):
    """Die letzten `limit` Nachrichten holen, älteste zuerst."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, frage, antwort, erstellt_am FROM (
                SELECT id, frage, antwort, erstellt_am
                FROM nachrichten
                ORDER BY id DESC
                LIMIT %s
            ) AS letzte
            ORDER BY id ASC
            """,
            (limit,),
        ).fetchall()
    return [
        {"id": r[0], "frage": r[1], "antwort": r[2], "erstellt_am": r[3]}
        for r in rows
    ]


def save_messages(frage: str, antwort: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO nachrichten (frage, antwort) VALUES (%s, %s)",
            (frage, antwort),
        )
