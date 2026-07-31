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
    def test_catalog_freezes_exact_identity_and_partial_gate_progress(self) -> None:
        with (ROOT / "data_catalog/r25b_runtime_source_activation_v0.toml").open("rb") as stream:
            record = tomllib.load(stream)

        source = record["source_binary"]
        self.assertEqual(source["file_id"], "1890914118742")
        self.assertEqual(source["file_version_id"], "2085674725942")
        self.assertEqual(source["name"], EXPECTED_NAME)
        self.assertEqual(source["size_bytes"], EXPECTED_SIZE_BYTES)
        self.assertEqual(source["sha1"], EXPECTED_SHA1)

        gate = record["activation_gate"]
        for key in (
            "source_binary_identity_verified",
            "supporting_artifact_hashes_verified",
            "source_binary_structure_audited",
            "reference_prepeak_export_complete",
            "reference_prepeak_exchange_frozen",
            "representative_curve_cross_checks_complete",
        ):
            self.assertTrue(gate[key], key)
        for key in (
            "source_binary_bytes_present_in_repository",
            "full_signed_curve_exchange_frozen",
            "source_profile_generation_match_confirmed",
            "source_to_canonical_adapter_reviewed",
            "source_specific_runtime_activation_authorized",
        ):
            self.assertFalse(gate[key], key)

        observed = record["observed_binary_structure"]
        self.assertEqual(observed["total_rows"], 9630)
        self.assertEqual(observed["state_count"], 60)
        self.assertEqual(observed["normal_load_values_n"], [222.0, 445.0, 667.0, 890.0, 1112.0])
        self.assertEqual(observed["pressure_values_kpa"], [55.2, 68.9, 82.7, 96.5])
        self.assertFalse(record["frozen_generator_description"]["matches_observed_binary"])

    def test_quarantined_reference_export_is_exact_and_not_authorized(self) -> None:
        path = ROOT / "benchmarks/tires/WUFR26_H43105_R25B_QUARANTINED_REFERENCE_EXPORT_V0.toml"
        with path.open("rb") as stream:
            record = tomllib.load(stream)

        self.assertFalse(record["runtime_authorized"])
        self.assertEqual(record["source_sha1"], EXPECTED_SHA1)
        self.assertEqual(len(record["branches"]), 2)
        inside, outside = record["branches"]
        self.assertEqual(inside["prepeak_rows"], 64)
        self.assertEqual(outside["prepeak_rows"], 86)
        self.assertEqual(len(inside["slip_angle_magnitude_deg"]), 64)
        self.assertEqual(len(outside["slip_angle_magnitude_deg"]), 86)
        self.assertAlmostEqual(inside["source_peak_lateral_force_n"], 694.041896190421)
        self.assertAlmostEqual(outside["source_peak_lateral_force_n"], 2737.8937842052433)
        for branch in record["branches"]:
            slip = branch["slip_angle_magnitude_deg"]
            force = branch["lateral_force_magnitude_n"]
            self.assertEqual(len(slip), len(force))
            self.assertTrue(all(right > left for left, right in zip(slip, slip[1:])))
            self.assertTrue(all(right > left for left, right in zip(force, force[1:])))

        expected_sha256 = "af59ab4a1962c859f269c0374032855df17895a80991d8412da38f1b740c82f1"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected_sha256)

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
