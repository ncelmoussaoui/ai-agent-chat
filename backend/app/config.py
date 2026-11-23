import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DATABASE_URL = os.getenv("DATABASE_URL")

# Wie viele vergangene Fragen+Antworten die KI bei jeder Anfrage "mitbekommt"
GEDAECHTNIS_ANZAHL = int(os.getenv("GEDAECHTNIS_ANZAHL", "10"))