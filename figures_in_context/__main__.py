"""Figures in Context von der Kommandozeile.

    python -m figures_in_context app                       Web-App im Browser (empfohlen, alles an einem Ort)

    python -m figures_in_context pruefe                    Testfälle gegen die Dokumente prüfen
    python -m figures_in_context neu pilot [--test]        neuen Lauf anlegen (--test: Testmodelle, keine Kosten)
    python -m figures_in_context start <lauf>              Stufen 1–4: Antworten, Check, Judges, Weiterleitung
    python -m figures_in_context review <lauf>             Stufe 5: nur die Review-Oberfläche im Browser
    python -m figures_in_context auswertung <lauf>         Stufe 6, nach dem Review
    python -m figures_in_context kalibrierung [--test]     Finden die Judges eingebaute Fehler? (vor dem ersten echten Lauf)

Einzelne Stufen: antworten, check, judges, weiterleitung <lauf>.
<lauf> ist der Ordnername unter laeufe/ (z. B. 2026-10-20_pilot).
"""

import sys

from . import antworten, auswertung, check, judges, pipeline, review, weiterleitung


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "hilfe"):
        print(__doc__)
        return
    befehl, rest = argv[0], argv[1:]
    try:
        if befehl == "app":
            from . import app
            app.starte(port=int(rest[0]) if rest else 8765)
            return
        if befehl == "pruefe":
            anzahl, probleme = pipeline.pruefe()
            for p in probleme:
                print(p)
            print(f"{anzahl} Testfälle geprüft, {len(probleme)} Probleme.")
            sys.exit(1 if probleme else 0)
        if befehl == "kalibrierung":
            from . import kalibrierung
            ordner = kalibrierung.neu(test="--test" in rest)
            ok = kalibrierung.start(ordner, kalibrierung.lade(ordner.name)[1])
            if ok:
                print(f"Ergebnis: {ordner / 'kalibrierung.html'}")
            else:
                print(f"Weiter mit: python -m figures_in_context kalibrierung-weiter {ordner.name}")
            return
        if befehl == "kalibrierung-weiter":
            from . import kalibrierung
            ordner, config = kalibrierung.lade(rest[0] if rest else "")
            kalibrierung.start(ordner, config)
            return
        if befehl == "neu":
            if not rest:
                sys.exit("Name fehlt, z. B. `python -m figures_in_context neu pilot`")
            ordner = pipeline.neu(rest[0], test="--test" in rest)
            print(f"Lauf angelegt: {ordner}")
            print(f"Weiter mit: python -m figures_in_context start {ordner.name}")
            return
        if not rest:
            sys.exit(f"Lauf fehlt, z. B. `python -m figures_in_context {befehl} 2026-10-20_pilot`")
        ordner, config, testfaelle = pipeline.lade_lauf(rest[0])
    except pipeline.LaufFehler as e:
        sys.exit(str(e))

    if befehl == "start":
        pipeline.start(ordner, config, testfaelle)
    elif befehl == "antworten":
        antworten.lauf(ordner, config, testfaelle)
    elif befehl == "check":
        check.lauf(ordner, testfaelle)
    elif befehl == "judges":
        judges.lauf(ordner, config, testfaelle)
    elif befehl == "weiterleitung":
        weiterleitung.lauf(ordner, config, testfaelle)
    elif befehl == "review":
        review.starte(ordner, testfaelle)
    elif befehl == "auswertung":
        auswertung.lauf(ordner, config, testfaelle)
    else:
        sys.exit(f"Unbekannter Befehl: {befehl}\n{__doc__}")


if __name__ == "__main__":
    main(sys.argv[1:])
