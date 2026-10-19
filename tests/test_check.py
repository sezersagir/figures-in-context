"""Tests für den Python-Check. Ausführen: python -m unittest discover tests"""

import unittest
from decimal import Decimal

from figures_in_context.check import lies_result, vergleiche

EXAKT = {"wert": "32334339.375", "einheit": "GBP", "nachkommastellen": None, "exakt": True}
GERUNDET = {"wert": "7.29", "einheit": "%", "nachkommastellen": 2, "exakt": False}


class LiesResult(unittest.TestCase):
    def test_normalfall(self):
        self.assertEqual(lies_result("Working...\nRESULT: 5614779.00 EUR"), (Decimal("5614779.00"), "EUR", None))

    def test_tausendertrenner_und_symbol(self):
        self.assertEqual(lies_result("RESULT: €5,614,779"), (Decimal("5614779"), "EUR", None))

    def test_prozent_ohne_leerzeichen(self):
        self.assertEqual(lies_result("RESULT: 7.29%"), (Decimal("7.29"), "%", None))

    def test_markdown_fett(self):
        self.assertEqual(lies_result("**RESULT: 130522.25 GBP**")[0], Decimal("130522.25"))

    def test_negativ(self):
        self.assertEqual(lies_result("RESULT: -887000000 EUR")[0], Decimal("-887000000"))

    def test_formatfehler(self):
        self.assertEqual(lies_result("no result here")[2], "keine RESULT-Zeile")
        self.assertEqual(lies_result("RESULT: 1 EUR\nRESULT: 2 EUR")[2], "mehr als eine RESULT-Zeile")
        self.assertEqual(lies_result("RESULT: 5.6 million EUR")[2], "Zahlwort in der RESULT-Zeile")
        self.assertEqual(lies_result("RESULT: 5.6bn EUR")[2], "Zahlwort in der RESULT-Zeile")
        self.assertEqual(lies_result("RESULT: 5614779")[2], "Einheit fehlt")
        self.assertEqual(lies_result("RESULT: about five EUR")[2], "Zahl nicht lesbar")
        self.assertEqual(lies_result("RESULT: 1,5 EUR")[2], "Zahl nicht lesbar")


class Vergleiche(unittest.TestCase):
    def test_exakt(self):
        self.assertTrue(vergleiche(Decimal("32334339.375"), "GBP", EXAKT))
        self.assertTrue(vergleiche(Decimal("32334339.3750"), "GBP", EXAKT))
        self.assertFalse(vergleiche(Decimal("32334339.38"), "GBP", EXAKT))

    def test_gerundet(self):
        self.assertTrue(vergleiche(Decimal("7.2914"), "%", GERUNDET))
        self.assertTrue(vergleiche(Decimal("7.29"), "%", GERUNDET))
        self.assertFalse(vergleiche(Decimal("7.3"), "%", GERUNDET))

    def test_kaufmaennisch(self):
        loesung = {"wert": "0.13", "einheit": "%", "nachkommastellen": 2, "exakt": False}
        self.assertTrue(vergleiche(Decimal("0.125"), "%", loesung))

    def test_falsche_einheit(self):
        self.assertFalse(vergleiche(Decimal("32334339.375"), "EUR", EXAKT))


if __name__ == "__main__":
    unittest.main()
