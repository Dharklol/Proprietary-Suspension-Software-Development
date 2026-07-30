from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WufrStaticLevel1InterfaceLoadAuthorizationTests(unittest.TestCase):
    def test_auth_susp_0017_is_narrow_static_composition(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0017.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0017")
        self.assertEqual(auth["status"], "review_ready")
        self.assertTrue(auth["implementation_authorized"])
        scope = auth["scope"]
        self.assertTrue(scope["static_four_corner_level1_publication_authorized"])
        self.assertTrue(scope["source_preserving_composition_authorized"])
        self.assertFalse(scope["new_force_law_authorized"])
        self.assertFalse(scope["new_joint_idealization_authorized"])
        self.assertFalse(scope["rocker_result_publication_authorized"])
        self.assertFalse(scope["structural_load_case_packet_authorized"])
        self.assertFalse(scope["maneuver_load_generation_authorized"])
        self.assertFalse(scope["installed_as_built_authority"])

    def test_exact_upstream_models_and_corner_order_are_frozen(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0017.toml")
        contract = auth["input_contract"]
        self.assertEqual(contract["required_carrier_model"], "MOD-VEH-0008")
        self.assertEqual(contract["required_carrier_authorization"], "AUTH-VEH-0011")
        self.assertEqual(contract["required_level1_model"], "MOD-SUSP-0007")
        self.assertEqual(contract["required_level1_authorization"], "AUTH-SUSP-0012")
        self.assertEqual(
            contract["required_corner_order"],
            ["front_left", "front_right", "rear_left", "rear_right"],
        )
        self.assertIn("MOD-STEER-0001", contract["required_front_steering_state"])
        self.assertIn("same suspension state", contract["required_front_steering_state"])

    def test_atomic_synchronization_and_no_partial_publication(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0017.toml")
        sync = auth["synchronization"]
        self.assertTrue(sync["atomic_collection"])
        self.assertIn("No permutation", sync["corner_rule"])
        self.assertIn("all four", sync["all_or_nothing_rule"].lower())
        self.assertIn("carrier_reference_point", sync["identity_tuple"])
        self.assertIn("geometry_source_id", sync["identity_tuple"])
        failure = auth["failure_behavior"]
        self.assertIn("collection_incomplete", failure["codes"])
        self.assertIn("Never publish a partial", failure["rule"])

    def test_no_load_generation_or_numerical_repair_is_authorized(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0017.toml")
        self.assertIn("No external force or couple is created", auth["mechanics"]["external_load_rule"])
        numerics = auth["numerics"]
        for key in (
            "least_squares_allowed",
            "pseudoinverse_allowed",
            "regularization_allowed",
            "stiffness_weighting_allowed",
            "hidden_balancing_wrench_allowed",
            "force_or_moment_clipping_allowed",
            "absolute_value_sign_repair_allowed",
            "historical_load_fallback_allowed",
        ):
            self.assertFalse(numerics[key])
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        for phrase in (
            "nominal front tie-rod",
            "permuting corners",
            "historical optimumk force tables",
            "forward/aft a-arm",
            "complete while the kw v5",
        ):
            self.assertIn(phrase, prohibited)

    def test_registry_links_and_benchmarks_are_consistent(self) -> None:
        model = _load("registry/records/models/MOD-SUSP-0009.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0017")
        self.assertEqual(model["equation_ids"], ["EQ-SUSP-0032", "EQ-SUSP-0033", "EQ-SUSP-0034"])
        self.assertEqual(model["benchmark_ids"], ["BENCH-SUSP-0029", "BENCH-SUSP-0030", "BENCH-SUSP-0031"])
        self.assertIn("MOD-VEH-0008", model["upstream_model_ids"])
        self.assertIn("MOD-SUSP-0007", model["upstream_model_ids"])
        for benchmark_id in model["benchmark_ids"]:
            benchmark = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertIn("MOD-SUSP-0009", benchmark["target_ids"])

    def test_rocker_handoff_remains_incomplete(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0017.toml")
        handoff = auth["mechanics"]["rocker_handoff_rule"].lower()
        self.assertIn("force_on_remote_n", handoff)
        self.assertIn("does not itself publish rocker results", handoff)
        source = _load("data_catalog/wufr27_static_level1_interface_loads_v0.toml")
        rocker = source["downstream"]["rocker"]
        self.assertEqual(rocker["authorization_id"], "AUTH-SUSP-0016")
        self.assertFalse(rocker["complete_rocker_reaction"])
        self.assertEqual(rocker["missing_force_authorization"], "AUTH-SUSP-0015")


if __name__ == "__main__":
    unittest.main()
