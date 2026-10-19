"""Erzeugt kalibrierung/antworten.json: Antworten mit absichtlich eingebauten Fehlern plus fehlerfreie.

    python kalibrierung/_quelle/erzeuge.py

Jede Antwort hat `erwartet`: die eingebauten Fehlertypen (leer = fehlerfrei). Alle Zahlen werden hier
mit Decimal gerechnet, damit in den Antworten keine Tippfehler stecken, die nicht geplant sind.
"""

import json
from decimal import ROUND_HALF_UP, Decimal as D
from pathlib import Path

ZIEL = Path(__file__).resolve().parent.parent / "antworten.json"


def r2(x):
    return x.quantize(D("0.01"), ROUND_HALF_UP)


A = []


def antwort(testfall, erwartet, beschreibung, text, result):
    A.append({"testfall_id": testfall, "erwartet": erwartet, "beschreibung": beschreibung,
              "antwort_text": text.strip() + f"\n\nRESULT: {result}"})


# ---------------- ZE-001 Umsatzwachstum (Lösung 7.29 %) ----------------
antwort("ZE-001", [], "fehlerfrei", """
Revenue 2025: £1,284.6 million. Revenue 2024 as restated: £1,197.3 million (the restated figure is the
correct comparison basis).
Growth: (1,284.6 - 1,197.3) / 1,197.3 = 87.3 / 1,197.3 = 0.072914... = 7.29%.
""", "7.29 %")
antwort("ZE-001", ["falsche_quelle"], "Originalwert 2024 aus Note 4 statt restated", """
Revenue 2025: £1,284.6 million. Revenue 2024: £1,211.8 million as originally reported.
Growth: (1,284.6 - 1,211.8) / 1,211.8 = 72.8 / 1,211.8 = 0.060076... = 6.01%.
""", f"{r2((D('1284.6') - D('1211.8')) / D('1211.8') * 100)} %")
antwort("ZE-001", ["ausgelassene_information"], "nur Ergebnis, Vergleichsbasis fehlt", """
Halvorsen's revenue grew by 7.29% in 2025.
""", "7.29 %")

# ---------------- ZE-002 Umsatz je Mitarbeiter (130,522.25 GBP) ----------------
antwort("ZE-002", [], "fehlerfrei", """
Revenue 2025: £1,284.6 million = £1,284,600,000. Average number of employees in 2025: 9,842.
Revenue per average employee: 1,284,600,000 / 9,842 = 130,522.2515... = £130,522.25.
""", "130522.25 GBP")
antwort("ZE-002", ["falsche_quelle"], "Mitarbeiterzahl 2024 statt 2025", """
Revenue 2025: £1,284.6 million = £1,284,600,000. Average number of employees: 9,517.
Revenue per average employee: 1,284,600,000 / 9,517 = 134,979.51.
""", f"{r2(D(1284600000) / D(9517))} GBP")
antwort("ZE-002", ["falsch_gerechnet"], "richtige Zahlen, Divisionsfehler (eine Ziffer verrutscht)", """
Revenue 2025: £1,284.6 million = £1,284,600,000. Average number of employees in 2025: 9,842.
Revenue per average employee: 1,284,600,000 / 9,842 = 131,522.25.
""", "131522.25 GBP")

# ---------------- ZE-003 Anteil Ocean Forwarding (34.17 %) ----------------
antwort("ZE-003", [], "fehlerfrei", """
Ocean Forwarding revenue 2025 (Note 3): £438,915 thousand, i.e. about £438.9 million.
Total revenue 2025: £1,284.6 million = £1,284,600 thousand.
Share: 438,915 / 1,284,600 = 0.341674... = 34.17%.
""", "34.17 %")
antwort("ZE-003", ["erfundene_zahl"], "Segmentumsatz 452,300 steht nirgends im Dokument", """
Ocean Forwarding revenue 2025: £452,300 thousand, i.e. about £452.3 million.
Total revenue 2025: £1,284.6 million = £1,284,600 thousand.
Share: 452,300 / 1,284,600 = 35.21%.
""", f"{r2(D(452300) / D(1284600) * 100)} %")

# ---------------- ZE-004 Dividendensumme (32,334,339.375 GBP) ----------------
antwort("ZE-004", [], "fehlerfrei", """
Dividend per share for 2025: 3.40p interim + 7.85p proposed final = 11.25 pence = £0.1125.
Shares in issue at 31 December 2025: 287,416,350. As instructed, this assumes the same number of shares
for both the interim and the final dividend.
Total: 287,416,350 x 0.1125 = £32,334,339.375.
""", "32334339.375 GBP")
antwort("ZE-004", ["erfundene_zahl"], "Aktienzahl 290,000,000 erfunden", """
Dividend per share for 2025: 3.40p interim + 7.85p proposed final = 11.25 pence = £0.1125.
Shares in issue: 290,000,000 (assumed to be the same for both payments).
Total: 290,000,000 x 0.1125 = £32,625,000.
""", f"{D(290000000) * D('0.1125'):f} GBP".replace(".0000", ""))
antwort("ZE-004", ["falsch_gerechnet"], "Multiplikation mit Zahlendreher", """
Dividend per share for 2025: 3.40p interim + 7.85p proposed final = 11.25 pence = £0.1125.
Shares in issue at 31 December 2025: 287,416,350, assumed to apply to both payments.
Total: 287,416,350 x 0.1125 = £32,343,339.375.
""", "32343339.375 GBP")

# ---------------- ZE-005 Preiserhöhung A-220 (5.57 %) ----------------
antwort("ZE-005", [], "fehlerfrei", """
Current unit price of A-220: EUR 4.85. New price from 1 March 2026: EUR 5.12.
Increase: (5.12 - 4.85) / 4.85 = 0.27 / 4.85 = 0.055670... = 5.57%.
""", "5.57 %")
antwort("ZE-005", ["falsche_quelle"], "vorläufiger Preis 5.25 aus dem Novemberbrief", """
Current unit price of A-220: EUR 4.85. New price: EUR 5.25 per unit.
Increase: (5.25 - 4.85) / 4.85 = 0.40 / 4.85 = 8.25%.
""", f"{r2((D('5.25') - D('4.85')) / D('4.85') * 100)} %")

# ---------------- ZE-006 Netto-Rechnungswert (1,345,925.40 EUR) ----------------
antwort("ZE-006", [], "fehlerfrei", """
A-220: 48,500 units x EUR 5.12 = EUR 248,320.00
B-310: 1,240 packs of 1,000 x EUR 912.50 per pack = EUR 1,131,500.00
C-045: no quantity in the planning basis = EUR 0
Gross value before rebate: EUR 1,379,820.00
The 3% volume rebate applies only to the part above EUR 250,000: 3% x 1,129,820.00 = EUR 33,894.60.
Net invoice value: 1,379,820.00 - 33,894.60 = EUR 1,345,925.40.
""", "1345925.40 EUR")
antwort("ZE-006", ["falsch_gerechnet"], "Rabatt auf den ganzen Betrag statt nur über der Schwelle", """
A-220: 48,500 units x EUR 5.12 = EUR 248,320.00
B-310: 1,240 packs of 1,000 x EUR 912.50 per pack = EUR 1,131,500.00
Gross value before rebate: EUR 1,379,820.00
Volume rebate of 3% on the gross value: 3% x 1,379,820.00 = EUR 41,394.60.
Net invoice value: 1,379,820.00 - 41,394.60 = EUR 1,338,425.40.
""", "1338425.40 EUR")
antwort("ZE-006", ["ausgelassene_information"], "richtiges Ergebnis, Bruttowert und Rabatthöhe fehlen", """
Using the 2025 quantities and the new prices, and applying the volume rebate as described in the letter,
Brightwater's annual net invoice value comes to EUR 1,345,925.40.
""", "1345925.40 EUR")

# ---------------- ZE-007 Stromerlös (3,616,565,400 EUR) ----------------
antwort("ZE-007", [], "fehlerfrei", """
Electricity delivered in 9M 2025: 41.37 TWh = 41,370,000 MWh (1 TWh = 1,000,000 MWh).
Average realised price: EUR 87.42/MWh.
Revenue: 41,370,000 x 87.42 = EUR 3,616,565,400, i.e. about EUR 3.62 billion.
""", "3616565400 EUR")
antwort("ZE-007", ["erfundene_zahl"], "Preis 89.15 EUR/MWh erfunden", """
Electricity delivered in 9M 2025: 41.37 TWh = 41,370,000 MWh.
Average realised price: EUR 89.15/MWh.
Revenue: 41,370,000 x 89.15 = EUR 3,688,135,500, i.e. about EUR 3.69 billion.
""", f"{D(41370000) * D('89.15'):.0f} EUR")
antwort("ZE-007", ["falsch_gerechnet"], "TWh mit Faktor 1,000 statt 1,000,000 umgerechnet", """
Electricity delivered in 9M 2025: 41.37 TWh = 41,370 MWh.
Average realised price: EUR 87.42/MWh.
Revenue: 41,370 x 87.42 = EUR 3,616,565.40.
""", "3616565.40 EUR")

# ---------------- ZE-008 Marktkapitalisierung (26,961,464,480.2 EUR) ----------------
antwort("ZE-008", [], "fehlerfrei", """
Shares outstanding excluding treasury shares at 30 September 2025: 1,148,273,615.
XETRA closing price on 30 September 2025: EUR 23.48.
Market capitalisation: 1,148,273,615 x 23.48 = EUR 26,961,464,480.20, about EUR 26.96 billion.
""", "26961464480.20 EUR")
antwort("ZE-008", ["falsche_quelle"], "Kurs vom 30. Juni statt 30. September", """
Shares outstanding excluding treasury shares at 30 September 2025: 1,148,273,615.
Share price: EUR 21.96.
Market capitalisation: 1,148,273,615 x 21.96 = EUR 25,216,088,585.40, about EUR 25.22 billion.
""", f"{D(1148273615) * D('21.96')} EUR")
antwort("ZE-008", ["ausgelassene_information"], "richtiges Ergebnis, Aktienzahl und Kurs fehlen", """
Meridian Grid Energy's market capitalisation at the end of September 2025 was EUR 26,961,464,480.20.
""", "26961464480.20 EUR")

# ---------------- ZE-009 Kupon Green Bond (53,281,250 EUR) ----------------
antwort("ZE-009", [], "fehlerfrei", """
Green bond nominal value: EUR 2.75 billion = EUR 2,750,000,000. Coupon: 3.875% p.a.
Annual interest: 2,750,000,000 x 3.875% = EUR 106,562,500.
The coupon is paid semi-annually (2 January and 2 July), so each payment is 106,562,500 / 2 = EUR 53,281,250.
""", "53281250 EUR")
antwort("ZE-009", ["erfundene_zahl"], "Kupon 4.0 % erfunden", """
Green bond nominal value: EUR 2.75 billion = EUR 2,750,000,000. Coupon: 4.0% p.a.
Annual interest: 2,750,000,000 x 4.0% = EUR 110,000,000.
The coupon is paid semi-annually (2 January and 2 July), so each payment is EUR 55,000,000.
""", f"{D(2750000000) * D('0.04') / 2:.0f} EUR")
antwort("ZE-009", ["ausgelassene_information"], "richtiges Ergebnis, Zahlungsrhythmus und Jahresbetrag fehlen", """
Each coupon payment on the green bond amounts to EUR 53,281,250.
""", "53281250 EUR")

# ---------------- ZE-010 Investition je Kunde (500.64 EUR) ----------------
antwort("ZE-010", [], "fehlerfrei", """
Grid investment programme 2025 to 2029: EUR 6.25 billion = EUR 6,250,000,000.
Latest customer count (supply points at 30 September 2025): 12,483,906.
Per customer: 6,250,000,000 / 12,483,906 = 500.6445... = EUR 500.64.
""", "500.64 EUR")
antwort("ZE-010", ["falsche_quelle"], "Kundenzahl vom 31.12.2024 statt der neuesten", """
Grid investment programme 2025 to 2029: EUR 6.25 billion = EUR 6,250,000,000.
Customer count: 12,107,455.
Per customer: 6,250,000,000 / 12,107,455 = EUR 516.21.
""", f"{r2(D(6250000000) / D(12107455))} EUR")

# ---------------- ZE-011 Veränderung Nettoverschuldung (887,000,000 EUR) ----------------
antwort("ZE-011", [], "fehlerfrei", """
Net financial debt at 31 December 2024: EUR 13,975 million.
Net financial debt at 30 September 2025: EUR 14.862 billion = EUR 14,862 million.
Change: 14,862 - 13,975 = +887 million, so net financial debt increased by EUR 887,000,000.
""", "887000000 EUR")
antwort("ZE-011", ["falsch_gerechnet"], "Subtraktionsfehler (897 statt 887)", """
Net financial debt at 31 December 2024: EUR 13,975 million.
Net financial debt at 30 September 2025: EUR 14.862 billion = EUR 14,862 million.
Change: 14,862 - 13,975 = +897 million, so net financial debt increased by EUR 897,000,000.
""", "897000000 EUR")
antwort("ZE-011", ["ausgelassene_information"], "richtiges Ergebnis, Richtung und beide Stände fehlen", """
The change in net financial debt between the end of 2024 and 30 September 2025 was EUR 887,000,000.
""", "887000000 EUR")

for i, a in enumerate(A, 1):
    a["kal_id"] = f"K-{i:03d}"
ZIEL.write_text(json.dumps([{"kal_id": a.pop("kal_id"), **a} for a in A], indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")
print(f"{len(A)} Antworten, davon {sum(1 for a in A if not a['erwartet'])} fehlerfrei → {ZIEL}")
