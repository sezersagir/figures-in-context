"""Erzeugt charge-01.json. Musterloesungen werden hier exakt (Fraction) berechnet,
nicht von Hand eingetragen. Aufruf: python3 charge_01.py"""
import json
from fractions import Fraction as F
from pathlib import Path

from gemeinsam import loesung

AR = "dokumente/halvorsen-annual-report-2025.md"
BR = "dokumente/kessler-price-adjustment-letter.md"

faelle = []

# T001 Prozentrechnung, leicht
x = (F("1284.6") - F("1197.3")) / F("1197.3") * 100
faelle.append({
    "id": "ZE-001",
    "kategorie": "Prozentrechnung",
    "schwierigkeit": "leicht",
    "dokument": {"datei": AR, "seite": 1},
    "frage": "By what percentage did Halvorsen Freight Group's revenue grow in 2025 compared with 2024? Give the result in percent, rounded to 2 decimal places.",
    "musterloesung": loesung(x, "%", 2),
    "verwendete_zahlen": [
        {"wert": "1,284.6", "einheit": "£ million", "bedeutung": "Revenue 2025", "fundstelle": "Seite 1, Financial Highlights, Zeile Revenue"},
        {"wert": "1,197.3", "einheit": "£ million", "bedeutung": "Revenue 2024 (restated)", "fundstelle": "Seite 1, Financial Highlights, Zeile Revenue"},
    ],
    "rechenweg": [
        "Differenz: 1,284.6 - 1,197.3 = 87.3 (£ million)",
        "Wachstum: 87.3 / 1,197.3 = 0.072914...",
        "In Prozent: 7.2914...% -> gerundet 7.29%",
    ],
    "pflicht_infos": [
        "Nennt die Vergleichsbasis: korrigierter (restated) Umsatz 2024 von 1,197.3 £ million",
    ],
    "fallen": ["Originalwert 1,211.8 aus Note 4 ergaebe 6.01%"],
})

# T002 Einheiten-Mix, mittel
x = F(1284600000, 9842)
faelle.append({
    "id": "ZE-002",
    "kategorie": "Einheiten-Mix",
    "schwierigkeit": "mittel",
    "dokument": {"datei": AR, "seite": 1},
    "frage": "What was Halvorsen Freight Group's revenue per average employee in 2025? Give the result in pounds sterling (GBP), rounded to 2 decimal places.",
    "musterloesung": loesung(x, "GBP", 2),
    "verwendete_zahlen": [
        {"wert": "1,284.6", "einheit": "£ million", "bedeutung": "Revenue 2025", "fundstelle": "Seite 1, Financial Highlights, Zeile Revenue"},
        {"wert": "9,842", "einheit": "Personen", "bedeutung": "Average number of employees 2025", "fundstelle": "Seite 1, Financial Highlights, letzte Zeile"},
    ],
    "rechenweg": [
        "Umsatz in GBP: 1,284.6 million = 1,284,600,000",
        "Pro Mitarbeiter: 1,284,600,000 / 9,842 = 130,522.2515...",
        "Gerundet: 130,522.25 GBP",
    ],
    "pflicht_infos": [
        "Nennt die Bezugsgroesse: durchschnittlich 9,842 Mitarbeiter in 2025",
    ],
    "fallen": ["Ohne Umrechnung von Millionen kaeme 0.13 heraus", "Mitarbeiterzahl 2024 (9,517) ergaebe 134,979.51"],
})

# T003 Einheiten-Mix, mittel (Segment in £ thousand vs. Gruppe in £ million)
x = F(438915, 1284600) * 100
faelle.append({
    "id": "ZE-003",
    "kategorie": "Einheiten-Mix",
    "schwierigkeit": "mittel",
    "dokument": {"datei": AR, "seite": "1-2"},
    "frage": "What share of Halvorsen Freight Group's total 2025 revenue came from the Ocean Forwarding segment? Give the result in percent, rounded to 2 decimal places.",
    "musterloesung": loesung(x, "%", 2),
    "verwendete_zahlen": [
        {"wert": "438,915", "einheit": "£ thousand", "bedeutung": "Ocean Forwarding revenue 2025", "fundstelle": "Seite 2, Note 3, Zeile Ocean Forwarding"},
        {"wert": "1,284.6", "einheit": "£ million", "bedeutung": "Revenue 2025", "fundstelle": "Seite 1, Financial Highlights, Zeile Revenue"},
    ],
    "rechenweg": [
        "Gleiche Einheit herstellen: 1,284.6 £ million = 1,284,600 £ thousand",
        "Anteil: 438,915 / 1,284,600 = 0.341674...",
        "In Prozent: 34.1674...% -> gerundet 34.17%",
    ],
    "pflicht_infos": ["Nennt den Segmentumsatz Ocean Forwarding 2025 (ca. £438.9 million)"],
    "fallen": ["Ohne Angleichen: 438,915 / 1,284.6 ergibt einen absurden Wert (ca. 34,167%)"],
})

# T004 sehr grosse Zahlen, mittel
x = 287416350 * (F("3.40") + F("7.85")) / 100
faelle.append({
    "id": "ZE-004",
    "kategorie": "sehr große Zahlen",
    "schwierigkeit": "mittel",
    "dokument": {"datei": AR, "seite": 1},
    "frage": "Assuming the number of shares in issue at 31 December 2025 applies to both the interim and the proposed final dividend, what is the total dividend amount for the 2025 financial year? Give the exact result in pounds sterling (GBP), without rounding.",
    "musterloesung": loesung(x, "GBP", None),
    "verwendete_zahlen": [
        {"wert": "287,416,350", "einheit": "Aktien", "bedeutung": "Shares in issue at 31 December 2025", "fundstelle": "Seite 1, Absatz unter der Tabelle"},
        {"wert": "3.40", "einheit": "pence", "bedeutung": "Interim dividend per share 2025", "fundstelle": "Seite 1, Financial Highlights"},
        {"wert": "7.85", "einheit": "pence", "bedeutung": "Proposed final dividend per share 2025", "fundstelle": "Seite 1, Financial Highlights (auch Chair's statement)"},
    ],
    "rechenweg": [
        "Dividende pro Aktie gesamt: 3.40 + 7.85 = 11.25 pence",
        "In GBP: 11.25 pence = 0.1125 GBP",
        "Gesamt: 287,416,350 x 0.1125 = 32,334,339.375 GBP",
    ],
    "pflicht_infos": [
        "Nennt die Dividende pro Aktie fuer 2025: 11.25 pence (3.40 interim + 7.85 final)",
        "Weist darauf hin, dass der Betrag auf der Annahme gleicher Aktienzahl beruht",
    ],
    "fallen": ["Aktienzahl 2024 (291,032,800) ergaebe 32,741,190", "Ohne pence-Umrechnung 100-fach zu gross", "Nur Schlussdividende 7.85p ergaebe 22,562,183.475", "Dividenden 2024 (3.15 + 7.60) ergaebe 30,897,257.625"],
})

# T005 Prozentrechnung, leicht (Brief)
x = (F("5.12") - F("4.85")) / F("4.85") * 100
faelle.append({
    "id": "ZE-005",
    "kategorie": "Prozentrechnung",
    "schwierigkeit": "leicht",
    "dokument": {"datei": BR, "seite": 1},
    "frage": "By what percentage will the unit price of article A-220 increase from 1 March 2026? Give the result in percent, rounded to 2 decimal places.",
    "musterloesung": loesung(x, "%", 2),
    "verwendete_zahlen": [
        {"wert": "4.85", "einheit": "EUR pro Stueck", "bedeutung": "Current price A-220", "fundstelle": "Seite 1, Preistabelle, Zeile A-220"},
        {"wert": "5.12", "einheit": "EUR pro Stueck", "bedeutung": "New price A-220", "fundstelle": "Seite 1, Preistabelle, Zeile A-220"},
    ],
    "rechenweg": [
        "Differenz: 5.12 - 4.85 = 0.27 EUR",
        "Anstieg: 0.27 / 4.85 = 0.055670...",
        "In Prozent: 5.5670...% -> gerundet 5.57%",
    ],
    "pflicht_infos": ["Nennt alten und neuen Preis: 4.85 EUR -> 5.12 EUR pro Stueck"],
    "fallen": ["Vorlaeufiger Preis 5.25 aus dem Novemberbrief ergaebe 8.25%"],
})

# T006 mehrstufig, schwer (Brief)
a = 48500 * F("5.12")
b = 1240 * F("912.50")
brutto = a + b
x = brutto - F("0.03") * (brutto - 250000)
faelle.append({
    "id": "ZE-006",
    "kategorie": "mehrstufige Berechnung",
    "schwierigkeit": "schwer",
    "dokument": {"datei": BR, "seite": "1-2"},
    "frage": "Using the 2025 quantities given as the planning basis and the new prices, what would Brightwater Packaging Ltd's annual net invoice value be after the volume rebate? Give the exact result in euros (EUR), without rounding.",
    "musterloesung": loesung(x, "EUR", None),
    "verwendete_zahlen": [
        {"wert": "48,500", "einheit": "Stueck", "bedeutung": "Menge A-220", "fundstelle": "Seite 2, Planning basis"},
        {"wert": "5.12", "einheit": "EUR pro Stueck", "bedeutung": "New price A-220", "fundstelle": "Seite 1, Preistabelle"},
        {"wert": "1,240", "einheit": "Packs a 1,000 Stueck", "bedeutung": "Menge B-310", "fundstelle": "Seite 2, Planning basis"},
        {"wert": "912.50", "einheit": "EUR pro 1,000 Stueck", "bedeutung": "New price B-310", "fundstelle": "Seite 1, Preistabelle"},
        {"wert": "3%", "einheit": "", "bedeutung": "Volume rebate", "fundstelle": "Seite 2, Volume rebate"},
        {"wert": "250,000", "einheit": "EUR", "bedeutung": "Rebate-Schwelle", "fundstelle": "Seite 2, Volume rebate"},
    ],
    "rechenweg": [
        "A-220: 48,500 x 5.12 = 248,320.00 EUR",
        "B-310: 1,240 Packs x 912.50 = 1,131,500.00 EUR",
        "C-045: 0 Stueck = 0 EUR",
        "Brutto: 248,320 + 1,131,500 = 1,379,820.00 EUR",
        "Rabatt nur auf den Teil ueber 250,000: 3% x 1,129,820 = 33,894.60 EUR",
        "Netto: 1,379,820 - 33,894.60 = 1,345,925.40 EUR",
    ],
    "pflicht_infos": [
        "Nennt den Bruttowert vor Rabatt: 1,379,820.00 EUR",
        "Nennt die Hoehe des Rabatts: 33,894.60 EUR",
    ],
    "fallen": [
        "Rabatt auf den ganzen Betrag: 1,338,425.40",
        "B-310 als 1,240 Stueck statt Packs gerechnet",
        "USD-Umrechnung mit 1.0835 (gilt nur fuer die US-Tochter)",
    ],
})

out = Path(__file__).resolve().parent.parent / "charge-01.json"
out.write_text(json.dumps(faelle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for f in faelle:
    m = f["musterloesung"]
    print(f["id"], m["wert"], m["einheit"], "exakt" if m["exakt"] else f"{m['nachkommastellen']} Stellen")
