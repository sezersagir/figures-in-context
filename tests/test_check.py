"""Tests for the Python check. Run: python -m unittest discover tests"""

import unittest
from decimal import Decimal

from figures_in_context.check import compare, read_result

EXACT = {"value": "32334339.375", "unit": "GBP", "decimals": None, "exact": True}
ROUNDED = {"value": "7.29", "unit": "%", "decimals": 2, "exact": False}


class ReadResult(unittest.TestCase):
    def test_normal_case(self):
        self.assertEqual(read_result("Working...\nRESULT: 5614779.00 EUR"), (Decimal("5614779.00"), "EUR", None))

    def test_thousands_separator_and_symbol(self):
        self.assertEqual(read_result("RESULT: €5,614,779"), (Decimal("5614779"), "EUR", None))

    def test_percent_without_space(self):
        self.assertEqual(read_result("RESULT: 7.29%"), (Decimal("7.29"), "%", None))

    def test_markdown_bold(self):
        self.assertEqual(read_result("**RESULT: 130522.25 GBP**")[0], Decimal("130522.25"))

    def test_negative(self):
        self.assertEqual(read_result("RESULT: -887000000 EUR")[0], Decimal("-887000000"))

    def test_format_errors(self):
        self.assertEqual(read_result("no result here")[2], "no RESULT line")
        self.assertEqual(read_result("RESULT: 1 EUR\nRESULT: 2 EUR")[2], "more than one RESULT line")
        self.assertEqual(read_result("RESULT: 5.6 million EUR")[2], "number word in the RESULT line")
        self.assertEqual(read_result("RESULT: 5.6bn EUR")[2], "number word in the RESULT line")
        self.assertEqual(read_result("RESULT: 5614779")[2], "unit missing")
        self.assertEqual(read_result("RESULT: about five EUR")[2], "number not readable")
        self.assertEqual(read_result("RESULT: 1,5 EUR")[2], "number not readable")


class Compare(unittest.TestCase):
    def test_exact(self):
        self.assertTrue(compare(Decimal("32334339.375"), "GBP", EXACT))
        self.assertTrue(compare(Decimal("32334339.3750"), "GBP", EXACT))
        self.assertFalse(compare(Decimal("32334339.38"), "GBP", EXACT))

    def test_rounded(self):
        self.assertTrue(compare(Decimal("7.2914"), "%", ROUNDED))
        self.assertTrue(compare(Decimal("7.29"), "%", ROUNDED))
        self.assertFalse(compare(Decimal("7.3"), "%", ROUNDED))

    def test_round_half_up(self):
        reference = {"value": "0.13", "unit": "%", "decimals": 2, "exact": False}
        self.assertTrue(compare(Decimal("0.125"), "%", reference))

    def test_wrong_unit(self):
        self.assertFalse(compare(Decimal("32334339.375"), "EUR", EXACT))


if __name__ == "__main__":
    unittest.main()
