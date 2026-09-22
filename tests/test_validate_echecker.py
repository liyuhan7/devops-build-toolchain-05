import unittest

from scripts.validate import validate_echecker_semantics


class ECheckerSemanticsTests(unittest.TestCase):
    def test_echecker_examples_and_negative_cases_are_valid(self):
        errors = validate_echecker_semantics()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
