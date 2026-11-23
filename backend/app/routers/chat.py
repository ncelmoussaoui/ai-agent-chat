import psycopg
from fastapi import APIRouter, HTTPException, Query

from app.database import get_nachrichten, save_messages
from app.schemas.chat import ChatRequest, ChatResponse, Nachricht
from app.services.openai_service import get_reply

router = APIRouter()

DB_FEHLER = "Datenbankverbindung fehlgeschlagen (DATABASE_URL in .env prüfen)"


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        reply = get_reply(request.message)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI-Fehler: {e}")

    try:
        save_messages(request.message, reply)
    except psycopg.OperationalError as e:
        raise HTTPException(status_code=500, detail=f"{DB_FEHLER}: {e}")

    return ChatResponse(reply=reply)


@router.get("/nachrichten", response_model=list[Nachricht])
def nachrichten(limit: int = Query(100, ge=1, le=1000)):
    """Chatverlauf aus der Datenbank (älteste Nachricht zuerst)."""
    try:
        return get_nachrichten(limit)
    except psycopg.OperationalError as e:
        raise HTTPException(status_code=500, detail=f"{DB_FEHLER}: {e}")
