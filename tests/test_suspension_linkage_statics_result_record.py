from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from scripts.run_suspension_linkage_statics_benchmarks import build_report


ROOT = Path(__file__).resolve().parents[1]


class SuspensionLinkageStaticsResultRecordTests(unittest.TestCase):
    def test_frozen_result_matches_live_benchmarks(self) -> None:
        with (ROOT / "benchmarks/suspension/suspension_linkage_statics_result_v0.1.0.toml").open("rb") as stream:
            frozen = tomllib.load(stream)
        live = build_report()

        self.assertEqual(live["model_id"], frozen["model_id"])
        self.assertEqual(live["authorization_id"], frozen["authorization_id"])
        self.assertEqual(live["assumption_id"], frozen["assumption_id"])

        for benchmark_id in ("BENCH-SUSP-0018", "BENCH-SUSP-0019", "BENCH-SUSP-0020"):
            self.assertTrue(live[benchmark_id]["pass"])
            self.assertTrue(frozen[benchmark_id]["pass"])

        b18_live = live["BENCH-SUSP-0018"]
        b18_frozen = frozen["BENCH-SUSP-0018"]
        self.assertEqual(b18_live["link_order"], b18_frozen["link_order"])
        self.assertEqual(b18_live["target_axial_force_N"], b18_frozen["target_axial_force_N"])
        for actual, expected in zip(b18_live["solved_axial_force_N"], b18_frozen["solved_axial_force_N"]):
            self.assertAlmostEqual(actual, expected, places=12)
        self.assertAlmostEqual(b18_live["condition_number_inf"], b18_frozen["condition_number_inf"], places=12)
        self.assertLessEqual(b18_live["maximum_axial_force_error_N"], 1.0e-9)
        self.assertLessEqual(b18_live["force_residual_inf_norm_N"], 1.0e-9)
        self.assertLessEqual(b18_live["moment_residual_inf_norm_Nm"], 1.0e-9)

        b19_live = live["BENCH-SUSP-0019"]
        b19_frozen = frozen["BENCH-SUSP-0019"]
        self.assertLessEqual(b19_live["reference_point_max_force_difference_N"], 1.0e-9)
        self.assertLessEqual(b19_live["rigid_translation_max_force_difference_N"], 1.0e-9)
        self.assertAlmostEqual(
            b19_live["reference_point_condition_number_inf"],
            b19_frozen["reference_point_condition_number_inf"],
            places=10,
        )

        b20_live = live["BENCH-SUSP-0020"]
        b20_frozen = frozen["BENCH-SUSP-0020"]
        self.assertEqual(b20_live["failure_codes"], b20_frozen["failure_codes"])
        self.assertGreater(b20_live["ill_conditioned_condition_number_inf"], b20_live["condition_limit"])
        self.assertAlmostEqual(
            b20_live["ill_conditioned_condition_number_inf"],
            b20_frozen["ill_conditioned_condition_number_inf"],
            places=3,
        )
        self.assertFalse(b20_live["five_link_force_vector_available"])
        self.assertFalse(b20_live["seven_link_force_vector_available"])
        self.assertFalse(b20_live["singular_force_vector_available"])
        self.assertFalse(b20_live["ill_conditioned_force_vector_available"])

        self.assertEqual(live["authority_boundary"], frozen["authority_boundary"])
        self.assertFalse(live["authority_boundary"]["wufr_corner_adapter_authorized"])
        self.assertFalse(live["authority_boundary"]["structural_release_authorized"])


if __name__ == "__main__":
    unittest.main()
