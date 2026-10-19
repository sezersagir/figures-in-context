"""Stage 4: Which answers go to a human? → review_queue.csv (for the reviewer) + review_internal.csv

correct and no judge flags     → done
otherwise                      → human
a sample of the "done" answers → human (looks exactly the same to the reviewer)
"""

import csv
import math
import random
from collections import defaultdict

from . import data

DELIMITER = ";"  # Excel in many European locales opens semicolon CSV correctly

REVIEW_COLUMNS = [
    "case_no", "case_id", "question", "reference_answer", "python_result", "answer_text",
    "traps", "judge_findings", "final_error_types", "comment", "reviewer", "checked",
]


def draw_sample(done, share, minimum, seed, cases):
    """Stratified by model × category: draw from each stratum in turn until the count is reached."""
    count = min(len(done), max(math.ceil(share * len(done)), minimum))
    rnd = random.Random(seed)
    strata = defaultdict(list)
    for c in sorted(done, key=data.answer_key):
        strata[(c["model"], cases[c["case_id"]]["category"])].append(c)
    for items in strata.values():
        rnd.shuffle(items)
    order = sorted(strata)
    drawn = []
    while len(drawn) < count:
        for s in order:
            if strata[s] and len(drawn) < count:
                drawn.append(strata[s].pop())
    return drawn


def run(run_dir, config, cases):
    checks = data.read_jsonl(run_dir / "checks.jsonl")
    answers = {data.answer_key(a): a for a in data.read_jsonl(run_dir / "answers.jsonl")}
    verdicts = defaultdict(list)
    for v in data.read_jsonl(run_dir / "verdicts.jsonl"):
        verdicts[data.answer_key(v)].append(v)

    valid = [c for c in checks if c["format_ok"]]
    missing = [data.answer_key(c) for c in valid
               if len(verdicts[data.answer_key(c)]) < len(config["judges"])]
    if missing:
        data.log(run_dir, "error", f"Stopped: {len(missing)} answers are missing judge verdicts. Run `judges` again first.")
        return False

    to_human, done = [], []
    for c in valid:
        flagged = any(v["flag"] for v in verdicts[data.answer_key(c)])
        (done if c["result_correct"] and not flagged else to_human).append(c)

    s = config["sample"]
    sample = draw_sample(done, s["share"], s["minimum"], s["seed"], cases)
    queue = [(c, "flagged") for c in to_human] + [(c, "sample") for c in sample]
    random.Random(s["seed"]).shuffle(queue)  # spread the sample out so nobody can spot it

    with open(run_dir / "review_queue.csv", "w", newline="", encoding="utf-8-sig") as f_review, \
         open(run_dir / "review_internal.csv", "w", newline="", encoding="utf-8-sig") as f_internal:
        review = csv.DictWriter(f_review, REVIEW_COLUMNS, delimiter=DELIMITER)
        internal = csv.DictWriter(f_internal, ["case_no", "case_id", "model", "repetition", "reason"],
                                  delimiter=DELIMITER)
        review.writeheader()
        internal.writeheader()
        for no, (c, reason) in enumerate(queue, 1):
            t = cases[c["case_id"]]
            key = data.answer_key(c)
            findings = [f"[{v['judge']}] {'FLAG' if v['flag'] else 'ok'} {','.join(v['error_types'])}: {v['finding']}"
                        for v in sorted(verdicts[key], key=lambda v: v["judge"])]
            review.writerow({
                "case_no": no,
                "case_id": t["id"],
                "question": t["question"],
                "reference_answer": f"{t['reference_answer']['value']} {t['reference_answer']['unit']}",
                "python_result": ("correct" if c["result_correct"] else "WRONG")
                                 + f" (AI: {c['ai_value']} {c['ai_unit']})",
                "answer_text": answers[key]["answer_text"],
                "traps": " | ".join(t.get("traps", [])),
                "judge_findings": "\n".join(findings),
                "final_error_types": "wrong_result" if not c["result_correct"] else "",
                "comment": "", "reviewer": "", "checked": "",
            })
            internal.writerow({"case_no": no, "case_id": c["case_id"], "model": c["model"],
                               "repetition": c["repetition"], "reason": reason})

    data.log(run_dir, "info", f"Routing: {len(done)} done, {len(to_human)} to a human, "
                              f"{len(sample)} sample, {len(checks) - len(valid)} format errors.")
    data.log(run_dir, "info", f"Review queue created: {len(to_human) + len(sample)} cases. Next: the review.")
    return True
