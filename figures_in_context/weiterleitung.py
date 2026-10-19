"""Stufe 4: Wer muss zum Menschen? → review_queue.csv (für den Reviewer) + review_intern.csv

richtig und kein Judge flaggt  → fertig
sonst                         → Mensch
aus „fertig“ eine Stichprobe  → Mensch (sieht für den Reviewer genauso aus)
"""

import csv
import math
import random
from collections import defaultdict

from . import daten

TRENNER = ";"  # deutsches Excel öffnet Semikolon-CSV direkt richtig

REVIEW_SPALTEN = [
    "fall_nr", "testfall_id", "frage", "musterloesung", "python_ergebnis", "antwort_text",
    "fallen", "judge_befunde", "fehlertypen_final", "kommentar", "reviewer", "geprueft",
]


def ziehe_stichprobe(fertige, anteil, minimum, seed, testfaelle):
    """Geschichtet nach Modell × Kategorie: reihum aus jeder Schicht ziehen, bis die Zahl erreicht ist."""
    anzahl = min(len(fertige), max(math.ceil(anteil * len(fertige)), minimum))
    rnd = random.Random(seed)
    schichten = defaultdict(list)
    for c in sorted(fertige, key=daten.antwort_schluessel):
        schichten[(c["modell"], testfaelle[c["testfall_id"]]["kategorie"])].append(c)
    for liste in schichten.values():
        rnd.shuffle(liste)
    reihenfolge = sorted(schichten)
    gezogen = []
    while len(gezogen) < anzahl:
        for s in reihenfolge:
            if schichten[s] and len(gezogen) < anzahl:
                gezogen.append(schichten[s].pop())
    return gezogen


def lauf(laufordner, config, testfaelle):
    checks = daten.lies_jsonl(laufordner / "checks.jsonl")
    antworten = {daten.antwort_schluessel(a): a for a in daten.lies_jsonl(laufordner / "antworten.jsonl")}
    urteile = defaultdict(list)
    for u in daten.lies_jsonl(laufordner / "judges.jsonl"):
        urteile[daten.antwort_schluessel(u)].append(u)

    gueltig = [c for c in checks if c["format_ok"]]
    fehlend = [daten.antwort_schluessel(c) for c in gueltig
               if len(urteile[daten.antwort_schluessel(c)]) < len(config["judges"])]
    if fehlend:
        daten.protokoll(laufordner, "fehler", f"Abbruch: Für {len(fehlend)} Antworten fehlen Judge-Urteile. Erst `judges` erneut ausführen.")
        return False

    zum_menschen, fertig = [], []
    for c in gueltig:
        geflaggt = any(u["flag"] for u in urteile[daten.antwort_schluessel(c)])
        (fertig if c["ergebnis_richtig"] and not geflaggt else zum_menschen).append(c)

    s = config["stichprobe"]
    stichprobe = ziehe_stichprobe(fertig, s["anteil"], s["minimum"], s["seed"], testfaelle)
    faelle = [(c, "geflaggt") for c in zum_menschen] + [(c, "stichprobe") for c in stichprobe]
    random.Random(s["seed"]).shuffle(faelle)  # Stichproben nicht am Stück, damit niemand sie erkennt

    with open(laufordner / "review_queue.csv", "w", newline="", encoding="utf-8-sig") as f_review, \
         open(laufordner / "review_intern.csv", "w", newline="", encoding="utf-8-sig") as f_intern:
        review = csv.DictWriter(f_review, REVIEW_SPALTEN, delimiter=TRENNER)
        intern = csv.DictWriter(f_intern, ["fall_nr", "testfall_id", "modell", "wiederholung", "grund"],
                                delimiter=TRENNER)
        review.writeheader()
        intern.writeheader()
        for nr, (c, grund) in enumerate(faelle, 1):
            t = testfaelle[c["testfall_id"]]
            schluessel = daten.antwort_schluessel(c)
            befunde = [f"[{u['judge']}] {'FLAG' if u['flag'] else 'ok'} {','.join(u['fehlertypen'])}: {u['befund']}"
                       for u in sorted(urteile[schluessel], key=lambda u: u["judge"])]
            review.writerow({
                "fall_nr": nr,
                "testfall_id": t["id"],
                "frage": t["frage"],
                "musterloesung": f"{t['musterloesung']['wert']} {t['musterloesung']['einheit']}",
                "python_ergebnis": ("richtig" if c["ergebnis_richtig"] else "FALSCH")
                                   + f" (KI: {c['wert_ki']} {c['einheit_ki']})",
                "antwort_text": antworten[schluessel]["antwort_text"],
                "fallen": " | ".join(t.get("fallen", [])),
                "judge_befunde": "\n".join(befunde),
                "fehlertypen_final": "falsches_ergebnis" if not c["ergebnis_richtig"] else "",
                "kommentar": "", "reviewer": "", "geprueft": "",
            })
            intern.writerow({"fall_nr": nr, "testfall_id": c["testfall_id"], "modell": c["modell"],
                             "wiederholung": c["wiederholung"], "grund": grund})

    daten.protokoll(laufordner, "info", f"Weiterleitung: {len(fertig)} fertig, {len(zum_menschen)} zum Menschen, "
          f"{len(stichprobe)} Stichprobe, {len(checks) - len(gueltig)} Formatfehler.")
    daten.protokoll(laufordner, "info", f"Review-Liste erstellt: {len(zum_menschen) + len(stichprobe)} Fälle. Weiter mit dem Review.")
    return True
