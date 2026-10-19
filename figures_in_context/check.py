"""Stufe 2: Python-Check. Kein KI-Modell. → checks.jsonl

Liest die RESULT-Zeile, prüft das Format und vergleicht exakt mit der Musterlösung.
"""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from . import daten

_RESULT_ZEILE = re.compile(r"^\W*RESULT\s*:(.*)$", re.IGNORECASE | re.MULTILINE)
_ZAHLWOERTER = re.compile(
    r"(?:(?<=\d)|\b)(thousand|million|millions|mn|mio|billion|billions|bn|bln|mrd|trillion|k|m|b)\b", re.IGNORECASE
)
_ZAHL = r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|[+-]?\.\d+"
_ZAHL_DANN_EINHEIT = re.compile(rf"^({_ZAHL})(?![\d,.])\s*(.*)$")
_EINHEIT_DANN_ZAHL = re.compile(rf"^(\D+?)\s*({_ZAHL})$")


def _einheiten_tabelle():
    tabelle = {}
    for norm, schreibweisen in daten.lade_json(daten.BASIS / "config" / "einheiten.json").items():
        for s in schreibweisen:
            tabelle[s.lower()] = norm
    return tabelle


_EINHEITEN = None


def normiere_einheit(einheit):
    global _EINHEITEN
    if _EINHEITEN is None:
        _EINHEITEN = _einheiten_tabelle()
    e = einheit.strip().rstrip(".").strip()
    return _EINHEITEN.get(e.lower(), e.upper())


def lies_result(text):
    """→ (wert: Decimal | None, einheit: str | None, formatfehler: str | None)"""
    zeilen = _RESULT_ZEILE.findall(text or "")
    if not zeilen:
        return None, None, "keine RESULT-Zeile"
    if len(zeilen) > 1:
        return None, None, "mehr als eine RESULT-Zeile"
    inhalt = zeilen[0].replace("*", "").replace("`", "").strip()
    if _ZAHLWOERTER.search(inhalt):
        return None, None, "Zahlwort in der RESULT-Zeile"

    m = _ZAHL_DANN_EINHEIT.match(inhalt)
    if m:
        zahl, einheit = m.group(1), m.group(2)
    else:
        m = _EINHEIT_DANN_ZAHL.match(inhalt)
        if not m:
            return None, None, "Zahl nicht lesbar"
        einheit, zahl = m.group(1), m.group(2)
    if not einheit.strip():
        return None, None, "Einheit fehlt"
    try:
        wert = Decimal(zahl.replace(",", ""))
    except InvalidOperation:
        return None, None, "Zahl nicht lesbar"
    return wert, normiere_einheit(einheit), None


def vergleiche(wert, einheit, musterloesung):
    """Hero's Regel: exakt gleich; nur bei exakt=false wird kaufmännisch auf n Stellen gerundet."""
    if einheit != normiere_einheit(musterloesung["einheit"]):
        return False
    soll = Decimal(musterloesung["wert"])
    if musterloesung.get("exakt", True):
        return wert == soll
    stellen = Decimal(1).scaleb(-int(musterloesung["nachkommastellen"]))
    return wert.quantize(stellen, rounding=ROUND_HALF_UP) == soll


def pruefe(antwort, testfall):
    wert, einheit, formatfehler = lies_result(antwort["antwort_text"])
    return {
        "testfall_id": antwort["testfall_id"],
        "modell": antwort["modell"],
        "wiederholung": antwort["wiederholung"],
        "format_ok": formatfehler is None,
        "format_grund": formatfehler,
        "wert_ki": None if wert is None else str(wert),
        "einheit_ki": einheit,
        "ergebnis_richtig": None if formatfehler else vergleiche(wert, einheit, testfall["musterloesung"]),
    }


def lauf(laufordner, testfaelle):
    antworten = daten.lies_jsonl(laufordner / "antworten.jsonl")
    ziel = laufordner / "checks.jsonl"
    ziel.write_text("", encoding="utf-8")  # günstig, wird immer komplett neu berechnet
    zaehler = {"richtig": 0, "falsch": 0, "format": 0}
    for a in antworten:
        c = pruefe(a, testfaelle[a["testfall_id"]])
        daten.haenge_an(ziel, c)
        zaehler["format" if not c["format_ok"] else "richtig" if c["ergebnis_richtig"] else "falsch"] += 1
    daten.protokoll(laufordner, "info", f"Python-Check: {zaehler['richtig']} richtig, {zaehler['falsch']} falsch, "
                                        f"{zaehler['format']} Formatfehler.")
