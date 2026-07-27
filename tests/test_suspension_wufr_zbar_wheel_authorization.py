from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WufrZBarWheelAuthorizationTests(unittest.TestCase):
    def test_auth_susp_0009_authorizes_only_physical_wheel_coordinate_force(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0009.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0009")
        self.assertEqual(auth["status"], "review_ready")
        self.assertTrue(auth["scope"]["wheel_coordinate_map_authorized"])
        self.assertTrue(auth["scope"]["wheel_coordinate_generalized_force_authorized"])
        self.assertFalse(auth["scope"]["vehicle_equilibrium_authorized"])
        self.assertFalse(auth["scope"]["body_roll_reduction_authorized"])
        self.assertEqual(
            auth["coordinates"]["wheel_coordinate_order"],
            ["delta_z_wc_body_left_m", "delta_z_wc_body_right_m"],
        )
        self.assertIn("positive upward", auth["coordinates"]["wheel_coordinate_sign"].lower())
        self.assertIn("diag", auth["coordinates"]["rocker_to_wheel_jacobian"].lower())
        self.assertIn("q_z", auth["coordinates"]["generalized_force"].lower())

    def test_historical_motion_ratio_and_body_roll_shortcuts_remain_blocked(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0009.toml")
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        self.assertIn("optimumk motion ratio heave", prohibited)
        self.assertIn("track width", prohibited)
        self.assertIn("body roll", prohibited)
        self.assertIn("load transfer", prohibited)
        self.assertFalse(auth["numerics"]["historical_motion_ratio_allowed"])
        self.assertFalse(auth["numerics"]["absolute_value_ratio_allowed"])
        self.assertFalse(auth["numerics"]["body_roll_substitution_allowed"])
        self.assertFalse(auth["numerics"]["track_width_approximation_allowed"])

    def test_benchmark_and_model_promote_wheel_coordinate_chain(self) -> None:
        benchmark = _load("registry/records/benchmarks/BENCH-SUSP-0017.toml")["record"]
        self.assertEqual(benchmark["authorization"], "authorizations/suspension/AUTH-SUSP-0009.toml")
        self.assertIn("MOD-SUSP-0005", benchmark["target_ids"])
        self.assertIn("energy-gradient", benchmark["title"].lower())

        model = _load("registry/records/models/MOD-SUSP-0005.toml")["record"]
        self.assertIn("BENCH-SUSP-0017", model["benchmark_ids"])
        self.assertIn("AUTH-SUSP-0009", model["authorization_state"])
        self.assertIn("wufr_zbar_wheel.py", model["implementation_package"])
        self.assertIn("whole-vehicle", model["next_implementation_gate"].lower())

    def test_current_package_stops_at_wheel_force_not_vehicle_equilibrium(self) -> None:
        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        boundary = package["authority_boundaries"]
        self.assertTrue(boundary["rocker_coordinate_generalized_force_authorized"])
        self.assertTrue(boundary["wheel_coordinate_generalized_force_authorized"])
        self.assertFalse(boundary["vehicle_equilibrium_authorized"])
        self.assertEqual(
            boundary["wheel_coordinate_order"],
            ["delta_z_wc_body_left_m", "delta_z_wc_body_right_m"],
        )
        self.assertFalse(boundary["historical_motion_ratio_substitution_allowed"])


if __name__ == "__main__":
    unittest.main()
