"""Stufe 3: Drei Judges diagnostizieren jede Antwort mit gültigem Format. → judges.jsonl

Judges entscheiden nicht über richtig/falsch, das hat Python schon getan.
Ein kaputtes oder unerlaubtes Urteil zählt als Flag, damit kein Fall still durchrutscht.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor

from . import daten, modelle

ERLAUBT = {
    "zahlen": ["falsche_quelle", "erfundene_zahl"],
    "rechenweg": ["falsch_gerechnet"],
    "plausibilitaet": ["ausgelassene_information"],
}


def schema(judge):
    return {
        "type": "object",
        "properties": {
            "flag": {"type": "boolean"},
            "fehlertypen": {"type": "array", "items": {"type": "string", "enum": ERLAUBT[judge]}},
            "befund": {"type": "string"},
            "belege": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "zitat_antwort": {"type": "string"},
                        "fundstelle_dokument": {"type": "string"},
                    },
                    "required": ["zitat_antwort", "fundstelle_dokument"],
                    "additionalProperties": False,
                },
            },
            "sicherheit": {"type": "string", "enum": ["niedrig", "mittel", "hoch"]},
        },
        "required": ["flag", "fehlertypen", "befund", "belege", "sicherheit"],
        "additionalProperties": False,
    }


def _liste(eintraege):
    return "\n".join(f"- {e}" for e in eintraege) or "- (none)"


def judge_text(judge, testfall, antwort, check):
    t = testfall
    loesung = f"{t['musterloesung']['wert']} {t['musterloesung']['einheit']}"
    if judge == "zahlen":
        zahlen = "\n".join(
            f"- {z['wert']} {z['einheit']} ({z['bedeutung']}), found at: {z['fundstelle']}"
            for z in t["verwendete_zahlen"]
        )
        teile = [
            f"<document>\n{daten.ganzes_dokument(t)}\n</document>",
            f"<numbers_needed_for_the_correct_solution>\n{zahlen}\n</numbers_needed_for_the_correct_solution>",
        ]
    elif judge == "rechenweg":
        urteil = "correct" if check["ergebnis_richtig"] else f"WRONG (answer gave {check['wert_ki']} {check['einheit_ki']})"
        teile = [
            f"<question>\n{t['frage']}\n</question>",
            f"<reference_solution>{loesung}</reference_solution>",
            f"<reference_working>\n{_liste(t['rechenweg'])}\n</reference_working>",
            f"<known_traps>\n{_liste(t.get('fallen', []))}\n</known_traps>",
            f"<exact_comparison_result>{urteil}</exact_comparison_result>",
        ]
    else:
        teile = [
            f"<question>\n{t['frage']}\n</question>",
            f"<required_information>\n{_liste(t['pflicht_infos'])}\n</required_information>",
        ]
    teile.append(f"<ai_answer>\n{antwort['antwort_text']}\n</ai_answer>")
    return "\n\n".join(teile)


def werte_aus(judge, roh_text):
    """Prüft das Judge-JSON. Alles Ungültige wird zum Flag mit Grund „Judge-Fehler“."""
    try:
        u = json.loads(roh_text)
        assert isinstance(u, dict) and isinstance(u.get("flag"), bool)
        typen = u.get("fehlertypen") or []
        assert isinstance(typen, list)
    except (ValueError, AssertionError):
        return {"flag": True, "fehlertypen": [], "befund": "Judge-Fehler: kein gültiges JSON.",
                "belege": [], "sicherheit": None, "judge_fehler": True}
    unerlaubt = [x for x in typen if x not in ERLAUBT[judge]]
    if unerlaubt:
        return {**u, "flag": True, "fehlertypen": [x for x in typen if x in ERLAUBT[judge]],
                "befund": f"Judge-Fehler: unerlaubter Fehlertyp {unerlaubt}. " + str(u.get("befund", "")),
                "judge_fehler": True}
    # Wer einen Fehlertyp meldet, flaggt auch.
    return {**u, "flag": u["flag"] or bool(typen), "judge_fehler": False}


def lauf(laufordner, config, testfaelle):
    antworten = {daten.antwort_schluessel(a): a for a in daten.lies_jsonl(laufordner / "antworten.jsonl")}
    checks = daten.lies_jsonl(laufordner / "checks.jsonl")
    ziel_datei = laufordner / "judges.jsonl"
    vorhanden = {(daten.antwort_schluessel(u), u["judge"]) for u in daten.lies_jsonl(ziel_datei)}

    auftraege = []
    for c in checks:
        if not c["format_ok"]:
            continue  # Entscheidung D: Formatfehler werden nur gezählt
        for judge, ziel in config["judges"].items():
            if (daten.antwort_schluessel(c), judge) not in vorhanden:
                auftraege.append((judge, ziel, c))

    daten.protokoll(laufordner, "info", f"Judges: {len(vorhanden)} Urteile schon vorhanden, {len(auftraege)} werden angefragt.")
    fehler = 0
    erledigt = 0

    def eins(auftrag):
        nonlocal fehler, erledigt
        try:
            _eins(auftrag)
        finally:
            erledigt += 1
            daten.melde(f"Judges: {erledigt}/{len(auftraege)}")

    def _eins(auftrag):
        nonlocal fehler
        judge, ziel, c = auftrag
        testfall = testfaelle[c["testfall_id"]]
        antwort = antworten[daten.antwort_schluessel(c)]
        beginn = time.monotonic()
        kopf = {"testfall_id": c["testfall_id"], "modell": c["modell"], "wiederholung": c["wiederholung"],
                "judge": judge, "judge_modell": modelle.modell_name(ziel)}
        try:
            ergebnis = modelle.frage(
                ziel, daten.lade_prompt(f"judge_{judge}"), judge_text(judge, testfall, antwort, c),
                schema=schema(judge), kontext={"judge": judge, **c},
            )
        except Exception as e:
            fehler += 1
            daten.protokoll(laufordner, "fehler", f"  FEHLER {judge} {daten.antwort_schluessel(c)}: {type(e).__name__}: {e}",
                            schritt="urteil", **kopf, dauer_s=round(time.monotonic() - beginn, 1))
            return
        urteil = werte_aus(judge, ergebnis["text"])
        daten.haenge_an(ziel_datei, {**kopf, **urteil})
        daten.protokoll(laufordner, "urteil", schritt="urteil", **kopf,
                        dauer_s=round(time.monotonic() - beginn, 1), versuche=ergebnis.get("versuche", 1),
                        tokens_rein=ergebnis["tokens_rein"], tokens_raus=ergebnis["tokens_raus"],
                        flag=urteil["flag"], fehlertypen=urteil.get("fehlertypen", []),
                        judge_fehler=urteil.get("judge_fehler", False), befund=str(urteil.get("befund", ""))[:400])

    with ThreadPoolExecutor(max_workers=config.get("parallel", 4)) as pool:
        list(pool.map(eins, auftraege))

    if fehler:
        daten.protokoll(laufordner, "warnung", f"{fehler} Judge-Anfragen fehlgeschlagen. Einfach noch einmal starten.")
    return fehler == 0
