from datetime import datetime

from pydantic import BaseModel, Field, field_validator

MAX_LAENGE = 4000


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=MAX_LAENGE)

    @field_validator("message")
    @classmethod
    def nicht_leer(cls, wert: str) -> str:
        wert = wert.strip()  # Leerzeichen am Anfang/Ende entfernen
        if not wert:
            raise ValueError("Die Nachricht darf nicht leer sein")
        return wert


class ChatResponse(BaseModel):
    reply: str
    tools: list[str] = []  # welche Tools der Agent benutzt hat


class Nachricht(BaseModel):
    id: int
    frage: str
    antwort: str
    erstellt_am: datetime | None
