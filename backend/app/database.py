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


def save_messages(frage: str, antwort: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO nachrichten (frage, antwort) VALUES (%s, %s)",
            (frage, antwort),
        )
