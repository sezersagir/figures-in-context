"""Shared steps for the command line and the web app: create, load and start runs, check test cases."""

import json
import re
from datetime import date

from . import answers, check, data, judges, routing

PROMPTS = ["model_under_test", "judge_numbers", "judge_calculation", "judge_plausibility"]
RUNS_DIR = data.BASE / "runs"


class RunError(Exception):
    pass


def new(name, test=False):
    name = re.sub(r"[^\w-]+", "-", name.strip()).strip("-")
    if not name:
        raise RunError("Please enter a name, e.g. pilot.")
    config = data.load_config()
    if test:
        config["models_under_test"] = [{"provider": "test", "model": "random"}, {"provider": "test", "model": "correct"}]
        config["judges"] = {j: {"provider": "test", "model": f"judge-{j}"} for j in config["judges"]}
        config["sample"]["minimum"] = 3
    run_dir = RUNS_DIR / f"{date.today().isoformat()}_{name}"
    if run_dir.exists():
        raise RunError(f"The run {run_dir.name} already exists. Runs are never overwritten, please pick another name.")
    cases = data.load_test_cases(config["test_cases"])
    run_dir.mkdir(parents=True)
    config["test"] = test
    config["record"] = {
        "prompt_hashes": {p: data.text_hash(data.load_prompt(p)) for p in PROMPTS},
        "test_cases": sorted(cases),
        "test_cases_hash": data.text_hash(json.dumps(cases, sort_keys=True, ensure_ascii=False)),
    }
    (run_dir / "run.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    return run_dir


def load_run(name, warn=True):
    run_dir = RUNS_DIR / name
    if "/" in name or "\\" in name or ".." in name or not (run_dir / "run.json").exists():
        raise RunError(f"Run {name} not found.")
    config = data.load_json(run_dir / "run.json")
    cases = data.load_test_cases(config["test_cases"])
    if warn:
        current = {p: data.text_hash(data.load_prompt(p)) for p in PROMPTS}
        if current != config["record"]["prompt_hashes"]:
            data.log(run_dir, "warning", "WARNING: The prompts have changed since this run was created. "
                                         "Create a new run for comparable results.")
        if sorted(cases) != config["record"]["test_cases"]:
            data.log(run_dir, "warning", "WARNING: The test cases have changed since this run was created.")
    return run_dir, config, cases


def all_runs():
    if not RUNS_DIR.exists():
        return []
    return sorted((p.name for p in RUNS_DIR.iterdir() if (p / "run.json").exists()), reverse=True)


def start(run_dir, config, cases):
    """Stages 1–4. Can be called any number of times; nothing already there is requested again."""
    data.log(run_dir, "info", "Run started: " + ", ".join(f"{t['provider']}:{t['model']}" for t in config["models_under_test"]))
    ok = answers.run(run_dir, config, cases)
    check.run(run_dir, cases)
    ok = judges.run(run_dir, config, cases) and ok
    if not ok:
        data.log(run_dir, "warning", "Not all requests succeeded. Just start again; "
                                     "nothing already there is requested twice.")
        return False
    if (run_dir / "review_results.csv").exists():
        data.log(run_dir, "info", "The review has already begun, so the review queue stays as it is.")
        return True
    return routing.run(run_dir, config, cases)


def check_cases():
    """Does every number in numbers_used really appear in the document? Is the page reference right?"""
    cases = data.load_test_cases(data.load_config()["test_cases"])
    problems = []
    for t in cases.values():
        try:
            data.document_excerpt(t)
        except (ValueError, FileNotFoundError) as e:
            problems.append(f"{t['id']}: {e}")
            continue
        text = data.full_document(t)
        for n in t["numbers_used"]:
            if n["value"] not in text:
                problems.append(f"{t['id']}: number {n['value']} ({n['meaning']}) is not in the document")
    return len(cases), problems


def progress(run_dir):
    """Counts how far a run has got. For the overview in the web app."""
    config = data.load_json(run_dir / "run.json")
    n_cases = len(config["record"]["test_cases"])
    answers_expected = n_cases * len(config["models_under_test"]) * config["repetitions"]
    checks = data.read_jsonl(run_dir / "checks.jsonl")
    valid = sum(1 for c in checks if c["format_ok"])
    p = {
        "test": config.get("test", False),
        "models": [f"{t['provider']}:{t['model']}" for t in config["models_under_test"]],
        "answers": len(data.read_jsonl(run_dir / "answers.jsonl")),
        "answers_expected": answers_expected,
        "correct": sum(1 for c in checks if c["result_correct"]),
        "wrong": sum(1 for c in checks if c["format_ok"] and not c["result_correct"]),
        "format_errors": len(checks) - valid,
        "verdicts": len(data.read_jsonl(run_dir / "verdicts.jsonl")),
        "verdicts_expected": valid * len(config["judges"]),
        "review_total": 0,
        "review_checked": 0,
        "report": (run_dir / "report.html").exists(),
    }
    if (run_dir / "review_queue.csv").exists():
        from .review import load_cases
        queue = load_cases(run_dir, {}, with_document=False)
        p["review_total"] = len(queue)
        p["review_checked"] = sum(1 for c in queue if c.get("checked"))
    return p
