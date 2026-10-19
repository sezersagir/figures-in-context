# Vorschläge zum Testfall-Format (für die SPEZIFIKATION.md)

Die Spezifikation gehört dem Thread „Figures in Context Konzept“. Hier stehen nur Vorschläge aus dem Testfall-Thread; charge-01.json nutzt sie schon, sie lassen sich aber ohne Folgen wieder entfernen.

1. **Datenformat:** JSON, eine Datei pro Charge, Liste von Testfällen. Feldnamen genau wie in der Spezifikation.
2. **Neues Feld `fallen`** (optional): typische falsche Ergebnisse und woher sie kommen (z. B. „Originalwert statt restated → 6.01%“). Hilft dem Rechenweg-Judge und dem Menschen, die Fehlerursache schnell zuzuordnen.
3. **`musterloesung` genauer:** `{"wert": "7.29", "einheit": "%", "nachkommastellen": 2, "exakt": false}`. `nachkommastellen: null` + `exakt: true` heißt: endliches Ergebnis, muss genau stimmen. Gerundet wird kaufmännisch (ab 5 aufrunden), nur bei periodischen Ergebnissen.
4. **`dokument`:** `{"datei": "...", "seite": 1}` oder `"seite": "1-2"`, wenn die KI beide Seiten braucht. Die Dokumente sind vorerst Markdown mit Seitenüberschriften; PDF können wir später daraus erzeugen.
5. **Musterlösungen werden per Skript berechnet** (`_quelle/charge_01.py`, exakte Bruchrechnung), nie von Hand eingetragen. Das Skript bricht ab, wenn ein endliches Ergebnis gerundet oder ein periodisches exakt verlangt würde.
