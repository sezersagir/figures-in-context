"""Generates calibration/answers.json: answers with deliberately planted errors plus clean ones.

    python calibration/_source/generate.py

Every answer has `expected`: the planted error types (empty = clean). All numbers are computed here
with Decimal, so the answers contain no typos that weren't planned.
"""

import json
from decimal import ROUND_HALF_UP, Decimal as D
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / "answers.json"


def r2(x):
    return x.quantize(D("0.01"), ROUND_HALF_UP)


A = []


def answer(case, expected, description, text, result):
    A.append({"case_id": case, "expected": expected, "description": description,
              "answer_text": text.strip() + f"\n\nRESULT: {result}"})


# ---------------- FC-001 revenue growth (answer 7.29 %) ----------------
answer("FC-001", [], "clean", """
Revenue 2025: £1,284.6 million. Revenue 2024 as restated: £1,197.3 million (the restated figure is the
correct comparison basis).
Growth: (1,284.6 - 1,197.3) / 1,197.3 = 87.3 / 1,197.3 = 0.072914... = 7.29%.
""", "7.29 %")
answer("FC-001", ["wrong_source"], "original 2024 figure from Note 4 instead of restated", """
Revenue 2025: £1,284.6 million. Revenue 2024: £1,211.8 million as originally reported.
Growth: (1,284.6 - 1,211.8) / 1,211.8 = 72.8 / 1,211.8 = 0.060076... = 6.01%.
""", f"{r2((D('1284.6') - D('1211.8')) / D('1211.8') * 100)} %")
answer("FC-001", ["missing_information"], "result only, basis of comparison missing", """
Halvorsen's revenue grew by 7.29% in 2025.
""", "7.29 %")

# ---------------- FC-002 revenue per employee (130,522.25 GBP) ----------------
answer("FC-002", [], "clean", """
Revenue 2025: £1,284.6 million = £1,284,600,000. Average number of employees in 2025: 9,842.
Revenue per average employee: 1,284,600,000 / 9,842 = 130,522.2515... = £130,522.25.
""", "130522.25 GBP")
answer("FC-002", ["wrong_source"], "2024 headcount instead of 2025", """
Revenue 2025: £1,284.6 million = £1,284,600,000. Average number of employees: 9,517.
Revenue per average employee: 1,284,600,000 / 9,517 = 134,979.51.
""", f"{r2(D(1284600000) / D(9517))} GBP")
answer("FC-002", ["calculation_error"], "right numbers, division error (one digit off)", """
Revenue 2025: £1,284.6 million = £1,284,600,000. Average number of employees in 2025: 9,842.
Revenue per average employee: 1,284,600,000 / 9,842 = 131,522.25.
""", "131522.25 GBP")

# ---------------- FC-003 Ocean Forwarding share (34.17 %) ----------------
answer("FC-003", [], "clean", """
Ocean Forwarding revenue 2025 (Note 3): £438,915 thousand, i.e. about £438.9 million.
Total revenue 2025: £1,284.6 million = £1,284,600 thousand.
Share: 438,915 / 1,284,600 = 0.341674... = 34.17%.
""", "34.17 %")
answer("FC-003", ["invented_number"], "segment revenue 452,300 appears nowhere in the document", """
Ocean Forwarding revenue 2025: £452,300 thousand, i.e. about £452.3 million.
Total revenue 2025: £1,284.6 million = £1,284,600 thousand.
Share: 452,300 / 1,284,600 = 35.21%.
""", f"{r2(D(452300) / D(1284600) * 100)} %")

# ---------------- FC-004 total dividend (32,334,339.375 GBP) ----------------
answer("FC-004", [], "clean", """
Dividend per share for 2025: 3.40p interim + 7.85p proposed final = 11.25 pence = £0.1125.
Shares in issue at 31 December 2025: 287,416,350. As instructed, this assumes the same number of shares
for both the interim and the final dividend.
Total: 287,416,350 x 0.1125 = £32,334,339.375.
""", "32334339.375 GBP")
answer("FC-004", ["invented_number"], "share count 290,000,000 invented", """
Dividend per share for 2025: 3.40p interim + 7.85p proposed final = 11.25 pence = £0.1125.
Shares in issue: 290,000,000 (assumed to be the same for both payments).
Total: 290,000,000 x 0.1125 = £32,625,000.
""", f"{D(290000000) * D('0.1125'):f} GBP".replace(".0000", ""))
answer("FC-004", ["calculation_error"], "multiplication with transposed digits", """
Dividend per share for 2025: 3.40p interim + 7.85p proposed final = 11.25 pence = £0.1125.
Shares in issue at 31 December 2025: 287,416,350, assumed to apply to both payments.
Total: 287,416,350 x 0.1125 = £32,343,339.375.
""", "32343339.375 GBP")

# ---------------- FC-005 A-220 price increase (5.57 %) ----------------
answer("FC-005", [], "clean", """
Current unit price of A-220: EUR 4.85. New price from 1 March 2026: EUR 5.12.
Increase: (5.12 - 4.85) / 4.85 = 0.27 / 4.85 = 0.055670... = 5.57%.
""", "5.57 %")
answer("FC-005", ["wrong_source"], "provisional price 5.25 from the November letter", """
Current unit price of A-220: EUR 4.85. New price: EUR 5.25 per unit.
Increase: (5.25 - 4.85) / 4.85 = 0.40 / 4.85 = 8.25%.
""", f"{r2((D('5.25') - D('4.85')) / D('4.85') * 100)} %")

# ---------------- FC-006 net invoice value (1,345,925.40 EUR) ----------------
answer("FC-006", [], "clean", """
A-220: 48,500 units x EUR 5.12 = EUR 248,320.00
B-310: 1,240 packs of 1,000 x EUR 912.50 per pack = EUR 1,131,500.00
C-045: no quantity in the planning basis = EUR 0
Gross value before rebate: EUR 1,379,820.00
The 3% volume rebate applies only to the part above EUR 250,000: 3% x 1,129,820.00 = EUR 33,894.60.
Net invoice value: 1,379,820.00 - 33,894.60 = EUR 1,345,925.40.
""", "1345925.40 EUR")
answer("FC-006", ["calculation_error"], "rebate on the whole amount instead of only above the threshold", """
A-220: 48,500 units x EUR 5.12 = EUR 248,320.00
B-310: 1,240 packs of 1,000 x EUR 912.50 per pack = EUR 1,131,500.00
Gross value before rebate: EUR 1,379,820.00
Volume rebate of 3% on the gross value: 3% x 1,379,820.00 = EUR 41,394.60.
Net invoice value: 1,379,820.00 - 41,394.60 = EUR 1,338,425.40.
""", "1338425.40 EUR")
answer("FC-006", ["missing_information"], "right result, gross value and rebate amount missing", """
Using the 2025 quantities and the new prices, and applying the volume rebate as described in the letter,
Brightwater's annual net invoice value comes to EUR 1,345,925.40.
""", "1345925.40 EUR")

# ---------------- FC-007 electricity revenue (3,616,565,400 EUR) ----------------
answer("FC-007", [], "clean", """
Electricity delivered in 9M 2025: 41.37 TWh = 41,370,000 MWh (1 TWh = 1,000,000 MWh).
Average realised price: EUR 87.42/MWh.
Revenue: 41,370,000 x 87.42 = EUR 3,616,565,400, i.e. about EUR 3.62 billion.
""", "3616565400 EUR")
answer("FC-007", ["invented_number"], "price 89.15 EUR/MWh invented", """
Electricity delivered in 9M 2025: 41.37 TWh = 41,370,000 MWh.
Average realised price: EUR 89.15/MWh.
Revenue: 41,370,000 x 89.15 = EUR 3,688,135,500, i.e. about EUR 3.69 billion.
""", f"{D(41370000) * D('89.15'):.0f} EUR")
answer("FC-007", ["calculation_error"], "TWh converted with factor 1,000 instead of 1,000,000", """
Electricity delivered in 9M 2025: 41.37 TWh = 41,370 MWh.
Average realised price: EUR 87.42/MWh.
Revenue: 41,370 x 87.42 = EUR 3,616,565.40.
""", "3616565.40 EUR")

# ---------------- FC-008 market capitalisation (26,961,464,480.2 EUR) ----------------
answer("FC-008", [], "clean", """
Shares outstanding excluding treasury shares at 30 September 2025: 1,148,273,615.
XETRA closing price on 30 September 2025: EUR 23.48.
Market capitalisation: 1,148,273,615 x 23.48 = EUR 26,961,464,480.20, about EUR 26.96 billion.
""", "26961464480.20 EUR")
answer("FC-008", ["wrong_source"], "price on 30 June instead of 30 September", """
Shares outstanding excluding treasury shares at 30 September 2025: 1,148,273,615.
Share price: EUR 21.96.
Market capitalisation: 1,148,273,615 x 21.96 = EUR 25,216,088,585.40, about EUR 25.22 billion.
""", f"{D(1148273615) * D('21.96')} EUR")
answer("FC-008", ["missing_information"], "right result, share count and price missing", """
Meridian Grid Energy's market capitalisation at the end of September 2025 was EUR 26,961,464,480.20.
""", "26961464480.20 EUR")

# ---------------- FC-009 green bond coupon (53,281,250 EUR) ----------------
answer("FC-009", [], "clean", """
Green bond nominal value: EUR 2.75 billion = EUR 2,750,000,000. Coupon: 3.875% p.a.
Annual interest: 2,750,000,000 x 3.875% = EUR 106,562,500.
The coupon is paid semi-annually (2 January and 2 July), so each payment is 106,562,500 / 2 = EUR 53,281,250.
""", "53281250 EUR")
answer("FC-009", ["invented_number"], "coupon of 4.0 % invented", """
Green bond nominal value: EUR 2.75 billion = EUR 2,750,000,000. Coupon: 4.0% p.a.
Annual interest: 2,750,000,000 x 4.0% = EUR 110,000,000.
The coupon is paid semi-annually (2 January and 2 July), so each payment is EUR 55,000,000.
""", f"{D(2750000000) * D('0.04') / 2:.0f} EUR")
answer("FC-009", ["missing_information"], "right result, payment frequency and annual amount missing", """
Each coupon payment on the green bond amounts to EUR 53,281,250.
""", "53281250 EUR")

# ---------------- FC-010 investment per customer (500.64 EUR) ----------------
answer("FC-010", [], "clean", """
Grid investment programme 2025 to 2029: EUR 6.25 billion = EUR 6,250,000,000.
Latest customer count (supply points at 30 September 2025): 12,483,906.
Per customer: 6,250,000,000 / 12,483,906 = 500.6445... = EUR 500.64.
""", "500.64 EUR")
answer("FC-010", ["wrong_source"], "customer count at 31 Dec 2024 instead of the latest", """
Grid investment programme 2025 to 2029: EUR 6.25 billion = EUR 6,250,000,000.
Customer count: 12,107,455.
Per customer: 6,250,000,000 / 12,107,455 = EUR 516.21.
""", f"{r2(D(6250000000) / D(12107455))} EUR")

# ---------------- FC-011 change in net financial debt (887,000,000 EUR) ----------------
answer("FC-011", [], "clean", """
Net financial debt at 31 December 2024: EUR 13,975 million.
Net financial debt at 30 September 2025: EUR 14.862 billion = EUR 14,862 million.
Change: 14,862 - 13,975 = +887 million, so net financial debt increased by EUR 887,000,000.
""", "887000000 EUR")
answer("FC-011", ["calculation_error"], "subtraction error (897 instead of 887)", """
Net financial debt at 31 December 2024: EUR 13,975 million.
Net financial debt at 30 September 2025: EUR 14.862 billion = EUR 14,862 million.
Change: 14,862 - 13,975 = +897 million, so net financial debt increased by EUR 897,000,000.
""", "897000000 EUR")
answer("FC-011", ["missing_information"], "right result, direction and both levels missing", """
The change in net financial debt between the end of 2024 and 30 September 2025 was EUR 887,000,000.
""", "887000000 EUR")

for i, a in enumerate(A, 1):
    a["cal_id"] = f"C-{i:03d}"
TARGET.write_text(json.dumps([{"cal_id": a.pop("cal_id"), **a} for a in A], indent=2, ensure_ascii=False) + "\n",
                  encoding="utf-8")
print(f"{len(A)} answers, {sum(1 for a in A if not a['expected'])} of them clean → {TARGET}")
