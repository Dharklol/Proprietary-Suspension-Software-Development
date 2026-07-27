from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WUFRRoadContactAuthorizationTests(unittest.TestCase):
    def test_authorization_packet_is_review_ready(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0006.toml")
        model = _load("registry/records/models/MOD-VEH-0006.toml")["record"]
        assumption = _load("registry/records/assumptions/ASM-VEH-0004.toml")["record"]
        self.assertEqual(auth["authorization_id"], "AUTH-VEH-0006")
        self.assertEqual(auth["status"], "review_ready")
        self.assertEqual(auth["scope"]["model_ids"], ["MOD-VEH-0006"])
        self.assertEqual(auth["scope"]["equation_ids"], ["EQ-VEH-0011", "EQ-VEH-0012", "EQ-VEH-0013"])
        self.assertEqual(auth["scope"]["benchmark_ids"], ["BENCH-VEH-0008", "BENCH-VEH-0009"])
        self.assertEqual(auth["scope"]["assumption_ids"], ["ASM-VEH-0004"])
        self.assertEqual(model["authorization_id"], "AUTH-VEH-0006")
        self.assertEqual(model["equation_ids"], ["EQ-VEH-0011", "EQ-VEH-0012", "EQ-VEH-0013"])
        self.assertIn("rigid upright-attached", assumption["description"])
        self.assertIn("not a generic tire", assumption["description"])

    def test_source_contact_points_and_contract_are_frozen(self) -> None:
        source = _load("data_catalog/wufr26_road_contact_reference_v0.toml")
        self.assertEqual(source["record_id"], "WUFR26_ROAD_CONTACT_REFERENCE_V0")
        contact = source["contact_reference"]
        self.assertEqual(contact["front_left_source_m"], [0.0, 0.61598556, 0.0])
        self.assertEqual(contact["front_right_source_m"], [0.0, -0.61598556, 0.0])
        self.assertEqual(contact["rear_left_source_m"], [-1.5624, 0.60328556, 0.0])
        self.assertEqual(contact["rear_right_source_m"], [-1.5624, -0.60328556, 0.0])
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
        self.assertIn("g_i", contract["road_closure"])
        self.assertIn("partial(z_w)", contract["jacobian"])

    def test_front_runtime_steering_ownership_is_explicit(self) -> None:
        source = _load("data_catalog/wufr26_road_contact_reference_v0.toml")
        rule = source["contact_reference"]["front_rule"]
        steering = source["contact_reference"]["steering_rule"]
        self.assertIn("MOD-SUSP-0002", rule)
        self.assertIn("MOD-STEER-0001", rule)
        self.assertIn("centered-rack", rule)
        self.assertIn("never", steering)
        self.assertIn("scalar Steer Angle", steering)
        auth = _load("authorizations/vehicle/AUTH-VEH-0006.toml")
        permitted = "\n".join(auth["permitted"]["items"])
        self.assertIn("No duplicate steering closure equation", permitted)

    def test_forbidden_shortcuts_remain_prohibited(self) -> None:
        source = _load("data_catalog/wufr26_road_contact_reference_v0.toml")
        prohibited = "\n".join(source["authority_boundaries"]["prohibited_substitutions"]).lower()
        for phrase in (
            "body roll times track",
            "wheel-travel difference",
            "scalar spring or arb motion ratio",
            "scalar steer angle",
            "translation-only front contact",
            "generic tire-radius",
            "hard-coded unit contact coefficient",
            "hard-coded -49.05 n",
        ):
            self.assertIn(phrase, prohibited)
        self.assertFalse(source["authority_boundaries"]["generic_tire_contact_patch_authority"])
        self.assertFalse(source["authority_boundaries"]["loaded_radius_authority"])
        self.assertFalse(source["authority_boundaries"]["tire_deflection_authority"])
        self.assertFalse(source["authority_boundaries"]["installed_as_built_authority"])

    def test_benchmarks_separate_source_reconstruction_from_runtime_map(self) -> None:
        b8 = _load("registry/records/benchmarks/BENCH-VEH-0008.toml")["record"]
        b9 = _load("registry/records/benchmarks/BENCH-VEH-0009.toml")["record"]
        self.assertEqual(b8["target_ids"], ["MOD-VEH-0006", "EQ-VEH-0011"])
        text8 = "\n".join(b8["acceptance_criteria"])
        self.assertIn("historical", text8.lower())
        self.assertIn("MOD-STEER-0001", text8)
        text9 = "\n".join(b9["acceptance_criteria"])
        self.assertIn("J_wb", text9)
        self.assertIn("5 kg unsprung gravity", text9)
        self.assertIn("structured failure", text9)


if __name__ == "__main__":
    unittest.main()
