"""
Tests für die API-Endpunkte.

Datenbank und OpenAI werden durch Fake-Funktionen ersetzt (monkeypatch).
So laufen die Tests schnell, kostenlos und verändern keine echten Daten.
"""

import psycopg
import pytest
from fastapi.testclient import TestClient

import app.routers.chat as chat_router
from app.main import app
from app.services.openai_service import FehlenderApiKey

client = TestClient(app)


@pytest.fixture
def fake_backend(monkeypatch):
    """Ersetzt Datenbank und OpenAI durch Fakes und merkt sich, was gespeichert wurde."""
    gespeichert = []

    monkeypatch.setattr(chat_router, "get_nachrichten", lambda limit: [
        {"id": 1, "frage": "Ich heiße Sam", "antwort": "Hallo Sam!", "erstellt_am": None},
    ])
    monkeypatch.setattr(chat_router, "save_messages", lambda f, a: gespeichert.append((f, a)))
    monkeypatch.setattr(chat_router, "get_reply", lambda msg, verlauf: (f"Echo: {msg}", ["rechnen"]))
    return gespeichert


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_erfolgreich(fake_backend):
    response = client.post("/chat", json={"message": "  Hallo  "})

    assert response.status_code == 200
    assert response.json() == {"reply": "Echo: Hallo", "tools": ["rechnen"]}
    # Leerzeichen wurden entfernt, Frage und Antwort gespeichert
    assert fake_backend == [("Hallo", "Echo: Hallo")]


@pytest.mark.parametrize("body", [
    {"message": ""},
    {"message": "    "},
    {"message": "x" * 4001},
    {},
    {"falsches_feld": "Hallo"},
])
def test_chat_ungueltige_eingabe(fake_backend, body):
    response = client.post("/chat", json=body)
    assert response.status_code == 422
    assert fake_backend == []  # nichts gespeichert


def test_chat_datenbank_fehler(monkeypatch):
    def db_kaputt(limit):
        raise psycopg.OperationalError("Passwort falsch")

    monkeypatch.setattr(chat_router, "get_nachrichten", db_kaputt)
    response = client.post("/chat", json={"message": "Hallo"})

    assert response.status_code == 500
    assert "Datenbank ist nicht erreichbar" in response.json()["detail"]
    assert "Passwort falsch" not in response.json()["detail"]  # keine internen Details nach außen


def test_chat_ohne_api_key(fake_backend, monkeypatch):
    def kein_key(msg, verlauf):
        raise FehlenderApiKey()

    monkeypatch.setattr(chat_router, "get_reply", kein_key)
    response = client.post("/chat", json={"message": "Hallo"})

    assert response.status_code == 502
    assert "API-Key" in response.json()["detail"]
    assert fake_backend == []


def test_nachrichten(fake_backend):
    response = client.get("/nachrichten")
    assert response.status_code == 200
    assert response.json()[0]["frage"] == "Ich heiße Sam"


@pytest.mark.parametrize("limit", [0, 1001, -5])
def test_nachrichten_ungueltiges_limit(fake_backend, limit):
    response = client.get(f"/nachrichten?limit={limit}")
    assert response.status_code == 422
