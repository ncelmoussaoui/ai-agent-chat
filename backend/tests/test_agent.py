"""
Tests für die Agent-Schleife.

Statt OpenAI benutzen wir einen Fake-Client, der vorher festgelegte Antworten zurückgibt.
"""

import json
from types import SimpleNamespace

import app.services.openai_service as agent


def tool_aufruf(name, argumente, id="call_1"):
    return SimpleNamespace(id=id, function=SimpleNamespace(name=name, arguments=json.dumps(argumente)))


def ki_antwort(text=None, tool_calls=None):
    nachricht = SimpleNamespace(content=text, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=nachricht)])


class FakeOpenAI:
    """Gibt nacheinander die vorbereiteten Antworten zurück und merkt sich jede Anfrage."""

    def __init__(self, antworten):
        self.antworten = list(antworten)
        self.anfragen = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        # Kopie speichern, weil die Liste danach weiter verändert wird
        self.anfragen.append([dict(m) for m in kwargs["messages"]])
        if len(self.antworten) > 1:
            return self.antworten.pop(0)
        return self.antworten[0]


def test_antwort_ohne_tool(monkeypatch):
    fake = FakeOpenAI([ki_antwort("Hallo!")])
    monkeypatch.setattr(agent, "get_client", lambda: fake)

    antwort, tools = agent.get_reply("Hi")

    assert antwort == "Hallo!"
    assert tools == []


def test_gedaechtnis_wird_mitgeschickt(monkeypatch):
    fake = FakeOpenAI([ki_antwort("Du heißt Sam.")])
    monkeypatch.setattr(agent, "get_client", lambda: fake)

    agent.get_reply("Wie heiße ich?", [{"frage": "Ich heiße Sam", "antwort": "Hallo Sam!"}])

    rollen = [(m["role"], m["content"]) for m in fake.anfragen[0]]
    assert rollen[0][0] == "system"
    assert rollen[1:] == [
        ("user", "Ich heiße Sam"),
        ("assistant", "Hallo Sam!"),
        ("user", "Wie heiße ich?"),
    ]


def test_agent_benutzt_tool_und_bekommt_ergebnis(monkeypatch):
    fake = FakeOpenAI([
        ki_antwort(tool_calls=[tool_aufruf("rechnen", {"ausdruck": "2 + 3"})]),  # 1. KI will rechnen
        ki_antwort("Das Ergebnis ist 5."),                                        # 2. KI antwortet
    ])
    monkeypatch.setattr(agent, "get_client", lambda: fake)

    antwort, tools = agent.get_reply("Was ist 2 + 3?")

    assert antwort == "Das Ergebnis ist 5."
    assert tools == ["rechnen"]

    # Bei der 2. Anfrage muss das Tool-Ergebnis dabei sein
    letzte = fake.anfragen[1][-1]
    assert letzte["role"] == "tool"
    assert letzte["tool_call_id"] == "call_1"
    assert json.loads(letzte["content"])["ergebnis"] == 5


def test_agent_bricht_nach_max_schritten_ab(monkeypatch):
    # Die KI will endlos Tools aufrufen
    fake = FakeOpenAI([ki_antwort(tool_calls=[tool_aufruf("aktuelle_uhrzeit", {})])])
    monkeypatch.setattr(agent, "get_client", lambda: fake)

    antwort, tools = agent.get_reply("Endlosschleife?")

    assert "zu viele Schritte" in antwort
    assert len(tools) == agent.MAX_SCHRITTE
    assert len(fake.anfragen) == agent.MAX_SCHRITTE


def test_fehlender_api_key(monkeypatch):
    monkeypatch.setattr(agent, "OPENAI_API_KEY", None)
    monkeypatch.setattr(agent, "_client", None)

    try:
        agent.get_client()
        assert False, "Es hätte ein Fehler kommen müssen"
    except agent.FehlenderApiKey:
        pass
