"""Gemeinsame Hilfsfunktionen fuer die Charge-Skripte."""
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction as F


def ist_endlich(x: F) -> bool:
    d = x.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    return d == 1


def loesung(x: F, einheit: str, stellen: int | None):
    """stellen=None: Ergebnis ist endlich und wird exakt verlangt.
    stellen=n: Ergebnis ist periodisch, kaufmaennisch auf n Stellen gerundet."""
    if stellen is None:
        assert ist_endlich(x), "periodisches Ergebnis braucht Nachkommastellen"
        wert = Decimal(x.numerator) / Decimal(x.denominator)
        return {"wert": format(wert.normalize(), "f"), "einheit": einheit, "nachkommastellen": None, "exakt": True}
    assert not ist_endlich(x), "endliches Ergebnis wird exakt verlangt, nicht gerundet"
    q = Decimal(1).scaleb(-stellen)
    wert = (Decimal(x.numerator) / Decimal(x.denominator)).quantize(q, ROUND_HALF_UP)
    return {"wert": str(wert), "einheit": einheit, "nachkommastellen": stellen, "exakt": False}
