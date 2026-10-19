"""Stage 6: Error rates, judge miss rate, judge hit rate. → report.md + report.html

The unit of counting is the answer. Every rate gets a 95 % confidence interval (Wilson).
"""

import csv
import html
import math
import re
from collections import defaultdict
from datetime import date

from . import data
from .judges import ALLOWED


def wilson(hits, n, z=1.96):
    if n == 0:
        return None, None
    p = hits / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    width = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, centre - width), min(1.0, centre + width)


def rate(hits, n):
    if n == 0:
        return "–"
    low, high = wilson(hits, n)
    return f"{hits / n:.1%} ({low:.1%}–{high:.1%}), {hits}/{n}"


def read_review(run_dir, notes):
    path = run_dir / "review_results.csv"
    if not path.exists():
        notes.append("review_results.csv is missing: all cases sent to a human are scored provisionally "
                     "(Python + judges), and the miss rate is unknown.")
        return {}
    text = path.read_text(encoding="utf-8-sig")
    first = text.split("\n", 1)[0]
    delimiter = ";" if first.count(";") >= first.count(",") else ","
    result = {}
    for row in csv.DictReader(text.splitlines(keepends=True), delimiter=delimiter):
        if not (row.get("checked") or "").strip():
            continue
        types = [t for t in re.split(r"[,;\s]+", row.get("final_error_types") or "") if t]
        unknown = [t for t in types if t not in data.ERROR_TYPES]
        if unknown:
            notes.append(f"Case {row['case_no']}: unknown error types {unknown} ignored.")
        result[row["case_no"]] = [t for t in types if t in data.ERROR_TYPES]
    return result


def run(run_dir, config, cases):
    notes = []
    checks = data.read_jsonl(run_dir / "checks.jsonl")
    verdicts = defaultdict(list)
    for v in data.read_jsonl(run_dir / "verdicts.jsonl"):
        verdicts[data.answer_key(v)].append(v)
    internal = {}
    if (run_dir / "review_internal.csv").exists():
        with open(run_dir / "review_internal.csv", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f, delimiter=";"):
                internal[f"{row['case_id']}|{row['model']}|{row['repetition']}"] = row
    review = read_review(run_dir, notes)

    # Settle the error types of every answer
    scored = []  # (check, error_types, status)
    for c in checks:
        k = data.answer_key(c)
        if not c["format_ok"]:
            scored.append((c, None, "format"))
            continue
        entry = internal.get(k)
        if entry and entry["case_no"] in review:
            scored.append((c, review[entry["case_no"]], "human_" + entry["reason"]))
        elif entry and entry["reason"] == "sample":
            scored.append((c, [], "done"))  # a sample case not yet reviewed counts as "done"
        elif entry:
            provisional = ([] if c["result_correct"] else ["wrong_result"]) + \
                          [t for v in verdicts[k] for t in v["error_types"]]
            scored.append((c, sorted(set(provisional)), "provisional"))
        else:
            scored.append((c, [], "done"))

    valid = [a for a in scored if a[2] != "format"]
    open_cases = sum(1 for a in valid if a[2] == "provisional")
    if open_cases:
        notes.append(f"{open_cases} cases sent to a human are not reviewed yet and only scored provisionally.")

    # Judge miss rate from the reviewed sample
    sample = [a for a in valid if a[2] == "human_sample"]
    missed = sum(1 for a in sample if a[1])
    miss_rate = missed / len(sample) if sample else None
    done_unreviewed = sum(1 for a in valid if a[2] == "done")

    z = []
    z.append(f"# Figures in Context: report \"{run_dir.name}\"\n")
    z.append(f"Created on {date.today().isoformat()}. Unit of counting: answer. "
             "Values in brackets: 95 % confidence interval (Wilson).\n")
    if notes:
        z.append("**Notes**\n")
        z.extend(f"- {n}" for n in notes)
        z.append("")

    z.append("## Overall error rate\n")
    wrong = sum(1 for a in valid if a[1])
    z.append(f"- **Measured error rate:** {rate(wrong, len(valid))}")
    if miss_rate is not None and valid:
        corrected = (wrong + miss_rate * done_unreviewed) / len(valid)
        z.append(f"- **Corrected error rate** (adjusted for the judge miss rate): {corrected:.1%}")
    z.append(f"- **Format error rate** (separate, not part of the error rate): "
             f"{rate(len(scored) - len(valid), len(scored))}")
    z.append(f"- **Judge miss rate** (sample): {rate(missed, len(sample)) if sample else 'no reviewed sample yet'}\n")

    for title, key in [("model", lambda c: c["model"]),
                       ("category", lambda c: cases[c["case_id"]]["category"]),
                       ("difficulty", lambda c: cases[c["case_id"]]["difficulty"])]:
        groups = defaultdict(list)
        for a in valid:
            groups[key(a[0])].append(a)
        z.append(f"## Error rate per {title}\n")
        z.append(f"| {title.capitalize()} | Error rate |")
        z.append("|---|---|")
        for g in sorted(groups):
            z.append(f"| {g} | {rate(sum(1 for a in groups[g] if a[1]), len(groups[g]))} |")
        z.append("")

    z.append("## Error rate per error type and model\n")
    model_names = sorted({a[0]["model"] for a in valid})
    z.append("| Error type | " + " | ".join(model_names) + " |")
    z.append("|---|" + "---|" * len(model_names))
    for error_type in data.ERROR_TYPES:
        values = []
        for m in model_names:
            subset = [a for a in valid if a[0]["model"] == m]
            values.append(rate(sum(1 for a in subset if error_type in a[1]), len(subset)))
        z.append(f"| {error_type} | " + " | ".join(values) + " |")
    z.append("")

    # Judge hit rate: of a judge's flags that a human reviewed,
    # how many does the human confirm with one of this judge's error types?
    z.append("## Judge hit rate (human-reviewed cases only)\n")
    z.append("| Judge | same family as the model under test | different family |")
    z.append("|---|---|---|")
    for judge in config["judges"]:
        counts = {True: [0, 0], False: [0, 0]}
        for c, types, status in valid:
            if not status.startswith("human_"):
                continue
            for v in verdicts[data.answer_key(c)]:
                if v["judge"] == judge and v["flag"]:
                    same = v["judge_model"].split(":")[0] == c["model"].split(":")[0]
                    counts[same][1] += 1
                    counts[same][0] += any(t in types for t in ALLOWED[judge])
        z.append(f"| {judge} | {rate(*counts[True])} | {rate(*counts[False])} |")
    z.append("")

    md = "\n".join(z)
    (run_dir / "report.md").write_text(md, encoding="utf-8")
    (run_dir / "report.html").write_text(to_html(md, run_dir.name), encoding="utf-8")
    data.log(run_dir, "info", "Report created (report.md and report.html).")


def to_html(md, title):
    """Minimal Markdown → HTML for headings, lists, tables and bold text."""
    def inline(t):
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(t))

    parts, in_list, in_table = [], False, False
    for line in md.splitlines():
        if in_list and not line.startswith("- "):
            parts.append("</ul>")
            in_list = False
        if in_table and not line.startswith("|"):
            parts.append("</table>")
            in_table = False
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            parts.append(f"<h{level}>{inline(line.lstrip('#').strip())}</h{level}>")
        elif line.startswith("- "):
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{inline(line[2:])}</li>")
        elif line.startswith("|"):
            cells = [x.strip() for x in line.strip("|").split("|")]
            if set("".join(cells)) <= {"-"}:
                continue
            tag = "th" if not in_table else "td"
            if not in_table:
                parts.append("<table>")
                in_table = True
            parts.append("<tr>" + "".join(f"<{tag}>{inline(x)}</{tag}>" for x in cells) + "</tr>")
        elif line.strip():
            parts.append(f"<p>{inline(line)}</p>")
    if in_list:
        parts.append("</ul>")
    if in_table:
        parts.append("</table>")
    style = ("body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}"
             "table{border-collapse:collapse;margin:.5rem 0 1.5rem;width:100%}"
             "th,td{border:1px solid #ccc;padding:.35rem .6rem;text-align:left}th{background:#eef3f8}"
             "h1,h2{color:#1f4e79}")
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{html.escape(title)}</title>"
            f"<style>{style}</style></head><body>{''.join(parts)}</body></html>")
