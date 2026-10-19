"""Stage 5: Review UI in the browser. Standard library only.

    python -m figures_in_context review <run>       (or in the web app: python -m figures_in_context app)

Reads review_queue.csv (and review_results.csv, if it exists) and saves every
change straight away to review_results.csv. The report reads exactly this file.
"""

import csv
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import data
from .routing import DELIMITER, REVIEW_COLUMNS

PAGE = Path(__file__).parent / "review.html"


def _read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        header = f.readline()
        f.seek(0)
        delimiter = ";" if header.count(";") >= header.count(",") else ","
        return list(csv.DictReader(f, delimiter=delimiter))


def load_cases(run_dir, cases, with_document=True):
    queue = _read_csv(run_dir / "review_queue.csv")
    results_path = run_dir / "review_results.csv"
    if results_path.exists():
        previous = {row["case_no"]: row for row in _read_csv(results_path)}
        for c in queue:
            old = previous.get(c["case_no"])
            if old:
                for field in ("final_error_types", "comment", "reviewer", "checked"):
                    c[field] = old.get(field, "")
    if with_document:
        for c in queue:
            t = cases.get(c["case_id"])
            c["document"] = data.full_document(t) if t else ""
            c["document_page"] = str(t["document"]["page"]) if t else ""
            c["document_file"] = Path(t["document"]["file"]).name if t else ""
    return queue


def save(run_dir, queue):
    target = run_dir / "review_results.csv"
    tmp = target.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, REVIEW_COLUMNS, delimiter=DELIMITER, extrasaction="ignore")
        w.writeheader()
        w.writerows(queue)
    tmp.replace(target)


class ReviewSession:
    """Keeps a run's review cases in memory and writes every change to disk straight away."""

    def __init__(self, run_dir, cases):
        if not (run_dir / "review_queue.csv").exists():
            raise FileNotFoundError("This run has no review queue yet. Start the run first.")
        self.run_dir = run_dir
        self.queue = load_cases(run_dir, cases)
        self.by_no = {c["case_no"]: c for c in self.queue}
        self.lock = threading.Lock()

    def data(self):
        test = data.load_json(self.run_dir / "run.json").get("test", False)
        return {"run": self.run_dir.name, "test": test, "error_types": data.ERROR_TYPES, "cases": self.queue}

    def save(self, payload):
        case = self.by_no.get(str(payload.get("case_no")))
        if not case:
            raise KeyError("unknown case")
        types = [t for t in payload.get("error_types", []) if t in data.ERROR_TYPES]
        with self.lock:
            case["final_error_types"] = ",".join(types)
            case["comment"] = str(payload.get("comment", ""))
            case["reviewer"] = str(payload.get("reviewer", ""))
            case["checked"] = "x" if payload.get("checked") else ""
            save(self.run_dir, self.queue)


def serve(run_dir, cases, port=8765, browser=True):
    try:
        session = ReviewSession(run_dir, cases)
    except FileNotFoundError as e:
        raise SystemExit(str(e))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body, content_type="application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/cases":
                self._send(200, json.dumps(session.data(), ensure_ascii=False).encode("utf-8"))
            else:
                self._send(404, b"{}")

        def do_POST(self):
            if self.path != "/api/save":
                return self._send(404, b"{}")
            length = int(self.headers.get("Content-Length", 0))
            try:
                session.save(json.loads(self.rfile.read(length) or b"{}"))
            except KeyError:
                return self._send(400, b'{"error": "unknown case"}')
            self._send(200, b'{"ok": true}')

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Review UI running: {url}")
    print(f"Changes are saved automatically to {run_dir / 'review_results.csv'}")
    print("Stop with Ctrl+C.")
    if browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Next: python -m figures_in_context report " + run_dir.name)
    finally:
        server.server_close()
