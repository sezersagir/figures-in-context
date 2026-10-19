"""Gemeinsame Abläufe für Kommandozeile und Web-App: Lauf anlegen, laden, starten, Testfälle prüfen."""

import json
import re
from datetime import date

from . import antworten, check, daten, judges, weiterleitung

PROMPTS = ["testobjekt", "judge_zahlen", "judge_rechenweg", "judge_plausibilitaet"]
LAUFORDNER = daten.BASIS / "laeufe"


class LaufFehler(Exception):
    pass


def neu(name, test=False):
    name = re.sub(r"[^\w-]+", "-", name.strip()).strip("-")
    if not name:
        raise LaufFehler("Bitte einen Namen angeben, z. B. pilot.")
    config = daten.lade_config()
    if test:
        config["testobjekte"] = [{"anbieter": "test", "modell": "zufall"}, {"anbieter": "test", "modell": "richtig"}]
        config["judges"] = {j: {"anbieter": "test", "modell": f"judge-{j}"} for j in config["judges"]}
        config["stichprobe"]["minimum"] = 3
    ordner = LAUFORDNER / f"{date.today().isoformat()}_{name}"
    if ordner.exists():
        raise LaufFehler(f"Den Lauf {ordner.name} gibt es schon. Läufe werden nie überschrieben, bitte anderen Namen wählen.")
    testfaelle = daten.lade_testfaelle(config["testfaelle"])
    ordner.mkdir(parents=True)
    config["test"] = test
    config["protokoll"] = {
        "prompt_hashes": {p: daten.text_hash(daten.lade_prompt(p)) for p in PROMPTS},
        "testfaelle": sorted(testfaelle),
        "testfaelle_hash": daten.text_hash(json.dumps(testfaelle, sort_keys=True, ensure_ascii=False)),
    }
    (ordner / "lauf.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    return ordner


def lade_lauf(name, warnen=True):
    ordner = LAUFORDNER / name
    if "/" in name or "\\" in name or ".." in name or not (ordner / "lauf.json").exists():
        raise LaufFehler(f"Lauf {name} nicht gefunden.")
    config = daten.lade_json(ordner / "lauf.json")
    testfaelle = daten.lade_testfaelle(config["testfaelle"])
    if warnen:
        aktuell = {p: daten.text_hash(daten.lade_prompt(p)) for p in PROMPTS}
        if aktuell != config["protokoll"]["prompt_hashes"]:
            daten.protokoll(ordner, "warnung", "WARNUNG: Die Prompts wurden seit dem Anlegen des Laufs geändert. "
                        "Für vergleichbare Ergebnisse einen neuen Lauf anlegen.")
        if sorted(testfaelle) != config["protokoll"]["testfaelle"]:
            daten.protokoll(ordner, "warnung", "WARNUNG: Die Testfälle haben sich seit dem Anlegen des Laufs geändert.")
    return ordner, config, testfaelle


def alle_laeufe():
    if not LAUFORDNER.exists():
        return []
    return sorted((p.name for p in LAUFORDNER.iterdir() if (p / "lauf.json").exists()), reverse=True)


def start(ordner, config, testfaelle):
    """Stufen 1–4. Kann beliebig oft aufgerufen werden, Vorhandenes wird nicht erneut angefragt."""
    daten.protokoll(ordner, "info", "Lauf gestartet: " + ", ".join(f"{z['anbieter']}:{z['modell']}" for z in config["testobjekte"]))
    ok = antworten.lauf(ordner, config, testfaelle)
    check.lauf(ordner, testfaelle)
    ok = judges.lauf(ordner, config, testfaelle) and ok
    if not ok:
        daten.protokoll(ordner, "warnung", "Nicht alle Anfragen haben geklappt. Einfach noch einmal starten, "
                    "Vorhandenes wird nicht doppelt angefragt.")
        return False
    if (ordner / "review_ergebnis.csv").exists():
        daten.protokoll(ordner, "info", "Review hat schon begonnen, die Review-Liste bleibt unverändert.")
        return True
    return weiterleitung.lauf(ordner, config, testfaelle)


def pruefe():
    """Steht jede Zahl aus verwendete_zahlen wirklich im Dokument? Stimmt die Seitenangabe?"""
    testfaelle = daten.lade_testfaelle(daten.lade_config()["testfaelle"])
    probleme = []
    for t in testfaelle.values():
        try:
            daten.dokument_ausschnitt(t)
        except (ValueError, FileNotFoundError) as e:
            probleme.append(f"{t['id']}: {e}")
            continue
        text = daten.ganzes_dokument(t)
        for z in t["verwendete_zahlen"]:
            if z["wert"] not in text:
                probleme.append(f"{t['id']}: Zahl {z['wert']} ({z['bedeutung']}) steht nicht im Dokument")
    return len(testfaelle), probleme


def kennzahlen(ordner):
    """Zählt, wie weit ein Lauf ist. Für die Übersicht in der Web-App."""
    config = daten.lade_json(ordner / "lauf.json")
    n_testfaelle = len(config["protokoll"]["testfaelle"])
    soll_antworten = n_testfaelle * len(config["testobjekte"]) * config["wiederholungen"]
    checks = daten.lies_jsonl(ordner / "checks.jsonl")
    gueltig = sum(1 for c in checks if c["format_ok"])
    k = {
        "test": config.get("test", False),
        "testobjekte": [f"{z['anbieter']}:{z['modell']}" for z in config["testobjekte"]],
        "antworten": len(daten.lies_jsonl(ordner / "antworten.jsonl")),
        "antworten_soll": soll_antworten,
        "richtig": sum(1 for c in checks if c["ergebnis_richtig"]),
        "falsch": sum(1 for c in checks if c["format_ok"] and not c["ergebnis_richtig"]),
        "formatfehler": len(checks) - gueltig,
        "urteile": len(daten.lies_jsonl(ordner / "judges.jsonl")),
        "urteile_soll": gueltig * len(config["judges"]),
        "review_gesamt": 0,
        "review_geprueft": 0,
        "report": (ordner / "report.html").exists(),
    }
    if (ordner / "review_queue.csv").exists():
        from .review import lade_faelle
        faelle = lade_faelle(ordner, {}, mit_dokument=False)
        k["review_gesamt"] = len(faelle)
        k["review_geprueft"] = sum(1 for f in faelle if f.get("geprueft"))
    return k
