// Adresse deines FastAPI-Backends
const API_URL = "http://127.0.0.1:8000";

// Elemente aus der HTML-Seite holen
const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("input");
const sendButton = document.getElementById("send");
const statusText = document.getElementById("status");

// Eine Chat-Blase hinzufügen. role = "user", "assistant" oder "error"
function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text; // textContent statt innerHTML = sicher gegen eingeschleusten HTML-Code
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight; // nach unten scrollen
  return div;
}

// Ladeanzeige (drei Punkte) anzeigen, während die KI antwortet
function showTyping() {
  const div = document.createElement("div");
  div.className = "message assistant typing";
  div.innerHTML = "<span></span><span></span><span></span>";
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

// Eingabe sperren/freigeben, damit man nicht doppelt sendet
function setLoading(isLoading) {
  sendButton.disabled = isLoading;
  input.disabled = isLoading;
  statusText.textContent = isLoading ? "KI denkt nach..." : "Bereit";
}

// Nachricht an das Backend schicken und Antwort zurückgeben
async function sendToBackend(message) {
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: message }),
  });

  const data = await response.json();

  if (!response.ok) {
    // FastAPI schickt Fehler im Feld "detail"
    const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    throw new Error(`Fehler ${response.status}: ${detail}`);
  }

  return data.reply;
}

// Wird ausgeführt, wenn man auf "Senden" klickt oder Enter drückt
form.addEventListener("submit", async (event) => {
  event.preventDefault(); // verhindert, dass die Seite neu lädt

  const message = input.value.trim();
  if (!message) return; // leere Nachrichten ignorieren

  addMessage(message, "user");
  input.value = "";
  autoResize();

  setLoading(true);
  const typing = showTyping();

  try {
    const reply = await sendToBackend(message);
    typing.remove();
    addMessage(reply, "assistant");
  } catch (error) {
    typing.remove();
    if (error instanceof TypeError) {
      // TypeError bei fetch = Server nicht erreichbar
      addMessage("Server nicht erreichbar. Läuft das Backend (uvicorn)?", "error");
    } else {
      addMessage(error.message, "error");
    }
  } finally {
    setLoading(false);
    input.focus();
  }
});

// Enter = senden, Shift+Enter = neue Zeile
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

// Eingabefeld wächst mit dem Text mit
function autoResize() {
  input.style.height = "auto";
  input.style.height = input.scrollHeight + "px";
}
input.addEventListener("input", autoResize);

// Chatverlauf aus der Datenbank laden (wird beim Öffnen der Seite ausgeführt)
async function loadHistory() {
  statusText.textContent = "Lade Verlauf...";
  try {
    const response = await fetch(`${API_URL}/nachrichten`);
    if (!response.ok) {
      const data = await response.json();
      throw new Error(`Fehler ${response.status}: ${data.detail}`);
    }
    const nachrichten = await response.json();

    if (nachrichten.length === 0) {
      addMessage("Hallo! Ich bin dein KI-Assistent. Stell mir eine Frage.", "assistant");
    }

    // Jede Zeile aus der Tabelle = eine Frage + eine Antwort
    for (const n of nachrichten) {
      addMessage(n.frage, "user");
      addMessage(n.antwort, "assistant");
    }
  } catch (error) {
    if (error instanceof TypeError) {
      addMessage("Verlauf konnte nicht geladen werden: Server nicht erreichbar. Läuft das Backend (uvicorn)?", "error");
    } else {
      addMessage(`Verlauf konnte nicht geladen werden. ${error.message}`, "error");
    }
  } finally {
    statusText.textContent = "Bereit";
  }
}

loadHistory();
input.focus();
