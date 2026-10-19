# Vorschläge zur SPEZIFIKATION.md (aus dem Architektur-Thread)

Die Spezifikation gehört dem Thread „Figures in Context Konzept“. Hier stehen nur Vorschläge; übernommen wird, was hero entscheidet. Begründungen stehen in [ARCHITEKTUR.md](ARCHITEKTUR.md).

1. **„Offen: Technik“ schließen:** Python 3.11+, offizielle SDKs der drei Anbieter, Testfälle als JSON (Format des Testfall-Threads), Dokumente als Markdown, Laufdaten als JSONL, Review als CSV. Details: ARCHITEKTUR.md, Abschnitt 4.

2. **Zähleinheit festschreiben:** Ein Fehler wird **pro Antwort** gezählt. Eine Antwort ist fehlerhaft, wenn sie mindestens einen Fehlertyp hat; sie kann mehrere haben. Ohne diese Regel sind Fehlerquoten zwischen Läufen nicht vergleichbar.

3. **Zuständigkeit pro Fehlertyp festschreiben:**

   | Fehlertyp | wer meldet |
   |---|---|
   | falsches Ergebnis | Python |
   | Format nicht eingehalten | Python |
   | falsche Quelle, erfundene Zahl | Zahlen-Judge |
   | falsch gerechnet | Rechenweg-Judge |
   | ausgelassene Information | Plausibilitäts-Judge |
   | alle (final) | Mensch |

4. **Was ist ein Formatfehler?** Keine RESULT-Zeile, mehr als eine, Zahl nicht lesbar, Zahlwörter wie „million“ in der Zeile, Einheit fehlt. Falsche Einheit ist kein Formatfehler, sondern falsches Ergebnis.

5. **Kaputtes Judge-Urteil = Flag.** Liefert ein Judge kein gültiges Urteil, geht der Fall zum Menschen, statt still als „fertig“ durchzurutschen.

6. **Genauigkeit in jeder Frage nennen** (charge-01 macht das schon, als Regel festschreiben). Bei `exakt: true` mit vielen Nachkommastellen (z. B. ZE-004: 32,334,339.375 GBP) würde ein Modell ohne Hinweis auf Pence runden und wäre „falsch“, obwohl es richtig gerechnet hat. Deshalb sagt jede Frage, wie genau das Ergebnis sein soll („without rounding“ bzw. „rounded to 2 decimal places“). Sonst misst der Test Rundungsgewohnheiten statt Rechenfehler.

7. **Stichprobe (Schritt 7):** Standardvorschlag 20 % der „fertigen“ Fälle, mindestens 30, geschichtet nach Modell × Kategorie, fester Zufalls-Seed. Entscheidung liegt bei hero.

8. **Ergebnis mit Unsicherheit berichten:** Jede Quote mit 95-%-Konfidenzintervall, und neben der gemessenen Fehlerquote eine um die Judge-Übersehrate korrigierte.
