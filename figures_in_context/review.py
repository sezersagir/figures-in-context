"""Stufe 5: Review-Oberfläche im Browser. Nur Standardbibliothek.

    python -m figures_in_context review <lauf>       (oder in der Web-App: python -m figures_in_context app)

Liest review_queue.csv (und, falls vorhanden, review_ergebnis.csv) und speichert jede
Änderung sofort in review_ergebnis.csv. Die Auswertung liest genau diese Datei.
"""

import csv
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import daten
from .weiterleitung import REVIEW_SPALTEN, TRENNER

SEITE = Path(__file__).parent / "review.html"


def _lies_csv(pfad):
    with open(pfad, encoding="utf-8-sig", newline="") as f:
        kopf = f.readline()
        f.seek(0)
        trenner = ";" if kopf.count(";") >= kopf.count(",") else ","
        return list(csv.DictReader(f, delimiter=trenner))


def lade_faelle(laufordner, testfaelle, mit_dokument=True):
    faelle = _lies_csv(laufordner / "review_queue.csv")
    ergebnis_pfad = laufordner / "review_ergebnis.csv"
    if ergebnis_pfad.exists():
        bisher = {z["fall_nr"]: z for z in _lies_csv(ergebnis_pfad)}
        for f in faelle:
            alt = bisher.get(f["fall_nr"])
            if alt:
                for feld in ("fehlertypen_final", "kommentar", "reviewer", "geprueft"):
                    f[feld] = alt.get(feld, "")
    if mit_dokument:
        for f in faelle:
            t = testfaelle.get(f["testfall_id"])
            f["dokument"] = daten.ganzes_dokument(t) if t else ""
            f["dokument_seite"] = str(t["dokument"]["seite"]) if t else ""
            f["dokument_datei"] = Path(t["dokument"]["datei"]).name if t else ""
    return faelle


def speichere(laufordner, faelle):
    ziel = laufordner / "review_ergebnis.csv"
    tmp = ziel.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, REVIEW_SPALTEN, delimiter=TRENNER, extrasaction="ignore")
        w.writeheader()
        w.writerows(faelle)
    tmp.replace(ziel)


class ReviewSitzung:
    """Hält die Fälle eines Laufs im Speicher und schreibt jede Änderung sofort auf die Platte."""

    def __init__(self, laufordner, testfaelle):
        if not (laufordner / "review_queue.csv").exists():
            raise FileNotFoundError("Für diesen Lauf gibt es noch keine Review-Liste. Erst den Lauf starten.")
        self.laufordner = laufordner
        self.faelle = lade_faelle(laufordner, testfaelle)
        self.nach_nr = {f["fall_nr"]: f for f in self.faelle}
        self.sperre = threading.Lock()

    def daten(self):
        test = daten.lade_json(self.laufordner / "lauf.json").get("test", False)
        return {"lauf": self.laufordner.name, "test": test, "fehlertypen": daten.FEHLERTYPEN, "faelle": self.faelle}

    def speichern(self, eingabe):
        fall = self.nach_nr.get(str(eingabe.get("fall_nr")))
        if not fall:
            raise KeyError("unbekannter Fall")
        typen = [t for t in eingabe.get("fehlertypen", []) if t in daten.FEHLERTYPEN]
        with self.sperre:
            fall["fehlertypen_final"] = ",".join(typen)
            fall["kommentar"] = str(eingabe.get("kommentar", ""))
            fall["reviewer"] = str(eingabe.get("reviewer", ""))
            fall["geprueft"] = "x" if eingabe.get("geprueft") else ""
            speichere(self.laufordner, self.faelle)


def starte(laufordner, testfaelle, port=8765, browser=True):
    try:
        sitzung = ReviewSitzung(laufordner, testfaelle)
    except FileNotFoundError as e:
        raise SystemExit(str(e))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _sende(self, code, inhalt, typ="application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", typ)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(inhalt)

        def do_GET(self):
            if self.path == "/":
                self._sende(200, SEITE.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/faelle":
                self._sende(200, json.dumps(sitzung.daten(), ensure_ascii=False).encode("utf-8"))
            else:
                self._sende(404, b"{}")

        def do_POST(self):
            if self.path != "/api/speichern":
                return self._sende(404, b"{}")
            laenge = int(self.headers.get("Content-Length", 0))
            try:
                sitzung.speichern(json.loads(self.rfile.read(laenge) or b"{}"))
            except KeyError:
                return self._sende(400, b'{"fehler": "unbekannter Fall"}')
            self._sende(200, b'{"ok": true}')

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Review-Oberfläche läuft: {url}")
    print(f"Gespeichert wird automatisch in {laufordner / 'review_ergebnis.csv'}")
    print("Beenden mit Strg+C.")
    if browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet. Danach: python -m figures_in_context auswertung " + laufordner.name)
    finally:
        server.server_close()
