from pathlib import Path
import unittest

from pssd_registry import validate_repository


class RegistryValidationTests(unittest.TestCase):
    def test_repository_records_are_structurally_valid(self) -> None:
        root = Path(__file__).resolve().parents[1]
        issues = validate_repository(root)
        self.assertEqual([], issues, "\n".join(str(issue) for issue in issues))


if __name__ == "__main__":
    unittest.main()
