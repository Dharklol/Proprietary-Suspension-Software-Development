from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import tomllib
import unittest

from scripts.verify_r25b_runtime_source import (
    EXPECTED_NAME,
    EXPECTED_SHA1,
    EXPECTED_SIZE_BYTES,
    sha1_file,
    verify_source,
)

ROOT = Path(__file__).resolve().parents[1]


class R25bRuntimeSourceActivationPreflightTests(unittest.TestCase):
    def test_catalog_freezes_exact_box_identity_and_blocked_gate(self) -> None:
        with (ROOT / "data_catalog/r25b_runtime_source_activation_v0.toml").open("rb") as stream:
            record = tomllib.load(stream)

        source = record["source_binary"]
        self.assertEqual(source["file_id"], "1890914118742")
        self.assertEqual(source["file_version_id"], "2085674725942")
        self.assertEqual(source["name"], EXPECTED_NAME)
        self.assertEqual(source["size_bytes"], EXPECTED_SIZE_BYTES)
        self.assertEqual(source["sha1"], EXPECTED_SHA1)

        gate = record["activation_gate"]
        self.assertTrue(all(value is False for value in gate.values()))

    def test_sha1_helper_reads_binary_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.bin"
            path.write_bytes(b"r25b-preflight")
            expected = hashlib.sha1(b"r25b-preflight", usedforsecurity=False).hexdigest()
            self.assertEqual(sha1_file(path), expected)

    def test_verifier_fails_closed_for_missing_or_wrong_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            with self.assertRaises(SystemExit):
                verify_source(directory_path / EXPECTED_NAME)

            wrong_name = directory_path / "wrong.mat"
            wrong_name.write_bytes(b"x" * EXPECTED_SIZE_BYTES)
            with self.assertRaises(SystemExit):
                verify_source(wrong_name)

            wrong_size = directory_path / EXPECTED_NAME
            wrong_size.write_bytes(b"short")
            with self.assertRaises(SystemExit):
                verify_source(wrong_size)


if __name__ == "__main__":
    unittest.main()
