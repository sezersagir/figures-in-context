"""Web app: Python backend, HTML frontend, standard library only.

    python -m figures_in_context app        → http://127.0.0.1:8765/

Create and start runs (with progress), review, report, set models and API keys.
The server only listens on 127.0.0.1, so it can only be reached from this computer.
"""

import collections
import json
import re
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import calibration, data, models, pipeline, report
from .review import PAGE as REVIEW_PAGE
from .review import ReviewSession

APP_PAGE = Path(__file__).parent / "app.html"
PROVIDERS = ("anthropic", "openai", "google", "test")
DOWNLOADS = {"report.html", "report.md", "review_results.csv", "review_queue.csv"}


class Job:
    """A run (or calibration) working in the background. At most one runs at a time."""

    def __init__(self, name):
        self.name = name
        self.log = collections.deque(maxlen=300)
        self.progress = ""
        self.running = True
        self.outcome = None


_job = None
_job_lock = threading.Lock()
_sessions = {}


def _report_progress(text):
    print(text, flush=True)
    job = _job
    if job is None:
        return
    if re.match(r"^(Answers|Judges): \d+/\d+$", text):
        job.progress = text
    else:
        job.log.append(text)


data.report_progress = _report_progress


def _in_background(name, prepare, work):
    """Runs work() in its own thread. prepare() runs first and may raise to cancel.
    name may be a function when the name is only known after prepare()."""
    global _job
    with _job_lock:
        if _job and _job.running:
            raise pipeline.RunError(f"Something is already running ({_job.name}). Please wait until it has finished.")
        prepare()
        name = name() if callable(name) else name
        _job = Job(name)
    job = _job

    def execute():
        try:
            job.outcome = "done" if work() else "incomplete"
        except Exception as e:
            job.log.append(f"ERROR: {type(e).__name__}: {e}")
            traceback.print_exc()
            job.outcome = "failed"
        finally:
            job.progress = ""
            job.running = False
            _sessions.pop(name, None)  # the review queue may be new

    threading.Thread(target=execute, daemon=True).start()


def _start_run(name):
    loaded = {}

    def prepare():
        loaded["run"] = pipeline.load_run(name, warn=False)

    def work():
        pipeline.load_run(name)  # writes warnings to the log
        return pipeline.start(*loaded["run"])

    _in_background(name, prepare, work)


def _start_calibration(name=None, test=False):
    target = {}

    def prepare():
        target["dir"] = calibration.load(name)[0] if name else calibration.new(test=test)
        target["name"] = "calibration:" + target["dir"].name

    def work():
        return calibration.start(target["dir"], calibration.load(target["dir"].name)[1])

    _in_background(lambda: target["name"], prepare, work)
    return target["dir"].name


def _status():
    config = data.load_config()
    count, problems = pipeline.check_cases()
    runs = []
    for name in pipeline.all_runs():
        try:
            p = pipeline.progress(pipeline.RUNS_DIR / name)
        except Exception as e:
            p = {"error": str(e)}
        runs.append({"name": name, **p})
    calibrations = []
    for name in calibration.all_calibrations():
        try:
            s = calibration.status(calibration.RUNS_DIR / name)
        except Exception as e:
            s = {"error": str(e)}
        calibrations.append({"name": name, **s})
    return {
        "config": config,
        "keys": {p: bool(_has_key(p)) for p in ("anthropic", "openai", "google")},
        "test_cases": count,
        "test_case_problems": problems,
        "runs": runs,
        "calibrations": calibrations,
        "calibration_answers": len(calibration.load_answers()),
        "job": _job_info(),
    }


def _has_key(provider):
    try:
        return models.api_key(provider)
    except models.ApiError:
        return None


def _job_info():
    if not _job:
        return None
    return {"name": _job.name, "running": _job.running, "progress": _job.progress,
            "log": list(_job.log), "outcome": _job.outcome}


def _save_keys(payload):
    lines = models.ENV_FILE.read_text(encoding="utf-8").splitlines() if models.ENV_FILE.exists() else []
    for provider, name in models.KEYS.items():
        value = (payload.get(provider) or "").strip()
        if not value:
            continue
        if not re.fullmatch(r"[\x21-\x7e]+", value):
            raise ValueError(f"The key for {provider} contains invalid characters.")
        lines = [line for line in lines if not line.strip().startswith(name + "=")]
        lines.append(f"{name}={value}")
    models.ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    models.load_env()


def _save_config(payload):
    config = data.load_config()

    def target(t):
        if t.get("provider") not in PROVIDERS or not str(t.get("model", "")).strip():
            raise ValueError("Every model needs a provider and a model name.")
        out = {"provider": t["provider"], "model": str(t["model"]).strip()}
        if t.get("effort"):
            out["effort"] = str(t["effort"])
        return out

    under_test = [target(t) for t in payload.get("models_under_test", []) if str(t.get("model", "")).strip()]
    if not under_test:
        raise ValueError("Enter at least one model under test.")
    config["models_under_test"] = under_test
    config["judges"] = {j: target(payload["judges"][j]) for j in ("numbers", "calculation", "plausibility")}
    reps = int(payload.get("repetitions", 1))
    share = float(payload["sample"]["share"])
    minimum = int(payload["sample"]["minimum"])
    if not (1 <= reps <= 10 and 0 <= share <= 1 and minimum >= 0):
        raise ValueError("Repetitions 1–10, sample share 0–1, minimum 0 or more.")
    config["repetitions"] = reps
    config["sample"].update({"share": share, "minimum": minimum})
    (data.BASE / "config" / "run.json").write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n",
                                                   encoding="utf-8")


def _log(run_dir, start):
    """Entries from number `start` on (for live loading) and a summary over all of them."""
    entries = data.read_jsonl(run_dir / data.LOG)
    requests = [e for e in entries if e.get("step")]
    summary = {
        "requests": len(requests),
        "errors": sum(1 for e in requests if e["kind"] == "error"),
        "retried": sum(1 for e in requests if (e.get("attempts") or 1) > 1),
        "tokens_in": sum(e.get("tokens_in") or 0 for e in requests),
        "tokens_out": sum(e.get("tokens_out") or 0 for e in requests),
        "duration_s": round(sum(e.get("duration_s") or 0 for e in requests), 1),
    }
    return {"total": len(entries), "entries": entries[start:], "summary": summary}


def _session(name):
    if name not in _sessions:
        run_dir, _, cases = pipeline.load_run(name, warn=False)
        _sessions[name] = ReviewSession(run_dir, cases)
    return _sessions[name]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, content_type="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code, text):
        self._send(code, {"error": text})

    def _allowed(self):
        # Protects against a foreign web page in the browser sending requests to this server
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self._allowed():
            return self._error(403, "Only reachable locally.")
        path = unquote(urlparse(self.path).path)
        try:
            if path == "/":
                return self._send(200, APP_PAGE.read_bytes(), "text/html; charset=utf-8")
            if path == "/api/status":
                return self._send(200, _status())
            m = re.fullmatch(r"/api/(runs|calibrations)/([\w.-]+)/log", path)
            if m:
                run_dir = (pipeline.load_run(m.group(2), warn=False)[0] if m.group(1) == "runs"
                           else calibration.load(m.group(2))[0])
                start = int((parse_qs(urlparse(self.path).query).get("from") or ["0"])[0])
                return self._send(200, _log(run_dir, max(0, start)))
            m = re.fullmatch(r"/review/([\w.-]+)/", path)
            if m:
                return self._send(200, REVIEW_PAGE.read_bytes(), "text/html; charset=utf-8")
            m = re.fullmatch(r"/review/([\w.-]+)/api/cases", path)
            if m:
                return self._send(200, _session(m.group(1)).data())
            m = re.fullmatch(r"/calibrations/([\w.-]+)/calibration\.html", path)
            if m:
                file = calibration.load(m.group(1))[0] / "calibration.html"
                if not file.exists():
                    return self._error(404, "No result yet.")
                return self._send(200, file.read_bytes(), "text/html; charset=utf-8")
            m = re.fullmatch(r"/runs/([\w.-]+)/([\w.-]+)", path)
            if m and m.group(2) in DOWNLOADS:
                run_dir = pipeline.load_run(m.group(1), warn=False)[0]
                file = run_dir / m.group(2)
                if not file.exists():
                    return self._error(404, "This file doesn't exist yet.")
                content_type = "text/html; charset=utf-8" if file.suffix == ".html" else "text/plain; charset=utf-8"
                extra = {} if file.suffix == ".html" else {
                    "Content-Disposition": f'attachment; filename="{m.group(1)}_{m.group(2)}"'}
                return self._send(200, file.read_bytes(), content_type, extra)
            self._error(404, "Not found.")
        except (pipeline.RunError, calibration.CalibrationError, FileNotFoundError, ValueError) as e:
            self._error(404, str(e))

    def do_POST(self):
        # A custom header forces foreign pages into a CORS preflight, which this server never allows
        if not self._allowed() or self.headers.get("X-Figures-In-Context") != "1":
            return self._error(403, "Only allowed from the Figures in Context interface.")
        path = unquote(urlparse(self.path).path)
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self._error(400, "Invalid request.")
        try:
            if path == "/api/runs":
                run_dir = pipeline.new(str(payload.get("name", "")), test=bool(payload.get("test")))
                return self._send(200, {"name": run_dir.name})
            m = re.fullmatch(r"/api/runs/([\w.-]+)/start", path)
            if m:
                _start_run(m.group(1))
                return self._send(200, {"ok": True})
            if path == "/api/calibration":
                name = _start_calibration(payload.get("name"), test=bool(payload.get("test")))
                return self._send(200, {"name": name})
            m = re.fullmatch(r"/api/runs/([\w.-]+)/report", path)
            if m:
                run_dir, config, cases = pipeline.load_run(m.group(1), warn=False)
                report.run(run_dir, config, cases)
                return self._send(200, {"ok": True})
            m = re.fullmatch(r"/review/([\w.-]+)/api/save", path)
            if m:
                _session(m.group(1)).save(payload)
                return self._send(200, {"ok": True})
            if path == "/api/keys":
                _save_keys(payload)
                return self._send(200, {"ok": True})
            if path == "/api/config":
                _save_config(payload)
                return self._send(200, {"ok": True})
            self._error(404, "Not found.")
        except (pipeline.RunError, calibration.CalibrationError, ValueError, KeyError, TypeError,
                FileNotFoundError) as e:
            self._error(400, str(e))


def serve(port=8765, browser=True):
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:
        raise SystemExit(f"Port {port} is in use. Is the app already running? Otherwise: python -m figures_in_context app 8766")
    url = f"http://127.0.0.1:{port}/"
    print(f"Figures in Context running: {url}")
    print("Keep this window open. Stop with Ctrl+C.")
    if browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
