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
        self.assertEqual(auth["scope"]["model_ids"], ["MOD-SUSP-0005"])
        self.assertEqual(
            auth["scope"]["equation_ids"],
            ["EQ-SUSP-0016", "EQ-SUSP-0017", "EQ-SUSP-0018"],
        )
        self.assertEqual(auth["scope"]["benchmark_ids"], ["BENCH-SUSP-0011", "BENCH-SUSP-0012"])
        self.assertEqual(auth["scope"]["assumption_ids"], ["ASM-SUSP-0003"])
        self.assertFalse(auth["numerics"]["hidden_clipping_allowed"])
        self.assertFalse(auth["numerics"]["absolute_ratio_allowed"])
        self.assertFalse(auth["numerics"]["stiffness_inference_allowed"])
        self.assertFalse(auth["numerics"]["interpolation_allowed"])

        permitted = "\n".join(auth["permitted"]["items"]).lower()
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        self.assertIn("bilateral", permitted)
        self.assertIn("280/300/400/700/2300", permitted)
        self.assertIn("scalar k_arb*mr^2", prohibited)
        self.assertIn("interpolating", prohibited)
        self.assertIn("body roll", prohibited)

    def test_registry_links_and_equation_contracts_are_frozen(self) -> None:
        model = _load("registry/records/models/MOD-SUSP-0005.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0005")
        self.assertEqual(model["equation_ids"], ["EQ-SUSP-0016", "EQ-SUSP-0017", "EQ-SUSP-0018"])
        self.assertEqual(model["benchmark_ids"], ["BENCH-SUSP-0011", "BENCH-SUSP-0012"])
        self.assertEqual(model["upstream_model_ids"], ["MOD-SUSP-0001", "MOD-SUSP-0002", "MOD-SUSP-0003"])

        assumption = _load("registry/records/assumptions/ASM-SUSP-0003.toml")["record"]
        self.assertEqual(assumption["id"], "ASM-SUSP-0003")
        self.assertEqual(assumption["severity"], "high")
        self.assertIn("zero intentional arb preload", assumption["description"].lower())
        self.assertIn("280/300/400/700/2300", assumption["description"])
        self.assertIn("2560/2270", assumption["description"])
        self.assertIn("comparison-only", assumption["description"].lower())

        for equation_id in model["equation_ids"]:
            equation = _load(f"registry/records/equations/{equation_id}.toml")["record"]
            self.assertEqual(equation["id"], equation_id)
            self.assertEqual(equation["verification_level"], "none")
            self.assertEqual(set(equation["benchmark_ids"]), {"BENCH-SUSP-0011", "BENCH-SUSP-0012"})

        for benchmark_id in model["benchmark_ids"]:
            benchmark = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertEqual(benchmark["id"], benchmark_id)
            self.assertIn("MOD-SUSP-0005", benchmark["target_ids"])

    def test_synthetic_common_and_differential_hand_cases(self) -> None:
        k = 10000.0
        z_left = 0.010
        z_right = -0.010
        s = z_left - z_right
        action = k * s
        energy = 0.5 * k * s * s
        self.assertAlmostEqual(s, 0.020)
        self.assertAlmostEqual(action, 200.0)
        self.assertAlmostEqual(energy, 2.0)
        self.assertAlmostEqual(-action + action, 0.0)

    def test_wufr_package_freezes_discrete_solidworks_authority(self) -> None:
        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        self.assertEqual(package["configuration_id"], "WUFR27_SUSPENSION_BASELINE_V0")
        self.assertFalse(package["installed_as_built_authority"])
        self.assertTrue(package["constitutive_stiffness_authority"])
        self.assertEqual(package["reviewed_setup"]["intentional_preload"], "zero")

        authority = package["governing_solidworks_fea"]
        self.assertEqual(authority["sheet_name"], "ARB FEA vs Simulink")
        self.assertEqual(authority["source_column"], "FEA SolidWorks Stiffness")
        self.assertEqual(authority["source_unit"], "N/mm")
        self.assertEqual(authority["setting_numbers"], [1, 2, 3, 4, 5])
        self.assertEqual(authority["stiffness_N_per_mm"], [280.0, 300.0, 400.0, 700.0, 2300.0])
        self.assertEqual(authority["stiffness_N_per_m"], [280000.0, 300000.0, 400000.0, 700000.0, 2300000.0])
        self.assertIn("3EI/L^3", authority["beam_theory_unit_check"])

    def test_comparison_sources_remain_non_governing(self) -> None:
        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        comparison = package["comparison_only"]
        self.assertEqual(comparison["matlab_reduced_axle_Nm_per_deg"], [2560.0, 2270.0])
        self.assertEqual(comparison["simulink_stiffness_N_per_mm"], [285.0, 309.0, 400.0, 724.0, 2628.0])
        self.assertEqual(comparison["instron_stiffness_N_per_mm"], [900.0, 980.0, 1320.0, 1970.0, 2630.0])
        self.assertIn("comparison-only", comparison["matlab_semantics"].lower())
        self.assertIn("do not average", comparison["comparison_rule"].lower())

    def test_wufr_geometry_map_and_interpolation_are_not_authorized(self) -> None:
        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        boundaries = package["authority_boundaries"]
        self.assertFalse(boundaries["interpolation_authorized"])
        self.assertFalse(boundaries["z_bar_geometry_map_authorized"])
        self.assertFalse(boundaries["body_roll_substitution_allowed"])
        self.assertFalse(boundaries["track_width_approximation_allowed"])
        self.assertIn("not yet authorized", boundaries["z_bar_geometry_map_status"].lower())

    def test_one_mm_hand_case(self) -> None:
        stiffness_N_per_mm = [280.0, 300.0, 400.0, 700.0, 2300.0]
        expected_energy_J = [0.140, 0.150, 0.200, 0.350, 1.150]
        for stiffness, expected_energy in zip(stiffness_N_per_mm, expected_energy_J):
            k_si = stiffness * 1000.0
            delta_b = 0.001
            force = k_si * delta_b
            energy = 0.5 * k_si * delta_b * delta_b
            self.assertAlmostEqual(force, stiffness, places=12)
            self.assertAlmostEqual(energy, expected_energy, places=12)


if __name__ == "__main__":
    unittest.main()
