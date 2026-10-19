# Test cases

- `batch-01.json`: first batch, 6 test cases (FC-001 to FC-006)
- `batch-02.json`: second batch, 5 test cases (FC-007 to FC-011), focus on very large numbers
- `documents/`: the documents the model receives (English, fictional companies)
- `_source/batch_NN.py`: generates batch-NN.json and computes the reference answers exactly (`python3 batch_01.py`), helpers in `_source/common.py`

| id | Category | Difficulty | Answer | Main trap |
|---|---|---|---|---|
| FC-001 | percentages | easy | 7.29 % | restated vs. original prior-year revenue |
| FC-002 | mixed units | medium | 130,522.25 GBP | £ million → GBP |
| FC-003 | mixed units | medium | 34.17 % | £ thousand vs. £ million |
| FC-004 | very large numbers | medium | 32,334,339.375 GBP | pence → GBP, the 11.25p total appears nowhere |
| FC-005 | percentages | easy | 5.57 % | provisional price 5.25 |
| FC-006 | multi-step calculation | hard | 1,345,925.40 EUR | rebate only above the threshold, packs of 1,000 |
| FC-007 | very large numbers | hard | 3,616,565,400 EUR | TWh → MWh, total revenue as a distraction |
| FC-008 | very large numbers | medium | 26,961,464,480.20 EUR | price from the wrong date |
| FC-009 | very large numbers | hard | 53,281,250 EUR | semi-annual coupon, a second bond |
| FC-010 | very large numbers | hard | 500.64 EUR | rounded customer count from the CEO quote |
| FC-011 | mixed units | medium | 887,000,000 EUR | bn vs. million in one table |
