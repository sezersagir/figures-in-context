"""Eine dünne Schicht pro Anbieter. Alle liefern dasselbe Ergebnis-Dict.

frage(ziel, system, text, schema=None, kontext=None) -> {
    "text": str, "tokens_rein": int, "tokens_raus": int, "abbruchgrund": str, "versuche": int
}

ziel ist ein Eintrag aus config/lauf.json, z. B. {"anbieter": "openai", "modell": "gpt-5"}.
schema (JSON-Schema) erzwingt eine JSON-Antwort über die Structured-Output-Funktion des Anbieters.

Bewusst nur Standardbibliothek (urllib): Es muss nichts per pip installiert werden.
API-Schlüssel kommen aus der .env-Datei (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY).
"""

import json
import os
import random
import time
import urllib.error
import urllib.request

from . import daten
from .daten import BASIS

SCHLUESSEL = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "google": "GEMINI_API_KEY"}
ENV_DATEI = BASIS / ".env"
VERSUCHE = 5
TIMEOUT = 600


class ApiFehler(Exception):
    pass


def lade_env():
    if not ENV_DATEI.exists():
        return
    for zeile in ENV_DATEI.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if zeile and not zeile.startswith("#") and "=" in zeile:
            name, wert = zeile.split("=", 1)
            wert = wert.strip().strip('"').strip("'")
            if wert:
                os.environ[name.strip()] = wert


lade_env()


def schluessel(anbieter):
    name = SCHLUESSEL[anbieter]
    wert = os.environ.get(name) or (os.environ.get("GOOGLE_API_KEY") if anbieter == "google" else None)
    if not wert:
        raise ApiFehler(f"Kein API-Schlüssel für {anbieter}. {name} in der .env eintragen.")
    return wert


def modell_name(ziel):
    return f"{ziel['anbieter']}:{ziel['modell']}"


def frage(ziel, system, text, schema=None, kontext=None):
    anbieter = ziel["anbieter"]
    if anbieter == "anthropic":
        return _anthropic(ziel, system, text, schema)
    if anbieter == "openai":
        return _openai(ziel, system, text, schema)
    if anbieter == "google":
        return _google(ziel, system, text, schema)
    if anbieter == "test":
        return _test(ziel, schema, kontext)
    raise ApiFehler(f"Unbekannter Anbieter: {anbieter}")


def _post(url, kopf, inhalt):
    """POST mit JSON. Wiederholt bei Rate-Limit, Überlastung, Serverfehlern und Netzwerkproblemen.
    → (Antwort-JSON, Anzahl Versuche)"""
    koerper = json.dumps(inhalt).encode("utf-8")
    for versuch in range(1, VERSUCHE + 1):
        anfrage = urllib.request.Request(url, data=koerper, method="POST",
                                         headers={"Content-Type": "application/json", **kopf})
        try:
            with urllib.request.urlopen(anfrage, timeout=TIMEOUT) as antwort:
                return json.loads(antwort.read().decode("utf-8")), versuch
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")[:500]
            wiederholbar = e.code in (408, 409, 429) or e.code >= 500
            if not wiederholbar or versuch == VERSUCHE:
                raise ApiFehler(f"HTTP {e.code}: {text}") from None
            warten = float(e.headers.get("retry-after") or 0) or min(60, 2 ** versuch)
            grund = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if versuch == VERSUCHE:
                raise ApiFehler(f"Keine Verbindung: {e}") from None
            warten = min(60, 2 ** versuch)
            grund = "keine Verbindung"
        daten.melde(f"  {grund} bei {url.split('/')[2]}, Versuch {versuch + 1}/{VERSUCHE} in {warten:.0f} s")
        time.sleep(warten + random.random())


def _anthropic(ziel, system, text, schema):
    inhalt = {
        "model": ziel["modell"],
        "max_tokens": 16000,
        "system": system,
        "messages": [{"role": "user", "content": text}],
    }
    if ziel.get("effort"):
        inhalt["output_config"] = {"effort": ziel["effort"]}
    if schema:
        inhalt.setdefault("output_config", {})["format"] = {"type": "json_schema", "schema": schema}
    # Bewusst ohne Fallback auf ein anderes Modell: Eine Antwort von einem Ersatzmodell
    # würde die Messung des getesteten Modells verfälschen.
    a, versuche = _post("https://api.anthropic.com/v1/messages",
              {"x-api-key": schluessel("anthropic"), "anthropic-version": "2023-06-01"}, inhalt)
    return {
        "text": "".join(b.get("text", "") for b in a.get("content", []) if b.get("type") == "text"),
        "tokens_rein": a.get("usage", {}).get("input_tokens"),
        "tokens_raus": a.get("usage", {}).get("output_tokens"),
        "abbruchgrund": a.get("stop_reason"),
        "versuche": versuche,
    }


def _openai(ziel, system, text, schema):
    inhalt = {"model": ziel["modell"], "instructions": system, "input": text}
    if ziel.get("effort"):
        inhalt["reasoning"] = {"effort": ziel["effort"]}
    if schema:
        inhalt["text"] = {"format": {"type": "json_schema", "name": "urteil", "schema": schema, "strict": True}}
    a, versuche = _post("https://api.openai.com/v1/responses",
              {"Authorization": f"Bearer {schluessel('openai')}"}, inhalt)
    teile = [c.get("text", "") for item in a.get("output", []) if item.get("type") == "message"
             for c in item.get("content", []) if c.get("type") == "output_text"]
    nutzung = a.get("usage") or {}
    return {
        "text": "".join(teile),
        "tokens_rein": nutzung.get("input_tokens"),
        "tokens_raus": nutzung.get("output_tokens"),
        "abbruchgrund": a.get("status"),
        "versuche": versuche,
    }


def _google(ziel, system, text, schema):
    inhalt = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
    }
    if schema:
        inhalt["generationConfig"] = {"responseMimeType": "application/json", "responseJsonSchema": schema}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{ziel['modell']}:generateContent"
    a, versuche = _post(url, {"x-goog-api-key": schluessel("google")}, inhalt)
    kandidat = (a.get("candidates") or [{}])[0]
    teile = [p.get("text", "") for p in kandidat.get("content", {}).get("parts", []) if not p.get("thought")]
    nutzung = a.get("usageMetadata") or {}
    return {
        "text": "".join(teile),
        "tokens_rein": nutzung.get("promptTokenCount"),
        "tokens_raus": nutzung.get("candidatesTokenCount"),
        "abbruchgrund": kandidat.get("finishReason"),
        "versuche": versuche,
    }


# --- Testmodell: probt die Pipeline ohne API-Schlüssel und ohne Kosten --------

def _test(ziel, schema, kontext):
    rnd = random.Random(json.dumps(kontext, sort_keys=True, default=str) + ziel["modell"])
    if schema:
        erlaubt = schema["properties"]["fehlertypen"]["items"]["enum"]
        typen = [rnd.choice(erlaubt)] if rnd.random() < 0.25 else []
        urteil = {
            "flag": bool(typen),
            "fehlertypen": typen,
            "befund": "Testurteil." if typen else "No problems found (test model).",
            "belege": [],
            "sicherheit": "mittel",
        }
        return {"text": json.dumps(urteil), "tokens_rein": 0, "tokens_raus": 0, "abbruchgrund": "test", "versuche": 1}

    loesung = kontext["musterloesung"]
    wurf = rnd.random() if ziel["modell"] == "zufall" else 0.0
    if wurf < 0.6:
        zeile = f"RESULT: {loesung['wert']} {loesung['einheit']}"
    elif wurf < 0.85:
        zeile = f"RESULT: {loesung['wert']}1 {loesung['einheit']}"
    elif wurf < 0.95:
        zeile = f"RESULT: {loesung['wert']} million {loesung['einheit']}"
    else:
        zeile = "The result could not be determined."
    return {"text": "Working (test model).\n\n" + zeile, "tokens_rein": 0, "tokens_raus": 0, "abbruchgrund": "test", "versuche": 1}
