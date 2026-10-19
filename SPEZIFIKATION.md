# Figures in Context: Spezifikation

Stand: 2026-10-18 (Format ergänzt nach Review der Charge 01). Entworfen von hero im Thread „Multi-Judge-Eval für Zahlen“. Die Entscheidungen sind seine; dieses Dokument fasst sie nur zusammen.

## Ziel

Messen, wie oft eine KI Fehler macht, wenn sie aus wirtschaftlichen Dokumenten mit großen, verwirrenden Zahlen Berechnungen wiedergibt. Ergebnis ist eine Fehlerquote pro Modell und pro Fehlertyp.

## Ablauf

1. **Testfälle:** selbst gebaute Dokumente im Stil echter Geschäftsberichte/-briefe, auf Englisch. Musterlösung vorher festgelegt.
2. **KI antwortet** frei und hängt am Ende eine feste Zeile an: `RESULT: <Wert> <Einheit>`
3. **Python-Check:** liest nur die RESULT-Zeile, vergleicht mit der Musterlösung. Kein KI-Modell in diesem Schritt.
4. **Judges** (verschiedene Modelle, laufen bei allen Antworten):
   - Zahlen-Judge: stammt jede Zahl aus dem Dokument, oder ist sie erfunden bzw. falsch zitiert?
   - Rechenweg-Judge: bei falschem Ergebnis, wo ist es schiefgegangen?
   - Plausibilitäts-Judge: passt die Antwort zur Frage, fehlt Pflicht-Information?
5. **Weiterleitung:** Ergebnis richtig und kein Judge flaggt → fertig. Alles andere → menschlicher Reviewer.
6. **Mensch** bestätigt oder korrigiert die Fehlerursache (feste Liste unten).
7. **Stichprobe:** ein Teil der „fertigen“ Fälle geht trotzdem zum Menschen, um zu messen, was die Judges übersehen.
8. **Ergebnis:** Fehlerquote gesamt, pro Fehlertyp, pro Kategorie, pro Modell, plus separate Formatfehlerquote.

## Fehlertypen (feste Liste)

- falsches Ergebnis
- falsche Quelle
- erfundene Zahl
- falsch gerechnet
- ausgelassene Information
- Format nicht eingehalten (wird gemeldet und markiert, zählt aber nicht in die Fehlerquote)

## Regeln

- **Genauigkeit:** exakt. Ausnahme: periodische Zahlen; die Anzahl der Nachkommastellen steht im Testfall.
- **Sprache:** Englisch.

## Testfall-Format

| Feld | Inhalt | Wofür |
|---|---|---|
| id | eindeutige Kennung | |
| kategorie | z. B. Prozentrechnung, Einheiten-Mix, sehr große Zahlen | Fehlerquote pro Kategorie |
| schwierigkeit | z. B. leicht / mittel / schwer | Fehlerquote pro Schwierigkeit |
| dokument | Datei und Seite, die die KI bekommt | Input |
| frage | was die KI ausrechnen soll | Input |
| musterloesung | Wert, Einheit, Nachkommastellen | Python-Check |
| verwendete_zahlen | jede benötigte Zahl mit Fundstelle im Dokument | Zahlen-Judge |
| rechenweg | die Schritte zur Lösung | Rechenweg-Judge |
| pflicht_infos | was in der Antwort stehen muss (Inhalt, den der Leser braucht, keine Beschreibung des Rechenwegs) | Plausibilitäts-Judge |
| fallen | optional: typische falsche Ergebnisse und woher sie kommen | Rechenweg-Judge, Mensch |

**Details zum Format** (übernommen aus dem Testfall-Thread, 2026-10-18):
- JSON, eine Datei pro Charge, Liste von Testfällen.
- `dokument`: `{"datei": "...", "seite": 1}` oder `"seite": "1-2"`.
- `musterloesung`: `{"wert": "7.29", "einheit": "%", "nachkommastellen": 2, "exakt": false}`. Wert als String. `exakt: true` + `nachkommastellen: null` heißt: endliches Ergebnis, muss genau stimmen. Gerundet wird kaufmännisch, nur bei periodischen Ergebnissen.
- Musterlösungen werden per Skript mit exakter Bruchrechnung berechnet, nie von Hand eingetragen.
- Fragen enthalten keine Hinweise auf die Falle (z. B. nicht „use the restated figure“), sonst misst die Eval die Frage statt das Modell.

## Zuständigkeiten und Zählregeln (übernommen aus dem Architektur-Thread, 2026-10-18)

- **Zähleinheit:** pro Antwort. Eine Antwort ist fehlerhaft, wenn sie mindestens einen Fehlertyp hat; sie kann mehrere haben.
- **Wer meldet welchen Fehler:** falsches Ergebnis und Formatfehler → Python; falsche Quelle und erfundene Zahl → Zahlen-Judge; falsch gerechnet → Rechenweg-Judge; ausgelassene Information → Plausibilitäts-Judge; final entscheidet immer der Mensch.
- **Formatfehler:** keine RESULT-Zeile, mehr als eine, Zahl nicht lesbar, Zahlwörter wie „million“ in der Zeile, Einheit fehlt. Falsche Einheit ist kein Formatfehler, sondern falsches Ergebnis.
- **Kaputtes Judge-Urteil** (kein gültiges Urteil geliefert) zählt als Flag → Mensch.
- **Jede Frage nennt die verlangte Genauigkeit** („without rounding“ bzw. „rounded to 2 decimal places“), sonst misst der Test Rundungsgewohnheiten.
- **Ergebnisse mit Unsicherheit:** jede Quote mit 95-%-Konfidenzintervall, dazu eine um die Judge-Übersehrate korrigierte Fehlerquote.
- **Getestete Modelle:** je ein aktuelles Spitzenmodell von Anthropic, OpenAI und Google (hero, 2026-10-18).
- **Technik:** siehe architektur/ARCHITEKTUR.md (Python, JSON/JSONL, Review als CSV).

## Entscheidungen vom 18.10.2026 (hero: „alles wie empfohlen“)

- **Stichprobe:** 20 % der „fertigen“ Fälle, mindestens 30, geschichtet nach Modell × Kategorie.
- **Kein RAG pro Judge:** Jeder Judge bekommt das ganze Dokument. RAG erst bei sehr langen Dokumenten.
- **Formatfehler:** werden nur gezählt und gemeldet, nicht von Judges oder Mensch geprüft.
- **Review:** CSV in Excel/Sheets. Eigene Weboberfläche später möglich.
- **API-Schlüssel** kommen aus einer .env-Datei.
