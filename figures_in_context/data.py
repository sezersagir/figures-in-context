"""Read and write test cases, documents, config and run files."""

import glob
import hashlib
import json
import re
import threading
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

ERROR_TYPES = [
    "wrong_result",
    "wrong_source",
    "invented_number",
    "calculation_error",
    "missing_information",
]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_config():
    return load_json(BASE / "config" / "run.json")


def load_test_cases(pattern):
    cases = []
    for file in sorted(glob.glob(str(BASE / pattern))):
        cases.extend(load_json(file))
    ids = [c["id"] for c in cases]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"Duplicate test case IDs: {sorted(duplicates)}")
    return {c["id"]: c for c in cases}


def load_prompt(name):
    return (BASE / "prompts" / f"{name}.md").read_text(encoding="utf-8")


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


# --- Documents -----------------------------------------------------------------

_PAGE = re.compile(r"^###\s+Page\s+(\d+)\b", re.MULTILINE)


def _page_numbers(spec):
    """1 → [1]; "1-2" → [1, 2]; "1,3" → [1, 3]."""
    if isinstance(spec, int):
        return [spec]
    numbers = []
    for part in str(spec).split(","):
        if "-" in part:
            start, end = (int(x) for x in part.split("-"))
            numbers.extend(range(start, end + 1))
        else:
            numbers.append(int(part))
    return numbers


def document_excerpt(case):
    """The pages the model gets for this test case. The company header before page 1 is always included."""
    text = full_document(case)
    matches = list(_PAGE.finditer(text))
    if not matches:
        return text
    header = text[: matches[0].start()]
    pages = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        pages[int(m.group(1))] = text[m.start():end]
    wanted = _page_numbers(case["document"]["page"])
    missing = [p for p in wanted if p not in pages]
    if missing:
        raise ValueError(f"{case['id']}: page(s) {missing} not in the document")
    return header + "".join(pages[p] for p in wanted)


def full_document(case):
    return (BASE / "test_cases" / case["document"]["file"]).read_text(encoding="utf-8")


# --- Run files (JSONL) ---------------------------------------------------------

_write_lock = threading.Lock()


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    records = []
    for i, line in enumerate(lines):
        try:
            records.append(json.loads(line))
        except ValueError:
            if i < len(lines) - 1:
                raise
            # the last line is still being written (the web app reads while a run is going)
    return records


def append(path, record):
    with _write_lock, open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def answer_key(d):
    return f"{d['case_id']}|{d['model']}|{d['repetition']}"


# --- Progress ------------------------------------------------------------------
# Default: print to the terminal. The web app replaces this to show progress.

def _print(text):
    print(text, flush=True)


report_progress = _print


# --- Log -----------------------------------------------------------------------
# Every run (and every calibration) gets a log.jsonl: what happened when, and every
# request with model, duration, tokens and result. The web app shows it live.

LOG = "log.jsonl"


def log(run_dir, kind, text="", **fields):
    """kind: info, warning, error, answer, verdict. text is also shown as progress output."""
    append(Path(run_dir) / LOG,
           {"time": datetime.now().isoformat(timespec="seconds"), "kind": kind, "text": text, **fields})
    if text:
        report_progress(text)
