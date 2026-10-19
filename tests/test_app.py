"""Tests for provider responses and the web app. No network, no API keys."""

import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from figures_in_context import app, calibration, check, data, models, pipeline


class ProviderResponses(unittest.TestCase):
    def ask(self, provider, response):
        with mock.patch.object(models, "_post", return_value=(response, 1)) as post, \
                mock.patch.object(models, "api_key", return_value="k"):
            result = models.ask({"provider": provider, "model": "m"}, "sys", "text", schema={"type": "object"})
        return result, post.call_args[0][2]

    def test_anthropic(self):
        r, request = self.ask("anthropic", {"content": [{"type": "thinking", "thinking": "x"}, {"type": "text", "text": "{}"}],
                                            "usage": {"input_tokens": 3, "output_tokens": 4}, "stop_reason": "end_turn"})
        self.assertEqual(r["text"], "{}")
        self.assertEqual(request["output_config"]["format"]["type"], "json_schema")
        self.assertNotIn("temperature", request)

    def test_openai(self):
        r, request = self.ask("openai", {"output": [{"type": "reasoning"}, {"type": "message", "content": [
            {"type": "output_text", "text": "{}"}]}], "usage": {"input_tokens": 1, "output_tokens": 2}, "status": "completed"})
        self.assertEqual(r["text"], "{}")
        self.assertTrue(request["text"]["format"]["strict"])

    def test_google_without_thoughts(self):
        r, request = self.ask("google", {"candidates": [{"content": {"parts": [
            {"text": "thinking", "thought": True}, {"text": "{}"}]}, "finishReason": "STOP"}]})
        self.assertEqual(r["text"], "{}")
        self.assertEqual(request["generationConfig"]["responseMimeType"], "application/json")


class Calibration(unittest.TestCase):
    def test_answers_match_their_intent(self):
        """Clean answers must pass the Python check; source, invention and calculation errors must not."""
        cases = data.load_test_cases(data.load_config()["test_cases"])
        for a in calibration.load_answers():
            c = check.check_answer(a, cases[a["case_id"]])
            self.assertTrue(c["format_ok"], a["cal_id"])
            result_wrong = {"wrong_source", "invented_number", "calculation_error"} & set(a["expected"])
            self.assertEqual(c["result_correct"], not result_wrong, a["cal_id"])

    def test_invented_numbers_are_not_in_the_document(self):
        cases = data.load_test_cases(data.load_config()["test_cases"])
        invented = {"C-008": "452,300", "C-010": "290,000,000", "C-018": "89.15", "C-024": "4.0%"}
        answers = {a["cal_id"]: a for a in calibration.load_answers()}
        for cal_id, number in invented.items():
            a = answers[cal_id]
            self.assertIn("invented_number", a["expected"])
            self.assertIn(number, a["answer_text"])
            self.assertNotIn(number, data.full_document(cases[a["case_id"]]))

    def test_scoring(self):
        answers = [
            {"cal_id": "C-1", "case_id": "T", "description": "", "repetition": 1, "expected": ["calculation_error"]},
            {"cal_id": "C-2", "case_id": "T", "description": "", "repetition": 2, "expected": []},
            {"cal_id": "C-3", "case_id": "T", "description": "", "repetition": 3, "expected": ["invented_number"]},
        ]
        verdicts = [
            {"repetition": 1, "judge": "calculation", "flag": True, "error_types": ["calculation_error"]},
            {"repetition": 2, "judge": "calculation", "flag": True, "error_types": ["calculation_error"], "finding": "x"},
            {"repetition": 3, "judge": "calculation", "flag": True, "error_types": ["calculation_error"]},
        ]
        e = calibration.score(answers, verdicts, ["calculation"])["calculation"]
        self.assertEqual((e["hits"], e["expected"], e["false_alarms"], e["clean"]), (1, 1, 1, 1))
        self.assertFalse(e["passed"])


class WebApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.patch = mock.patch.object(pipeline, "RUNS_DIR", Path(cls.tmp.name) / "runs")
        cls.patch.start()
        cls.patch_cal = mock.patch.object(calibration, "RUNS_DIR", Path(cls.tmp.name) / "calibration_runs")
        cls.patch_cal.start()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.patch.stop()
        cls.patch_cal.stop()
        cls.tmp.cleanup()

    def request(self, path, body=None, headers=None):
        payload = None if body is None else json.dumps(body).encode()
        r = urllib.request.Request(self.url + path, data=payload, headers=headers or {})
        try:
            with urllib.request.urlopen(r) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_post_without_custom_header_forbidden(self):
        code, _ = self.request("/api/runs", {"name": "x", "test": True})
        self.assertEqual(code, 403)

    def test_foreign_host_forbidden(self):
        code, _ = self.request("/api/status", headers={"Host": "evil.example"})
        self.assertEqual(code, 403)

    def test_full_test_run(self):
        h = {"X-Figures-In-Context": "1"}
        code, d = self.request("/api/runs", {"name": "trial", "test": True}, h)
        self.assertEqual(code, 200)
        name = d["name"]
        self.assertEqual(self.request(f"/api/runs/{name}/start", {}, h)[0], 200)
        job = self.wait()
        self.assertEqual(job["outcome"], "done", job["log"])
        log = self.request(f"/api/runs/{name}/log")[1]
        kinds = [e["kind"] for e in log["entries"]]
        run = next(r for r in self.request("/api/status")[1]["runs"] if r["name"] == name)
        valid = 22 - run["format_errors"]
        self.assertEqual((kinds.count("answer"), kinds.count("verdict")), (22, 3 * valid))
        self.assertEqual(log["summary"]["requests"], 22 + 3 * valid)
        more = self.request(f"/api/runs/{name}/log?from={log['total'] - 2}")[1]
        self.assertEqual(len(more["entries"]), 2)
        cases = self.request(f"/review/{name}/api/cases")[1]["cases"]
        self.assertTrue(cases)
        code, _ = self.request(f"/review/{name}/api/save",
                               {"case_no": cases[0]["case_no"], "error_types": ["wrong_source"], "checked": True}, h)
        self.assertEqual(code, 200)
        self.assertEqual(self.request(f"/api/runs/{name}/report", {}, h)[0], 200)
        run = next(r for r in self.request("/api/status")[1]["runs"] if r["name"] == name)
        self.assertEqual(run["review_checked"], 1)
        self.assertTrue(run["report"])

    def wait(self):
        for _ in range(400):
            job = self.request("/api/status")[1]["job"]
            if not job["running"]:
                return job
            time.sleep(0.05)
        self.fail("Job does not finish")

    def test_calibration_test_run(self):
        code, d = self.request("/api/calibration", {"test": True}, {"X-Figures-In-Context": "1"})
        self.assertEqual(code, 200, d)
        job = self.wait()
        self.assertEqual(job["outcome"], "done", job["log"])
        c = self.request("/api/status")[1]["calibrations"][0]
        self.assertEqual(set(c["result"]), {"numbers", "calculation", "plausibility"})
        self.assertEqual(c["result"]["numbers"]["expected"], 9)
        r = urllib.request.urlopen(f"{self.url}/calibrations/{d['name']}/calibration.html")
        self.assertEqual(r.status, 200)

    def test_unknown_run(self):
        self.assertEqual(self.request("/review/doesnotexist/api/cases")[0], 404)
        self.assertIn(self.request("/api/runs/..%2F..%2Fx/start", {}, {"X-Figures-In-Context": "1"})[0], (400, 404))


if __name__ == "__main__":
    unittest.main()
