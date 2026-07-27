from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "benchmarks/vehicle/vehicle_quasi_static_result_v0.1.0.toml"


class VehicleQuasiStaticResultRecordTests(unittest.TestCase):
    def test_frozen_symmetric_benchmark_result(self) -> None:
        with RESULT.open("rb") as stream:
            data = tomllib.load(stream)
        self.assertEqual(data["model_id"], "MOD-VEH-0004")
        self.assertEqual(data["authorization_id"], "AUTH-VEH-0004")
        b5 = data["BENCH-VEH-0005"]
        self.assertTrue(b5["pass"])
        self.assertTrue(b5["synthetic_only"])
        self.assertEqual(b5["sprung_mass_kg"], 100.0)
        self.assertEqual(b5["synthetic_wheel_side_mass_kg_per_corner"], 5.0)
        self.assertEqual(b5["support_stiffness_N_per_m"], 10000.0)
        self.assertAlmostEqual(b5["body_solution"][0], -0.024525, places=10)
        self.assertLess(b5["max_body_coordinate_error"], 1.0e-9)
        self.assertLess(b5["max_wheel_coordinate_error_m"], 1.0e-9)
        self.assertLess(b5["max_suspension_force_error_N"], 1.0e-7)
        self.assertLess(b5["max_reaction_error_N"], 1.0e-7)
        self.assertLess(b5["total_reaction_error_N"], 1.0e-7)
        self.assertLess(b5["scaled_residual_norm"], 1.0e-8)
        self.assertLess(b5["energy_gradient_max_residual"], 1.0e-6)
        self.assertGreater(b5["reciprocal_pivot_ratio"], 1.0e-8)
        self.assertAlmostEqual(b5["normal_reaction_sum_N"], 1177.20, places=7)

    def test_failure_boundary_and_wufr_authority_remain_frozen(self) -> None:
        with RESULT.open("rb") as stream:
            data = tomllib.load(stream)
        b6 = data["BENCH-VEH-0006"]
        self.assertTrue(b6["pass"])
        self.assertEqual(b6["singular_failure"], "singular_or_ill_conditioned_tangent")
        self.assertEqual(b6["bounded_failure"], "line_search_failure")
        self.assertEqual(
            b6["missing_wheel_external_force_failure"],
            "missing_wheel_external_force_authority",
        )
        self.assertEqual(b6["negative_reaction_failure"], "negative_normal_reaction")
        self.assertEqual(b6["negative_reaction_preserved_N"][0], -10.0)
        self.assertFalse(b6["hidden_wufr_mass_default_used"])

        boundary = data["authority_boundary"]
        self.assertFalse(boundary["wufr_mass_adapter_implemented"])
        self.assertFalse(boundary["wufr_road_reactions_available"])
        self.assertIn("10 kg front axle + 10 kg rear axle", boundary["current_reviewed_unsprung_evidence"])
        joined = "\n".join(boundary["prohibited_substitutions"]).lower()
        self.assertIn("5 kg/corner", joined)
        self.assertIn("10 kg/corner", joined)
        self.assertIn("crossweight", joined)


if __name__ == "__main__":
    unittest.main()
