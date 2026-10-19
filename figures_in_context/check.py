"""Stage 2: Python check. No AI model. → checks.jsonl

Reads the RESULT line, checks the format and compares exactly with the reference answer.
"""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from . import data

_RESULT_LINE = re.compile(r"^\W*RESULT\s*:(.*)$", re.IGNORECASE | re.MULTILINE)
_NUMBER_WORDS = re.compile(
    r"(?:(?<=\d)|\b)(thousand|million|millions|mn|mio|billion|billions|bn|bln|mrd|trillion|k|m|b)\b", re.IGNORECASE
)
_NUMBER = r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|[+-]?\.\d+"
_NUMBER_THEN_UNIT = re.compile(rf"^({_NUMBER})(?![\d,.])\s*(.*)$")
_UNIT_THEN_NUMBER = re.compile(rf"^(\D+?)\s*({_NUMBER})$")


def _unit_table():
    table = {}
    for norm, spellings in data.load_json(data.BASE / "config" / "units.json").items():
        for s in spellings:
            table[s.lower()] = norm
    return table


_UNITS = None


def normalize_unit(unit):
    global _UNITS
    if _UNITS is None:
        _UNITS = _unit_table()
    u = unit.strip().rstrip(".").strip()
    return _UNITS.get(u.lower(), u.upper())


def read_result(text):
    """→ (value: Decimal | None, unit: str | None, format_error: str | None)"""
    lines = _RESULT_LINE.findall(text or "")
    if not lines:
        return None, None, "no RESULT line"
    if len(lines) > 1:
        return None, None, "more than one RESULT line"
    content = lines[0].replace("*", "").replace("`", "").strip()
    if _NUMBER_WORDS.search(content):
        return None, None, "number word in the RESULT line"

    m = _NUMBER_THEN_UNIT.match(content)
    if m:
        number, unit = m.group(1), m.group(2)
    else:
        m = _UNIT_THEN_NUMBER.match(content)
        if not m:
            return None, None, "number not readable"
        unit, number = m.group(1), m.group(2)
    if not unit.strip():
        return None, None, "unit missing"
    try:
        value = Decimal(number.replace(",", ""))
    except InvalidOperation:
        return None, None, "number not readable"
    return value, normalize_unit(unit), None


def compare(value, unit, reference):
    """Exactly equal; only when exact=false is the value rounded half up to n decimals."""
    if unit != normalize_unit(reference["unit"]):
        return False
    expected = Decimal(reference["value"])
    if reference.get("exact", True):
        return value == expected
    places = Decimal(1).scaleb(-int(reference["decimals"]))
    return value.quantize(places, rounding=ROUND_HALF_UP) == expected


def check_answer(answer, case):
    value, unit, format_error = read_result(answer["answer_text"])
    return {
        "case_id": answer["case_id"],
        "model": answer["model"],
        "repetition": answer["repetition"],
        "format_ok": format_error is None,
        "format_reason": format_error,
        "ai_value": None if value is None else str(value),
        "ai_unit": unit,
        "result_correct": None if format_error else compare(value, unit, case["reference_answer"]),
    }


def run(run_dir, cases):
    answers = data.read_jsonl(run_dir / "answers.jsonl")
    target = run_dir / "checks.jsonl"
    target.write_text("", encoding="utf-8")  # cheap, always recomputed from scratch
    counts = {"correct": 0, "wrong": 0, "format": 0}
    for a in answers:
        c = check_answer(a, cases[a["case_id"]])
        data.append(target, c)
        counts["format" if not c["format_ok"] else "correct" if c["result_correct"] else "wrong"] += 1
    data.log(run_dir, "info", f"Python check: {counts['correct']} correct, {counts['wrong']} wrong, "
                              f"{counts['format']} format errors.")
