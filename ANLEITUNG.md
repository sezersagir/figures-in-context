# Figures in Context: Anleitung

So startest du einen Lauf. Konzept: [SPEZIFIKATION.md](SPEZIFIKATION.md), Technik: [architektur/ARCHITEKTUR.md](architektur/ARCHITEKTUR.md).

## Starten

Python 3.9 oder neuer reicht. Zusatzpakete braucht es keine, also auch kein `pip install` und keine venv.

- **Windows:** Doppelklick auf `starten.bat`.
- **Mac/Linux:** Doppelklick auf `starten.command` (oder `python3 -m figures_in_context app`).
- **Von Hand:** im Ordner `figures-in-context` `python -m figures_in_context app` ausführen.

Die Web-App öffnet sich im Browser unter http://127.0.0.1:8765/. Das schwarze Fenster offen lassen, solange du arbeitest; Schließen beendet die App. Die App ist nur von deinem eigenen Rechner aus erreichbar.

## In der Web-App

1. **Einstellungen:** die drei API-Schlüssel eintragen (landen nur lokal in der Datei `.env`) und die Modellnamen prüfen. Bei OpenAI und Google stehen dort `gpt-5` und `gemini-2.5-pro`; trag die aktuellen Spitzenmodelle ein, falls es neuere gibt.
2. **Neuer Lauf:** links unten in der Leiste einen Namen eingeben. Zum Ausprobieren „Probelauf mit Testmodellen“ ankreuzen, das kostet nichts.
3. **Lauf starten:** Antworten, Python-Check, Judges und Weiterleitung laufen nacheinander, mit Fortschrittsanzeige. Bricht etwas ab (Netzwerk, Rate-Limit), einfach „Fortsetzen“ drücken. Schon Vorhandenes wird nicht doppelt angefragt und nicht doppelt bezahlt.
4. **Review öffnen**, Fälle prüfen (siehe unten).
5. **Report erstellen** und **Report ansehen**.

Rechts neben jedem Lauf steht das **Protokoll**: jede Anfrage, sobald sie zurückkommt, mit Testfall, Modell oder Judge, Ergebnis bzw. Urteil und Dauer. Ein Klick auf eine Zeile zeigt Details (Tokens, Befund des Judges, Wiederholungen). Oben stehen die Summen: Anfragen, Fehler, Tokens und Zeit pro Anfrage. Mit den Knöpfen filterst du nach Antworten, Judges oder Fehlern. Fehlgeschlagene Anfragen stehen rot drin, samt Grund. Das Protokoll wird pro Lauf in `laeufe/<lauf>/protokoll.jsonl` gespeichert, bleibt also auch nach dem Schließen erhalten. Die Kalibrierung hat ihr eigenes.

Unten links steht, wie viele Testfälle geladen sind. Stimmt bei einem Testfall eine Zahl oder Seitenangabe nicht mit dem Dokument überein, zeigt die App das als rote Meldung.

## Kommandozeile (geht auch ohne App)

```
python -m figures_in_context pruefe                 # prüft die Testfälle gegen die Dokumente
python -m figures_in_context neu pilot [--test]     # legt laeufe/<datum>_pilot an (--test: Testmodelle)
python -m figures_in_context start <datum>_pilot    # Antworten → Python-Check → Judges → Weiterleitung
python -m figures_in_context review <datum>_pilot   # nur die Review-Oberfläche
python -m figures_in_context auswertung <datum>_pilot
```

API-Schlüssel stehen dann in der Datei `.env` (Vorlage: `.env.example`). Die `.env` nie weitergeben oder hochladen.

## Review

In der App über „Review öffnen“. Die Oberfläche zeigt einen Fall nach dem anderen: Frage, Musterlösung und KI-Ergebnis Ziffer für Ziffer nebeneinander (abweichende Ziffern rot), die Antwort der KI, die Befunde der drei Judges, die bekannten Fallen und auf Wunsch das Dokument.

- Fehlertypen per Klick oder mit den Tasten **1–5** an- und abwählen. Nichts gewählt heißt fehlerfrei.
- **Enter** = geprüft, weiter zum nächsten offenen Fall. **← →** blättern, **D** zeigt das Dokument.
- Jede Änderung wird sofort in `laeufe/<lauf>/review_ergebnis.csv` gespeichert. Du kannst jederzeit aufhören und später weitermachen.

Wer lieber in Excel arbeitet: `review_queue.csv` öffnen, `fehlertypen_final` ausfüllen (mehrere mit Komma), in `geprueft` ein `x` setzen und als `review_ergebnis.csv` speichern.

Ob ein Fall wegen eines Judge-Flags oder als Stichprobe beim Menschen landet, siehst du absichtlich nicht.

Erlaubte Fehlertypen:

| Eintrag | Bedeutung |
|---|---|
| `falsches_ergebnis` | Endergebnis stimmt nicht |
| `falsche_quelle` | Zahl aus dem Dokument, aber die falsche (falsches Jahr, falsche Zeile, Originalwert statt korrigiert …) |
| `erfundene_zahl` | Zahl steht so nirgends im Dokument |
| `falsch_gerechnet` | Rechen- oder Methodenfehler im Rechenweg |
| `ausgelassene_information` | Pflicht-Information fehlt oder Frage nicht beantwortet |

## Report

In der App über „Report erstellen“. Ergebnis: `laeufe/<lauf>/report.md` und `report.html`. Fehlerquoten gesamt und pro Modell, Kategorie, Schwierigkeit und Fehlertyp, jeweils mit 95-%-Konfidenzintervall, dazu Formatfehlerquote, Judge-Übersehrate und Judge-Trefferquote. Du kannst die Auswertung auch schon vor dem Review laufen lassen, dann sind die offenen Fälle als vorläufig markiert.

## Was wo liegt

| Ordner/Datei | Inhalt |
|---|---|
| `config/lauf.json` | Modelle, Wiederholungen, Stichprobe (20 %, mindestens 30) |
| `config/einheiten.json` | erlaubte Schreibweisen von Einheiten (`€` = `EUR`) |
| `prompts/` | Systemprompts für Testobjekt und die drei Judges |
| `starten.bat`, `starten.command` | Start per Doppelklick |
| `figures_in_context/` | der Code, eine Datei pro Stufe; `app.py` + `app.html` ist die Web-App, `review.html` die Review-Oberfläche |
| `kalibrierung/`, `kalibrierungen/` | Antworten für die Judge-Kalibrierung und deren Ergebnisse |
| `laeufe/` | ein Ordner pro Lauf, wird nie überschrieben. `lauf.json` darin protokolliert Modelle, Prompt-Versionen und Testfälle |
| `tests/` | Tests: `python -m unittest discover tests` |

## Judge-Kalibrierung (vor dem ersten Lauf, der zählt)

In der App unter **Kalibrierung** (oder `python -m figures_in_context kalibrierung`). Die Judges bekommen 30 vorbereitete Antworten zu den Testfällen: 19 mit absichtlich eingebautem Fehler (5× falsche Quelle, 4× erfundene Zahl, 5× falsch gerechnet, 5× ausgelassene Information) und 11 fehlerfreie. Gemessen wird pro Judge, nur für seinen Bereich:

- **Fehler gefunden:** eingebauter Fehler, Judge flaggt und nennt den richtigen Typ.
- **Fehlalarme:** fehlerfreie Antwort, Judge flaggt trotzdem.

Bestanden heißt: alle gefunden, kein Fehlalarm, kein kaputtes Urteil. Sonst zeigt „Details“, welche Fälle übersehen wurden und was der Judge dazu geschrieben hat. Dann Prompt oder Judge-Modell anpassen und neu kalibrieren. Wiederholen nach jeder Änderung an Judge-Prompts oder Judge-Modellen.

Die Antworten stehen in `kalibrierung/antworten.json` und werden von `kalibrierung/_quelle/erzeuge.py` erzeugt (alle Zahlen exakt gerechnet). Ergebnisse landen in `kalibrierungen/<datum_uhrzeit>/`.

## Noch offen

- **Pilot** (ARCHITEKTUR.md, Abschnitt 5): nach bestandener Kalibrierung ein kleiner Lauf mit einem Modell, alles von Hand reviewen, dann Prompts und Testfälle nachschärfen.
