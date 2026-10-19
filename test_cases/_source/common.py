"""Shared helpers for the batch scripts."""
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction as F


def is_terminating(x: F) -> bool:
    d = x.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    return d == 1


def solution(x: F, unit: str, decimals):
    """decimals=None: the result terminates and is required exactly.
    decimals=n: the result repeats and is rounded half up to n decimal places."""
    if decimals is None:
        assert is_terminating(x), "a repeating result needs decimal places"
        value = Decimal(x.numerator) / Decimal(x.denominator)
        return {"value": format(value.normalize(), "f"), "unit": unit, "decimals": None, "exact": True}
    assert not is_terminating(x), "a terminating result is required exactly, not rounded"
    q = Decimal(1).scaleb(-decimals)
    value = (Decimal(x.numerator) / Decimal(x.denominator)).quantize(q, ROUND_HALF_UP)
    return {"value": str(value), "unit": unit, "decimals": decimals, "exact": False}
