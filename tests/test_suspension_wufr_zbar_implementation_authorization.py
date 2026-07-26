from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WufrZBarImplementationAuthorizationTests(unittest.TestCase):
    def test_auth_susp_0008_promotes_only_rocker_coordinate_force(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0008.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0008")
        self.assertEqual(auth["status"], "review_ready")
        scope = auth["scope"]
        self.assertTrue(scope["implementation_authorized"])
        self.assertTrue(scope["rocker_coordinate_generalized_force_authorized"])
        self.assertFalse(scope["wheel_coordinate_generalized_force_authorized"])
        self.assertFalse(scope["vehicle_equilibrium_authorized"])
        self.assertEqual(auth["numerics"]["input_coordinate_order"], ["theta_RL_rad", "theta_RR_rad"])
        self.assertEqual(auth["numerics"]["elastic_coordinate_order"], ["d_L_m", "d_R_m"])
        self.assertIn("energy", auth["numerics"]["energy_gradient_rule"].lower())

    def test_benchmark_and_model_point_to_the_promoted_implementation(self) -> None:
        benchmark = _load("registry/records/benchmarks/BENCH-SUSP-0016.toml")["record"]
        self.assertEqual(benchmark["authorization"], "authorizations/suspension/AUTH-SUSP-0008.toml")
        self.assertIn("MOD-SUSP-0005", benchmark["target_ids"])
        self.assertIn("rocker", benchmark["title"].lower())

        model = _load("registry/records/models/MOD-SUSP-0005.toml")["record"]
        self.assertIn("BENCH-SUSP-0016", model["benchmark_ids"])
        self.assertIn("AUTH-SUSP-0008", model["authorization_state"])
        self.assertIn("wufr_zbar.py", model["implementation_package"])
        self.assertIn("wheel", model["next_implementation_gate"].lower())

    def test_fixture_boundary_matches_authorization_chain(self) -> None:
        fixture = _load("benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml")
        boundary = fixture["current_boundary"]
        self.assertTrue(boundary["two_arm_elastic_coordinate_authorized"])
        self.assertTrue(boundary["rocker_coordinate_jacobian_authorized"])
        self.assertTrue(boundary["rocker_coordinate_generalized_force_authorized"])
        self.assertFalse(boundary["wheel_coordinate_generalized_force_authorized"])
        self.assertEqual(
            boundary["authorization_chain"],
            ["AUTH-SUSP-0006", "AUTH-SUSP-0007", "AUTH-SUSP-0008"],
        )


if __name__ == "__main__":
    unittest.main()
