"""Tests für die Agent-Tools."""

import json

import pytest

import app.services.tools as tools
from app.services.tools import aktuelle_uhrzeit, rechnen, tool_ausfuehren


# ---------- Rechnen ----------

@pytest.mark.parametrize("ausdruck, erwartet", [
    ("2 + 3", 5),
    ("(12.5 * 4) / 3", 50 / 3),
    ("12,5 * 2", 25.0),      # Komma als Dezimaltrennzeichen
    ("2^10", 1024),          # ^ als Hoch-Zeichen
    ("-4 + 10 % 3", -3),
    ("2340 * 0.175", 409.5),
])
def test_rechnen(ausdruck, erwartet):
    assert rechnen(ausdruck)["ergebnis"] == pytest.approx(erwartet)


@pytest.mark.parametrize("gefaehrlich", [
    '__import__("os").system("dir")',
    "open('geheim.txt').read()",
    "[x for x in range(10)]",
    "9 ** 999999",
    "abc",
])
def test_rechnen_blockiert_gefaehrliches(gefaehrlich):
    ergebnis = json.loads(tool_ausfuehren("rechnen", json.dumps({"ausdruck": gefaehrlich})))
    assert "fehler" in ergebnis


def test_rechnen_division_durch_null():
    ergebnis = json.loads(tool_ausfuehren("rechnen", '{"ausdruck": "1/0"}'))
    assert "fehler" in ergebnis


# ---------- Uhrzeit ----------

def test_aktuelle_uhrzeit():
    ergebnis = aktuelle_uhrzeit()
    assert set(ergebnis) == {"datum", "uhrzeit", "wochentag", "zeitzone"}
    assert ergebnis["wochentag"] in tools.WOCHENTAGE


# ---------- Suche (mit Fake-Datenbank) ----------

class FakeConnection:
    """Tut so, als wäre es eine Datenbankverbindung, und merkt sich die Suchparameter."""

    def __init__(self):
        self.parameter = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, parameter):
        self.parameter = parameter
        return self

    def fetchall(self):
        return [("ist ai agent mit zukunft kann man damit brot verdeinen", "Ja!", None)]


def test_nachrichten_suchen_sucht_jedes_wort(monkeypatch):
    fake = FakeConnection()
    monkeypatch.setattr(tools, "get_connection", lambda: fake)

    ergebnis = tools.nachrichten_suchen("Brot verdienen")

    # Gesucht wird nach jedem Wort einzeln
    assert fake.parameter[0] == ["%Brot%", "%verdienen%"]
    assert ergebnis["treffer"][0]["antwort"] == "Ja!"


def test_nachrichten_suchen_ignoriert_kurze_woerter(monkeypatch):
    fake = FakeConnection()
    monkeypatch.setattr(tools, "get_connection", lambda: fake)

    tools.nachrichten_suchen("ob es Python gibt")

    assert fake.parameter[0] == ["%Python%", "%gibt%"]


# ---------- Allgemein ----------

def test_unbekanntes_tool():
    ergebnis = json.loads(tool_ausfuehren("alles_loeschen", "{}"))
    assert "Unbekanntes Tool" in ergebnis["fehler"]


def test_alle_tools_sind_beschrieben_und_registriert():
    beschrieben = {t["function"]["name"] for t in tools.TOOLS}
    assert beschrieben == set(tools.TOOL_FUNKTIONEN)
