import logging

import openai
import psycopg
from fastapi import APIRouter, HTTPException, Query

from app.config import GEDAECHTNIS_ANZAHL
from app.database import get_nachrichten, save_messages
from app.schemas.chat import ChatRequest, ChatResponse, Nachricht
from app.services.openai_service import FehlenderApiKey, get_reply

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

DB_FEHLER = "Die Datenbank ist nicht erreichbar. Läuft PostgreSQL und stimmt DATABASE_URL in der .env?"


def openai_fehlermeldung(e: Exception) -> tuple[int, str]:
    """Technischen OpenAI-Fehler in eine verständliche Meldung übersetzen."""
    if isinstance(e, (FehlenderApiKey, openai.AuthenticationError)):
        return 502, "Der OpenAI-API-Key ist ungültig oder fehlt. Bitte OPENAI_API_KEY in der .env prüfen."
    if isinstance(e, openai.RateLimitError):
        return 429, "OpenAI-Limit erreicht (zu viele Anfragen oder kein Guthaben). Bitte später erneut versuchen."
    if isinstance(e, openai.NotFoundError):
        return 502, "Das OpenAI-Modell wurde nicht gefunden. Bitte OPENAI_MODEL in der .env prüfen."
    if isinstance(e, openai.APIConnectionError):
        return 503, "OpenAI ist nicht erreichbar. Bitte Internetverbindung prüfen."
    return 502, "Bei der Anfrage an OpenAI ist ein Fehler aufgetreten."


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # 1. Gedächtnis: die letzten Unterhaltungen aus der Datenbank holen
    try:
        verlauf = get_nachrichten(GEDAECHTNIS_ANZAHL)
    except psycopg.Error:
        logger.exception("Datenbankfehler beim Laden des Verlaufs")
        raise HTTPException(status_code=500, detail=DB_FEHLER)

    # 2. Agent fragen
    try:
        reply, tools = get_reply(request.message, verlauf)
    except Exception as e:
        logger.exception("Fehler bei der OpenAI-Anfrage")
        status, meldung = openai_fehlermeldung(e)
        raise HTTPException(status_code=status, detail=meldung)

    # 3. Frage + Antwort speichern
    try:
        save_messages(request.message, reply)
    except psycopg.Error:
        logger.exception("Datenbankfehler beim Speichern")
        raise HTTPException(status_code=500, detail=DB_FEHLER)

    return ChatResponse(reply=reply, tools=tools)


@router.get("/nachrichten", response_model=list[Nachricht])
def nachrichten(limit: int = Query(100, ge=1, le=1000)):
    """Chatverlauf aus der Datenbank (älteste Nachricht zuerst)."""
    try:
        return get_nachrichten(limit)
    except psycopg.Error:
        logger.exception("Datenbankfehler beim Laden des Verlaufs")
        raise HTTPException(status_code=500, detail=DB_FEHLER)
