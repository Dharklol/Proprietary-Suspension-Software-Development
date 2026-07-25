from __future__ import annotations

import math
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class SuspensionKinematicsAuthorizationTests(unittest.TestCase):
    def test_authorization_packet_is_review_ready_and_bounded(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0001.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0001")
        self.assertEqual(auth["status"], "review_ready")
        self.assertEqual(auth["scope"]["model_ids"], ["MOD-SUSP-0001"])
        self.assertEqual(
            auth["scope"]["equation_ids"],
            ["EQ-SUSP-0001", "EQ-SUSP-0002", "EQ-SUSP-0003", "EQ-SUSP-0004"],
        )
        self.assertEqual(
            auth["scope"]["benchmark_ids"],
            ["BENCH-SUSP-0001", "BENCH-SUSP-0002", "BENCH-SUSP-0003"],
        )
        prohibited = "\n".join(auth["prohibited"]["items"])
        self.assertIn("front steering tie rod", prohibited)
        self.assertIn("wheel-center", prohibited)
        self.assertIn("1562.4 mm", prohibited)
        self.assertFalse(auth["numerics"]["unconstrained_newton_default_allowed"])
        self.assertFalse(auth["numerics"]["alternate_root_fallback_allowed"])
        self.assertFalse(auth["numerics"]["extrapolation_allowed"])

    def test_model_record_links_equations_benchmarks_and_authorization(self) -> None:
        model = _load("registry/records/models/MOD-SUSP-0001.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0001")
        self.assertEqual(
            model["equation_ids"],
            ["EQ-SUSP-0001", "EQ-SUSP-0002", "EQ-SUSP-0003", "EQ-SUSP-0004"],
        )
        self.assertEqual(
            model["benchmark_ids"],
            ["BENCH-SUSP-0001", "BENCH-SUSP-0002", "BENCH-SUSP-0003"],
        )
        self.assertIn("pending_PR39_merge", model["authorization_state"])

    def test_all_equation_records_point_to_frozen_benchmarks(self) -> None:
        expected = {
            "EQ-SUSP-0001": {"BENCH-SUSP-0001", "BENCH-SUSP-0002"},
            "EQ-SUSP-0002": {"BENCH-SUSP-0001", "BENCH-SUSP-0002"},
            "EQ-SUSP-0003": {"BENCH-SUSP-0001", "BENCH-SUSP-0002"},
            "EQ-SUSP-0004": {"BENCH-SUSP-0003"},
        }
        for equation_id, benchmark_ids in expected.items():
            record = _load(f"registry/records/equations/{equation_id}.toml")["record"]
            self.assertEqual(record["id"], equation_id)
            self.assertEqual(set(record["benchmark_ids"]), benchmark_ids)
            self.assertEqual(record["verification_level"], "none")

    def test_parallel_arm_fixture_matches_closed_form(self) -> None:
        fixture = _load("benchmarks/suspension/GEO-SUSP-BASIC-001.toml")
        tol = fixture["tolerances"]["position_m"]
        for state in fixture["states"]:
            q = math.radians(state["q_L_deg"])
            expected_lower = (0.0, 0.4 * math.cos(q), 0.4 * math.sin(q))
            expected_upper = (0.0, expected_lower[1], 0.2 + expected_lower[2])
            self.assertEqual(state["expected_q_U_deg"], state["q_L_deg"])
            for actual, expected in zip(state["expected_lower_upright_m"], expected_lower):
                self.assertLessEqual(abs(actual - expected), tol)
            for actual, expected in zip(state["expected_upper_upright_m"], expected_upper):
                self.assertLessEqual(abs(actual - expected), tol)
            separation = math.dist(
                state["expected_lower_upright_m"], state["expected_upper_upright_m"]
            )
            self.assertLessEqual(abs(separation - 0.2), tol)

    def test_rear_toe_fixture_has_known_ten_degree_solution(self) -> None:
        fixture = _load("benchmarks/suspension/GEO-SUSP-REAR-TOE-001.toml")
        ref = fixture["current_reference"]["zero_twist_toe_outboard_m"]
        psi = math.radians(fixture["expected"]["twist_deg"])
        rotated = (
            ref[0] * math.cos(psi) - ref[1] * math.sin(psi),
            ref[0] * math.sin(psi) + ref[1] * math.cos(psi),
            ref[2],
        )
        tol = fixture["tolerances"]["position_m"]
        for actual, expected in zip(rotated, fixture["expected"]["toe_outboard_m"]):
            self.assertLessEqual(abs(actual - expected), tol)
        length = math.dist(rotated, fixture["current_reference"]["toe_inboard_m"])
        self.assertLessEqual(
            abs(length - fixture["current_reference"]["nominal_toe_link_length_m"]),
            fixture["tolerances"]["length_residual_m"],
        )

    def test_wufr_front_fixture_preserves_source_and_exclusions(self) -> None:
        fixture = _load(
            "benchmarks/suspension/WUFR26_OPTIMUMK_HEAVE_FRONT_KINEMATICS_V0.toml"
        )
        self.assertEqual(
            fixture["source_sha256"],
            "db071b7e696149ec82213e9ed05aa557349d18d19debe7925e7e01058534e4b8",
        )
        self.assertEqual(fixture["source_export_version"], "2.3.0")
        self.assertEqual(len(fixture["states"]), 11)
        self.assertEqual([state["heave_mm"] for state in fixture["states"]], [
            -25.4, -20.32, -15.24, -10.16, -5.08, 0.0, 5.08, 10.16, 15.24, 20.32, 25.4
        ])
        nominal = fixture["states"][5]
        self.assertEqual(nominal["q_L_deg"], 0.0)
        self.assertEqual(nominal["expected_q_U_deg"], 0.0)
        self.assertEqual(fixture["tolerances"]["position_m"], 2e-6)
        excluded = "\n".join(fixture["excluded_channels"]["items"])
        self.assertIn("Toe Angle", excluded)
        self.assertIn("bump steer", excluded)
        self.assertIn("do_not_generalize", fixture["adapter"]["applicability"])
        self.assertEqual(
            fixture["rear_origin_observation"]["status"],
            "evidence_only_not_authorized_in_PR39",
        )


if __name__ == "__main__":
    unittest.main()
