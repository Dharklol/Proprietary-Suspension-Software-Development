from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WufrStaticRockerIncludedLoadAuthorizationTests(unittest.TestCase):
    def test_auth_susp_0018_is_incomplete_atomic_composition(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0018.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0018")
        self.assertEqual(auth["status"], "review_ready")
        self.assertTrue(auth["implementation_authorized"])
        scope = auth["scope"]
        self.assertTrue(scope["static_four_corner_rocker_included_load_publication_authorized"])
        self.assertTrue(scope["source_preserving_composition_authorized"])
        self.assertTrue(scope["unit_damper_force_influence_authorized"])
        self.assertFalse(scope["actual_damper_static_force_model_authorized"])
        self.assertFalse(scope["actual_damper_force_magnitude_authorized"])
        self.assertFalse(scope["complete_rocker_equilibrium_authorized"])
        self.assertFalse(scope["complete_hardware_reaction_authorized"])
        self.assertFalse(scope["structural_load_case_packet_authorized"])
        self.assertFalse(scope["installed_as_built_authority"])

    def test_exact_upstream_contract_and_remote_end_handoff_are_frozen(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0018.toml")
        contract = auth["input_contract"]
        self.assertEqual(contract["required_level1_model"], "MOD-SUSP-0009")
        self.assertEqual(contract["required_level1_authorization"], "AUTH-SUSP-0017")
        self.assertEqual(contract["required_rocker_model"], "MOD-SUSP-0008")
        self.assertEqual(contract["required_rocker_authorization"], "AUTH-SUSP-0016")
        self.assertEqual(contract["required_damper_hold_authorization"], "AUTH-SUSP-0015")
        self.assertEqual(
            contract["required_corner_order"],
            ["front_left", "front_right", "rear_left", "rear_right"],
        )
        handoff = contract["required_push_pull_handoff"]
        self.assertIn("force_on_remote_N", handoff)
        self.assertIn("remote_point_m", handoff)
        self.assertIn("unchanged", handoff)
        self.assertEqual(
            contract["required_missing_load_ids"],
            ["KW_V5_non_spring_static_force"],
        )

    def test_atomic_synchronization_preserves_points_axes_and_corner_identity(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0018.toml")
        sync = auth["synchronization"]
        self.assertTrue(sync["atomic_collection"])
        self.assertIn("No permutation", sync["corner_rule"])
        self.assertIn("source-owned current application point", sync["point_rule"])
        self.assertIn("axis sign is retained", sync["axis_rule"])
        self.assertIn("all four", sync["all_or_nothing_rule"].lower())
        for identity in (
            "corner_id",
            "load_case_id",
            "rocker_pivot_m",
            "rocker_axis_unit",
            "spring_source_id",
            "arb_fixture_id",
        ):
            self.assertIn(identity, sync["identity_tuple"])
        failure = auth["failure_behavior"]
        self.assertIn("collection_incomplete", failure["codes"])
        self.assertIn("Never publish a partial", failure["rule"])

    def test_unit_damper_influence_is_not_a_force_model(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0018.toml")
        influence = auth["damper_unit_influence"]
        self.assertEqual(influence["unit_force_N"], 1.0)
        self.assertIn("chassis eye toward the current rocker eye", influence["positive_coordinate"])
        self.assertIn("not a prediction", influence["interpretation_rule"])
        self.assertIn("future reviewed signed scalar", influence["affine_reconstruction_rule"])
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        self.assertIn("setting the unavailable kw v5", prohibited)
        self.assertIn("unit influence coefficient as an actual force estimate", prohibited)

    def test_no_numerical_or_physical_repair_is_authorized(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0018.toml")
        numerics = auth["numerics"]
        for key in (
            "least_squares_allowed",
            "pseudoinverse_allowed",
            "regularization_allowed",
            "hidden_balancing_force_or_couple_allowed",
            "force_or_moment_clipping_allowed",
            "absolute_value_sign_repair_allowed",
            "historical_load_fallback_allowed",
            "zero_damper_force_assumption_allowed",
        ):
            self.assertFalse(numerics[key])
        mechanics = auth["mechanics"]
        self.assertIn("No force, couple, constitutive law", mechanics["external_load_rule"])
        self.assertIn("complete_hardware_reaction", mechanics["completeness_rule"])

    def test_registry_links_are_consistent(self) -> None:
        model = _load("registry/records/models/MOD-SUSP-0010.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0018")
        self.assertEqual(model["equation_ids"], ["EQ-SUSP-0035", "EQ-SUSP-0036", "EQ-SUSP-0037"])
        self.assertEqual(model["benchmark_ids"], ["BENCH-SUSP-0032", "BENCH-SUSP-0033", "BENCH-SUSP-0034"])
        for upstream in ("MOD-SUSP-0004", "MOD-SUSP-0005", "MOD-SUSP-0008", "MOD-SUSP-0009"):
            self.assertIn(upstream, model["upstream_model_ids"])
        for benchmark_id in model["benchmark_ids"]:
            benchmark = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertIn("MOD-SUSP-0010", benchmark["target_ids"])

    def test_source_record_keeps_kw_v5_hold_and_collection_boundaries(self) -> None:
        source = _load("data_catalog/wufr27_static_rocker_included_loads_v0.toml")
        self.assertEqual(source["record_id"], "WUFR27_STATIC_ROCKER_INCLUDED_LOADS_V0")
        self.assertEqual(source["source"]["static_level1"]["model_id"], "MOD-SUSP-0009")
        hold = source["source"]["damper_hold"]
        self.assertEqual(hold["authorization_id"], "AUTH-SUSP-0015")
        self.assertFalse(hold["actual_force_available"])
        self.assertFalse(hold["zero_force_assumption_authorized"])
        boundaries = source["boundaries"]
        self.assertTrue(boundaries["complete_for_named_included_load_set"])
        self.assertFalse(boundaries["complete_hardware_reaction"])
        self.assertFalse(boundaries["complete_rocker_equilibrium"])
        self.assertFalse(boundaries["structural_load_case_authority"])


if __name__ == "__main__":
    unittest.main()
