from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.services.tools import TOOLS, tool_ausfuehren

client = OpenAI(api_key=OPENAI_API_KEY)

# Der System-Prompt gibt der KI ihre Rolle. Er wird bei jeder Anfrage als erstes mitgeschickt.
SYSTEM_PROMPT = (
    "Du bist ein freundlicher und hilfsbereiter KI-Agent. "
    "Antworte in der Sprache, in der der Nutzer schreibt (meistens Deutsch). "
    "Erkläre verständlich und nicht zu lang. "
    "Nutze den bisherigen Gesprächsverlauf, um dich an frühere Aussagen des Nutzers zu erinnern. "
    "Du hast Tools: Benutze sie, wenn du Datum/Uhrzeit brauchst, etwas rechnen musst "
    "oder in älteren Gesprächen suchen sollst. Erfinde keine Uhrzeiten oder Rechenergebnisse."
)

# Sicherheitsgrenze: so oft darf die KI pro Frage höchstens Tools aufrufen
MAX_SCHRITTE = 5


def get_reply(message: str, verlauf: list[dict] | None = None) -> tuple[str, list[str]]:
    """
    Antwort vom Agenten holen.

    Gibt zurück: (antwort, liste_der_benutzten_tools)
    """
    # 1. Rolle der KI
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 2. Gedächtnis: frühere Fragen und Antworten
    for n in verlauf or []:
        messages.append({"role": "user", "content": n["frage"]})
        messages.append({"role": "assistant", "content": n["antwort"]})

    # 3. Die neue Frage
    messages.append({"role": "user", "content": message})

    benutzte_tools: list[str] = []

    # 4. Agent-Schleife: KI fragen -> Tools ausführen -> Ergebnis zurückgeben -> wieder fragen ...
    for _ in range(MAX_SCHRITTE):
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=TOOLS,
        )
        antwort = response.choices[0].message

        # Keine Tool-Aufrufe? Dann ist das die fertige Antwort.
        if not antwort.tool_calls:
            return antwort.content or "", benutzte_tools

        # Die KI möchte Tools benutzen: ihre Anfrage in den Verlauf aufnehmen ...
        messages.append({
            "role": "assistant",
            "content": antwort.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in antwort.tool_calls
            ],
        })

        # ... jedes Tool ausführen und das Ergebnis zurückgeben
        for tc in antwort.tool_calls:
            ergebnis = tool_ausfuehren(tc.function.name, tc.function.arguments)
            benutzte_tools.append(tc.function.name)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": ergebnis})

    return "Entschuldigung, ich habe zu viele Schritte gebraucht und abgebrochen.", benutzte_tools
