from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class Nachricht(BaseModel):
    id: int
    frage: str
    antwort: str
    erstellt_am: datetime | None
