"""Tests für Anbieter-Antworten und die Web-App. Ohne Netz, ohne API-Schlüssel."""

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

from figures_in_context import app, check, daten, kalibrierung, modelle, pipeline


class AnbieterAntworten(unittest.TestCase):
    def frage(self, anbieter, antwort):
        with mock.patch.object(modelle, "_post", return_value=(antwort, 1)) as post, \
                mock.patch.object(modelle, "schluessel", return_value="k"):
            ergebnis = modelle.frage({"anbieter": anbieter, "modell": "m"}, "sys", "text", schema={"type": "object"})
        return ergebnis, post.call_args[0][2]

    def test_anthropic(self):
        e, anfrage = self.frage("anthropic", {"content": [{"type": "thinking", "thinking": "x"}, {"type": "text", "text": "{}"}],
                                              "usage": {"input_tokens": 3, "output_tokens": 4}, "stop_reason": "end_turn"})
        self.assertEqual(e["text"], "{}")
        self.assertEqual(anfrage["output_config"]["format"]["type"], "json_schema")
        self.assertNotIn("temperature", anfrage)

    def test_openai(self):
        e, anfrage = self.frage("openai", {"output": [{"type": "reasoning"}, {"type": "message", "content": [
            {"type": "output_text", "text": "{}"}]}], "usage": {"input_tokens": 1, "output_tokens": 2}, "status": "completed"})
        self.assertEqual(e["text"], "{}")
        self.assertTrue(anfrage["text"]["format"]["strict"])

    def test_google_ohne_gedanken(self):
        e, anfrage = self.frage("google", {"candidates": [{"content": {"parts": [
            {"text": "denke", "thought": True}, {"text": "{}"}]}, "finishReason": "STOP"}]})
        self.assertEqual(e["text"], "{}")
        self.assertEqual(anfrage["generationConfig"]["responseMimeType"], "application/json")


class Kalibrierung(unittest.TestCase):
    def test_antworten_passen_zur_absicht(self):
        """Fehlerfreie Antworten müssen den Python-Check bestehen, Quellen-, Erfindungs- und Rechenfehler nicht."""
        testfaelle = daten.lade_testfaelle(daten.lade_config()["testfaelle"])
        for a in kalibrierung.lade_antworten():
            c = check.pruefe(a, testfaelle[a["testfall_id"]])
            self.assertTrue(c["format_ok"], a["kal_id"])
            ergebnis_falsch = {"falsche_quelle", "erfundene_zahl", "falsch_gerechnet"} & set(a["erwartet"])
            self.assertEqual(c["ergebnis_richtig"], not ergebnis_falsch, a["kal_id"])

    def test_erfundene_zahlen_stehen_nicht_im_dokument(self):
        testfaelle = daten.lade_testfaelle(daten.lade_config()["testfaelle"])
        erfunden = {"K-008": "452,300", "K-010": "290,000,000", "K-018": "89.15", "K-024": "4.0%"}
        antworten = {a["kal_id"]: a for a in kalibrierung.lade_antworten()}
        for kal_id, zahl in erfunden.items():
            a = antworten[kal_id]
            self.assertIn("erfundene_zahl", a["erwartet"])
            self.assertIn(zahl, a["antwort_text"])
            self.assertNotIn(zahl, daten.ganzes_dokument(testfaelle[a["testfall_id"]]))

    def test_bewertung(self):
        antworten = [
            {"kal_id": "K-1", "testfall_id": "T", "beschreibung": "", "wiederholung": 1, "erwartet": ["falsch_gerechnet"]},
            {"kal_id": "K-2", "testfall_id": "T", "beschreibung": "", "wiederholung": 2, "erwartet": []},
            {"kal_id": "K-3", "testfall_id": "T", "beschreibung": "", "wiederholung": 3, "erwartet": ["erfundene_zahl"]},
        ]
        urteile = [
            {"wiederholung": 1, "judge": "rechenweg", "flag": True, "fehlertypen": ["falsch_gerechnet"]},
            {"wiederholung": 2, "judge": "rechenweg", "flag": True, "fehlertypen": ["falsch_gerechnet"], "befund": "x"},
            {"wiederholung": 3, "judge": "rechenweg", "flag": True, "fehlertypen": ["falsch_gerechnet"]},
        ]
        e = kalibrierung.bewerte(antworten, urteile, ["rechenweg"])["rechenweg"]
        self.assertEqual((e["treffer"], e["soll"], e["fehlalarme"], e["sauber"]), (1, 1, 1, 1))
        self.assertFalse(e["bestanden"])


class WebApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.patch = mock.patch.object(pipeline, "LAUFORDNER", Path(cls.tmp.name) / "laeufe")
        cls.patch.start()
        cls.patch_kal = mock.patch.object(kalibrierung, "ORDNER", Path(cls.tmp.name) / "kalibrierungen")
        cls.patch_kal.start()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.patch.stop()
        cls.patch_kal.stop()
        cls.tmp.cleanup()

    def anfrage(self, pfad, inhalt=None, kopf=None):
        daten = None if inhalt is None else json.dumps(inhalt).encode()
        r = urllib.request.Request(self.url + pfad, data=daten, headers=kopf or {})
        try:
            with urllib.request.urlopen(r) as a:
                return a.status, json.loads(a.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_post_ohne_eigenen_header_verboten(self):
        code, _ = self.anfrage("/api/laeufe", {"name": "x", "test": True})
        self.assertEqual(code, 403)

    def test_fremder_host_verboten(self):
        code, _ = self.anfrage("/api/status", kopf={"Host": "boese.example"})
        self.assertEqual(code, 403)

    def test_ganzer_probelauf(self):
        h = {"X-Figures-In-Context": "1"}
        code, d = self.anfrage("/api/laeufe", {"name": "probe", "test": True}, h)
        self.assertEqual(code, 200)
        name = d["name"]
        self.assertEqual(self.anfrage(f"/api/laeufe/{name}/start", {}, h)[0], 200)
        job = self.warte()
        self.assertEqual(job["ergebnis"], "fertig", job["log"])
        p = self.anfrage(f"/api/laeufe/{name}/protokoll")[1]
        arten = [e["art"] for e in p["eintraege"]]
        self.assertEqual((arten.count("antwort"), arten.count("urteil")), (22, 66))
        self.assertEqual(p["summe"]["anfragen"], 88)
        nachgeladen = self.anfrage(f"/api/laeufe/{name}/protokoll?ab={p['gesamt'] - 2}")[1]
        self.assertEqual(len(nachgeladen["eintraege"]), 2)
        faelle = self.anfrage(f"/review/{name}/api/faelle")[1]["faelle"]
        self.assertTrue(faelle)
        code, _ = self.anfrage(f"/review/{name}/api/speichern",
                               {"fall_nr": faelle[0]["fall_nr"], "fehlertypen": ["falsche_quelle"], "geprueft": True}, h)
        self.assertEqual(code, 200)
        self.assertEqual(self.anfrage(f"/api/laeufe/{name}/auswertung", {}, h)[0], 200)
        lauf = next(l for l in self.anfrage("/api/status")[1]["laeufe"] if l["name"] == name)
        self.assertEqual(lauf["review_geprueft"], 1)
        self.assertTrue(lauf["report"])

    def warte(self):
        for _ in range(400):
            job = self.anfrage("/api/status")[1]["job"]
            if not job["laeuft"]:
                return job
            time.sleep(0.05)
        self.fail("Job wird nicht fertig")

    def test_kalibrierung_probe(self):
        code, d = self.anfrage("/api/kalibrierung", {"test": True}, {"X-Figures-In-Context": "1"})
        self.assertEqual(code, 200, d)
        job = self.warte()
        self.assertEqual(job["ergebnis"], "fertig", job["log"])
        k = self.anfrage("/api/status")[1]["kalibrierungen"][0]
        self.assertEqual(set(k["ergebnis"]), {"zahlen", "rechenweg", "plausibilitaet"})
        self.assertEqual(k["ergebnis"]["zahlen"]["soll"], 9)
        r = urllib.request.urlopen(f"{self.url}/kalibrierungen/{d['name']}/kalibrierung.html")
        self.assertEqual(r.status, 200)

    def test_unbekannter_lauf(self):
        self.assertEqual(self.anfrage("/review/gibtsnicht/api/faelle")[0], 404)
        self.assertIn(self.anfrage("/api/laeufe/..%2F..%2Fx/start", {}, {"X-Figures-In-Context": "1"})[0], (400, 404))


if __name__ == "__main__":
    unittest.main()
