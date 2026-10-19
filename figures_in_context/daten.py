"""Testfälle, Dokumente, Config und Laufdateien lesen und schreiben."""

import glob
import hashlib
import json
import re
import threading
from datetime import datetime
from pathlib import Path

BASIS = Path(__file__).resolve().parent.parent

FEHLERTYPEN = [
    "falsches_ergebnis",
    "falsche_quelle",
    "erfundene_zahl",
    "falsch_gerechnet",
    "ausgelassene_information",
]


def lade_json(pfad):
    return json.loads(Path(pfad).read_text(encoding="utf-8"))


def lade_config():
    return lade_json(BASIS / "config" / "lauf.json")


def lade_testfaelle(muster):
    faelle = []
    for datei in sorted(glob.glob(str(BASIS / muster))):
        faelle.extend(lade_json(datei))
    ids = [f["id"] for f in faelle]
    doppelt = {i for i in ids if ids.count(i) > 1}
    if doppelt:
        raise ValueError(f"Testfall-IDs doppelt vergeben: {sorted(doppelt)}")
    return {f["id"]: f for f in faelle}


def lade_prompt(name):
    return (BASIS / "prompts" / f"{name}.md").read_text(encoding="utf-8")


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


# --- Dokumente ---------------------------------------------------------------

_SEITE = re.compile(r"^###\s+Page\s+(\d+)\b", re.MULTILINE)


def _seitenzahlen(angabe):
    """1 → [1]; "1-2" → [1, 2]; "1,3" → [1, 3]."""
    if isinstance(angabe, int):
        return [angabe]
    zahlen = []
    for teil in str(angabe).split(","):
        if "-" in teil:
            von, bis = (int(x) for x in teil.split("-"))
            zahlen.extend(range(von, bis + 1))
        else:
            zahlen.append(int(teil))
    return zahlen


def dokument_ausschnitt(testfall):
    """Die Seiten, die die KI laut Testfall bekommt. Der Firmenkopf vor Seite 1 ist immer dabei."""
    text = (BASIS / "testfaelle" / testfall["dokument"]["datei"]).read_text(encoding="utf-8")
    treffer = list(_SEITE.finditer(text))
    if not treffer:
        return text
    kopf = text[: treffer[0].start()]
    seiten = {}
    for i, t in enumerate(treffer):
        ende = treffer[i + 1].start() if i + 1 < len(treffer) else len(text)
        seiten[int(t.group(1))] = text[t.start():ende]
    gewuenscht = _seitenzahlen(testfall["dokument"]["seite"])
    fehlt = [s for s in gewuenscht if s not in seiten]
    if fehlt:
        raise ValueError(f"{testfall['id']}: Seite(n) {fehlt} nicht im Dokument")
    return kopf + "".join(seiten[s] for s in gewuenscht)


def ganzes_dokument(testfall):
    return (BASIS / "testfaelle" / testfall["dokument"]["datei"]).read_text(encoding="utf-8")


# --- Laufdateien (JSONL) -------------------------------------------------------

_schreibsperre = threading.Lock()


def lies_jsonl(pfad):
    pfad = Path(pfad)
    if not pfad.exists():
        return []
    zeilen = [z for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]
    ergebnis = []
    for i, z in enumerate(zeilen):
        try:
            ergebnis.append(json.loads(z))
        except ValueError:
            if i < len(zeilen) - 1:
                raise
            # letzte Zeile wird gerade noch geschrieben (Web-App liest während eines Laufs mit)
    return ergebnis


def haenge_an(pfad, datensatz):
    with _schreibsperre, open(pfad, "a", encoding="utf-8") as f:
        f.write(json.dumps(datensatz, ensure_ascii=False) + "\n")


def antwort_schluessel(d):
    return f"{d['testfall_id']}|{d['modell']}|{d['wiederholung']}"


# --- Fortschritt ---------------------------------------------------------------
# Standard: Ausgabe im Terminal. Die Web-App ersetzt das, um Fortschritt anzuzeigen.

def _drucke(text):
    print(text, flush=True)


melde = _drucke


# --- Protokoll -----------------------------------------------------------------
# Jeder Lauf (und jede Kalibrierung) bekommt ein protokoll.jsonl: was wann passiert ist,
# jede Anfrage mit Modell, Dauer, Tokens und Ergebnis. Die Web-App zeigt es live an.

PROTOKOLL = "protokoll.jsonl"


def protokoll(laufordner, art, text="", **felder):
    """art: info, warnung, fehler, antwort, urteil. text wird zusätzlich angezeigt (melde)."""
    haenge_an(Path(laufordner) / PROTOKOLL,
              {"zeit": datetime.now().isoformat(timespec="seconds"), "art": art, "text": text, **felder})
    if text:
        melde(text)
