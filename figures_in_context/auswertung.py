"""Stufe 6: Fehlerquoten, Judge-Übersehrate, Judge-Trefferquote. → report.md + report.html

Zähleinheit ist die Antwort. Jede Quote bekommt ein 95-%-Konfidenzintervall (Wilson).
"""

import csv
import html
import math
import re
from collections import defaultdict
from datetime import date

from . import daten
from .judges import ERLAUBT


def wilson(treffer, n, z=1.96):
    if n == 0:
        return None, None
    p = treffer / n
    nenner = 1 + z * z / n
    mitte = (p + z * z / (2 * n)) / nenner
    breite = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / nenner
    return max(0.0, mitte - breite), min(1.0, mitte + breite)


def quote(treffer, n):
    if n == 0:
        return "–"
    unten, oben = wilson(treffer, n)
    return f"{treffer / n:.1%} ({unten:.1%}–{oben:.1%}), {treffer}/{n}"


def lies_review(laufordner, warnungen):
    pfad = laufordner / "review_ergebnis.csv"
    if not pfad.exists():
        warnungen.append("review_ergebnis.csv fehlt: Alle Fälle beim Menschen sind vorläufig "
                         "(Python + Judges) gewertet, und die Übersehrate ist unbekannt.")
        return {}
    text = pfad.read_text(encoding="utf-8-sig")
    trenner = ";" if text.split("\n", 1)[0].count(";") >= text.split("\n", 1)[0].count(",") else ","
    ergebnis = {}
    for zeile in csv.DictReader(text.splitlines(keepends=True), delimiter=trenner):
        if not (zeile.get("geprueft") or "").strip():
            continue
        typen = [t for t in re.split(r"[,;\s]+", zeile.get("fehlertypen_final") or "") if t]
        unbekannt = [t for t in typen if t not in daten.FEHLERTYPEN]
        if unbekannt:
            warnungen.append(f"Fall {zeile['fall_nr']}: unbekannte Fehlertypen {unbekannt} ignoriert.")
        ergebnis[zeile["fall_nr"]] = [t for t in typen if t in daten.FEHLERTYPEN]
    return ergebnis


def lauf(laufordner, config, testfaelle):
    warnungen = []
    checks = daten.lies_jsonl(laufordner / "checks.jsonl")
    urteile = defaultdict(list)
    for u in daten.lies_jsonl(laufordner / "judges.jsonl"):
        urteile[daten.antwort_schluessel(u)].append(u)
    intern = {}
    if (laufordner / "review_intern.csv").exists():
        with open(laufordner / "review_intern.csv", encoding="utf-8-sig") as f:
            for z in csv.DictReader(f, delimiter=";"):
                intern[f"{z['testfall_id']}|{z['modell']}|{z['wiederholung']}"] = z
    review = lies_review(laufordner, warnungen)

    # Fehlertypen pro Antwort festlegen
    antworten = []  # (check, fehlertypen, status)
    for c in checks:
        k = daten.antwort_schluessel(c)
        if not c["format_ok"]:
            antworten.append((c, None, "format"))
            continue
        eintrag = intern.get(k)
        if eintrag and eintrag["fall_nr"] in review:
            antworten.append((c, review[eintrag["fall_nr"]], "mensch_" + eintrag["grund"]))
        elif eintrag and eintrag["grund"] == "stichprobe":
            antworten.append((c, [], "fertig"))  # noch nicht reviewte Stichprobe zählt wie „fertig“
        elif eintrag:
            vorlaeufig = ([] if c["ergebnis_richtig"] else ["falsches_ergebnis"]) + \
                         [t for u in urteile[k] for t in u["fehlertypen"]]
            antworten.append((c, sorted(set(vorlaeufig)), "vorlaeufig"))
        else:
            antworten.append((c, [], "fertig"))

    gueltig = [a for a in antworten if a[2] != "format"]
    offen = sum(1 for a in gueltig if a[2] == "vorlaeufig")
    if offen:
        warnungen.append(f"{offen} Fälle beim Menschen noch nicht geprüft und nur vorläufig gewertet.")

    # Judge-Übersehrate aus der geprüften Stichprobe
    stichprobe = [a for a in gueltig if a[2] == "mensch_stichprobe"]
    uebersehen = sum(1 for a in stichprobe if a[1])
    uebersehrate = uebersehen / len(stichprobe) if stichprobe else None
    nicht_reviewt_fertig = sum(1 for a in gueltig if a[2] == "fertig")

    z = []
    z.append(f"# Figures in Context: Report „{laufordner.name}“\n")
    z.append(f"Erstellt am {date.today().isoformat()}. Zähleinheit: Antwort. "
             "Werte in Klammern: 95-%-Konfidenzintervall (Wilson).\n")
    if warnungen:
        z.append("**Hinweise**\n")
        z.extend(f"- {w}" for w in warnungen)
        z.append("")

    z.append("## Fehlerquote gesamt\n")
    fehlerhaft = sum(1 for a in gueltig if a[1])
    z.append(f"- **Gemessene Fehlerquote:** {quote(fehlerhaft, len(gueltig))}")
    if uebersehrate is not None and gueltig:
        korrigiert = (fehlerhaft + uebersehrate * nicht_reviewt_fertig) / len(gueltig)
        z.append(f"- **Korrigierte Fehlerquote** (um Judge-Übersehrate bereinigt): {korrigiert:.1%}")
    z.append(f"- **Formatfehlerquote** (separat, nicht in der Fehlerquote): "
             f"{quote(len(antworten) - len(gueltig), len(antworten))}")
    z.append(f"- **Judge-Übersehrate** (Stichprobe): {quote(uebersehen, len(stichprobe)) if stichprobe else 'noch keine geprüfte Stichprobe'}\n")

    for titel, schluessel in [("Modell", lambda c: c["modell"]),
                              ("Kategorie", lambda c: testfaelle[c["testfall_id"]]["kategorie"]),
                              ("Schwierigkeit", lambda c: testfaelle[c["testfall_id"]]["schwierigkeit"])]:
        gruppen = defaultdict(list)
        for a in gueltig:
            gruppen[schluessel(a[0])].append(a)
        z.append(f"## Fehlerquote pro {titel}\n")
        z.append(f"| {titel} | Fehlerquote |")
        z.append("|---|---|")
        for g in sorted(gruppen):
            z.append(f"| {g} | {quote(sum(1 for a in gruppen[g] if a[1]), len(gruppen[g]))} |")
        z.append("")

    z.append("## Fehlerquote pro Fehlertyp und Modell\n")
    modelle = sorted({a[0]["modell"] for a in gueltig})
    z.append("| Fehlertyp | " + " | ".join(modelle) + " |")
    z.append("|---|" + "---|" * len(modelle))
    for typ in daten.FEHLERTYPEN:
        werte = []
        for m in modelle:
            auswahl = [a for a in gueltig if a[0]["modell"] == m]
            werte.append(quote(sum(1 for a in auswahl if typ in a[1]), len(auswahl)))
        z.append(f"| {typ} | " + " | ".join(werte) + " |")
    z.append("")

    # Judge-Trefferquote: von den Flags eines Judges, die ein Mensch geprüft hat,
    # wie viele bestätigt der Mensch mit einem Fehlertyp dieses Judges?
    z.append("## Judge-Trefferquote (nur vom Menschen geprüfte Fälle)\n")
    z.append("| Judge | gleiche Familie wie Testobjekt | andere Familie |")
    z.append("|---|---|---|")
    for judge in config["judges"]:
        zaehler = {True: [0, 0], False: [0, 0]}
        for c, typen, status in gueltig:
            if not status.startswith("mensch_"):
                continue
            for u in urteile[daten.antwort_schluessel(c)]:
                if u["judge"] == judge and u["flag"]:
                    gleich = u["judge_modell"].split(":")[0] == c["modell"].split(":")[0]
                    zaehler[gleich][1] += 1
                    zaehler[gleich][0] += any(t in typen for t in ERLAUBT[judge])
        z.append(f"| {judge} | {quote(*zaehler[True])} | {quote(*zaehler[False])} |")
    z.append("")

    md = "\n".join(z)
    (laufordner / "report.md").write_text(md, encoding="utf-8")
    (laufordner / "report.html").write_text(_als_html(md, laufordner.name), encoding="utf-8")
    daten.protokoll(laufordner, "info", "Report erstellt (report.md und report.html).")


def _als_html(md, titel):
    """Minimales Markdown → HTML für Überschriften, Listen, Tabellen und Fettdruck."""
    def inline(t):
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(t))

    teile, in_liste, in_tabelle = [], False, False
    for zeile in md.splitlines():
        if in_liste and not zeile.startswith("- "):
            teile.append("</ul>")
            in_liste = False
        if in_tabelle and not zeile.startswith("|"):
            teile.append("</table>")
            in_tabelle = False
        if zeile.startswith("#"):
            stufe = len(zeile) - len(zeile.lstrip("#"))
            teile.append(f"<h{stufe}>{inline(zeile.lstrip('#').strip())}</h{stufe}>")
        elif zeile.startswith("- "):
            if not in_liste:
                teile.append("<ul>")
                in_liste = True
            teile.append(f"<li>{inline(zeile[2:])}</li>")
        elif zeile.startswith("|"):
            zellen = [x.strip() for x in zeile.strip("|").split("|")]
            if set("".join(zellen)) <= {"-"}:
                continue
            tag = "th" if not in_tabelle else "td"
            if not in_tabelle:
                teile.append("<table>")
                in_tabelle = True
            teile.append("<tr>" + "".join(f"<{tag}>{inline(x)}</{tag}>" for x in zellen) + "</tr>")
        elif zeile.strip():
            teile.append(f"<p>{inline(zeile)}</p>")
    if in_liste:
        teile.append("</ul>")
    if in_tabelle:
        teile.append("</table>")
    stil = ("body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}"
            "table{border-collapse:collapse;margin:.5rem 0 1.5rem;width:100%}"
            "th,td{border:1px solid #ccc;padding:.35rem .6rem;text-align:left}th{background:#eef3f8}"
            "h1,h2{color:#1f4e79}")
    return (f"<!doctype html><html lang='de'><head><meta charset='utf-8'><title>{html.escape(titel)}</title>"
            f"<style>{stil}</style></head><body>{''.join(teile)}</body></html>")
