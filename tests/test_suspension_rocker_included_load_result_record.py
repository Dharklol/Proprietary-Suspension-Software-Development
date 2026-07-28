from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from scripts.run_rocker_included_load_benchmarks import build_report


ROOT = Path(__file__).resolve().parents[1]


class RockerIncludedLoadResultRecordTests(unittest.TestCase):
    def test_committed_result_matches_live_report(self) -> None:
        with (ROOT / "benchmarks/suspension/rocker_included_load_result_v0.1.0.toml").open("rb") as stream:
            record = tomllib.load(stream)
        report = build_report()
        hand = record["hand_case"]
        self.assertEqual(report["status"], record["status"])
        self.assertEqual(report["complete_hardware_reaction"], record["complete_hardware_reaction"])
        for key in (
            "included_load_ids",
            "missing_load_ids",
            "included_resultant_force_N",
            "included_resultant_moment_Nm",
            "pivot_force_contribution_N",
            "pivot_moment_contribution_Nm",
            "final_force_residual_N",
            "final_moment_residual_Nm",
            "perpendicular_moment_residual_Nm",
        ):
            self.assertEqual(report[key], hand[key])
        for key in (
            "free_axis_moment_residual_Nm",
            "support_axis_moment_component_Nm",
            "force_residual_inf_norm_N",
            "perpendicular_moment_residual_inf_norm_Nm",
        ):
            self.assertAlmostEqual(report[key], hand[key], places=12)


if __name__ == "__main__":
    unittest.main()
