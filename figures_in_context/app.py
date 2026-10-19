"""Web-App: Python-Backend, HTML-Frontend, nur Standardbibliothek.

    python -m figures_in_context app        → http://127.0.0.1:8765/

Läufe anlegen und starten (mit Fortschritt), Review, Report, Modelle und API-Schlüssel einstellen.
Der Server hört nur auf 127.0.0.1, ist also nur von diesem Rechner aus erreichbar.
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

from . import auswertung, daten, kalibrierung, modelle, pipeline
from .review import SEITE as REVIEW_SEITE
from .review import ReviewSitzung

APP_SEITE = Path(__file__).parent / "app.html"
ANBIETER = ("anthropic", "openai", "google", "test")
DOWNLOADS = {"report.html", "report.md", "review_ergebnis.csv", "review_queue.csv"}


class Job:
    """Ein laufender Start eines Laufs. Es läuft immer höchstens einer gleichzeitig."""

    def __init__(self, name):
        self.name = name
        self.log = collections.deque(maxlen=300)
        self.fortschritt = ""
        self.laeuft = True
        self.ergebnis = None


_job = None
_job_sperre = threading.Lock()
_sitzungen = {}


def _melde(text):
    print(text, flush=True)
    job = _job
    if job is None:
        return
    if re.match(r"^(Antworten|Judges): \d+/\d+$", text):
        job.fortschritt = text
    else:
        job.log.append(text)


daten.melde = _melde


def _im_hintergrund(name, vorbereiten, arbeit):
    """Startet arbeit() in einem eigenen Thread. vorbereiten() läuft vorher und darf abbrechen.
    name darf eine Funktion sein, wenn der Name erst nach vorbereiten() feststeht."""
    global _job
    with _job_sperre:
        if _job and _job.laeuft:
            raise pipeline.LaufFehler(f"Es läuft gerade schon etwas ({_job.name}). Bitte warten, bis es fertig ist.")
        vorbereiten()
        name = name() if callable(name) else name
        _job = Job(name)
    job = _job

    def ausfuehren():
        try:
            job.ergebnis = "fertig" if arbeit() else "unvollstaendig"
        except Exception as e:
            job.log.append(f"FEHLER: {type(e).__name__}: {e}")
            traceback.print_exc()
            job.ergebnis = "fehler"
        finally:
            job.fortschritt = ""
            job.laeuft = False
            _sitzungen.pop(name, None)  # Review-Liste kann neu sein

    threading.Thread(target=ausfuehren, daemon=True).start()


def _starte_lauf(name):
    geladen = {}

    def vorbereiten():
        geladen["lauf"] = pipeline.lade_lauf(name, warnen=False)

    def arbeit():
        pipeline.lade_lauf(name)  # gibt Warnungen ins Protokoll
        return pipeline.start(*geladen["lauf"])

    _im_hintergrund(name, vorbereiten, arbeit)


def _starte_kalibrierung(name=None, test=False):
    ziel = {}

    def vorbereiten():
        ziel["ordner"] = kalibrierung.lade(name)[0] if name else kalibrierung.neu(test=test)
        ziel["name"] = "kalibrierung:" + ziel["ordner"].name

    def arbeit():
        return kalibrierung.start(ziel["ordner"], kalibrierung.lade(ziel["ordner"].name)[1])

    _im_hintergrund(lambda: ziel["name"], vorbereiten, arbeit)
    return ziel["ordner"].name


def _status():
    config = daten.lade_config()
    anzahl, probleme = pipeline.pruefe()
    laeufe = []
    for name in pipeline.alle_laeufe():
        try:
            k = pipeline.kennzahlen(pipeline.LAUFORDNER / name)
        except Exception as e:
            k = {"fehler": str(e)}
        laeufe.append({"name": name, **k})
    kalibrierungen = []
    for name in kalibrierung.alle():
        try:
            k = kalibrierung.stand(kalibrierung.ORDNER / name)
        except Exception as e:
            k = {"fehler": str(e)}
        kalibrierungen.append({"name": name, **k})
    return {
        "config": config,
        "schluessel": {a: bool(_hat_schluessel(a)) for a in ("anthropic", "openai", "google")},
        "testfaelle": anzahl,
        "testfall_probleme": probleme,
        "laeufe": laeufe,
        "kalibrierungen": kalibrierungen,
        "kalibrierung_antworten": len(kalibrierung.lade_antworten()),
        "job": _job_info(),
    }


def _hat_schluessel(anbieter):
    try:
        return modelle.schluessel(anbieter)
    except modelle.ApiFehler:
        return None


def _job_info():
    if not _job:
        return None
    return {"name": _job.name, "laeuft": _job.laeuft, "fortschritt": _job.fortschritt,
            "log": list(_job.log), "ergebnis": _job.ergebnis}


def _speichere_schluessel(eingabe):
    zeilen = modelle.ENV_DATEI.read_text(encoding="utf-8").splitlines() if modelle.ENV_DATEI.exists() else []
    for anbieter, name in modelle.SCHLUESSEL.items():
        wert = (eingabe.get(anbieter) or "").strip()
        if not wert:
            continue
        if not re.fullmatch(r"[\x21-\x7e]+", wert):
            raise ValueError(f"Der Schlüssel für {anbieter} enthält ungültige Zeichen.")
        zeilen = [z for z in zeilen if not z.strip().startswith(name + "=")]
        zeilen.append(f"{name}={wert}")
    modelle.ENV_DATEI.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    modelle.lade_env()


def _speichere_config(eingabe):
    config = daten.lade_config()

    def ziel(z):
        if z.get("anbieter") not in ANBIETER or not str(z.get("modell", "")).strip():
            raise ValueError("Jedes Modell braucht einen Anbieter und einen Modellnamen.")
        aus = {"anbieter": z["anbieter"], "modell": str(z["modell"]).strip()}
        if z.get("effort"):
            aus["effort"] = str(z["effort"])
        return aus

    testobjekte = [ziel(z) for z in eingabe.get("testobjekte", []) if str(z.get("modell", "")).strip()]
    if not testobjekte:
        raise ValueError("Mindestens ein Testobjekt angeben.")
    config["testobjekte"] = testobjekte
    config["judges"] = {j: ziel(eingabe["judges"][j]) for j in ("zahlen", "rechenweg", "plausibilitaet")}
    wdh = int(eingabe.get("wiederholungen", 1))
    anteil = float(eingabe["stichprobe"]["anteil"])
    minimum = int(eingabe["stichprobe"]["minimum"])
    if not (1 <= wdh <= 10 and 0 <= anteil <= 1 and minimum >= 0):
        raise ValueError("Wiederholungen 1–10, Stichprobenanteil 0–1, Minimum ab 0.")
    config["wiederholungen"] = wdh
    config["stichprobe"].update({"anteil": anteil, "minimum": minimum})
    (daten.BASIS / "config" / "lauf.json").write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n",
                                                      encoding="utf-8")


def _protokoll(ordner, ab):
    """Einträge ab Nummer `ab` (für Live-Nachladen) und eine Summe über alle."""
    alle = daten.lies_jsonl(ordner / daten.PROTOKOLL)
    anfragen = [e for e in alle if e.get("schritt")]
    summe = {
        "anfragen": len(anfragen),
        "fehler": sum(1 for e in anfragen if e["art"] == "fehler"),
        "wiederholt": sum(1 for e in anfragen if (e.get("versuche") or 1) > 1),
        "tokens_rein": sum(e.get("tokens_rein") or 0 for e in anfragen),
        "tokens_raus": sum(e.get("tokens_raus") or 0 for e in anfragen),
        "dauer_s": round(sum(e.get("dauer_s") or 0 for e in anfragen), 1),
    }
    return {"gesamt": len(alle), "eintraege": alle[ab:], "summe": summe}


def _sitzung(name):
    if name not in _sitzungen:
        ordner, _, testfaelle = pipeline.lade_lauf(name, warnen=False)
        _sitzungen[name] = ReviewSitzung(ordner, testfaelle)
    return _sitzungen[name]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _sende(self, code, inhalt, typ="application/json; charset=utf-8", extra=None):
        if isinstance(inhalt, (dict, list)):
            inhalt = json.dumps(inhalt, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(inhalt)

    def _fehler(self, code, text):
        self._sende(code, {"fehler": text})

    def _erlaubt(self):
        # Schutz davor, dass eine fremde Webseite im Browser Anfragen an diesen Server schickt
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self._erlaubt():
            return self._fehler(403, "Nur lokal erreichbar.")
        pfad = unquote(urlparse(self.path).path)
        try:
            if pfad == "/":
                return self._sende(200, APP_SEITE.read_bytes(), "text/html; charset=utf-8")
            if pfad == "/api/status":
                return self._sende(200, _status())
            m = re.fullmatch(r"/api/(laeufe|kalibrierungen)/([\w.-]+)/protokoll", pfad)
            if m:
                ordner = (pipeline.lade_lauf(m.group(2), warnen=False)[0] if m.group(1) == "laeufe"
                          else kalibrierung.lade(m.group(2))[0])
                ab = int((parse_qs(urlparse(self.path).query).get("ab") or ["0"])[0])
                return self._sende(200, _protokoll(ordner, max(0, ab)))
            m = re.fullmatch(r"/review/([\w.-]+)/", pfad)
            if m:
                return self._sende(200, REVIEW_SEITE.read_bytes(), "text/html; charset=utf-8")
            m = re.fullmatch(r"/review/([\w.-]+)/api/faelle", pfad)
            if m:
                return self._sende(200, _sitzung(m.group(1)).daten())
            m = re.fullmatch(r"/kalibrierungen/([\w.-]+)/kalibrierung\.html", pfad)
            if m:
                datei = kalibrierung.lade(m.group(1))[0] / "kalibrierung.html"
                if not datei.exists():
                    return self._fehler(404, "Ergebnis gibt es noch nicht.")
                return self._sende(200, datei.read_bytes(), "text/html; charset=utf-8")
            m = re.fullmatch(r"/laeufe/([\w.-]+)/([\w.-]+)", pfad)
            if m and m.group(2) in DOWNLOADS:
                ordner = pipeline.lade_lauf(m.group(1), warnen=False)[0]
                datei = ordner / m.group(2)
                if not datei.exists():
                    return self._fehler(404, "Datei gibt es noch nicht.")
                typ = "text/html; charset=utf-8" if datei.suffix == ".html" else "text/plain; charset=utf-8"
                extra = {} if datei.suffix == ".html" else {
                    "Content-Disposition": f'attachment; filename="{m.group(1)}_{m.group(2)}"'}
                return self._sende(200, datei.read_bytes(), typ, extra)
            self._fehler(404, "Nicht gefunden.")
        except (pipeline.LaufFehler, kalibrierung.KalibrierungsFehler, FileNotFoundError, ValueError) as e:
            self._fehler(404, str(e))

    def do_POST(self):
        # Eigener Header erzwingt bei fremden Seiten einen CORS-Preflight, den dieser Server nie erlaubt
        if not self._erlaubt() or self.headers.get("X-Figures-In-Context") != "1":
            return self._fehler(403, "Nur aus der Oberfläche von Figures in Context erlaubt.")
        pfad = unquote(urlparse(self.path).path)
        laenge = int(self.headers.get("Content-Length", 0))
        try:
            eingabe = json.loads(self.rfile.read(laenge) or b"{}")
        except ValueError:
            return self._fehler(400, "Ungültige Anfrage.")
        try:
            if pfad == "/api/laeufe":
                ordner = pipeline.neu(str(eingabe.get("name", "")), test=bool(eingabe.get("test")))
                return self._sende(200, {"name": ordner.name})
            m = re.fullmatch(r"/api/laeufe/([\w.-]+)/start", pfad)
            if m:
                _starte_lauf(m.group(1))
                return self._sende(200, {"ok": True})
            if pfad == "/api/kalibrierung":
                name = _starte_kalibrierung(eingabe.get("name"), test=bool(eingabe.get("test")))
                return self._sende(200, {"name": name})
            m = re.fullmatch(r"/api/laeufe/([\w.-]+)/auswertung", pfad)
            if m:
                ordner, config, testfaelle = pipeline.lade_lauf(m.group(1), warnen=False)
                auswertung.lauf(ordner, config, testfaelle)
                return self._sende(200, {"ok": True})
            m = re.fullmatch(r"/review/([\w.-]+)/api/speichern", pfad)
            if m:
                _sitzung(m.group(1)).speichern(eingabe)
                return self._sende(200, {"ok": True})
            if pfad == "/api/schluessel":
                _speichere_schluessel(eingabe)
                return self._sende(200, {"ok": True})
            if pfad == "/api/config":
                _speichere_config(eingabe)
                return self._sende(200, {"ok": True})
            self._fehler(404, "Nicht gefunden.")
        except (pipeline.LaufFehler, kalibrierung.KalibrierungsFehler, ValueError, KeyError, TypeError,
                FileNotFoundError) as e:
            self._fehler(400, str(e))


def starte(port=8765, browser=True):
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:
        raise SystemExit(f"Port {port} ist belegt. Läuft die App schon? Sonst: python -m figures_in_context app 8766")
    url = f"http://127.0.0.1:{port}/"
    print(f"Figures in Context läuft: {url}")
    print("Dieses Fenster offen lassen. Beenden mit Strg+C.")
    if browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        server.server_close()
