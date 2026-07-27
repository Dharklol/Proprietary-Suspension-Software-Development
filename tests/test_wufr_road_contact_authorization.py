from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WUFRRoadContactAuthorizationTests(unittest.TestCase):
    def test_failed_implementation_authority_is_suspended(self) -> None:
        auth6 = _load("authorizations/vehicle/AUTH-VEH-0006.toml")
        auth7 = _load("authorizations/vehicle/AUTH-VEH-0007.toml")
        model = _load("registry/records/models/MOD-VEH-0006.toml")["record"]
        assumption = _load("registry/records/assumptions/ASM-VEH-0004.toml")["record"]

        self.assertEqual(auth6["authorization_id"], "AUTH-VEH-0006")
        self.assertEqual(auth6["status"], "suspended_by_AUTH-VEH-0007")
        self.assertFalse(auth6["implementation_authorized"])
        self.assertEqual(auth6["correction_authorization_id"], "AUTH-VEH-0007")

        self.assertEqual(auth7["authorization_id"], "AUTH-VEH-0007")
        self.assertEqual(auth7["status"], "review_ready")
        self.assertFalse(auth7["implementation_authorized"])
        self.assertEqual(auth7["scope"]["model_ids"], ["MOD-VEH-0006"])
        self.assertEqual(auth7["scope"]["assumption_ids"], ["ASM-VEH-0004"])

        self.assertEqual(model["status"], "blocked")
        self.assertEqual(model["authorization_id"], "AUTH-VEH-0006")
        self.assertEqual(model["correction_authorization_id"], "AUTH-VEH-0007")
        self.assertIn("implementation_blocked", model["authorization_state"])
        self.assertEqual(assumption["status"], "deprecated")
        self.assertIn("not valid", assumption["description"])
        self.assertIn("0.0008458158026623031", assumption["description"])

    def test_failed_bench_veh_0008_probe_is_frozen_without_tolerance_repair(self) -> None:
        result = _load("benchmarks/vehicle/wufr_road_contact_assumption_probe_v0.1.0.toml")
        b8 = _load("registry/records/benchmarks/BENCH-VEH-0008.toml")["record"]

        self.assertFalse(result["pass"])
        probe = result["historical_front_left_reconstruction"]
        self.assertAlmostEqual(probe["required_max_euclidean_error_m"], 5.0e-6, places=15)
        self.assertAlmostEqual(probe["observed_max_euclidean_error_m"], 0.0008458158026623031, places=15)
        self.assertGreater(probe["observed_max_euclidean_error_m"], 100.0 * probe["required_max_euclidean_error_m"])
        self.assertEqual(b8["status"], "active")
        self.assertAlmostEqual(b8["required_max_euclidean_error_m"], 5.0e-6, places=15)
        self.assertAlmostEqual(b8["observed_max_euclidean_error_m"], probe["observed_max_euclidean_error_m"], places=15)
        self.assertIn("failed", b8["outcome"])
        self.assertIn("invalidated", b8["outcome"])

    def test_source_nominal_contact_outputs_are_retained_but_rigid_attachment_is_rejected(self) -> None:
        source = _load("data_catalog/wufr26_road_contact_reference_v0.toml")
        self.assertEqual(source["record_id"], "WUFR26_ROAD_CONTACT_REFERENCE_V0")
        contact = source["contact_reference"]
        self.assertEqual(contact["front_left_source_m"], [0.0, 0.61598556, 0.0])
        self.assertEqual(contact["front_right_source_m"], [0.0, -0.61598556, 0.0])
        self.assertEqual(contact["rear_left_source_m"], [-1.5624, 0.60328556, 0.0])
        self.assertEqual(contact["rear_right_source_m"], [-1.5624, -0.60328556, 0.0])
        self.assertIn("road-contact output", contact["construction_role"])
        self.assertIn("failed", contact["source_correlation_rule"])

        outcome = source["validation_outcome"]
        self.assertFalse(outcome["rigid_upright_attachment_validated"])
        self.assertAlmostEqual(outcome["maximum_selected_front_reconstruction_error_m"], 0.0008458158026623031, places=15)
        self.assertEqual(outcome["correction_authorization_id"], "AUTH-VEH-0007")
        self.assertFalse(source["authority_boundaries"]["rigid_upright_attached_contact_authority"])

    def test_architecture_and_runtime_steering_ownership_are_preserved_without_contact_fallback(self) -> None:
        source = _load("data_catalog/wufr26_road_contact_reference_v0.toml")
        contract = source["map_contract"]
        self.assertEqual(contract["body_coordinate_order"], ["z_s_m", "phi_rad", "theta_rad"])
        self.assertEqual(
            contract["wheel_coordinate_order"],
            [
                "front_left_delta_z_wc_body_m",
                "front_right_delta_z_wc_body_m",
                "rear_left_delta_z_wc_body_m",
                "rear_right_delta_z_wc_body_m",
            ],
        )
        self.assertIn("Architectural target only", contract["road_closure"])
        self.assertIn("replacement", contract["contact_coefficient"])
        steering = source["contact_reference"]["steering_rule"]
        self.assertIn("MOD-STEER-0001", steering)
        self.assertIn("centered rack", steering)
        self.assertIn("never", steering)
        self.assertIn("scalar Steer Angle", steering)

    def test_forbidden_shortcuts_and_unreviewed_replacement_tire_models_remain_prohibited(self) -> None:
        source = _load("data_catalog/wufr26_road_contact_reference_v0.toml")
        prohibited = "\n".join(source["authority_boundaries"]["prohibited_substitutions"]).lower()
        for phrase in (
            "body roll times track",
            "wheel-travel difference",
            "scalar spring or arb motion ratio",
            "scalar steer angle",
            "invalidated rigid upright-attached",
            "rigid circular tire",
            "hard-coded unit contact coefficient",
            "hard-coded -49.05 n",
        ):
            self.assertIn(phrase, prohibited)
        self.assertFalse(source["authority_boundaries"]["generic_tire_contact_patch_authority"])
        self.assertFalse(source["authority_boundaries"]["loaded_radius_authority"])
        self.assertFalse(source["authority_boundaries"]["tire_deflection_authority"])
        self.assertFalse(source["authority_boundaries"]["installed_as_built_authority"])

    def test_blocked_records_use_registry_valid_statuses(self) -> None:
        for relative in (
            "registry/records/equations/EQ-VEH-0011.toml",
            "registry/records/equations/EQ-VEH-0012.toml",
            "registry/records/equations/EQ-VEH-0013.toml",
            "registry/records/benchmarks/BENCH-VEH-0009.toml",
        ):
            self.assertEqual(_load(relative)["record"]["status"], "blocked")

    def test_next_gate_requires_replacement_contact_review_before_implementation(self) -> None:
        auth7 = _load("authorizations/vehicle/AUTH-VEH-0007.toml")
        next_gate = auth7["next_gate"]
        self.assertIn("replacement road-contact model", next_gate["required_decision"])
        self.assertIn("rigid circular", next_gate["required_decision"])
        self.assertIn("candidate, not an authorization", next_gate["required_decision"])
        self.assertIn("must merge before", next_gate["implementation_rule"])


if __name__ == "__main__":
    unittest.main()
