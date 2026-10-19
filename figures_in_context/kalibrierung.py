"""Judge-Kalibrierung: Finden die Judges absichtlich eingebaute Fehler, ohne fehlerfreie Antworten zu flaggen?

    python -m figures_in_context kalibrierung [--test]     (oder in der Web-App unter „Kalibrierung“)

Die Antworten stehen in kalibrierung/antworten.json (erzeugt von kalibrierung/_quelle/erzeuge.py),
jede mit `erwartet` = eingebaute Fehlertypen. Die Judges sehen genau dasselbe wie im echten Lauf.
Ergebnis: kalibrierungen/<name>/kalibrierung.md und .html, dazu ergebnis.json für die Web-App.

Bewertung pro Judge, nur für die Fehlertypen, für die er zuständig ist:
- Treffer: Antwort mit eingebautem Fehler seines Typs, Judge flaggt und nennt den Typ.
- Fehlalarm: fehlerfreie Antwort, Judge flaggt trotzdem.
Antworten mit Fehlern anderer Typen zählen für ihn nicht (Folgefehler dürfen auffallen).
Bestanden heißt: alle eingebauten Fehler gefunden, kein Fehlalarm, kein kaputtes Urteil.
"""

import json
from datetime import datetime

from . import check, daten, judges
from .auswertung import _als_html, quote

ANTWORTEN = daten.BASIS / "kalibrierung" / "antworten.json"
ORDNER = daten.BASIS / "kalibrierungen"
MODELL = "kalibrierung"


class KalibrierungsFehler(Exception):
    pass


def lade_antworten():
    antworten = daten.lade_json(ANTWORTEN)
    for nr, a in enumerate(antworten, 1):
        a["modell"], a["wiederholung"] = MODELL, nr
    return antworten


def neu(test=False):
    config = daten.lade_config()
    judges_config = {j: {"anbieter": "test", "modell": f"judge-{j}"} for j in config["judges"]} if test \
        else config["judges"]
    name = datetime.now().strftime("%Y-%m-%d_%H%M%S") + ("_probe" if test else "")
    ordner = ORDNER / name
    ordner.mkdir(parents=True)
    antworten = lade_antworten()
    (ordner / "lauf.json").write_text(json.dumps({
        "testfaelle": config["testfaelle"],
        "judges": judges_config,
        "parallel": config.get("parallel", 4),
        "test": test,
        "protokoll": {
            "prompt_hashes": {f"judge_{j}": daten.text_hash(daten.lade_prompt(f"judge_{j}")) for j in judges_config},
            "antworten_hash": daten.text_hash(json.dumps(antworten, sort_keys=True, ensure_ascii=False)),
        },
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return ordner


def lade(name):
    ordner = ORDNER / name
    if "/" in name or "\\" in name or ".." in name or not (ordner / "lauf.json").exists():
        raise KalibrierungsFehler(f"Kalibrierung {name} nicht gefunden.")
    return ordner, daten.lade_json(ordner / "lauf.json")


def alle():
    if not ORDNER.exists():
        return []
    return sorted((p.name for p in ORDNER.iterdir() if (p / "lauf.json").exists()), reverse=True)


def start(ordner, config):
    """Schreibt die Kalibrierungsantworten, lässt Python-Check und Judges laufen und wertet aus."""
    antworten = lade_antworten()
    testfaelle = daten.lade_testfaelle(config["testfaelle"])
    unbekannt = sorted({a["testfall_id"] for a in antworten} - set(testfaelle))
    if unbekannt:
        raise KalibrierungsFehler(f"Testfälle fehlen: {', '.join(unbekannt)}")
    ziel = ordner / "antworten.jsonl"
    if not ziel.exists():
        for a in antworten:
            daten.haenge_an(ziel, {k: a[k] for k in ("testfall_id", "modell", "wiederholung", "antwort_text")})
    check.lauf(ordner, testfaelle)
    ok = judges.lauf(ordner, config, testfaelle)
    if not ok:
        daten.protokoll(ordner, "warnung", "Nicht alle Judge-Anfragen haben geklappt. Einfach noch einmal starten.")
        return False
    auswerten(ordner, config)
    return True


def bewerte(antworten, urteile, judge_namen):
    """→ {judge: {treffer, soll, fehlalarme, sauber, kaputt, falscher_typ, verfehlt: [...], alarme: [...]}}"""
    nach_schluessel = {(u["wiederholung"], u["judge"]): u for u in urteile}
    ergebnis = {}
    for judge in judge_namen:
        zustaendig = set(judges.ERLAUBT[judge])
        e = {"treffer": 0, "soll": 0, "fehlalarme": 0, "sauber": 0, "kaputt": 0, "falscher_typ": 0,
             "verfehlt": [], "alarme": []}
        for a in antworten:
            u = nach_schluessel.get((a["wiederholung"], judge))
            if u is None:
                continue
            if u.get("judge_fehler"):
                e["kaputt"] += 1
            eingebaut = set(a["erwartet"]) & zustaendig
            if eingebaut:
                e["soll"] += 1
                if u["flag"] and eingebaut & set(u["fehlertypen"]):
                    e["treffer"] += 1
                else:
                    if u["flag"]:
                        e["falscher_typ"] += 1
                    e["verfehlt"].append({**_kurz(a), "befund": u.get("befund", "")})
            elif not a["erwartet"]:
                e["sauber"] += 1
                if u["flag"]:
                    e["fehlalarme"] += 1
                    e["alarme"].append({**_kurz(a), "befund": u.get("befund", ""), "typen": u["fehlertypen"]})
        e["bestanden"] = e["soll"] > 0 and e["treffer"] == e["soll"] and e["fehlalarme"] == 0 and e["kaputt"] == 0
        ergebnis[judge] = e
    return ergebnis


def _kurz(a):
    return {"kal_id": a["kal_id"], "testfall_id": a["testfall_id"], "beschreibung": a["beschreibung"]}


def auswerten(ordner, config):
    antworten = lade_antworten()
    urteile = daten.lies_jsonl(ordner / "judges.jsonl")
    ergebnis = bewerte(antworten, urteile, list(config["judges"]))
    namen = {"zahlen": "Zahlen-Judge", "rechenweg": "Rechenweg-Judge", "plausibilitaet": "Plausibilitäts-Judge"}

    md = [f"# Judge-Kalibrierung {ordner.name}", ""]
    if config.get("test"):
        md += ["**Probelauf mit Testmodellen: Die Zahlen sagen nichts über echte Judges.**", ""]
    md += [f"{len(antworten)} Antworten, davon {sum(1 for a in antworten if not a['erwartet'])} fehlerfrei. "
           "Ziel: alle eingebauten Fehler finden, keine fehlerfreie Antwort flaggen.", "",
           "| Judge | Modell | Gefunden | Fehlalarme | Kaputte Urteile | Ergebnis |", "|---|---|---|---|---|---|"]
    for judge, e in ergebnis.items():
        ziel = config["judges"][judge]
        md.append(f"| {namen.get(judge, judge)} | {ziel['anbieter']}:{ziel['modell']} | {quote(e['treffer'], e['soll'])} | "
                  f"{quote(e['fehlalarme'], e['sauber'])} | {e['kaputt']} | "
                  f"{'**bestanden**' if e['bestanden'] else '**nachschärfen**'} |")
    md += ["", "Bei so wenigen Antworten sind die Konfidenzintervalle breit. Die Kalibrierung zeigt vor allem, "
           "welche Fehler ein Judge übersieht, und dafür lohnt der Blick auf die Einzelfälle unten.", ""]
    for judge, e in ergebnis.items():
        if not (e["verfehlt"] or e["alarme"]):
            continue
        md += [f"## {namen.get(judge, judge)}", ""]
        for v in e["verfehlt"]:
            md.append(f"- **Übersehen** {v['kal_id']} ({v['testfall_id']}, {v['beschreibung']}): {v['befund']}")
        for v in e["alarme"]:
            md.append(f"- **Fehlalarm** {v['kal_id']} ({v['testfall_id']}): {', '.join(v['typen']) or 'Flag'}: {v['befund']}")
        md.append("")
    md += ["## Was tun bei „nachschärfen“?", "",
           "- Befund des Judges zu den übersehenen Fällen lesen: Hat er den Fehler nicht gesehen oder falsch eingeordnet?",
           "- Prompt im Ordner prompts (judge_zahlen.md, judge_rechenweg.md, judge_plausibilitaet.md) anpassen oder ein anderes Modell in den Einstellungen wählen.",
           "- Danach eine neue Kalibrierung starten. Erst wenn alle drei bestanden haben, zählt ein echter Lauf voll.", ""]
    text = "\n".join(md)
    (ordner / "kalibrierung.md").write_text(text, encoding="utf-8")
    (ordner / "kalibrierung.html").write_text(_als_html(text, f"Kalibrierung {ordner.name}"), encoding="utf-8")
    (ordner / "ergebnis.json").write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False), encoding="utf-8")
    daten.protokoll(ordner, "info", "Kalibrierung: " + ", ".join(
        f"{namen.get(j, j)} {e['treffer']}/{e['soll']} gefunden, {e['fehlalarme']} Fehlalarme"
        for j, e in ergebnis.items()))
    return ergebnis


def stand(ordner):
    """Für die Übersicht in der Web-App."""
    config = daten.lade_json(ordner / "lauf.json")
    n = len(daten.lade_json(ANTWORTEN))
    erg = ordner / "ergebnis.json"
    return {
        "test": config.get("test", False),
        "judges": {j: f"{z['anbieter']}:{z['modell']}" for j, z in config["judges"].items()},
        "urteile": len(daten.lies_jsonl(ordner / "judges.jsonl")),
        "urteile_soll": n * len(config["judges"]),
        "ergebnis": daten.lade_json(erg) if erg.exists() else None,
    }
