"""Stufe 1: Das getestete Modell beantwortet jede Frage. → antworten.jsonl"""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import check, daten, modelle


def nutzertext(testfall):
    return f"<document>\n{daten.dokument_ausschnitt(testfall)}\n</document>\n\nQuestion: {testfall['frage']}"


def lauf(laufordner, config, testfaelle):
    ziel_datei = laufordner / "antworten.jsonl"
    vorhanden = {daten.antwort_schluessel(d) for d in daten.lies_jsonl(ziel_datei)}
    system = daten.lade_prompt("testobjekt")

    auftraege = []
    for ziel in config["testobjekte"]:
        for testfall in testfaelle.values():
            for w in range(1, config["wiederholungen"] + 1):
                d = {"testfall_id": testfall["id"], "modell": modelle.modell_name(ziel), "wiederholung": w}
                if daten.antwort_schluessel(d) not in vorhanden:
                    auftraege.append((ziel, testfall, d))

    daten.protokoll(laufordner, "info", f"Antworten: {len(vorhanden)} schon vorhanden, {len(auftraege)} werden angefragt.")
    fehler = 0
    erledigt = 0

    def eins(auftrag):
        nonlocal fehler, erledigt
        try:
            _eins(auftrag)
        finally:
            erledigt += 1
            daten.melde(f"Antworten: {erledigt}/{len(auftraege)}")

    def _eins(auftrag):
        nonlocal fehler
        ziel, testfall, d = auftrag
        beginn = time.monotonic()
        try:
            ergebnis = modelle.frage(ziel, system, nutzertext(testfall), kontext=testfall)
        except Exception as e:  # Fehler nicht speichern, damit der nächste Aufruf es erneut versucht
            fehler += 1
            daten.protokoll(laufordner, "fehler", f"  FEHLER {daten.antwort_schluessel(d)}: {type(e).__name__}: {e}",
                            schritt="antwort", **d, dauer_s=round(time.monotonic() - beginn, 1))
            return
        daten.haenge_an(ziel_datei, {
            **d,
            "antwort_text": ergebnis["text"],
            "tokens_rein": ergebnis["tokens_rein"],
            "tokens_raus": ergebnis["tokens_raus"],
            "abbruchgrund": ergebnis["abbruchgrund"],
            "zeitstempel": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        wert, einheit, formatfehler = check.lies_result(ergebnis["text"])
        daten.protokoll(laufordner, "antwort", schritt="antwort", **d,
                        dauer_s=round(time.monotonic() - beginn, 1), versuche=ergebnis.get("versuche", 1),
                        tokens_rein=ergebnis["tokens_rein"], tokens_raus=ergebnis["tokens_raus"],
                        abbruchgrund=ergebnis["abbruchgrund"],
                        ergebnis=formatfehler and f"Formatfehler: {formatfehler}" or f"{wert} {einheit}")

    with ThreadPoolExecutor(max_workers=config.get("parallel", 4)) as pool:
        list(pool.map(eins, auftraege))

    if fehler:
        daten.protokoll(laufordner, "warnung", f"{fehler} Anfragen fehlgeschlagen. Einfach noch einmal starten.")
    return fehler == 0
