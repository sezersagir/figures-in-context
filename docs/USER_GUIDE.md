# Figures in Context: user guide

How to start a run. Concept: [SPEC.md](SPEC.md), technical design: [ARCHITECTURE.md](ARCHITECTURE.md).

## Starting

Python 3.9 or newer is all you need. No extra packages, so no `pip install` and no virtual environment.

- **Windows:** double-click `start.bat`.
- **Mac/Linux:** double-click `start.command` (or run `python3 -m figures_in_context app`).
- **By hand:** run `python -m figures_in_context app` in the `figures-in-context` folder.

The web app opens in your browser at http://127.0.0.1:8765/. Keep the console window open while you work; closing it stops the app. The app can only be reached from your own computer.

## In the web app

1. **Settings:** enter the three API keys (they are stored only locally in the `.env` file) and check the model names. OpenAI and Google are set to `gpt-5` and `gemini-2.5-pro`; enter the current top models if newer ones exist.
2. **New run:** enter a name at the bottom of the sidebar. Tick "Test run with test models" to try things out; it costs nothing.
3. **Start run:** answers, Python check, judges and routing run one after another, with a progress display. If something stops (network, rate limit), just press "Resume". Anything already there is not requested or paid for twice.
4. **Open review** and check the cases (see below).
5. **Create report** and **View report**.

Next to every run is the **log**: every request as soon as it comes back, with test case, model or judge, result or verdict, and duration. Click a line for details (tokens, the judge's finding, retries). The totals sit at the top: requests, errors, tokens and time per request. The buttons filter by answers, judges or errors. Failed requests appear in red, with the reason. The log is saved per run in `runs/<run>/log.jsonl`, so it is still there after you close the app. The calibration has its own.

The bottom left shows how many test cases are loaded. If a number or page reference in a test case doesn't match its document, the app shows that as a red message.

## Command line (works without the app too)

```
python -m figures_in_context check-cases          # checks the test cases against the documents
python -m figures_in_context new pilot [--test]   # creates runs/<date>_pilot (--test: test models)
python -m figures_in_context start <date>_pilot   # answers → Python check → judges → routing
python -m figures_in_context review <date>_pilot  # just the review interface
python -m figures_in_context report <date>_pilot
```

The API keys then go in the `.env` file (template: `.env.example`). Never share or upload the `.env`.

## Review

In the app via "Open review". The interface shows one case at a time: the question, the reference answer and the AI result digit by digit side by side (differing digits in red), the AI's answer, the three judges' findings, the known traps and, on request, the document.

- Toggle error types by clicking or with the keys **1–5**. Nothing chosen means clean.
- **Enter** = checked, on to the next open case. **← →** to browse, **D** shows the document.
- Every change is saved straight away to `runs/<run>/review_results.csv`. You can stop at any time and carry on later.

If you prefer Excel: open `review_queue.csv`, fill in `final_error_types` (several separated by commas), put an `x` in `checked` and save it as `review_results.csv`.

On purpose, you don't see whether a case reached you because of a judge flag or as part of the sample.

Allowed error types:

| Entry | Meaning |
|---|---|
| `wrong_result` | the final result is wrong |
| `wrong_source` | a number from the document, but the wrong one (wrong year, wrong row, original instead of restated …) |
| `invented_number` | the number appears nowhere in the document |
| `calculation_error` | an arithmetic or method error in the working |
| `missing_information` | required information is missing, or the question isn't answered |

## Report

In the app via "Create report". Result: `runs/<run>/report.md` and `report.html`. Error rates overall and per model, category, difficulty and error type, each with a 95 % confidence interval, plus the format error rate, the judge miss rate and the judge hit rate. You can also create the report before the review is done; the open cases are then marked as provisional.

## What is where

| Folder/file | Contents |
|---|---|
| `config/run.json` | models, repetitions, sample (20 %, at least 30) |
| `config/units.json` | allowed spellings of units (`€` = `EUR`) |
| `prompts/` | system prompts for the model under test and the three judges |
| `start.bat`, `start.command` | start by double-click |
| `figures_in_context/` | the code, one file per stage; `app.py` + `app.html` is the web app, `review.html` the review interface |
| `calibration/`, `calibration_runs/` | answers for the judge calibration and its results |
| `runs/` | one folder per run, never overwritten. The `run.json` inside records models, prompt versions and test cases |
| `tests/` | tests: `python -m unittest discover tests` |

## Judge calibration (before the first run that counts)

In the app under **Calibration** (or `python -m figures_in_context calibration`). The judges get 30 prepared answers to the test cases: 19 with a deliberately planted error (5× wrong source, 4× invented number, 5× calculation error, 5× missing information) and 11 clean ones. Each judge is measured only for its own area:

- **Errors found:** planted error, the judge flags and names the right type.
- **False alarms:** clean answer, the judge flags anyway.

Passed means: everything found, no false alarm, no broken verdict. Otherwise "Details" shows which cases were missed and what the judge wrote about them. Then adjust the prompt or the judge model and calibrate again. Repeat after every change to judge prompts or judge models.

The answers are in `calibration/answers.json` and are generated by `calibration/_source/generate.py` (all numbers computed exactly). Results go to `calibration_runs/<date_time>/`.

## Still open

- **Pilot** (ARCHITECTURE.md, section 5): once the calibration passes, a small run with one model, review everything by hand, then sharpen the prompts and test cases.
