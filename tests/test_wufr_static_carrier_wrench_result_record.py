from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import tomllib
import unittest

from scripts.run_wufr_static_carrier_wrench_benchmarks import build_report


ROOT = Path(__file__).resolve().parents[1]
FULL_RESULT = ROOT / "benchmarks/vehicle/wufr_static_carrier_wrench_result_v0.1.0.json"
SUMMARY_RECORD = ROOT / "benchmarks/vehicle/wufr_static_carrier_wrench_result_v0.1.0.toml"


def _compare(expected, actual, path: str = "$") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or expected.keys() != actual.keys():
            raise AssertionError(f"{path}: object keys differ")
        for key in expected:
            _compare(expected[key], actual[key], f"{path}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise AssertionError(f"{path}: list shape differs")
        for index, (left, right) in enumerate(zip(expected, actual)):
            _compare(left, right, f"{path}[{index}]")
        return
    if (
        isinstance(expected, (int, float))
        and not isinstance(expected, bool)
        and isinstance(actual, (int, float))
        and not isinstance(actual, bool)
    ):
        if not math.isclose(float(expected), float(actual), rel_tol=1.0e-12, abs_tol=1.0e-12):
            raise AssertionError(f"{path}: {expected!r} != {actual!r}")
        return
    if expected != actual:
        raise AssertionError(f"{path}: {expected!r} != {actual!r}")


class WufrStaticCarrierWrenchResultRecordTests(unittest.TestCase):
    def test_live_report_matches_frozen_full_result(self) -> None:
        frozen = json.loads(FULL_RESULT.read_text(encoding="utf-8"))
        generated = build_report()
        _compare(frozen, generated)

    def test_summary_hash_and_acceptance_gates_are_frozen(self) -> None:
        report = json.loads(FULL_RESULT.read_text(encoding="utf-8"))
        with SUMMARY_RECORD.open("rb") as stream:
            summary = tomllib.load(stream)

        self.assertEqual(
            hashlib.sha256(FULL_RESULT.read_bytes()).hexdigest(),
            summary["full_result_sha256"],
        )
        self.assertEqual(report["version"], "0.1.0")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["authorization_id"], "AUTH-VEH-0011")
        self.assertEqual(report["model_id"], "MOD-VEH-0008")
        self.assertEqual(
            report["result_label"],
            "uncorrelated_design_intent_static_carrier_wrench",
        )
        self.assertEqual(
            [corner["corner_id"] for corner in report["corners"]],
            ["front_left", "front_right", "rear_left", "rear_right"],
        )
        self.assertTrue(report["BENCH-VEH-0015"]["pass"])
        self.assertTrue(report["BENCH-VEH-0016"]["pass"])
        self.assertTrue(report["BENCH-VEH-0017"]["pass"])
        self.assertLessEqual(
            report["reconstruction"]["maximum_force_residual_N"],
            1.0e-6,
        )
        self.assertLessEqual(
            report["reconstruction"]["maximum_moment_residual_Nm"],
            1.0e-6,
        )
        self.assertLessEqual(
            report["reconstruction"]["accepted_force_match_residual_N"],
            1.0e-10,
        )
        self.assertLessEqual(
            report["reconstruction"]["accepted_moment_match_residual_Nm"],
            1.0e-10,
        )

    def test_frozen_record_keeps_completeness_boundary_explicit(self) -> None:
        report = json.loads(FULL_RESULT.read_text(encoding="utf-8"))
        boundary = report["boundaries"]
        self.assertTrue(boundary["complete_for_authorized_static_gravity_case"])
        for key in (
            "complete_physical_hardware_wrench",
            "maneuver_complete",
            "installed_as_built_authority",
            "integrated_level1_linkage_result_authority",
            "historical_scale_reconstruction_used",
            "hidden_balancing_wrench_used",
            "structural_load_case_authority",
            "rocker_reaction_authority",
        ):
            self.assertFalse(boundary[key], key)

        for corner in report["corners"]:
            self.assertTrue(corner["complete_for_authorized_static_gravity_case"])
            self.assertFalse(corner["complete_physical_hardware_wrench"])
            self.assertFalse(corner["maneuver_complete"])
            self.assertFalse(corner["installed_as_built_authority"])
            self.assertTrue(corner["level1_wrench"]["complete"])
            self.assertEqual(len(corner["road_resultant"]["contributions"]), 2)


if __name__ == "__main__":
    unittest.main()
