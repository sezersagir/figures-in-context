# Figures in Context: Specification

As of: 2026-10-18 (format added after the review of batch 01). Designed by hero in the thread "Multi-judge eval for numbers". The decisions are his; this document only summarizes them.

## Goal

Measure how often an AI makes mistakes when it reports calculations from business documents with large, confusing numbers. The result is an error rate per model and per error type.

## Process

1. **Test cases:** self-built documents in the style of real annual reports and business letters, in English. The reference answer is fixed in advance.
2. **The AI answers** freely and adds a fixed line at the end: `RESULT: <value> <unit>`
3. **Python check:** reads only the RESULT line and compares it with the reference answer. No AI model is involved in this step.
4. **Judges** (different models, run on every answer):
   - Numbers judge: does every number come from the document, or is it invented or quoted wrongly?
   - Calculation judge: if the result is wrong, where did it go wrong?
   - Plausibility judge: does the answer fit the question, is required information missing?
5. **Routing:** result correct and no judge flags → done. Everything else → human reviewer.
6. **Human** confirms or corrects the cause of the error (fixed list below).
7. **Sample:** some of the "done" cases still go to the human, to measure what the judges miss.
8. **Result:** error rate overall, per error type, per category, per model, plus a separate format error rate.

## Error types (fixed list)

- wrong result
- wrong source
- invented number
- calculation error
- missing information
- format not followed (reported and marked, but does not count toward the error rate)

## Rules

- **Precision:** exact. Exception: recurring decimals; the number of decimal places is given in the test case.
- **Language:** English.

## Test case format

| Field | Content | Used for |
|---|---|---|
| id | unique identifier | |
| category | e.g. percentages, mixed units, very large numbers | error rate per category |
| difficulty | e.g. easy / medium / hard | error rate per difficulty |
| document | file and page the AI receives | input |
| question | what the AI should calculate | input |
| reference_answer | value, unit, decimal places | Python check |
| numbers_used | every number needed, with its location in the document | Numbers judge |
| working | the steps to the solution | Calculation judge |
| required_info | what the answer must contain (content the reader needs, not a description of the working) | Plausibility judge |
| traps | optional: typical wrong results and where they come from | Calculation judge, human |

**Format details** (taken from the test case thread, 2026-10-18):
- JSON, one file per batch, a list of test cases.
- `document`: `{"file": "...", "page": 1}` or `"page": "1-2"`.
- `reference_answer`: `{"value": "7.29", "unit": "%", "decimals": 2, "exact": false}`. Value as a string. `exact: true` + `decimals: null` means: finite result, must match exactly. Rounding is half up, and only for recurring results.
- Reference answers are computed by a script with exact fraction arithmetic, never entered by hand.
- Questions contain no hints about the trap (e.g. not "use the restated figure"), otherwise the eval measures the question instead of the model.

## Responsibilities and counting rules (taken from the architecture thread, 2026-10-18)

- **Counting unit:** per answer. An answer is wrong if it has at least one error type; it can have several.
- **Who reports which error:** wrong result and format errors → Python; wrong source and invented number → Numbers judge; calculation error → Calculation judge; missing information → Plausibility judge; the human always makes the final decision.
- **Format errors:** no RESULT line, more than one, number not readable, number words like "million" in the line, unit missing. A wrong unit is not a format error but a wrong result.
- **A broken judge verdict** (no valid verdict delivered) counts as a flag → human.
- **Every question states the required precision** ("without rounding" or "rounded to 2 decimal places"), otherwise the test measures rounding habits.
- **Results with uncertainty:** every rate with a 95% confidence interval, plus an error rate corrected for the judges' miss rate.
- **Models tested:** one current top model each from Anthropic, OpenAI and Google (hero, 2026-10-18).
- **Technology:** see docs/ARCHITECTURE.md (Python, JSON/JSONL, review as CSV).

## Decisions of 2026-10-18 (hero: "everything as recommended")

- **Sample:** 20% of the "done" cases, at least 30, stratified by model × category.
- **No RAG per judge:** every judge gets the whole document. RAG only for very long documents.
- **Format errors:** are only counted and reported, not checked by judges or the human.
- **Review:** CSV in Excel/Sheets. A dedicated web interface is possible later.
- **API keys** come from a .env file.
