from __future__ import annotations

import json
import math
from pathlib import Path
import tempfile
import tomllib
import unittest

from scripts.run_wufr_static_rocker_included_load_benchmarks import build_report, summary_toml

ROOT = Path(__file__).resolve().parents[1]
JSON_RECORD = ROOT / "benchmarks/suspension/wufr_static_rocker_included_loads_result_v0.1.0.json"
TOML_RECORD = ROOT / "benchmarks/suspension/wufr_static_rocker_included_loads_result_v0.1.0.toml"


def _assert_nested_close(test: unittest.TestCase, actual, expected, path: str = "root") -> None:
    test.assertEqual(type(actual), type(expected), f"{path}: type mismatch")
    if isinstance(expected, dict):
        test.assertEqual(set(actual), set(expected), f"{path}: key mismatch")
        for key in expected:
            _assert_nested_close(test, actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        test.assertEqual(len(actual), len(expected), f"{path}: length mismatch")
        for index, (a, e) in enumerate(zip(actual, expected)):
            _assert_nested_close(test, a, e, f"{path}[{index}]")
    elif isinstance(expected, float):
        test.assertTrue(
            math.isclose(actual, expected, rel_tol=1.0e-12, abs_tol=1.0e-12),
            f"{path}: {actual!r} != {expected!r}",
        )
    else:
        test.assertEqual(actual, expected, f"{path}: value mismatch")


class WufrStaticRockerResultRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frozen_json = json.loads(JSON_RECORD.read_text(encoding="utf-8"))
        with TOML_RECORD.open("rb") as stream:
            cls.frozen_toml = tomllib.load(stream)
        cls.regenerated = build_report()

    def test_frozen_json_matches_regeneration(self) -> None:
        _assert_nested_close(self, self.regenerated, self.frozen_json)

    def test_summary_record_matches_regeneration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.toml"
            path.write_text(summary_toml(self.regenerated), encoding="utf-8")
            with path.open("rb") as stream:
                regenerated_summary = tomllib.load(stream)
        _assert_nested_close(self, regenerated_summary, self.frozen_toml)

    def test_frozen_result_retains_exact_incomplete_boundary(self) -> None:
        self.assertEqual(
            self.frozen_json["result_label"],
            "uncorrelated_design_intent_static_rocker_included_loads",
        )
        self.assertEqual(
            self.frozen_json["corner_order"],
            ["front_left", "front_right", "rear_left", "rear_right"],
        )
        boundaries = self.frozen_json["boundaries"]
        self.assertTrue(boundaries["complete_for_named_included_load_set"])
        for key in (
            "complete_hardware_reaction",
            "complete_rocker_equilibrium",
            "actual_damper_force_applied",
            "structural_release_authority",
            "installed_as_built_authority",
            "production_authority",
        ):
            self.assertFalse(boundaries[key])
        for corner in self.frozen_json["corners"]:
            included = corner["included"]
            self.assertEqual(
                included["included_load_ids"],
                ["push_pull", "conservative_spring", "physical_arb_link"],
            )
            self.assertEqual(
                included["missing_load_ids"],
                ["KW_V5_non_spring_static_force"],
            )
            self.assertFalse(included["complete_hardware_reaction"])
            influence = corner["damper_unit_influence"]
            self.assertEqual(influence["unit_force_N"], 1.0)
            self.assertFalse(influence["actual_force_magnitude_assumed"])
            self.assertFalse(influence["actual_force_authorized"])

    def test_frozen_benchmark_gates_pass(self) -> None:
        for benchmark_id in ("BENCH-SUSP-0032", "BENCH-SUSP-0033", "BENCH-SUSP-0034"):
            self.assertTrue(self.frozen_json[benchmark_id]["pass"])
        collection = self.frozen_json["collection"]
        self.assertLessEqual(collection["maximum_force_residual_N"], 1.0e-10)
        self.assertLessEqual(collection["maximum_perpendicular_moment_residual_Nm"], 1.0e-10)
        self.assertLessEqual(collection["maximum_support_axis_moment_component_Nm"], 1.0e-10)


if __name__ == "__main__":
    unittest.main()
