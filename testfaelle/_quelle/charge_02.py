"""Erzeugt charge-02.json (Schwerpunkt: sehr grosse Zahlen). Aufruf: python3 charge_02.py"""
import json
from fractions import Fraction as F
from pathlib import Path

from gemeinsam import loesung

MG = "dokumente/meridian-grid-q3-2025-update.md"

faelle = []

# ZE-007 TWh x EUR/MWh
x = F("41.37") * 10**6 * F("87.42")
faelle.append({
    "id": "ZE-007",
    "kategorie": "sehr große Zahlen",
    "schwierigkeit": "schwer",
    "dokument": {"datei": MG, "seite": 1},
    "frage": "How much did Meridian Grid Energy earn from selling electricity in the first nine months of 2025, based on the volume delivered and the average price it realised? Give the exact result in euros (EUR), without rounding.",
    "musterloesung": loesung(x, "EUR", None),
    "verwendete_zahlen": [
        {"wert": "41.37", "einheit": "TWh", "bedeutung": "Electricity delivered 9M 2025", "fundstelle": "Seite 1, Key Figures, Zeile Electricity delivered"},
        {"wert": "87.42", "einheit": "EUR/MWh", "bedeutung": "Average realised electricity price 9M 2025", "fundstelle": "Seite 1, Key Figures"},
    ],
    "rechenweg": [
        "TWh in MWh: 41.37 TWh = 41,370,000 MWh (1 TWh = 1,000,000 MWh)",
        "Erloes: 41,370,000 x 87.42 = 3,616,565,400 EUR",
    ],
    "pflicht_infos": [
        "Nennt Menge und Preis: 41.37 TWh zu 87.42 EUR/MWh",
        "Ergebnis entspricht rund 3.62 Milliarden EUR",
    ],
    "fallen": [
        "Gesamtumsatz 5,912 million statt Berechnung",
        "Faktor 1,000 statt 1,000,000 (TWh -> GWh verwechselt): 3,616,565.4",
        "Wert aus CEO-Zitat (41 TWh): 3,584,220,000",
        "Vorjahreswerte (39.82 TWh, 94.10): 3,747,062,000",
    ],
})

# ZE-008 Marktkapitalisierung
x = 1148273615 * F("23.48")
faelle.append({
    "id": "ZE-008",
    "kategorie": "sehr große Zahlen",
    "schwierigkeit": "mittel",
    "dokument": {"datei": MG, "seite": 1},
    "frage": "What was Meridian Grid Energy's market capitalisation at the end of September 2025? Give the exact result in euros (EUR), without rounding.",
    "musterloesung": loesung(x, "EUR", None),
    "verwendete_zahlen": [
        {"wert": "1,148,273,615", "einheit": "Aktien", "bedeutung": "Shares outstanding excl. treasury, 30 Sep 2025", "fundstelle": "Seite 1, Share information"},
        {"wert": "23.48", "einheit": "EUR", "bedeutung": "XETRA closing price 30 Sep 2025", "fundstelle": "Seite 1, Share information"},
    ],
    "rechenweg": ["1,148,273,615 x 23.48 = 26,961,464,480.20 EUR"],
    "pflicht_infos": [
        "Nennt Aktienzahl und Schlusskurs vom 30 September 2025",
        "Ergebnis entspricht rund 26.96 Milliarden EUR",
    ],
    "fallen": ["Kurs vom 30 June 2025 (21.96): 25,216,088,585.40"],
})

# ZE-009 Halbjaehrlicher Kupon
x = F(2750000000) * F("0.03875") / 2
faelle.append({
    "id": "ZE-009",
    "kategorie": "sehr große Zahlen",
    "schwierigkeit": "schwer",
    "dokument": {"datei": MG, "seite": 2},
    "frage": "How much interest does Meridian Grid Energy pay to the holders of its green bond on each coupon date? Give the exact result in euros (EUR), without rounding.",
    "musterloesung": loesung(x, "EUR", None),
    "verwendete_zahlen": [
        {"wert": "2.75", "einheit": "billion EUR", "bedeutung": "Nominal value green bond", "fundstelle": "Seite 2, Bond issuance"},
        {"wert": "3.875%", "einheit": "p.a.", "bedeutung": "Coupon green bond", "fundstelle": "Seite 2, Bond issuance"},
        {"wert": "semi-annually", "einheit": "", "bedeutung": "Zahlungsrhythmus (2x pro Jahr)", "fundstelle": "Seite 2, Bond issuance"},
    ],
    "rechenweg": [
        "Jahreszins: 2,750,000,000 x 3.875% = 106,562,500 EUR",
        "Halbjaehrlich: 106,562,500 / 2 = 53,281,250 EUR",
    ],
    "pflicht_infos": [
        "Nennt, dass der Kupon halbjaehrlich (2 January und 2 July) gezahlt wird",
        "Nennt den Jahresbetrag von 106,562,500 EUR",
    ],
    "fallen": [
        "Jahreszins statt Halbjahresrate: 106,562,500",
        "Hybridanleihe (1.25 bn, 4.125%) verwechselt: 51,562,500 bzw. 25,781,250",
    ],
})

# ZE-010 Investition pro Kunde
x = F(6250000000, 12483906)
faelle.append({
    "id": "ZE-010",
    "kategorie": "sehr große Zahlen",
    "schwierigkeit": "schwer",
    "dokument": {"datei": MG, "seite": "1-2"},
    "frage": "How much will Meridian Grid Energy's grid investment programme for 2025 to 2029 amount to per customer, based on the latest customer count in the report? Give the result in euros (EUR), rounded to 2 decimal places.",
    "musterloesung": loesung(x, "EUR", 2),
    "verwendete_zahlen": [
        {"wert": "6.25", "einheit": "billion EUR", "bedeutung": "Grid investment programme 2025-2029", "fundstelle": "Seite 2, Grid investment programme"},
        {"wert": "12,483,906", "einheit": "Kunden", "bedeutung": "Customers (supply points) 30 Sep 2025", "fundstelle": "Seite 1, zweite Tabelle"},
    ],
    "rechenweg": [
        "6.25 billion = 6,250,000,000 EUR",
        "6,250,000,000 / 12,483,906 = 500.6445...",
        "Gerundet: 500.64 EUR",
    ],
    "pflicht_infos": [
        "Nennt die Kundenzahl zum 30 September 2025 (12,483,906)",
        "Nennt die Programmsumme von 6.25 Milliarden EUR fuer 2025 bis 2029",
    ],
    "fallen": [
        "Gerundete Kundenzahl aus CEO-Zitat (12.5 million): 500.00",
        "Kundenzahl 31 Dec 2024 (12,107,455): 516.21",
        "Nur 9M-Programmausgaben 1,102 million: 88.27",
    ],
})

# ZE-011 bn vs. million
x = F("14.862") * 1000 * 10**6 - 13975 * 10**6
faelle.append({
    "id": "ZE-011",
    "kategorie": "Einheiten-Mix",
    "schwierigkeit": "mittel",
    "dokument": {"datei": MG, "seite": "1-2"},
    "frage": "By how much did Meridian Grid Energy's net financial debt change between the end of 2024 and 30 September 2025? Give the exact result in euros (EUR), as a positive number for an increase and a negative number for a decrease.",
    "musterloesung": loesung(x, "EUR", None),
    "verwendete_zahlen": [
        {"wert": "14.862", "einheit": "billion EUR", "bedeutung": "Net financial debt 30 Sep 2025", "fundstelle": "Seite 1, zweite Tabelle"},
        {"wert": "13,975", "einheit": "million EUR", "bedeutung": "Net financial debt 31 Dec 2024", "fundstelle": "Seite 1, zweite Tabelle"},
    ],
    "rechenweg": [
        "Gleiche Einheit: 14.862 bn = 14,862 million",
        "Differenz: 14,862 - 13,975 = 887 million",
        "In EUR: 887,000,000",
    ],
    "pflicht_infos": [
        "Sagt, dass die Nettoverschuldung gestiegen ist",
        "Nennt beide Staende: 13,975 million (31 Dec 2024) und 14.862 billion (30 Sep 2025)",
    ],
    "fallen": [
        "Einheiten nicht angeglichen (13,975 - 14.862): ca. -13,960 million",
        "Prognose 15.5 bn statt Ist-Wert: 1,525,000,000",
    ],
})

out = Path(__file__).resolve().parent.parent / "charge-02.json"
out.write_text(json.dumps(faelle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for f in faelle:
    m = f["musterloesung"]
    print(f["id"], m["wert"], m["einheit"], "exakt" if m["exakt"] else f"{m['nachkommastellen']} Stellen")
