from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WufrStaticLoadPathExchangeAuthorizationTests(unittest.TestCase):
    def test_auth_susp_0019_is_screening_exchange_only(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0019.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0019")
        self.assertEqual(auth["status"], "review_ready")
        self.assertTrue(auth["implementation_authorized"])
        scope = auth["scope"]
        self.assertTrue(scope["source_preserving_exchange_authorized"])
        self.assertTrue(scope["static_load_path_screening_authorized"])
        self.assertTrue(scope["canonical_machine_readable_packet_authorized"])
        for key in (
            "structural_load_case_authority",
            "fea_boundary_condition_authority",
            "complete_hardware_load_case_authorized",
            "complete_rocker_reaction_authorized",
            "bearing_load_split_authorized",
            "individual_a_arm_joint_split_authorized",
            "member_internal_load_authorized",
            "stress_or_factor_of_safety_authorized",
            "maneuver_load_generation_authorized",
            "installed_as_built_authority",
            "production_authority",
        ):
            self.assertFalse(scope[key])

    def test_exact_four_source_contract_is_frozen(self) -> None:
        contract = _load("authorizations/suspension/AUTH-SUSP-0019.toml")["input_contract"]
        expected = {
            "required_vehicle_equilibrium_model": "MOD-VEH-0007",
            "required_vehicle_equilibrium_authorization": "AUTH-VEH-0010",
            "required_carrier_wrench_model": "MOD-VEH-0008",
            "required_carrier_wrench_authorization": "AUTH-VEH-0011",
            "required_level1_model": "MOD-SUSP-0009",
            "required_level1_authorization": "AUTH-SUSP-0017",
            "required_rocker_model": "MOD-SUSP-0010",
            "required_rocker_authorization": "AUTH-SUSP-0018",
        }
        for key, value in expected.items():
            self.assertEqual(contract[key], value)
        self.assertEqual(
            contract["required_corner_order"],
            ["front_left", "front_right", "rear_left", "rear_right"],
        )
        self.assertEqual(contract["required_missing_force_id"], "KW_V5_non_spring_static_force")

    def test_atomic_exact_copy_contract_forbids_reconstruction(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0019.toml")
        identity = auth["identity_and_atomicity"]
        self.assertTrue(identity["atomic_packet"])
        self.assertTrue(identity["source_hashes_required"])
        self.assertTrue(identity["source_path_and_field_path_required"])
        self.assertIn("all four", identity["all_or_nothing_rule"].lower())
        self.assertIn("may not rerun physics", identity["no_reconstruction_rule"])
        failure = auth["failure_behavior"]
        self.assertIn("source_hash_mismatch", failure["codes"])
        self.assertIn("packet_incomplete", failure["codes"])
        self.assertIn("Never publish a partial packet", failure["rule"])

    def test_load_records_preserve_sign_point_frame_and_body_identity(self) -> None:
        contract = _load("authorizations/suspension/AUTH-SUSP-0019.toml")["load_record_contract"]
        for field in (
            "acting_on_body_id",
            "counterparty_body_id",
            "frame_id",
            "point_or_reference_id",
            "application_or_reference_point_m",
            "source_result_path",
            "source_field_path",
            "sign_convention",
        ):
            self.assertIn(field, contract["required_fields"])
        self.assertIn("absolute values", contract["force_sign_rule"])
        self.assertIn("may not be merged or relocated", contract["point_rule"])
        self.assertIn("does not transform loads", contract["frame_rule"])
        self.assertIn("Do not invent chassis-side nodal loads", contract["action_reaction_rule"])

    def test_fidelity_and_missing_boundaries_are_explicit(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0019.toml")
        fidelity = auth["fidelity_and_use"]
        self.assertTrue(fidelity["complete_for_named_upstream_record_exchange"])
        for key in (
            "complete_physical_hardware_load_case",
            "complete_rocker_equilibrium",
            "complete_chassis_pickup_load_set",
            "structural_release_authority",
        ):
            self.assertFalse(fidelity[key])
        missing = "\n".join(auth["missing_and_deferred"]["required_missing_items"]).lower()
        for phrase in (
            "kw_v5_non_spring_static_force",
            "rocker bearing load split",
            "individual forward/aft a-arm",
            "welded wishbone member-force distribution",
            "maneuver",
            "as-built",
        ):
            self.assertIn(phrase, missing)
        self.assertIn("not be multiplied by an assumed force", auth["missing_and_deferred"]["unit_damper_influence_rule"])

    def test_no_numerical_or_physical_repair_is_authorized(self) -> None:
        numerics = _load("authorizations/suspension/AUTH-SUSP-0019.toml")["numerics"]
        for key in (
            "least_squares_allowed",
            "pseudoinverse_allowed",
            "regularization_allowed",
            "hidden_balancing_force_or_couple_allowed",
            "force_or_moment_clipping_allowed",
            "absolute_value_sign_repair_allowed",
            "frame_or_point_relocation_allowed",
            "historical_load_fallback_allowed",
            "zero_damper_force_assumption_allowed",
        ):
            self.assertFalse(numerics[key])
        self.assertEqual(numerics["source_hash_algorithm"], "sha256")
        self.assertEqual(numerics["copied_scalar_match_tolerance"], 0.0)
        self.assertEqual(numerics["copied_vector_match_tolerance"], 0.0)

    def test_registry_and_source_links_are_consistent(self) -> None:
        model = _load("registry/records/models/MOD-SUSP-0011.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0019")
        self.assertEqual(model["equation_ids"], [])
        self.assertEqual(
            model["benchmark_ids"],
            ["BENCH-SUSP-0035", "BENCH-SUSP-0036", "BENCH-SUSP-0037"],
        )
        for upstream in ("MOD-VEH-0007", "MOD-VEH-0008", "MOD-SUSP-0009", "MOD-SUSP-0010"):
            self.assertIn(upstream, model["upstream_model_ids"])
        for benchmark_id in model["benchmark_ids"]:
            benchmark = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertIn("MOD-SUSP-0011", benchmark["target_ids"])
        source = _load("data_catalog/wufr27_static_load_path_exchange_v0.toml")
        self.assertEqual(source["record_id"], "WUFR27_STATIC_LOAD_PATH_EXCHANGE_V0")
        self.assertEqual(source["authorization_id"], "AUTH-SUSP-0019")
        self.assertEqual(source["model_id"], "MOD-SUSP-0011")
        self.assertEqual(source["source"]["vehicle_equilibrium"]["model_id"], "MOD-VEH-0007")
        self.assertEqual(source["source"]["carrier_wrench"]["model_id"], "MOD-VEH-0008")
        self.assertEqual(source["source"]["level1_interface"]["model_id"], "MOD-SUSP-0009")
        self.assertEqual(source["source"]["rocker_included"]["model_id"], "MOD-SUSP-0010")
        packet_fidelity = source["packet"]["fidelity"]
        self.assertTrue(packet_fidelity["complete_for_named_upstream_record_exchange"])
        self.assertFalse(packet_fidelity["fea_boundary_condition_authority"])
        self.assertFalse(packet_fidelity["structural_release_authority"])


if __name__ == "__main__":
    unittest.main()
