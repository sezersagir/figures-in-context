# Figures in Context: Architecture

As of: 2026-10-18. Basis: [SPEC.md](SPEC.md) (concept by hero). This document defines *how* the concept is implemented technically. It changes nothing about the concept. Where a technical choice would touch the concept, it is listed under "Decisions for hero" at the end.

Test case data format: the format the test case thread defined in [test_cases/batch-01.json](../test_cases/batch-01.json). The architecture reads it unchanged.

---

## 1. Overview

The pipeline has six stages. Each stage reads files and writes files. This way every stage can be restarted on its own, and nothing has to be paid for twice.

```
 test_cases/batch-*.json ───┐
 test_cases/documents/*.md ─┤
                    ▼
 [1] ANSWERS        model under test answers the question  → answers.jsonl
                    ▼
 [2] PYTHON CHECK   read RESULT line, compare exactly       → checks.jsonl
                    ▼
 [3] JUDGES         3 judges, 3 model families, all cases   → verdicts.jsonl
                    ▼
 [4] ROUTING        correct + no flag → done; else human
                    + sample from "done"                    → review_queue.csv
                    ▼
 [5] HUMAN          confirms / corrects error types         → review_results.csv
                    ▼
 [6] REPORT         error rates + judge miss rate           → report.md / report.html
```

Core principle (from the concept): **Only Python decides right or wrong. The judges only diagnose. The human has the last word.**

---

## 2. Folder structure

```
figures-in-context/
├── docs/
│   ├── SPEC.md                 (belongs to the concept thread)
│   └── ARCHITECTURE.md         (this document)
├── test_cases/                 (belongs to the test case thread)
│   ├── batch-01.json           list of test cases, one file per batch
│   └── documents/*.md          business documents, Markdown with "### Page N"
├── config/
│   ├── run.json                which models, how many repetitions, sample
│   └── units.json              allowed spellings of units (EUR = €, …)
├── prompts/
│   ├── model_under_test.md     system prompt for the model under test
│   ├── judge_numbers.md
│   ├── judge_calculation.md
│   └── judge_plausibility.md
├── figures_in_context/         Python code (one file per stage)
│   ├── answers.py
│   ├── check.py
│   ├── judges.py
│   ├── routing.py
│   ├── report.py
│   └── models.py               one thin layer per provider
└── runs/
    └── 2026-10-20_pilot/       one folder per run, never overwritten
        ├── run.json            copy of the config + model IDs + prompt hashes
        ├── answers.jsonl
        ├── checks.jsonl
        ├── verdicts.jsonl
        ├── review_queue.csv
        ├── review_results.csv
        └── report.md
```

Why one folder per run: results are only comparable if you know which prompt, which model and which test cases produced them. The run folder is the log.

---

## 3. The stages in detail

### [1] Answers (model under test)

- **Input:** the pages of the document named in the test case (cut from the "### Page N" sections, ranges like `"1-2"` too, the company header always included) + the question from the test case + a fixed system prompt.
- **System prompt** (core):
  > Answer the question using only the attached document. Show your working. End your answer with exactly one final line in this format: `RESULT: <number> <unit>`. Write the number in full digits, without thousands separators and without words like "million" (e.g. `RESULT: 5614779.00 EUR`).
- The answer before that line is free. This tests realistic behavior, and the judges have a working to check.
- **Per test case × model × repetition** one record in `answers.jsonl`: `case_id`, `model`, `repetition`, `answer_text`, `timestamp`, token usage, stop reason.
- **Repetitions:** configurable (`repetitions` in `run.json`). AI answers vary; with 3 repetitions you can see whether an error is chance or a pattern. Pilot: 1.
- **Cache:** if an answer already exists for (test case, model, repetition, prompt hash), it is not requested again.

### [2] Python check (no AI model)

Reads **only the last RESULT line**.

1. **Check the format.** Format error if: no RESULT line, more than one, number not readable, words like "million" in the line, unit missing. → `format_ok = false`, the reason is stored.
2. **Read the number.** As `Decimal`, never as `float` (otherwise 0.1 + 0.2 does not become 0.3). Commas as thousands separators are tolerated and removed.
3. **Compare the unit** via `config/units.json` (e.g. `EUR`, `€`, `euro` → `EUR`). Wrong unit = wrong result.
4. **Compare the value** using hero's rule (fields `exact` and `decimals` of the reference answer):
   - Normal case: **exactly equal** (`5614779` = `5614779.00`, but ≠ `5614779.01`).
   - `exact: false` with `decimals: n` (recurring decimals): the AI value is rounded half up (`ROUND_HALF_UP`) to n places and must then match the reference answer exactly.
5. **Output** in `checks.jsonl`: `format_ok`, `format_reason`, `ai_value`, `ai_unit`, `result_correct` (true/false/null for a format error).

### [3] Judges (diagnosis, run on every answer)

Three judges, **each on a different model family** (e.g. Anthropic, OpenAI, Google), so they don't share the same blind spots.

Hero's idea of "a separate knowledge package/JSON per judge" is implemented like this: each judge gets only the test case fields it needs. A separate RAG system is not needed, because the documents are small enough to pass in full (see decision C).

| Judge | gets | checks | may report |
|---|---|---|---|
| **Numbers judge** | document, `numbers_used`, answer | Does every number in the answer come from the document? Quoted correctly? Right location? | wrong source, invented number |
| **Calculation judge** | question, `working`, `traps`, `reference_answer`, answer, Python result | If the result is wrong: at which step did it go wrong? If it is right: are there errors in intermediate steps? | calculation error |
| **Plausibility judge** | question, `required_info`, answer | Does the answer answer the question? Is required information missing? Gross outliers (no number, absurd order of magnitude)? | missing information |

No judge reports "wrong result"; Python sets that. The same goes for "format not followed".

**Output of every judge: fixed JSON** (enforced through the provider's structured output):

```json
{
  "flag": true,
  "error_types": ["invented_number"],
  "finding": "The answer uses 1,240,000 units for Q3; the document states 1,204,000 (p. 2, table 1).",
  "evidence": [
    {"answer_quote": "1,240,000 units", "document_location": "p. 2, table 1: 1,204,000"}
  ],
  "confidence": "high"
}
```

- `error_types` only from the fixed list, and only the types this judge may report.
- **Fail-safe:** if a judge returns broken JSON, nothing at all, or a type it may not report, that counts as a flag with the reason "judge error". A case is never silently waved through as "done".
- Judges run with the most deterministic settings the provider allows.
- Judges do **not** run on format errors (see decision D).

### [4] Routing

```
format_ok == false                          → format error statistics (no review)
result_correct and no judge flags           → DONE
otherwise                                   → HUMAN
from DONE: draw sample                      → HUMAN (reason "sample")
```

- The sample is drawn **stratified** (per model × category), so every model and every category is represented, and with a fixed random seed, so it is reproducible.
- To the reviewer, flagged cases and sample cases look the same. They don't know why a case landed with them. This way they don't look less carefully at sample cases.

### [5] Human (review)

First version: **a CSV file** that is opened in Excel or Google Sheets. No dedicated tool needed.

Columns in `review_queue.csv`:
`case_no`, `case_id`, `question`, `reference_answer`, `answer_text`, `python_result`, `traps` (known sources of error), `judge_findings` (all three combined), → to fill in: `final_error_types` (list, empty = no errors), `comment`, `reviewer`.

Not in the file: the model name (the reviewer should not know which model they are rating) and whether the case is a sample case. Both stay linked internally via `case_no`.

Can later be extended to a small web interface with the same fields (see decision E).

### [6] Report

**The counting unit is the answer.** An answer is wrong if it has at least one error type. An answer can have several error types.

| Metric | Formula |
|---|---|
| **Error rate** | wrong answers ÷ answers with a valid format |
| Error rate per type | answers with type X ÷ answers with a valid format |
| per model / category / difficulty | the same formulas, filtered |
| **Format error rate** (separate) | answers with a format error ÷ all answers |
| **Judge miss rate** | sample cases with an error according to the human ÷ sample cases |
| Judge hit rate per judge | flags confirmed by the human ÷ all flags of this judge |

Where do an answer's error types come from?
- Answers reviewed by the human: `final_error_types`.
- "Done" answers without review: no errors. Because the judges can miss something, the report shows **two numbers**: the measured error rate and an error rate **corrected** for the judge miss rate. Showing both is the honest approach.
- Every rate gets a **95% confidence interval** (Wilson). With 30 answers per model, "10%" really lies somewhere between 3% and 26%. Without the interval it looks more precise than it is.

Report as Markdown and HTML. Also suitable directly as a work sample for clients and AI labs.

---

## 4. Technology

| Topic | Choice | Why |
|---|---|---|
| Language | **Python 3.11+** | the Python check is Python anyway; `decimal` is built in |
| Dependencies | the official SDKs of the three providers, otherwise the standard library | little that can break |
| Model access | one file `models.py` with a function `ask(model, system, document, text, schema=None)` per provider | swapping models = one line in `run.json` |
| Test cases | **JSON, one file per batch** (as set up by the test case thread) | readable without an extra library; reference answers as text, so Python reads them exactly as `Decimal` |
| Documents | **Markdown** with page headings; later optionally rendered as PDF | text is simpler to start with; PDF would be more realistic (table layout, headers) and can be added as a second variant of the same test case |
| Run data | JSONL (one line per answer/judge verdict) | appendable, robust if interrupted |
| Review | CSV | Excel/Sheets is enough to start |
| Saving costs | the providers' batch APIs (usually ~50% cheaper) for large runs | answers don't need to arrive immediately |

**Rough costs** (estimated, not measured): 100 test cases × 3 models under test × 1 repetition = 300 answers + 900 judge verdicts ≈ 1,200 requests at ~5,000 tokens in / ~1,500 out. With current top models roughly $50 to $100 per run, about half that with batch. The pilot with 20 test cases costs a fifth of that.

**Avoiding self-assessment:** if, for example, a Claude model is tested, there is still a Claude model on the judge team. With three judges from three families this can't be fully avoided. Mitigation: the report shows the judge hit rate split into "judge and model under test from the same family" and "different". If that stands out, the judge from the same family can be swapped per model under test.

---

## 5. Quality assurance of the eval itself

Before real runs count:

1. **Test case check:** the test case thread already recomputes the reference answers exactly by script (`test_cases/_source/`). In addition, a check before every run verifies that every number in `numbers_used` really appears in the document. Errors in reference answers are the most common reason for wrong eval results.
2. **Judge calibration:** 10 to 20 answers with deliberately planted errors (an invented number, a calculation error, a missing piece of required information) and 10 error-free ones. Every judge must find the planted errors and must not flag the error-free ones. Only then is it used for real runs.
3. **Pilot:** 20 test cases, 1 model, review everything by hand. Then sharpen the prompts and test cases, then the full run.

---

## 6. Decisions for hero

All five points are decided; also recorded in docs/SPEC.md, "Decisions of 2026-10-18". The code is built in the thread "Figures in Context concept".

**A. Which models are tested?** ✓ Decided (hero, 2026-10-18): one current top model each from Anthropic, OpenAI and Google. Cheaper models can be added later as a separate run.

**B. Sample size (step 7, open according to the specification).** Default: ✓ Decided as recommended (hero, 2026-10-18). **20% of the "done" cases, at least 30**, stratified by model × category. With 30 sample cases and no findings you can say "the judges probably miss less than 10%". A smaller sample = less work, but the corrected error rate becomes blurry.

**C. RAG per judge.** ✓ Decided as recommended (hero, 2026-10-18). In your first draft every judge had its own RAG system. Default here: no RAG; instead every judge gets its own package of test case fields and the complete document. Reason: the documents are short enough, and RAG would add a new source of error (the judge doesn't find the right passage). RAG only pays off for very long documents (e.g. 200-page annual reports).

**D. Answers with format errors.** Default: ✓ Decided as recommended (hero, 2026-10-18). They are counted and reported, but not checked by judges or the human (according to the specification they don't count toward the error rate anyway). Alternative: check them anyway, to see whether there are calculation errors behind them too.

**E. Review interface.** Default: ✓ Decided as recommended (hero, 2026-10-18). CSV in Excel/Sheets. Alternative: a small web interface. That would be a good project to build yourself if you want something to show.
