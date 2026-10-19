"""Stage 1: The model under test answers every question. → answers.jsonl"""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import check, data, models


def user_text(case):
    return f"<document>\n{data.document_excerpt(case)}\n</document>\n\nQuestion: {case['question']}"


def run(run_dir, config, cases):
    target_file = run_dir / "answers.jsonl"
    existing = {data.answer_key(d) for d in data.read_jsonl(target_file)}
    system = data.load_prompt("model_under_test")

    jobs = []
    for target in config["models_under_test"]:
        for case in cases.values():
            for rep in range(1, config["repetitions"] + 1):
                d = {"case_id": case["id"], "model": models.model_name(target), "repetition": rep}
                if data.answer_key(d) not in existing:
                    jobs.append((target, case, d))

    data.log(run_dir, "info", f"Answers: {len(existing)} already there, {len(jobs)} to request.")
    errors = 0
    done = 0

    def one(job):
        nonlocal done
        try:
            _one(job)
        finally:
            done += 1
            data.report_progress(f"Answers: {done}/{len(jobs)}")

    def _one(job):
        nonlocal errors
        target, case, d = job
        start = time.monotonic()
        try:
            result = models.ask(target, system, user_text(case), context=case)
        except Exception as e:  # don't store failures, so the next start tries again
            errors += 1
            data.log(run_dir, "error", f"  ERROR {data.answer_key(d)}: {type(e).__name__}: {e}",
                     step="answer", **d, duration_s=round(time.monotonic() - start, 1))
            return
        data.append(target_file, {
            **d,
            "answer_text": result["text"],
            "tokens_in": result["tokens_in"],
            "tokens_out": result["tokens_out"],
            "stop_reason": result["stop_reason"],
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        value, unit, format_error = check.read_result(result["text"])
        data.log(run_dir, "answer", step="answer", **d,
                 duration_s=round(time.monotonic() - start, 1), attempts=result.get("attempts", 1),
                 tokens_in=result["tokens_in"], tokens_out=result["tokens_out"],
                 stop_reason=result["stop_reason"],
                 result=format_error and f"Format error: {format_error}" or f"{value} {unit}")

    with ThreadPoolExecutor(max_workers=config.get("parallel", 4)) as pool:
        list(pool.map(one, jobs))

    if errors:
        data.log(run_dir, "warning", f"{errors} requests failed. Just start again.")
    return errors == 0
