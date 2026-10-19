# Figures in Context: Architektur

Stand: 2026-10-18. Grundlage: [SPEZIFIKATION.md](../SPEZIFIKATION.md) (Konzept von hero). Dieses Dokument legt fest, *wie* das Konzept technisch umgesetzt wird. Es ändert am Konzept nichts. Wo eine Technik-Wahl das Konzept berühren würde, steht sie unter „Entscheidungen für hero“ am Ende.

Datenformat der Testfälle: das Format, das der Testfall-Thread in [testfaelle/charge-01.json](../testfaelle/charge-01.json) und [VORSCHLAG-FORMAT.md](../testfaelle/VORSCHLAG-FORMAT.md) festgelegt hat. Die Architektur liest es unverändert. Vorschläge zur Spezifikation: [vorschlaege-zur-spezifikation.md](vorschlaege-zur-spezifikation.md).

---

## 1. Überblick

Die Pipeline besteht aus sechs Stufen. Jede Stufe liest Dateien und schreibt Dateien. Dadurch lässt sich jede Stufe einzeln neu starten, und nichts muss doppelt bezahlt werden.

```
 testfaelle/charge-*.json ─┐
 testfaelle/dokumente/*.md ┤
                    ▼
 [1] ANTWORTEN      Testobjekt-Modell beantwortet Frage   → antworten.jsonl
                    ▼
 [2] PYTHON-CHECK   RESULT-Zeile lesen, exakt vergleichen  → checks.jsonl
                    ▼
 [3] JUDGES         3 Judges, 3 Modellfamilien, alle Fälle → judges.jsonl
                    ▼
 [4] WEITERLEITUNG  richtig + kein Flag → fertig; sonst Mensch
                    + Stichprobe aus „fertig“             → review_queue.csv
                    ▼
 [5] MENSCH         bestätigt / korrigiert Fehlertypen    → review_ergebnis.csv
                    ▼
 [6] AUSWERTUNG     Fehlerquoten + Judge-Übersehrate      → report.md / report.html
```

Grundprinzip (aus dem Konzept): **Richtig oder falsch entscheidet nur Python. Die Judges diagnostizieren nur. Das letzte Wort hat der Mensch.**

---

## 2. Ordnerstruktur

```
figures-in-context/
├── SPEZIFIKATION.md            (gehört dem Konzept-Thread)
├── architektur/                (dieses Dokument)
├── testfaelle/                 (gehört dem Testfall-Thread)
│   ├── charge-01.json          Liste von Testfällen, eine Datei pro Charge
│   └── dokumente/*.md          Geschäftsdokumente, Markdown mit „### Page N“
├── config/
│   ├── lauf.json               welche Modelle, wie viele Wiederholungen, Stichprobe
│   └── einheiten.json          erlaubte Schreibweisen von Einheiten (EUR = €, …)
├── prompts/
│   ├── testobjekt.md           Systemprompt fürs getestete Modell
│   ├── judge_zahlen.md
│   ├── judge_rechenweg.md
│   └── judge_plausibilitaet.md
├── figures_in_context/                 Python-Code (eine Datei pro Stufe)
│   ├── antworten.py
│   ├── check.py
│   ├── judges.py
│   ├── weiterleitung.py
│   ├── auswertung.py
│   └── modelle.py              eine dünne Schicht pro Anbieter
└── laeufe/
    └── 2026-10-20_pilot/       ein Ordner pro Durchlauf, wird nie überschrieben
        ├── lauf.json           Kopie der Config + Modell-IDs + Prompt-Hashes
        ├── antworten.jsonl
        ├── checks.jsonl
        ├── judges.jsonl
        ├── review_queue.csv
        ├── review_ergebnis.csv
        └── report.md
```

Warum ein Ordner pro Lauf: Ergebnisse sind nur vergleichbar, wenn man weiß, mit welchem Prompt, welchem Modell und welchen Testfällen sie entstanden sind. Der Lauf-Ordner ist das Protokoll.

---

## 3. Die Stufen im Detail

### [1] Antworten (Testobjekt)

- **Input:** die im Testfall genannten Seiten des Dokuments (aus den „### Page N“-Abschnitten geschnitten, auch Bereiche wie `"1-2"`, Firmenkopf immer dabei) + Frage aus dem Testfall + fester Systemprompt.
- **Systemprompt** (Kern, Englisch):
  > Answer the question using only the attached document. Show your working. End your answer with exactly one final line in this format: `RESULT: <number> <unit>`. Write the number in full digits, without thousands separators and without words like "million" (e.g. `RESULT: 5614779.00 EUR`).
- Die Antwort davor ist frei. So wird realistisches Verhalten getestet, und die Judges haben einen Rechenweg zum Prüfen.
- **Pro Testfall × Modell × Wiederholung** ein Datensatz in `antworten.jsonl`: `testfall_id`, `modell`, `wiederholung`, `antwort_text`, `zeitstempel`, Token-Verbrauch, Abbruchgrund.
- **Wiederholungen:** konfigurierbar (`wiederholungen` in `lauf.json`). KI-Antworten schwanken; mit 3 Wiederholungen sieht man, ob ein Fehler Zufall oder Muster ist. Pilot: 1.
- **Cache:** Existiert für (Testfall, Modell, Wiederholung, Prompt-Hash) schon eine Antwort, wird nicht neu angefragt.

### [2] Python-Check (kein KI-Modell)

Liest **nur die letzte RESULT-Zeile**.

1. **Format prüfen.** Formatfehler, wenn: keine RESULT-Zeile, mehr als eine, Zahl nicht lesbar, Wörter wie „million“ in der Zeile, Einheit fehlt. → `format_ok = false`, Grund wird gespeichert.
2. **Zahl lesen.** Als `Decimal`, nie als `float` (sonst wird aus 0.1 + 0.2 nicht 0.3). Kommas als Tausendertrenner werden toleriert und entfernt.
3. **Einheit vergleichen** über `config/einheiten.json` (z. B. `EUR`, `€`, `euro` → `EUR`). Falsche Einheit = falsches Ergebnis.
4. **Wert vergleichen** nach hero's Regel (Felder `exakt` und `nachkommastellen` der Musterlösung):
   - Normalfall: **exakt gleich** (`5614779` = `5614779.00`, aber ≠ `5614779.01`).
   - `exakt: false` mit `nachkommastellen: n` (periodische Zahlen): Der KI-Wert wird kaufmännisch (`ROUND_HALF_UP`) auf n Stellen gerundet und muss dann exakt der Musterlösung entsprechen.
5. **Ausgabe** in `checks.jsonl`: `format_ok`, `format_grund`, `wert_ki`, `einheit_ki`, `ergebnis_richtig` (true/false/null bei Formatfehler).

### [3] Judges (Diagnose, laufen bei allen Antworten)

Drei Judges, **jeder auf einer anderen Modellfamilie** (z. B. Anthropic, OpenAI, Google), damit sie nicht dieselben blinden Flecken teilen.

Hero's Idee „pro Judge ein eigenes Wissenspaket/JSON“ wird so umgesetzt: Jeder Judge bekommt nur die Felder des Testfalls, die er braucht. Ein eigenes RAG-System ist nicht nötig, weil die Dokumente klein genug sind, um sie komplett mitzugeben (siehe Entscheidung C).

| Judge | bekommt | prüft | darf melden |
|---|---|---|---|
| **Zahlen-Judge** | Dokument, `verwendete_zahlen`, Antwort | Stammt jede Zahl der Antwort aus dem Dokument? Richtig zitiert? Richtige Fundstelle? | falsche Quelle, erfundene Zahl |
| **Rechenweg-Judge** | Frage, `rechenweg`, `fallen`, `musterloesung`, Antwort, Python-Ergebnis | Bei falschem Ergebnis: an welchem Schritt ging es schief? Bei richtigem: stecken Fehler in Zwischenschritten? | falsch gerechnet |
| **Plausibilitäts-Judge** | Frage, `pflicht_infos`, Antwort | Beantwortet die Antwort die Frage? Fehlt Pflicht-Information? Grobe Ausreißer (keine Zahl, absurde Größenordnung)? | ausgelassene Information |

„Falsches Ergebnis“ meldet kein Judge, das setzt Python. „Format nicht eingehalten“ ebenfalls.

**Ausgabe jedes Judges: festes JSON** (per Structured Output des Anbieters erzwungen):

```json
{
  "flag": true,
  "fehlertypen": ["erfundene_zahl"],
  "befund": "The answer uses 1,240,000 units for Q3; the document states 1,204,000 (p. 2, table 1).",
  "belege": [
    {"zitat_antwort": "1,240,000 units", "fundstelle_dokument": "p. 2, table 1: 1,204,000"}
  ],
  "sicherheit": "hoch"
}
```

- `fehlertypen` nur aus der festen Liste und nur aus den Typen, die der Judge melden darf.
- **Ausfallsicher:** Liefert ein Judge kaputtes JSON, gar nichts oder einen Typ, den er nicht melden darf, zählt das als Flag mit Grund „Judge-Fehler“. Ein Fall wird nie still als „fertig“ durchgewunken.
- Judges laufen mit den deterministischsten Einstellungen, die der Anbieter erlaubt.
- Judges laufen **nicht** bei Formatfehlern (siehe Entscheidung D).

### [4] Weiterleitung

```
format_ok == false                          → Formatfehler-Statistik (kein Review)
ergebnis_richtig und kein Judge flaggt      → FERTIG
sonst                                       → MENSCH
aus FERTIG: Stichprobe ziehen               → MENSCH (Typ "stichprobe")
```

- Die Stichprobe wird **geschichtet** gezogen (pro Modell × Kategorie), damit jedes Modell und jede Kategorie vertreten ist, und mit festem Zufalls-Seed, damit sie reproduzierbar ist.
- Für den Reviewer sehen geflaggte Fälle und Stichproben gleich aus. Er weiß nicht, warum ein Fall bei ihm landet. So schaut er bei Stichproben nicht weniger genau hin.

### [5] Mensch (Review)

Erste Version: **eine CSV-Datei**, die in Excel oder Google Sheets geöffnet wird. Kein eigenes Tool nötig.

Spalten in `review_queue.csv`:
`fall_nr`, `testfall_id`, `frage`, `musterloesung`, `antwort_text`, `python_ergebnis`, `fallen` (bekannte Fehlerquellen), `judge_befunde` (alle drei zusammengefasst), → auszufüllen: `fehlertypen_final` (Liste, leer = fehlerfrei), `kommentar`, `reviewer`.

Nicht in der Datei: Modellname (Reviewer soll nicht wissen, welches Modell er bewertet) und ob der Fall Stichprobe ist. Beides bleibt intern über `fall_nr` verknüpft.

Später ausbaubar zu einer kleinen Weboberfläche mit denselben Feldern (siehe Entscheidung E).

### [6] Auswertung

**Zähleinheit ist die Antwort.** Eine Antwort ist fehlerhaft, wenn sie mindestens einen Fehlertyp hat. Eine Antwort kann mehrere Fehlertypen haben.

| Kennzahl | Formel |
|---|---|
| **Fehlerquote** | fehlerhafte Antworten ÷ Antworten mit gültigem Format |
| Fehlerquote pro Typ | Antworten mit Typ X ÷ Antworten mit gültigem Format |
| pro Modell / Kategorie / Schwierigkeit | dieselben Formeln, gefiltert |
| **Formatfehlerquote** (separat) | Antworten mit Formatfehler ÷ alle Antworten |
| **Judge-Übersehrate** | Stichprobenfälle mit Fehler laut Mensch ÷ Stichprobenfälle |
| Judge-Trefferquote pro Judge | Flags, die der Mensch bestätigt ÷ alle Flags dieses Judges |

Woher kommen die Fehlertypen einer Antwort?
- Vom Menschen reviewte Antworten: `fehlertypen_final`.
- „Fertige“ Antworten ohne Review: fehlerfrei. Weil die Judges etwas übersehen können, zeigt der Report **zwei Zahlen**: die gemessene Fehlerquote und eine um die Judge-Übersehrate **korrigierte** Fehlerquote. Ehrlich ist, beide zu zeigen.
- Jede Quote bekommt ein **95-%-Konfidenzintervall** (Wilson). Bei 30 Antworten pro Modell sind „10 %“ in Wahrheit irgendwo zwischen 3 % und 26 %. Ohne Intervall wirkt das genauer, als es ist.

Report als Markdown und HTML. Eignet sich auch direkt als Arbeitsprobe für Kunden und KI-Labs.

---

## 4. Technik

| Thema | Wahl | Warum |
|---|---|---|
| Sprache | **Python 3.11+** | Python-Check ist ohnehin Python; `decimal` ist eingebaut |
| Abhängigkeiten | offizielle SDKs der drei Anbieter, sonst Standardbibliothek | wenig, was kaputtgehen kann |
| Modellzugriff | eine Datei `modelle.py` mit einer Funktion `frage(modell, system, dokument, text, schema=None)` pro Anbieter | Modelle tauschen = eine Zeile in `lauf.json` |
| Testfälle | **JSON, eine Datei pro Charge** (wie vom Testfall-Thread angelegt) | ohne Zusatzbibliothek lesbar; Musterlösungen als Text, damit Python sie exakt als `Decimal` liest |
| Dokumente | **Markdown** mit Seitenüberschriften; später optional als PDF gerendert | Text ist für den Start einfacher; PDF wäre realistischer (Tabellenlayout, Kopfzeilen) und lässt sich als zweite Variante desselben Testfalls ergänzen |
| Laufdaten | JSONL (eine Zeile pro Antwort/Judge-Urteil) | anhängbar, robust bei Abbruch |
| Review | CSV | Excel/Sheets reicht für den Anfang |
| Kosten sparen | Batch-Schnittstellen der Anbieter (meist ~50 % günstiger) für große Läufe | Antworten müssen nicht sofort da sein |

**Kosten grob** (geschätzt, nicht gemessen): 100 Testfälle × 3 Testobjekte × 1 Wiederholung = 300 Antworten + 900 Judge-Urteile ≈ 1.200 Anfragen à ~5.000 Token rein / ~1.500 raus. Mit aktuellen Spitzenmodellen grob 50–100 $ pro Durchlauf, mit Batch etwa die Hälfte. Der Pilot mit 20 Testfällen kostet entsprechend ein Fünftel.

**Selbstbewertung vermeiden:** Wird z. B. ein Claude-Modell getestet, sitzt im Judge-Team trotzdem ein Claude-Modell. Das ist bei drei Judges aus drei Familien nicht ganz vermeidbar. Abfederung: Der Report zeigt die Judge-Trefferquote getrennt nach „Judge und Testobjekt aus derselben Familie“ und „verschieden“. Fällt das auf, kann man pro Testobjekt den Judge der eigenen Familie tauschen.

---

## 5. Qualitätssicherung der Eval selbst

Bevor echte Läufe zählen:

1. **Testfall-Check:** Die Musterlösungen rechnet der Testfall-Thread schon per Skript exakt nach (`testfaelle/_quelle/`). Zusätzlich prüft ein Check vor jedem Lauf, dass jede Zahl aus `verwendete_zahlen` wirklich im Dokument steht. Fehler in Musterlösungen sind der häufigste Grund für falsche Eval-Ergebnisse.
2. **Judge-Kalibrierung:** 10–20 Antworten mit absichtlich eingebauten Fehlern (eine erfundene Zahl, ein Rechenfehler, eine fehlende Pflicht-Info) und 10 fehlerfreie. Jeder Judge muss die eingebauten Fehler finden und darf die fehlerfreien nicht flaggen. Erst dann wird er für echte Läufe eingesetzt.
3. **Pilot:** 20 Testfälle, 1 Modell, alles von Hand reviewen. Danach Prompts und Testfälle nachschärfen, dann der volle Lauf.

---

## 6. Entscheidungen für hero

Alle fünf Punkte sind entschieden; festgehalten auch in SPEZIFIKATION.md, „Entscheidungen vom 18.10.2026“. Der Code wird im Thread „Figures in Context Konzept“ gebaut.

**A. Welche Modelle werden getestet?** ✓ Entschieden (hero, 2026-10-18): je ein aktuelles Spitzenmodell von Anthropic, OpenAI und Google. Günstigere Modelle können später als eigener Lauf dazukommen.

**B. Stichprobengröße (Schritt 7, laut Spezifikation offen).** Standard: ✓ Wie empfohlen entschieden (hero, 2026-10-18). **20 % der „fertigen“ Fälle, mindestens 30**, geschichtet nach Modell × Kategorie. Bei 30 Stichprobenfällen ohne Fund kann man sagen „die Judges übersehen vermutlich unter 10 %“. Weniger Stichprobe = weniger Arbeit, aber die korrigierte Fehlerquote wird unscharf.

**C. RAG pro Judge.** ✓ Wie empfohlen entschieden (hero, 2026-10-18). In deinem ersten Entwurf hatte jeder Judge ein eigenes RAG-System. Standard hier: kein RAG, stattdessen bekommt jeder Judge sein eigenes Paket aus Testfall-Feldern und das komplette Dokument. Grund: Die Dokumente sind kurz genug, und RAG würde eine neue Fehlerquelle einbauen (der Judge findet die richtige Stelle nicht). RAG lohnt sich erst bei sehr langen Dokumenten (z. B. 200-seitige Geschäftsberichte).

**D. Antworten mit Formatfehler.** Standard: ✓ Wie empfohlen entschieden (hero, 2026-10-18). werden gezählt und gemeldet, aber nicht von Judges und Mensch geprüft (sie zählen laut Spezifikation ja nicht in die Fehlerquote). Alternative: trotzdem prüfen, um zu sehen, ob dahinter auch Rechenfehler stecken.

**E. Review-Oberfläche.** Standard: ✓ Wie empfohlen entschieden (hero, 2026-10-18). CSV in Excel/Sheets. Alternative: eine kleine Weboberfläche. Die wäre ein gutes Projekt zum Selberbauen, wenn du etwas Vorzeigbares willst.
