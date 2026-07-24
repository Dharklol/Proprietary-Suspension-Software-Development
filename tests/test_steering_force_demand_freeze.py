from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SteeringForceDemandFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with (
            ROOT
            / "benchmarks/steering/steering_force_demand_target_result_v0.1.0.toml"
        ).open("rb") as stream:
            cls.result = tomllib.load(stream)

    def test_r25b_peak_slip_diagnostic_is_frozen(self) -> None:
        diagnostic = self.result["pr28_r25b_diagnostic"]
        self.assertEqual("HOOSIER_43105_18X7.5-10_R25B", diagnostic["source_tire_id"])
        self.assertEqual("HOOSIER_43104_18X7.5-10_R20", diagnostic["intended_tire_id"])
        self.assertAlmostEqual(9.6, diagnostic["inside_peak_slip_deg"])
        self.assertAlmostEqual(10.9, diagnostic["outside_peak_slip_deg"])
        self.assertAlmostEqual(1.3, diagnostic["outside_minus_inside_peak_slip_deg"])

    def test_full_steer_r25b_correction_remains_pro_ackermann(self) -> None:
        endpoint = self.result["pr28_r25b_diagnostic"]["endpoint"]
        self.assertAlmostEqual(32.18468832, endpoint["inside_heading_magnitude_deg"])
        self.assertAlmostEqual(
            22.868696046212865,
            endpoint["ackermann_outside_heading_magnitude_deg"],
        )
        self.assertAlmostEqual(
            9.315992273787135,
            endpoint["ackermann_inside_minus_outside_gap_deg"],
        )
        self.assertAlmostEqual(
            24.168696046212865,
            endpoint["corrected_outside_heading_magnitude_deg"],
        )
        self.assertAlmostEqual(
            8.015992273787134,
            endpoint["corrected_inside_minus_outside_gap_deg"],
        )
        self.assertEqual("pro_ackermann", endpoint["regime"])

    def test_near_center_r25b_correction_crosses_slightly_anti(self) -> None:
        sample = self.result["pr28_r25b_diagnostic"]["near_center_15deg_input"]
        self.assertAlmostEqual(3.6966375, sample["inside_heading_magnitude_deg"])
        self.assertAlmostEqual(
            3.710480534579104,
            sample["corrected_outside_heading_magnitude_deg"],
        )
        self.assertLess(sample["corrected_inside_minus_outside_gap_deg"], 0.0)
        self.assertEqual("anti_ackermann", sample["regime"])

    def test_synthetic_force_fixture_is_explicitly_nonphysical_and_mixed_regime(self) -> None:
        synthetic = self.result["synthetic_force_branch_verification"]
        self.assertFalse(synthetic["physical_tire_claim"])
        self.assertEqual(8, synthetic["anti_ackermann_sample_count"])
        self.assertEqual(1, synthetic["parallel_sample_count"])
        self.assertEqual(6, synthetic["pro_ackermann_sample_count"])
        self.assertIn("software evidence only", synthetic["regime_transition_summary"])

    def test_reference_candidate_remains_mechanism_feasible(self) -> None:
        candidate = self.result["reference_candidate"]
        self.assertTrue(candidate["feasible"])
        self.assertAlmostEqual(3.0401140155775543, candidate["total_objective"])

    def test_real_force_branch_remains_an_explicit_source_gap(self) -> None:
        source_gap = self.result["source_gap"]
        self.assertEqual(
            "real_force_branch_export_not_yet_frozen",
            source_gap["status"],
        )
        self.assertIn("TTC/TIR/MATLAB", source_gap["next_source_step"])


if __name__ == "__main__":
    unittest.main()
