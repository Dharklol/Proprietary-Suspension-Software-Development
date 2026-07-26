from __future__ import annotations

import math
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

        permitted = "\n".join(auth["permitted"]["items"]).lower()
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        self.assertIn("bilateral", permitted)
        self.assertIn("missing_stiffness_authority", permitted)
        self.assertIn("scalar k_arb*mr^2", prohibited)
        self.assertIn("556/458", prohibited)
        self.assertIn("2560", prohibited)

    def test_registry_links_and_equation_contracts_are_frozen(self) -> None:
        model = _load("registry/records/models/MOD-SUSP-0005.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0005")
        self.assertEqual(model["equation_ids"], ["EQ-SUSP-0016", "EQ-SUSP-0017", "EQ-SUSP-0018"])
        self.assertEqual(model["benchmark_ids"], ["BENCH-SUSP-0011", "BENCH-SUSP-0012"])
        self.assertEqual(
            model["upstream_model_ids"],
            ["MOD-SUSP-0001", "MOD-SUSP-0002", "MOD-SUSP-0003"],
        )

        assumption = _load("registry/records/assumptions/ASM-SUSP-0003.toml")["record"]
        self.assertEqual(assumption["id"], "ASM-SUSP-0003")
        self.assertEqual(assumption["severity"], "high")
        self.assertIn("zero intentional arb preload", assumption["description"].lower())

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
        s0 = 0.0

        z_left = 0.010
        z_right = 0.010
        s = z_left - z_right - s0
        action = k * s
        energy = 0.5 * k * s * s
        q_left = -1.0 * action
        q_right = +1.0 * action
        self.assertAlmostEqual(s, 0.0)
        self.assertAlmostEqual(energy, 0.0)
        self.assertAlmostEqual(q_left, 0.0)
        self.assertAlmostEqual(q_right, 0.0)

        z_left = 0.010
        z_right = -0.010
        s = z_left - z_right - s0
        action = k * s
        energy = 0.5 * k * s * s
        q_left = -action
        q_right = +action
        self.assertAlmostEqual(s, 0.020)
        self.assertAlmostEqual(action, 200.0)
        self.assertAlmostEqual(energy, 2.0)
        self.assertAlmostEqual(q_left, -200.0)
        self.assertAlmostEqual(q_right, 200.0)
        self.assertAlmostEqual(q_left + q_right, 0.0)

        h = 1.0e-6
        def u(z_l: float, z_r: float) -> float:
            local_s = z_l - z_r - s0
            return 0.5 * k * local_s * local_s

        d_u_d_zl = (u(z_left + h, z_right) - u(z_left - h, z_right)) / (2.0 * h)
        d_u_d_zr = (u(z_left, z_right + h) - u(z_left, z_right - h)) / (2.0 * h)
        self.assertTrue(math.isclose(-d_u_d_zl, q_left, rel_tol=1.0e-10, abs_tol=1.0e-8))
        self.assertTrue(math.isclose(-d_u_d_zr, q_right, rel_tol=1.0e-10, abs_tol=1.0e-8))

    def test_explicit_preload_reference_changes_only_named_coordinate(self) -> None:
        z_left = 0.010
        z_right = -0.010
        zero_preload_s = z_left - z_right
        preloaded_s = z_left - z_right - 0.003
        self.assertAlmostEqual(zero_preload_s, 0.020)
        self.assertAlmostEqual(preloaded_s, 0.017)
        self.assertNotEqual(zero_preload_s, preloaded_s)

    def test_wufr_package_freezes_geometry_lineage_without_stiffness(self) -> None:
        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        self.assertEqual(package["configuration_id"], "WUFR27_SUSPENSION_BASELINE_V0")
        self.assertFalse(package["installed_as_built_authority"])
        self.assertFalse(package["constitutive_stiffness_authority"])
        self.assertEqual(package["reviewed_setup"]["intentional_preload"], "zero")
        self.assertIn("2025", package["reviewed_setup"]["wufr27_carryover"])

        front = package["wufr26_front_arb"]
        rear = package["wufr26_rear_arb"]
        self.assertEqual(front["blade_material"], "Ti-6Al-4V")
        self.assertEqual(rear["blade_material"], "Ti-6Al-4V")
        self.assertEqual(front["linkage_material"], "CARBON FIBER")
        self.assertEqual(rear["linkage_material"], "CARBON FIBER")
        self.assertAlmostEqual(front["linkage_nominal_length_in"], 7.22)
        self.assertAlmostEqual(rear["linkage_nominal_length_in"], 6.22)

        authority = package["constitutive_authority"]
        self.assertEqual(authority["front_status"], "missing_stiffness_authority")
        self.assertEqual(authority["rear_status"], "missing_stiffness_authority")
        self.assertTrue(authority["allow_generic_synthetic_implementation"])
        self.assertTrue(authority["allow_wufr_geometry_only_evaluation"])
        self.assertFalse(authority["allow_wufr_force_energy_output"])

    def test_wufr27_direct_assembly_files_are_explicit_placeholders(self) -> None:
        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        direct = package["wufr27_direct_cad_placeholders"]
        self.assertEqual(direct["front_assembly_sha1"], direct["rear_assembly_sha1"])
        self.assertEqual(direct["front_assembly_size_bytes"], direct["rear_assembly_size_bytes"])
        self.assertIn("placeholder", direct["interpretation"].lower())

    def test_exported_sketch_points_are_not_connectivity_authority(self) -> None:
        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        geometry = package["wufr26_suspension_geometry"]
        self.assertIn("do not infer", geometry["connectivity_warning"].lower())
        self.assertEqual(len(geometry["front_arb_raw_sketch"]["points_m"]), 10)
        self.assertEqual(len(geometry["rear_arb_raw_sketch"]["points_m"]), 10)

    def test_historical_numeric_substitutes_remain_rejected(self) -> None:
        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        historical = package["historical_weight_transfer_script"]
        self.assertEqual(historical["observed_front_literal"], 2560.0)
        self.assertEqual(historical["observed_rear_literal"], 2270.0)
        self.assertIn("change and figure out", historical["source_warning"])
        self.assertIn("not arb constitutive stiffness", historical["authority"].lower())

        spec = package["wufr26_spec_sheet_comparison"]
        self.assertEqual(spec["front_suspension_roll_rate_Nm_per_deg"], 556.0)
        self.assertEqual(spec["rear_suspension_roll_rate_Nm_per_deg"], 458.0)
        self.assertIn("not arb-only", spec["interpretation"].lower())

        fea = package["wufr25_arb_stiffness_source"]
        self.assertEqual(fea["stiffness_recovery_status"], "incomplete")
        self.assertIn("no human-readable", fea["stiffness_recovery_gap"].lower())

    def test_active_suppressed_state_is_configuration_evidence_only(self) -> None:
        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        state = package["wufr26_active_assembly_state"]
        self.assertIn("included", state["front_top_level_arb"].lower())
        self.assertEqual(state["rear_top_level_arb"], "EXCLUDED_SUPPRESSED")
        self.assertIn("not a universal", state["interpretation"].lower())


if __name__ == "__main__":
    unittest.main()
