from __future__ import annotations

import math
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class WheelReferenceAuthorizationTests(unittest.TestCase):
    def test_authorization_is_bounded_and_review_ready(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0002.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0002")
        self.assertEqual(auth["status"], "review_ready")
        self.assertEqual(auth["scope"]["model_ids"], ["MOD-SUSP-0002"])
        self.assertEqual(
            auth["scope"]["equation_ids"],
            ["EQ-SUSP-0005", "EQ-SUSP-0006", "EQ-SUSP-0007", "EQ-SUSP-0008"],
        )
        self.assertEqual(
            auth["scope"]["benchmark_ids"],
            ["BENCH-SUSP-0004", "BENCH-SUSP-0005", "BENCH-SUSP-0006"],
        )
        prohibited = "\n".join(auth["prohibited"]["items"])
        self.assertIn("Steer Angle", prohibited)
        self.assertIn("nonzero", prohibited)
        self.assertIn("front steering tie rod", prohibited)
        self.assertIn("contact-patch", prohibited)
        self.assertFalse(auth["numerics"]["hidden_clipping_allowed"])
        self.assertFalse(auth["numerics"]["alternate_root_fallback_allowed"])
        self.assertFalse(auth["numerics"]["extrapolation_allowed"])
        self.assertEqual(auth["source_boundary"]["wheelbase_m"], 1.5624)

    def test_model_and_equations_have_frozen_links(self) -> None:
        model = _load("registry/records/models/MOD-SUSP-0002.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0002")
        self.assertEqual(model["upstream_model_ids"], ["MOD-SUSP-0001"])
        self.assertEqual(
            model["equation_ids"],
            ["EQ-SUSP-0005", "EQ-SUSP-0006", "EQ-SUSP-0007", "EQ-SUSP-0008"],
        )
        self.assertEqual(
            model["benchmark_ids"],
            ["BENCH-SUSP-0004", "BENCH-SUSP-0005", "BENCH-SUSP-0006"],
        )
        expected = {
            "EQ-SUSP-0005": {"BENCH-SUSP-0004"},
            "EQ-SUSP-0006": {"BENCH-SUSP-0004", "BENCH-SUSP-0005", "BENCH-SUSP-0006"},
            "EQ-SUSP-0007": {"BENCH-SUSP-0006"},
            "EQ-SUSP-0008": {"BENCH-SUSP-0005"},
        }
        for equation_id, benchmark_ids in expected.items():
            record = _load(f"registry/records/equations/{equation_id}.toml")["record"]
            self.assertEqual(record["id"], equation_id)
            self.assertEqual(record["verification_level"], "none")
            self.assertEqual(set(record["benchmark_ids"]), benchmark_ids)

    def test_nominal_wheel_centers_match_source_construction(self) -> None:
        fixture = _load("benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml")
        radius_m = fixture["nominal_source"]["tire_radius_mm"] * 1.0e-3
        source = fixture["nominal_source"]
        expected_by_key = {
            (row["axle"], row["side"]): row for row in fixture["nominal_expected"]
        }
        for axle in ("front", "rear"):
            half_track_m = source[axle]["half_track_mm"] * 1.0e-3
            camber = math.radians(source[axle]["static_camber_deg"])
            for side, side_sign in (("left", 1.0), ("right", -1.0)):
                expected = expected_by_key[(axle, side)]["wheel_center_m"]
                actual = (
                    0.0,
                    side_sign * (half_track_m + radius_m * math.sin(camber)),
                    radius_m * math.cos(camber),
                )
                for got, want in zip(actual, expected):
                    self.assertLessEqual(
                        abs(got - want), fixture["tolerances"]["nominal_wheel_center_m"]
                    )

    def test_frozen_wheel_plane_basis_matches_reviewed_alignment_convention(self) -> None:
        fixture = _load("benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml")
        source = fixture["nominal_source"]
        rows = {(row["axle"], row["side"]): row for row in fixture["nominal_expected"]}
        tol = fixture["tolerances"]["nominal_plane_component"]
        for axle in ("front", "rear"):
            toe = math.radians(source[axle]["static_toe_out_deg"])
            camber = math.radians(source[axle]["static_camber_deg"])
            for side, side_sign in (("left", 1.0), ("right", -1.0)):
                heading = side_sign * toe
                forward = (math.cos(heading), math.sin(heading), 0.0)
                outward = (
                    -side_sign * math.sin(heading),
                    side_sign * math.cos(heading),
                    0.0,
                )
                normal = (
                    math.cos(camber) * outward[0],
                    math.cos(camber) * outward[1],
                    -math.sin(camber),
                )
                row = rows[(axle, side)]
                self.assertLessEqual(abs(math.degrees(heading) - row["heading_deg"]), 1e-12)
                for got, want in zip(forward, row["forward_reference"]):
                    self.assertLessEqual(abs(got - want), tol)
                for got, want in zip(normal, row["plane_normal"]):
                    self.assertLessEqual(abs(got - want), tol)
                self.assertLessEqual(abs(_dot(forward, normal)), 2e-16)

    def test_source_steering_removal_freeze_does_not_equate_scalar_steer_angle(self) -> None:
        fixture = _load("benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml")
        section = fixture["source_front_steering_removal"]
        self.assertEqual(section["scalar_steer_angle_role"], "comparison_only_not_rotation_input")
        states = section["states"]
        self.assertEqual(len(states), 11)
        self.assertEqual(states[5]["heave_mm"], 0.0)
        self.assertEqual(states[5]["reconstructed_twist_deg"], 0.0)
        representative = [state for state in states if "source_scalar_steer_angle_deg" in state]
        self.assertGreaterEqual(len(representative), 4)
        endpoint = states[0]
        self.assertGreater(
            abs(endpoint["reconstructed_twist_deg"] - endpoint["source_scalar_steer_angle_deg"]),
            0.08,
        )
        endpoint = states[-1]
        self.assertGreater(
            abs(endpoint["reconstructed_twist_deg"] - endpoint["source_scalar_steer_angle_deg"]),
            0.08,
        )

    def test_benchmark_records_preserve_scope(self) -> None:
        for benchmark_id in ("BENCH-SUSP-0004", "BENCH-SUSP-0005", "BENCH-SUSP-0006"):
            record = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertEqual(record["id"], benchmark_id)
            self.assertIn("MOD-SUSP-0002", record["target_ids"])
        b5 = _load("registry/records/benchmarks/BENCH-SUSP-0005.toml")["record"]
        self.assertIn("Steer Angle", "\n".join(b5["acceptance_criteria"]))
        b6 = _load("registry/records/benchmarks/BENCH-SUSP-0006.toml")["record"]
        criteria = "\n".join(b6["acceptance_criteria"])
        self.assertIn("body-frame", criteria)
        self.assertIn("ambiguous", criteria)


if __name__ == "__main__":
    unittest.main()
