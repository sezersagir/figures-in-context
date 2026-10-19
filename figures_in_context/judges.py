"""Stage 3: Three judges diagnose every answer with a valid format. → verdicts.jsonl

Judges do not decide right or wrong; Python has already done that.
A broken or disallowed verdict counts as a flag, so no case slips through silently.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor

from . import data, models

ALLOWED = {
    "numbers": ["wrong_source", "invented_number"],
    "calculation": ["calculation_error"],
    "plausibility": ["missing_information"],
}


def schema(judge):
    return {
        "type": "object",
        "properties": {
            "flag": {"type": "boolean"},
            "error_types": {"type": "array", "items": {"type": "string", "enum": ALLOWED[judge]}},
            "finding": {"type": "string"},
            "evidence": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "answer_quote": {"type": "string"},
                        "document_location": {"type": "string"},
                    },
                    "required": ["answer_quote", "document_location"],
                    "additionalProperties": False,
                },
            },
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        "required": ["flag", "error_types", "finding", "evidence", "confidence"],
        "additionalProperties": False,
    }


def _bullets(items):
    return "\n".join(f"- {i}" for i in items) or "- (none)"


def judge_text(judge, case, answer, check):
    t = case
    solution = f"{t['reference_answer']['value']} {t['reference_answer']['unit']}"
    if judge == "numbers":
        numbers = "\n".join(
            f"- {n['value']} {n['unit']} ({n['meaning']}), found at: {n['location']}"
            for n in t["numbers_used"]
        )
        parts = [
            f"<document>\n{data.full_document(t)}\n</document>",
            f"<numbers_needed_for_the_correct_solution>\n{numbers}\n</numbers_needed_for_the_correct_solution>",
        ]
    elif judge == "calculation":
        outcome = "correct" if check["result_correct"] else f"WRONG (answer gave {check['ai_value']} {check['ai_unit']})"
        parts = [
            f"<question>\n{t['question']}\n</question>",
            f"<reference_solution>{solution}</reference_solution>",
            f"<reference_working>\n{_bullets(t['working'])}\n</reference_working>",
            f"<known_traps>\n{_bullets(t.get('traps', []))}\n</known_traps>",
            f"<exact_comparison_result>{outcome}</exact_comparison_result>",
        ]
    else:
        parts = [
            f"<question>\n{t['question']}\n</question>",
            f"<required_information>\n{_bullets(t['required_info'])}\n</required_information>",
        ]
    parts.append(f"<ai_answer>\n{answer['answer_text']}\n</ai_answer>")
    return "\n\n".join(parts)


def parse_verdict(judge, raw_text):
    """Validates the judge's JSON. Anything invalid becomes a flag marked as a judge error."""
    try:
        v = json.loads(raw_text)
        assert isinstance(v, dict) and isinstance(v.get("flag"), bool)
        types = v.get("error_types") or []
        assert isinstance(types, list)
    except (ValueError, AssertionError):
        return {"flag": True, "error_types": [], "finding": "Judge error: no valid JSON.",
                "evidence": [], "confidence": None, "judge_error": True}
    disallowed = [x for x in types if x not in ALLOWED[judge]]
    if disallowed:
        return {**v, "flag": True, "error_types": [x for x in types if x in ALLOWED[judge]],
                "finding": f"Judge error: disallowed error type {disallowed}. " + str(v.get("finding", "")),
                "judge_error": True}
    # Naming an error type means flagging.
    return {**v, "flag": v["flag"] or bool(types), "judge_error": False}


def run(run_dir, config, cases):
    answers = {data.answer_key(a): a for a in data.read_jsonl(run_dir / "answers.jsonl")}
    checks = data.read_jsonl(run_dir / "checks.jsonl")
    target_file = run_dir / "verdicts.jsonl"
    existing = {(data.answer_key(v), v["judge"]) for v in data.read_jsonl(target_file)}

    jobs = []
    for c in checks:
        if not c["format_ok"]:
            continue  # decision D: format errors are only counted
        for judge, target in config["judges"].items():
            if (data.answer_key(c), judge) not in existing:
                jobs.append((judge, target, c))

    data.log(run_dir, "info", f"Judges: {len(existing)} verdicts already there, {len(jobs)} to request.")
    errors = 0
    done = 0

    def one(job):
        nonlocal done
        try:
            _one(job)
        finally:
            done += 1
            data.report_progress(f"Judges: {done}/{len(jobs)}")

    def _one(job):
        nonlocal errors
        judge, target, c = job
        case = cases[c["case_id"]]
        answer = answers[data.answer_key(c)]
        start = time.monotonic()
        head = {"case_id": c["case_id"], "model": c["model"], "repetition": c["repetition"],
                "judge": judge, "judge_model": models.model_name(target)}
        try:
            result = models.ask(
                target, data.load_prompt(f"judge_{judge}"), judge_text(judge, case, answer, c),
                schema=schema(judge), context={"judge": judge, **c},
            )
        except Exception as e:
            errors += 1
            data.log(run_dir, "error", f"  ERROR {judge} {data.answer_key(c)}: {type(e).__name__}: {e}",
                     step="verdict", **head, duration_s=round(time.monotonic() - start, 1))
            return
        verdict = parse_verdict(judge, result["text"])
        data.append(target_file, {**head, **verdict})
        data.log(run_dir, "verdict", step="verdict", **head,
                 duration_s=round(time.monotonic() - start, 1), attempts=result.get("attempts", 1),
                 tokens_in=result["tokens_in"], tokens_out=result["tokens_out"],
                 flag=verdict["flag"], error_types=verdict.get("error_types", []),
                 judge_error=verdict.get("judge_error", False), finding=str(verdict.get("finding", ""))[:400])

    with ThreadPoolExecutor(max_workers=config.get("parallel", 4)) as pool:
        list(pool.map(one, jobs))

    if errors:
        data.log(run_dir, "warning", f"{errors} judge requests failed. Just start again.")
    return errors == 0
