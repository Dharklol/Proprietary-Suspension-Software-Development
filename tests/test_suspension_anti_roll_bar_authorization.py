from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class SuspensionAntiRollBarAuthorizationTests(unittest.TestCase):
    def test_authorization_is_review_ready_and_bilateral(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0005.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0005")
        self.assertEqual(auth["status"], "review_ready")
        self.assertEqual(auth["scope"]["equation_ids"], ["EQ-SUSP-0016", "EQ-SUSP-0017", "EQ-SUSP-0018"])
        self.assertEqual(auth["scope"]["benchmark_ids"], ["BENCH-SUSP-0011", "BENCH-SUSP-0012"])
        self.assertFalse(auth["numerics"]["interpolation_allowed"])
        self.assertIn("bilateral", "\n".join(auth["permitted"]["items"]).lower())

    def test_registry_links_are_frozen(self) -> None:
        model = _load("registry/records/models/MOD-SUSP-0005.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0005")
        self.assertEqual(model["equation_ids"], ["EQ-SUSP-0016", "EQ-SUSP-0017", "EQ-SUSP-0018"])
        self.assertEqual(
            model["benchmark_ids"],
            ["BENCH-SUSP-0011", "BENCH-SUSP-0012", "BENCH-SUSP-0013", "BENCH-SUSP-0014", "BENCH-SUSP-0015", "BENCH-SUSP-0016", "BENCH-SUSP-0017"],
        )
        for benchmark_id in model["benchmark_ids"]:
            benchmark = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertIn("MOD-SUSP-0005", benchmark["target_ids"])

    def test_wufr_package_freezes_discrete_per_arm_solidworks_authority(self) -> None:
        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        authority = package["governing_solidworks_fea"]
        self.assertEqual(authority["sheet_name"], "ARB FEA vs Simulink")
        self.assertEqual(authority["source_column"], "FEA SolidWorks Stiffness")
        self.assertEqual(authority["source_unit"], "N/mm")
        self.assertEqual(authority["stiffness_N_per_mm"], [280.0, 300.0, 400.0, 700.0, 2300.0])
        self.assertEqual(authority["stiffness_N_per_m"], [280000.0, 300000.0, 400000.0, 700000.0, 2300000.0])
        self.assertEqual(authority["arm_count"], 2)
        self.assertIn("blade arm", authority["beam_theory_semantics"].lower())
        self.assertIn("3ei/l^3", authority["beam_theory_semantics"].lower())
        self.assertTrue(package["authority_boundaries"]["two_arm_vector_constitutive_authorized"])
        self.assertFalse(package["authority_boundaries"]["scalar_whole_blade_rescaling_authorized"])

    def test_comparison_sources_remain_non_governing_and_lineage_is_corrected(self) -> None:
        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        comparison = package["comparison_only"]
        self.assertEqual(comparison["matlab_reduced_axle_Nm_per_deg"], [2560.0, 2270.0])
        self.assertEqual(comparison["simulink_stiffness_N_per_mm"], [285.0, 309.0, 400.0, 724.0, 2628.0])
        self.assertEqual(comparison["instron_stiffness_N_per_mm"], [900.0, 980.0, 1320.0, 1970.0, 2630.0])
        self.assertIn("setting-1 effective axle", comparison["matlab_semantics"].lower())
        lineage = package["historical_effective_axle_lineage"]
        self.assertEqual(lineage["fea_stiffness_N_per_mm_as_reported"], [282.0, 305.0, 396.0, 706.0, 2300.0])
        self.assertEqual(lineage["front_roll_stiffness_Nm_per_deg"], [2560.0, 2720.0, 3300.0, 5500.0, 16500.0])
        self.assertEqual(lineage["rear_roll_stiffness_Nm_per_deg"], [2270.0, 2430.0, 3000.0, 5100.0, 15600.0])

    def test_one_arm_and_two_arm_hand_cases(self) -> None:
        k = 280000.0
        d = 0.001
        self.assertAlmostEqual(k * d, 280.0)
        self.assertAlmostEqual(0.5 * k * d * d, 0.140)
        self.assertAlmostEqual(0.5 * k * (d * d + (-d) * (-d)), 0.280)

    def test_wheel_coordinate_map_is_promoted_but_vehicle_shortcuts_remain_blocked(self) -> None:
        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        boundaries = package["authority_boundaries"]
        self.assertFalse(boundaries["interpolation_authorized"])
        self.assertTrue(boundaries["z_bar_geometry_map_authorized"])
        self.assertIn("physical wheel-center", boundaries["z_bar_geometry_map_coordinate"].lower())
        self.assertTrue(boundaries["rocker_coordinate_generalized_force_authorized"])
        self.assertTrue(boundaries["wheel_coordinate_generalized_force_authorized"])
        self.assertEqual(
            boundaries["wheel_coordinate_order"],
            ["delta_z_wc_body_left_m", "delta_z_wc_body_right_m"],
        )
        self.assertFalse(boundaries["vehicle_equilibrium_authorized"])
        self.assertFalse(boundaries["body_roll_substitution_allowed"])
        self.assertFalse(boundaries["track_width_approximation_allowed"])
        self.assertFalse(boundaries["historical_motion_ratio_substitution_allowed"])


if __name__ == "__main__":
    unittest.main()
