# Figures in Context: Testfälle

- `charge-01.json`: erste Charge, 6 Testfälle (ZE-001 bis ZE-006)
- `charge-02.json`: zweite Charge, 5 Testfälle (ZE-007 bis ZE-011), Schwerpunkt sehr große Zahlen
- `dokumente/`: die Dokumente, die die KI bekommt (Englisch, fiktive Firmen)
- `_quelle/charge_NN.py`: erzeugt charge-NN.json und rechnet die Musterlösungen exakt nach (`python3 charge_01.py`), Hilfsfunktionen in `_quelle/gemeinsam.py`
- `VORSCHLAG-FORMAT.md`: Format-Vorschläge, inzwischen in die Spezifikation übernommen

| id | Kategorie | Schwierigkeit | Lösung | Hauptfalle |
|---|---|---|---|---|
| ZE-001 | Prozentrechnung | leicht | 7.29 % | restated vs. original Vorjahresumsatz |
| ZE-002 | Einheiten-Mix | mittel | 130,522.25 GBP | £ million → GBP |
| ZE-003 | Einheiten-Mix | mittel | 34.17 % | £ thousand vs. £ million |
| ZE-004 | sehr große Zahlen | mittel | 32,334,339.375 GBP | pence → GBP, Summe 11.25p steht nirgends |
| ZE-005 | Prozentrechnung | leicht | 5.57 % | vorläufiger Preis 5.25 |
| ZE-006 | mehrstufige Berechnung | schwer | 1,345,925.40 EUR | Rabatt nur über Schwelle, Packs à 1,000 |
| ZE-007 | sehr große Zahlen | schwer | 3,616,565,400 EUR | TWh → MWh, Gesamtumsatz als Ablenkung |
| ZE-008 | sehr große Zahlen | mittel | 26,961,464,480.20 EUR | Kurs vom falschen Stichtag |
| ZE-009 | sehr große Zahlen | schwer | 53,281,250 EUR | halbjährlicher Kupon, zweite Anleihe |
| ZE-010 | sehr große Zahlen | schwer | 500.64 EUR | gerundete Kundenzahl aus CEO-Zitat |
| ZE-011 | Einheiten-Mix | mittel | 887,000,000 EUR | bn vs. million in einer Tabelle |
