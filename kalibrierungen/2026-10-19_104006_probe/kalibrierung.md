# Judge-Kalibrierung 2026-10-19_104006_probe

**Probelauf mit Testmodellen: Die Zahlen sagen nichts über echte Judges.**

30 Antworten, davon 11 fehlerfrei. Ziel: alle eingebauten Fehler finden, keine fehlerfreie Antwort flaggen.

| Judge | Modell | Gefunden | Fehlalarme | Kaputte Urteile | Ergebnis |
|---|---|---|---|---|---|
| Zahlen-Judge | test:judge-zahlen | 22.2% (6.3%–54.7%), 2/9 | 9.1% (1.6%–37.7%), 1/11 | 0 | **nachschärfen** |
| Rechenweg-Judge | test:judge-rechenweg | 40.0% (11.8%–76.9%), 2/5 | 9.1% (1.6%–37.7%), 1/11 | 0 | **nachschärfen** |
| Plausibilitäts-Judge | test:judge-plausibilitaet | 40.0% (11.8%–76.9%), 2/5 | 54.5% (28.0%–78.7%), 6/11 | 0 | **nachschärfen** |

Bei so wenigen Antworten sind die Konfidenzintervalle breit. Die Kalibrierung zeigt vor allem, welche Fehler ein Judge übersieht, und dafür lohnt der Blick auf die Einzelfälle unten.

## Zahlen-Judge

- **Übersehen** K-002 (ZE-001, Originalwert 2024 aus Note 4 statt restated): No problems found (test model).
- **Übersehen** K-005 (ZE-002, Mitarbeiterzahl 2024 statt 2025): No problems found (test model).
- **Übersehen** K-010 (ZE-004, Aktienzahl 290,000,000 erfunden): Testurteil.
- **Übersehen** K-013 (ZE-005, vorläufiger Preis 5.25 aus dem Novemberbrief): No problems found (test model).
- **Übersehen** K-018 (ZE-007, Preis 89.15 EUR/MWh erfunden): No problems found (test model).
- **Übersehen** K-021 (ZE-008, Kurs vom 30. Juni statt 30. September): No problems found (test model).
- **Übersehen** K-024 (ZE-009, Kupon 4.0 % erfunden): No problems found (test model).
- **Fehlalarm** K-026 (ZE-010): falsche_quelle: Testurteil.

## Rechenweg-Judge

- **Übersehen** K-006 (ZE-002, richtige Zahlen, Divisionsfehler (eine Ziffer verrutscht)): No problems found (test model).
- **Übersehen** K-015 (ZE-006, Rabatt auf den ganzen Betrag statt nur über der Schwelle): No problems found (test model).
- **Übersehen** K-019 (ZE-007, TWh mit Faktor 1,000 statt 1,000,000 umgerechnet): No problems found (test model).
- **Fehlalarm** K-007 (ZE-003): falsch_gerechnet: Testurteil.

## Plausibilitäts-Judge

- **Übersehen** K-003 (ZE-001, nur Ergebnis, Vergleichsbasis fehlt): No problems found (test model).
- **Übersehen** K-016 (ZE-006, richtiges Ergebnis, Bruttowert und Rabatthöhe fehlen): No problems found (test model).
- **Übersehen** K-030 (ZE-011, richtiges Ergebnis, Richtung und beide Stände fehlen): No problems found (test model).
- **Fehlalarm** K-001 (ZE-001): ausgelassene_information: Testurteil.
- **Fehlalarm** K-009 (ZE-004): ausgelassene_information: Testurteil.
- **Fehlalarm** K-012 (ZE-005): ausgelassene_information: Testurteil.
- **Fehlalarm** K-017 (ZE-007): ausgelassene_information: Testurteil.
- **Fehlalarm** K-026 (ZE-010): ausgelassene_information: Testurteil.
- **Fehlalarm** K-028 (ZE-011): ausgelassene_information: Testurteil.

## Was tun bei „nachschärfen“?

- Befund des Judges zu den übersehenen Fällen lesen: Hat er den Fehler nicht gesehen oder falsch eingeordnet?
- Prompt im Ordner prompts (judge_zahlen.md, judge_rechenweg.md, judge_plausibilitaet.md) anpassen oder ein anderes Modell in den Einstellungen wählen.
- Danach eine neue Kalibrierung starten. Erst wenn alle drei bestanden haben, zählt ein echter Lauf voll.
