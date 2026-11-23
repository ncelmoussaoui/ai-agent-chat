import psycopg
from fastapi import APIRouter, HTTPException

from app.database import save_messages
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.openai_service import get_reply

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        reply = get_reply(request.message)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI-Fehler: {e}")

    try:
        save_messages(request.message, reply)
    except psycopg.OperationalError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Datenbankverbindung fehlgeschlagen (DATABASE_URL in .env prüfen): {e}",
        )

    return ChatResponse(reply=reply)
