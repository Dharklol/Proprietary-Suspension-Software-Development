from __future__ import annotations

import math
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


def _distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


class SuspensionActuationAuthorizationTests(unittest.TestCase):
    def test_authorization_is_bounded_and_review_ready(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0003.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0003")
        self.assertEqual(auth["status"], "review_ready")
        self.assertEqual(auth["scope"]["model_ids"], ["MOD-SUSP-0003"])
        self.assertEqual(
            auth["scope"]["equation_ids"],
            ["EQ-SUSP-0009", "EQ-SUSP-0010", "EQ-SUSP-0011", "EQ-SUSP-0012"],
        )
        self.assertEqual(
            auth["scope"]["benchmark_ids"],
            ["BENCH-SUSP-0007", "BENCH-SUSP-0008"],
        )
        self.assertEqual(
            auth["scope"]["upstream_model_ids"],
            ["MOD-SUSP-0001", "MOD-SUSP-0002"],
        )
        numerics = auth["numerics"]
        self.assertIn("d(delta_L_d_m)/d(delta_z_wc_body_m)", numerics["canonical_local_ratio"])
        self.assertFalse(numerics["hidden_clipping_allowed"])
        self.assertFalse(numerics["alternate_root_fallback_allowed"])
        self.assertFalse(numerics["extrapolation_allowed"])
        self.assertFalse(numerics["absolute_value_ratio_allowed"])
        prohibited = "\n".join(auth["prohibited"]["items"])
        self.assertIn("Motion Ratio Heave", prohibited)
        self.assertIn("Anti-roll-bar", prohibited)
        self.assertIn("installed suspension travel", prohibited)

    def test_authorization_matrix_explicitly_carries_actuation_scope(self) -> None:
        matrix = (ROOT / "docs/governance/implementation_authorization_matrix.md").read_text(encoding="utf-8")
        self.assertIn("`MOD-SUSP-0003`", matrix)
        self.assertIn("`EQ-SUSP-0009` through `0012`", matrix)
        self.assertIn("`AUTH-SUSP-0003`", matrix)
        self.assertIn("historical OptimumK `Motion Ratio Heave` as comparison-only evidence", matrix)
        self.assertIn("spring/damper forces", matrix)
        self.assertIn("installed/as-built validation", matrix)

    def test_model_and_equation_links_are_frozen(self) -> None:
        model = _load("registry/records/models/MOD-SUSP-0003.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0003")
        self.assertEqual(model["upstream_model_ids"], ["MOD-SUSP-0001", "MOD-SUSP-0002"])
        self.assertEqual(
            model["equation_ids"],
            ["EQ-SUSP-0009", "EQ-SUSP-0010", "EQ-SUSP-0011", "EQ-SUSP-0012"],
        )
        self.assertEqual(model["benchmark_ids"], ["BENCH-SUSP-0007", "BENCH-SUSP-0008"])
        for equation_id in model["equation_ids"]:
            record = _load(f"registry/records/equations/{equation_id}.toml")["record"]
            self.assertEqual(record["id"], equation_id)
            self.assertEqual(record["verification_level"], "none")
            self.assertEqual(set(record["benchmark_ids"]), {"BENCH-SUSP-0007", "BENCH-SUSP-0008"})

    def test_nominal_source_lengths_match_frozen_geometry(self) -> None:
        fixture = _load("benchmarks/suspension/WUFR26_OPTIMUMK_ACTUATION_V0.toml")
        tolerance = fixture["tolerances"]["nominal_length_mm"]
        for axle in ("front", "rear"):
            points = fixture[axle]["left"]
            pp_length = _distance(points["arm_attachment_mm"], points["rocker_rod_point_mm"])
            coil_length = _distance(points["coilover_chassis_mm"], points["rocker_coilover_point_mm"])
            self.assertLessEqual(abs(pp_length - fixture[axle]["nominal_push_pull_length_mm"]), tolerance)
            self.assertLessEqual(abs(coil_length - fixture[axle]["nominal_coilover_length_mm"]), tolerance)

    def test_source_roles_are_front_upper_rear_lower(self) -> None:
        fixture = _load("benchmarks/suspension/WUFR26_OPTIMUMK_ACTUATION_V0.toml")
        snapshot = _load("data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml")
        self.assertEqual(fixture["front"]["actuation_attachment"], "upper_arm")
        self.assertEqual(fixture["rear"]["actuation_attachment"], "lower_arm")
        self.assertEqual(snapshot["front"]["actuation_attachment"], "upper_arm")
        self.assertEqual(snapshot["rear"]["actuation_attachment"], "lower_arm")

    def test_source_heave_fixture_is_complete_and_scalar_displacement_is_consistent(self) -> None:
        fixture = _load("benchmarks/suspension/WUFR26_OPTIMUMK_ACTUATION_V0.toml")
        states = fixture["states"]
        self.assertEqual(len(states), 11)
        self.assertEqual(states[0]["heave_mm"], -25.4)
        self.assertEqual(states[5]["heave_mm"], 0.0)
        self.assertEqual(states[-1]["heave_mm"], 25.4)
        tol = fixture["tolerances"]["source_scalar_mm"] + 1.0e-12
        for state in states:
            for axle in ("front", "rear"):
                length = state[f"{axle}_coilover_length_mm"]
                nominal = fixture[axle]["nominal_coilover_length_mm"]
                displacement = state[f"{axle}_coilover_displacement_mm"]
                self.assertLessEqual(abs((length - nominal) - displacement), tol)
                self.assertTrue(math.isfinite(state[f"{axle}_source_motion_ratio_heave"]))

    def test_historical_ratio_is_explicitly_not_canonical_ratio(self) -> None:
        fixture = _load("benchmarks/suspension/WUFR26_OPTIMUMK_ACTUATION_V0.toml")
        auth = _load("authorizations/suspension/AUTH-SUSP-0003.toml")
        self.assertIn("historical source output", fixture["source"]["source_motion_ratio_channel"])
        self.assertIn("delta_z_wc_body", auth["numerics"]["canonical_local_ratio"])
        self.assertNotEqual(
            fixture["source"]["source_motion_ratio_channel"],
            auth["numerics"]["canonical_local_ratio"],
        )
        self.assertAlmostEqual(fixture["states"][5]["front_source_motion_ratio_heave"], 1.221)
        self.assertAlmostEqual(fixture["states"][5]["rear_source_motion_ratio_heave"], 1.006)

    def test_benchmark_records_preserve_scope_and_installed_boundary(self) -> None:
        for benchmark_id in ("BENCH-SUSP-0007", "BENCH-SUSP-0008"):
            record = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertEqual(record["id"], benchmark_id)
            self.assertIn("MOD-SUSP-0003", record["target_ids"])
        b8 = _load("registry/records/benchmarks/BENCH-SUSP-0008.toml")["record"]
        criteria = "\n".join(b8["acceptance_criteria"])
        self.assertIn("11 frozen pure-heave", criteria)
        self.assertIn("Motion Ratio Heave", criteria)
        self.assertIn("installed bump-stop", criteria)


if __name__ == "__main__":
    unittest.main()
