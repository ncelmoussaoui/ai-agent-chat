"""
Tools (Werkzeuge) für den AI Agent.

Jedes Tool besteht aus zwei Teilen:
1. Einer BESCHREIBUNG für OpenAI (in TOOLS) – daran erkennt die KI, wann und wie sie es benutzt.
2. Einer PYTHON-FUNKTION, die wirklich ausgeführt wird.

Die KI führt nie selbst Code aus. Sie sagt nur: "Bitte rufe Tool X mit diesen Argumenten auf".
Unser Code führt es aus und schickt das Ergebnis zurück an die KI.
"""

import ast
import json
import operator
from datetime import datetime
from zoneinfo import ZoneInfo

from app.database import get_connection


# ---------- Tool 1: Uhrzeit ----------

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def aktuelle_uhrzeit() -> dict:
    jetzt = datetime.now(ZoneInfo("Europe/Berlin"))
    return {
        "datum": jetzt.strftime("%d.%m.%Y"),
        "uhrzeit": jetzt.strftime("%H:%M"),
        "wochentag": WOCHENTAGE[jetzt.weekday()],
        "zeitzone": "Europe/Berlin",
    }


# ---------- Tool 2: Rechnen ----------
# Wichtig: NIEMALS eval() benutzen – damit könnte beliebiger Code ausgeführt werden.
# Stattdessen lesen wir den Ausdruck als Baum (ast) und erlauben nur Zahlen und Rechenzeichen.

ERLAUBTE_OPERATOREN = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _auswerten(knoten):
    if isinstance(knoten, ast.Constant) and isinstance(knoten.value, (int, float)):
        return knoten.value
    if isinstance(knoten, ast.BinOp) and type(knoten.op) in ERLAUBTE_OPERATOREN:
        links, rechts = _auswerten(knoten.left), _auswerten(knoten.right)
        if isinstance(knoten.op, ast.Pow) and abs(rechts) > 100:
            raise ValueError("Exponent zu groß (maximal 100)")
        return ERLAUBTE_OPERATOREN[type(knoten.op)](links, rechts)
    if isinstance(knoten, ast.UnaryOp) and type(knoten.op) in ERLAUBTE_OPERATOREN:
        return ERLAUBTE_OPERATOREN[type(knoten.op)](_auswerten(knoten.operand))
    raise ValueError("Nur Zahlen und + - * / // % ** und Klammern sind erlaubt")


def rechnen(ausdruck: str) -> dict:
    ausdruck = ausdruck.replace(",", ".").replace("^", "**")
    baum = ast.parse(ausdruck, mode="eval")
    return {"ausdruck": ausdruck, "ergebnis": _auswerten(baum.body)}


# ---------- Tool 3: Im Chatverlauf suchen ----------

def nachrichten_suchen(suchbegriff: str) -> dict:
    # Nach jedem Wort einzeln suchen ("Brot verdienen" findet auch "brot verdeinen").
    # Sehr kurze Wörter wie "ob" oder "es" ignorieren wir.
    woerter = [w for w in suchbegriff.split() if len(w) >= 3] or [suchbegriff]
    muster = [f"%{w}%" for w in woerter]

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT frage, antwort, erstellt_am
            FROM nachrichten
            WHERE frage ILIKE ANY(%s) OR antwort ILIKE ANY(%s)
            ORDER BY id DESC
            LIMIT 5
            """,
            (muster, muster),
        ).fetchall()
    return {
        "suchbegriff": suchbegriff,
        "treffer": [
            {
                "frage": r[0],
                "antwort": r[1][:300],  # gekürzt, damit es nicht zu lang wird
                "datum": r[2].strftime("%d.%m.%Y %H:%M") if r[2] else None,
            }
            for r in rows
        ],
    }


# ---------- Beschreibungen für OpenAI ----------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "aktuelle_uhrzeit",
            "description": "Gibt das aktuelle Datum, die Uhrzeit und den Wochentag zurück.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rechnen",
            "description": "Berechnet einen mathematischen Ausdruck exakt. "
                           "Benutze dieses Tool für jede Rechnung, statt selbst zu rechnen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ausdruck": {
                        "type": "string",
                        "description": "Rechenausdruck, z. B. '(12.5 * 4) / 3' oder '2 ** 10'",
                    }
                },
                "required": ["ausdruck"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "nachrichten_suchen",
            "description": "Durchsucht alle früheren Gespräche mit dem Nutzer in der Datenbank. "
                           "Benutze es, wenn der Nutzer nach etwas fragt, das er früher gesagt oder gefragt hat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "suchbegriff": {
                        "type": "string",
                        "description": "Ein oder mehrere Stichwörter, z. B. 'Python' oder 'Brot verdienen'. "
                                       "Gefunden wird alles, was mindestens eines der Wörter enthält.",
                    }
                },
                "required": ["suchbegriff"],
            },
        },
    },
]

# Name -> Python-Funktion
TOOL_FUNKTIONEN = {
    "aktuelle_uhrzeit": aktuelle_uhrzeit,
    "rechnen": rechnen,
    "nachrichten_suchen": nachrichten_suchen,
}


def tool_ausfuehren(name: str, argumente_json: str) -> str:
    """Führt ein Tool aus und gibt das Ergebnis als JSON-Text zurück (auch bei Fehlern)."""
    funktion = TOOL_FUNKTIONEN.get(name)
    if funktion is None:
        return json.dumps({"fehler": f"Unbekanntes Tool: {name}"})
    try:
        argumente = json.loads(argumente_json or "{}")
        ergebnis = funktion(**argumente)
    except Exception as e:
        # Fehler geben wir an die KI zurück – sie kann dann reagieren (z. B. neu versuchen)
        ergebnis = {"fehler": str(e)}
    return json.dumps(ergebnis, ensure_ascii=False, default=str)
