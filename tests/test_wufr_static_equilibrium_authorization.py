from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WufrStaticEquilibriumAuthorizationTests(unittest.TestCase):
    def test_authorization_is_bounded_and_implementation_ready(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0009.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-VEH-0009")
        self.assertEqual(auth["status"], "review_ready")
        self.assertTrue(auth["implementation_authorized"])

        scope = auth["scope"]
        self.assertEqual(scope["model_ids"], ["MOD-VEH-0007"])
        self.assertEqual(
            scope["equation_ids"],
            ["EQ-VEH-0015", "EQ-VEH-0016", "EQ-VEH-0017"],
        )
        self.assertEqual(
            scope["benchmark_ids"],
            ["BENCH-VEH-0011", "BENCH-VEH-0012", "BENCH-VEH-0013"],
        )
        self.assertTrue(scope["provider_composition_authorized"])
        self.assertTrue(scope["wufr_static_road_reaction_authorized"])
        self.assertTrue(scope["uncorrelated_design_intent_result_authorized"])
        self.assertFalse(scope["historical_scale_reconstruction_authorized"])
        self.assertFalse(scope["carrier_wrench_generation_authorized"])
        self.assertFalse(scope["maneuver_equilibrium_authorized"])
        self.assertFalse(scope["installed_as_built_authority"])
        self.assertFalse(scope["production_authority"])

    def test_exact_configuration_state_and_coordinate_contract_are_frozen(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0009.toml")
        boundary = auth["source_boundary"]
        self.assertEqual(boundary["configuration_id"], "WUFR27_SUSPENSION_BASELINE_V0")
        self.assertEqual(
            boundary["static_state_id"],
            "WUFR26_DRIVER_NO_FUEL_DESIGN_INTENT_REFERENCE",
        )
        self.assertEqual(
            auth["coordinates"]["body_coordinate_order"],
            ["z_s_m", "phi_rad", "theta_rad"],
        )
        self.assertEqual(
            auth["coordinates"]["wheel_coordinate_order"],
            ["front_left", "front_right", "rear_left", "rear_right"],
        )
        self.assertIn("positive upward", auth["coordinates"]["wheel_coordinate_definition"])

    def test_arb_settings_are_explicit_and_never_defaulted(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0009.toml")
        runtime = auth["runtime_configuration"]
        self.assertTrue(runtime["front_arb_setting_required"])
        self.assertTrue(runtime["rear_arb_setting_required"])
        self.assertEqual(runtime["allowed_arb_settings"], [1, 2, 3, 4, 5])
        self.assertFalse(runtime["arb_default_authorized"])
        self.assertFalse(runtime["arb_interpolation_authorized"])
        self.assertFalse(auth["numerics"]["hidden_arb_setting_default_allowed"])

        source = _load("data_catalog/wufr27_static_equilibrium_composition_v0.toml")
        arb = source["source"]["anti_roll_bar"]
        self.assertTrue(arb["explicit_front_setting_required"])
        self.assertTrue(arb["explicit_rear_setting_required"])
        self.assertFalse(arb["default_setting_authorized"])
        self.assertFalse(arb["interpolation_authorized"])
        self.assertEqual(source["verification_fixture"]["front_arb_setting"], 1)
        self.assertEqual(source["verification_fixture"]["rear_arb_setting"], 1)
        self.assertIn("not current setup authority", source["verification_fixture"]["setting_role"])

    def test_upstream_source_ownership_and_assumptions_are_complete(self) -> None:
        source = _load("data_catalog/wufr27_static_equilibrium_composition_v0.toml")
        self.assertEqual(source["static_state_id"], "WUFR26_DRIVER_NO_FUEL_DESIGN_INTENT_REFERENCE")
        self.assertEqual(source["source"]["whole_vehicle"]["model_id"], "MOD-VEH-0003")
        self.assertEqual(source["source"]["equilibrium"]["model_id"], "MOD-VEH-0004")
        self.assertEqual(source["source"]["gravity"]["model_id"], "MOD-VEH-0005")
        self.assertEqual(source["source"]["compatibility"]["model_id"], "MOD-VEH-0006")
        self.assertEqual(source["source"]["spring"]["model_id"], "MOD-SUSP-0004")
        self.assertEqual(source["source"]["anti_roll_bar"]["model_id"], "MOD-SUSP-0005")
        self.assertEqual(source["source"]["gravity"]["assumption_ids"], ["ASM-VEH-0002", "ASM-VEH-0003"])
        self.assertEqual(source["source"]["compatibility"]["assumption_id"], "ASM-VEH-0005")
        self.assertEqual(source["source"]["spring"]["assumption_id"], "ASM-SUSP-0002")
        self.assertEqual(source["source"]["anti_roll_bar"]["assumption_id"], "ASM-SUSP-0003")

    def test_mechanics_preserve_generic_kernel_and_physical_closure(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0009.toml")
        mechanics = auth["mechanics"]
        self.assertIn("Q_susp=Q_spring+Q_ARB", mechanics["suspension_composition"])
        self.assertIn("J_wb^T Q_susp", mechanics["body_equilibrium"])
        self.assertIn("Q_unsprung_gravity", mechanics["contact_recovery"])
        self.assertIn("physical wrenches", mechanics["physical_closure"])
        self.assertIn("without repair", mechanics["physical_closure"])
        self.assertIn("-partial", mechanics["energy_check"])

        numerics = auth["numerics"]
        self.assertFalse(numerics["hidden_clipping_allowed"])
        self.assertFalse(numerics["negative_reaction_clipping_allowed"])
        self.assertFalse(numerics["hidden_crossweight_rule_allowed"])
        self.assertFalse(numerics["scalar_motion_ratio_allowed"])
        self.assertFalse(numerics["scalar_wheel_rate_allowed"])
        self.assertFalse(numerics["least_squares_repair_allowed"])

    def test_model_equation_and_benchmark_registry_links_are_consistent(self) -> None:
        model = _load("registry/records/models/MOD-VEH-0007.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-VEH-0010")
        self.assertEqual(model["equation_ids"], ["EQ-VEH-0015", "EQ-VEH-0017", "EQ-VEH-0018", "EQ-VEH-0019"])
        self.assertEqual(model["benchmark_ids"], ["BENCH-VEH-0011", "BENCH-VEH-0012", "BENCH-VEH-0013", "BENCH-VEH-0014"])
        self.assertEqual(
            model["upstream_model_ids"],
            [
                "MOD-VEH-0003",
                "MOD-VEH-0004",
                "MOD-VEH-0005",
                "MOD-VEH-0006",
                "MOD-SUSP-0004",
                "MOD-SUSP-0005",
            ],
        )
        self.assertEqual(model["downstream_model_ids"], ["MOD-SUSP-0007"])

        for equation_id in model["equation_ids"]:
            equation = _load(f"registry/records/equations/{equation_id}.toml")["record"]
            expected_auth = "AUTH-VEH-0009" if equation_id == "EQ-VEH-0015" else "AUTH-VEH-0010"
            self.assertEqual(equation["authorization_id"], expected_auth)
            self.assertIn("MOD-VEH-0007", equation.get("target_ids", ["MOD-VEH-0007"]))

        for benchmark_id in model["benchmark_ids"]:
            benchmark = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertIn("MOD-VEH-0007", benchmark["target_ids"])
            self.assertEqual(
                benchmark["authorization"],
                "authorizations/vehicle/AUTH-VEH-0010.toml",
            )

    def test_no_historical_fitting_or_structural_scope_is_authorized(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0009.toml")
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        for phrase in (
            "installed/as-built corner-weight prediction",
            "historical scale state",
            "arb setting implicitly",
            "crossweight",
            "scalar wheel-rate",
            "negative road reaction",
            "carrier/upright external wrenches",
            "fea boundary conditions",
        ):
            self.assertIn(phrase, prohibited)

        boundaries = _load("data_catalog/wufr27_static_equilibrium_composition_v0.toml")["boundaries"]
        self.assertTrue(boundaries["wufr_static_road_reaction_authorized"])
        self.assertFalse(boundaries["historical_corner_weight_reconstruction_authorized"])
        self.assertFalse(boundaries["arb_setup_selection_authority"])
        self.assertFalse(boundaries["carrier_wrench_authority"])
        self.assertFalse(boundaries["structural_load_case_authority"])
        self.assertFalse(boundaries["maneuver_qss_authority"])
        self.assertFalse(boundaries["installed_as_built_authority"])


if __name__ == "__main__":
    unittest.main()
