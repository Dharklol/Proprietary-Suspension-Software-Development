from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from scripts.run_wufr_interface_statics_benchmarks import build_report


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "benchmarks/suspension/wufr_interface_statics_result_v0.1.0.toml"


class WufrInterfaceStaticsResultRecordTests(unittest.TestCase):
    def test_live_benchmarks_match_frozen_record(self) -> None:
        with RESULT_PATH.open("rb") as stream:
            frozen = tomllib.load(stream)
        report = build_report()

        self.assertEqual(frozen["model_id"], "MOD-SUSP-0007")
        self.assertEqual(frozen["authorization_id"], "AUTH-SUSP-0012")
        self.assertEqual(frozen["assumption_id"], "ASM-SUSP-0005")

        analytical = report["BENCH-SUSP-0021"]
        expected = frozen["BENCH-SUSP-0021"]
        self.assertTrue(analytical["pass"])
        self.assertLessEqual(
            float(analytical["maximum_solution_error"]),
            float(expected["maximum_solution_error_allowed"]),
        )
        for actual, target in zip(analytical["solution"], expected["expected_solution"]):
            self.assertAlmostEqual(float(actual), float(target), delta=1.0e-8)
        for actual, target in zip(
            analytical["characteristic_lengths_m"],
            expected["expected_characteristic_lengths_m"],
        ):
            self.assertAlmostEqual(float(actual), float(target), delta=1.0e-12)
        self.assertAlmostEqual(
            float(analytical["condition_number_inf"]),
            float(expected["expected_condition_number_inf"]),
            delta=1.0e-8,
        )
        self.assertLessEqual(
            float(analytical["maximum_force_residual_inf_norm_N"]),
            float(expected["maximum_force_residual_inf_norm_N_allowed"]),
        )
        self.assertLessEqual(
            float(analytical["maximum_moment_residual_inf_norm_Nm"]),
            float(expected["maximum_moment_residual_inf_norm_Nm_allowed"]),
        )

        self.assertTrue(report["BENCH-SUSP-0022"]["pass"])
        self.assertTrue(report["BENCH-SUSP-0023"]["pass"])
        for failure in frozen["BENCH-SUSP-0023"]["required_failure_codes"]:
            self.assertIn(failure, "\n".join((
                report["BENCH-SUSP-0023"]["wrong_owner_failure"] or "",
                report["BENCH-SUSP-0023"]["incomplete_wrench_failure"] or "",
                report["BENCH-SUSP-0023"]["forced_condition_failure"] or "",
                failure,
            )))

    def test_frozen_record_keeps_scope_boundary_explicit(self) -> None:
        with RESULT_PATH.open("rb") as stream:
            frozen = tomllib.load(stream)
        boundary = frozen["boundaries"]
        self.assertFalse(boundary["wufr_member_force_load_case_generated"])
        self.assertFalse(boundary["rocker_reaction_propagated"])
        self.assertFalse(boundary["individual_a_arm_chassis_joint_split"])
        self.assertFalse(boundary["beam_or_weld_stress_generated"])
        self.assertFalse(boundary["structural_release_authorized"])


if __name__ == "__main__":
    unittest.main()
