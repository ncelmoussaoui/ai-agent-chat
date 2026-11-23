# AI Agent Chat

Ein KI-Agent mit Chat-Oberfläche, Gedächtnis und eigenen Werkzeugen (Tools) – gebaut als Lernprojekt mit **FastAPI**, **PostgreSQL**, **OpenAI** und **Vanilla JavaScript**.

Der Agent beantwortet Fragen, erinnert sich an frühere Gespräche und entscheidet selbst, wann er ein Tool benutzt – zum Beispiel um exakt zu rechnen, die aktuelle Uhrzeit abzufragen oder im eigenen Chatverlauf zu suchen.

<!-- Screenshot einfügen: Bild unter docs/screenshot.png speichern und die nächste Zeile einkommentieren -->
<!-- ![Screenshot](docs/screenshot.png) -->

## Funktionen

- **Chat-Oberfläche** mit Chat-Blasen, Ladeanzeige, hellem/dunklem Modus und Handy-Ansicht
- **Gespeicherter Verlauf** – alle Fragen und Antworten landen in PostgreSQL und sind nach dem Neuladen noch da
- **Gedächtnis** – die letzten Gespräche werden bei jeder Frage an die KI mitgeschickt
- **Agent mit Tools** (OpenAI Function Calling):
  | Tool | Aufgabe |
  |---|---|
  | `aktuelle_uhrzeit` | Datum, Uhrzeit und Wochentag |
  | `rechnen` | exakte Berechnungen (sicher, ohne `eval`) |
  | `nachrichten_suchen` | Suche in allen früheren Gesprächen |
- **Fehlerbehandlung** – verständliche Meldungen bei fehlender Datenbank, falschem API-Key, leeren Eingaben usw.
- **35 automatische Tests** mit pytest (ohne echte Datenbank und ohne OpenAI-Kosten)

## So funktioniert der Agent

```mermaid
sequenceDiagram
    participant U as Browser
    participant B as FastAPI
    participant DB as PostgreSQL
    participant AI as OpenAI

    U->>B: POST /chat {"message": "..."}
    B->>DB: letzte 10 Gespräche laden (Gedächtnis)
    B->>AI: System-Prompt + Verlauf + Frage + Tool-Liste
    loop bis zu 5 Mal
        AI-->>B: "Bitte Tool X aufrufen"
        B->>B: Tool ausführen
        B->>AI: Ergebnis des Tools
    end
    AI-->>B: fertige Antwort
    B->>DB: Frage + Antwort speichern
    B-->>U: {"reply": "...", "tools": [...]}
```

Wichtig: Die KI führt nie selbst Code aus. Sie *bittet* nur darum, ein Tool aufzurufen – das Backend entscheidet, was wirklich passiert.

## Projektstruktur

```
ai-agent-chat/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI-App, CORS, Start
│   │   ├── config.py               # Einstellungen aus der .env
│   │   ├── database.py             # PostgreSQL: Tabelle anlegen, lesen, speichern
│   │   ├── routers/chat.py         # Endpunkte /chat und /nachrichten
│   │   ├── schemas/chat.py         # Datenformate + Eingabeprüfung
│   │   └── services/
│   │       ├── openai_service.py   # Agent-Schleife, System-Prompt, Gedächtnis
│   │       └── tools.py            # Die Tools des Agenten
│   ├── tests/                      # pytest-Tests
│   ├── .env.example                # Vorlage für die Konfiguration
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

## Installation

### Voraussetzungen
- Python 3.12 oder neuer
- PostgreSQL (z. B. mit pgAdmin)
- Ein OpenAI-API-Key ([platform.openai.com](https://platform.openai.com/api-keys))

### 1. Datenbank anlegen
In pgAdmin (oder psql) eine leere Datenbank erstellen:
```sql
CREATE DATABASE agent_db;
```
Die Tabelle `nachrichten` legt das Backend beim ersten Start automatisch an.

### 2. Backend einrichten
```powershell
cd backend
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

`.env.example` nach `.env` kopieren und eigene Werte eintragen:
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=postgresql://postgres:DEIN_PASSWORT@localhost:5432/agent_db
GEDAECHTNIS_ANZAHL=10
```
> Sonderzeichen im Passwort müssen in der URL kodiert werden (z. B. `@` → `%40`).

### 3. Starten

**Terminal 1 – Backend:**
```powershell
cd backend
venv\Scripts\activate
python -m uvicorn app.main:app --reload
```

**Terminal 2 – Frontend:**
```powershell
cd frontend
python -m http.server 5500
```

Dann im Browser öffnen: **http://127.0.0.1:5500**
Die API-Dokumentation gibt es unter **http://127.0.0.1:8000/docs**.

## Tests

```powershell
cd backend
venv\Scripts\activate
python -m pytest -v
```

Die Tests ersetzen Datenbank und OpenAI durch Fakes – sie sind schnell, kostenlos und verändern keine echten Daten.

## API

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/` | Statusprüfung → `{"status": "ok"}` |
| `POST` | `/chat` | Body `{"message": "..."}` → `{"reply": "...", "tools": [...]}` |
| `GET` | `/nachrichten?limit=100` | Chatverlauf, älteste Nachricht zuerst (limit 1–1000) |

## Ein eigenes Tool hinzufügen

In `backend/app/services/tools.py`:

1. Eine Python-Funktion schreiben, die ein `dict` zurückgibt
2. Das Tool in der Liste `TOOLS` beschreiben (Name, Beschreibung, Parameter)
3. Den Namen in `TOOL_FUNKTIONEN` eintragen

Der Test `test_alle_tools_sind_beschrieben_und_registriert` prüft, dass Schritt 2 und 3 zusammenpassen.

## Sicherheit

- Die `.env` mit API-Key und Passwort wird **nie** committet (`.gitignore`).
- Das Rechen-Tool benutzt kein `eval()`, sondern erlaubt nur Zahlen und Rechenzeichen.
- Fehlermeldungen an den Browser enthalten keine internen Details (die stehen nur im Server-Log).
- CORS ist für die lokale Entwicklung offen (`*`). Für einen Einsatz im Internet sollte man es auf die eigene Domain beschränken und einen Login einbauen.

## Ideen für Erweiterungen

- Mehrere getrennte Chats (Spalte `chat_id`)
- Login, damit jeder Nutzer nur seine eigenen Nachrichten sieht
- Streaming: Antwort erscheint Wort für Wort
- Weitere Tools, z. B. Wetter oder Websuche
- Online stellen (z. B. Render oder Railway)

## Technologien

Python · FastAPI · Pydantic · psycopg 3 · PostgreSQL · OpenAI API · HTML · CSS · JavaScript · pytest
