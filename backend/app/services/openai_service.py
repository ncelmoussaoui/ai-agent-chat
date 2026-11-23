from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

# Der System-Prompt gibt der KI ihre Rolle. Er wird bei jeder Anfrage als erstes mitgeschickt.
SYSTEM_PROMPT = (
    "Du bist ein freundlicher und hilfsbereiter KI-Assistent. "
    "Antworte in der Sprache, in der der Nutzer schreibt (meistens Deutsch). "
    "Erkläre verständlich und nicht zu lang. "
    "Nutze den bisherigen Gesprächsverlauf, um dich an frühere Aussagen des Nutzers zu erinnern."
)


def get_reply(message: str, verlauf: list[dict] | None = None) -> str:
    """
    Antwort von OpenAI holen.

    verlauf = frühere Nachrichten aus der Datenbank, z. B.
    [{"frage": "Ich heiße Max", "antwort": "Hallo Max!"}, ...]
    """
    # 1. Rolle der KI
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 2. Gedächtnis: frühere Fragen und Antworten
    for n in verlauf or []:
        messages.append({"role": "user", "content": n["frage"]})
        messages.append({"role": "assistant", "content": n["antwort"]})

    # 3. Die neue Frage
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
    )
    return response.choices[0].message.content or ""
