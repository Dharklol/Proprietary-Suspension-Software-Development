from __future__ import annotations

from pathlib import Path
import math
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WUFRStaticGravityAuthorizationTests(unittest.TestCase):
    def test_authorization_and_assumption_are_review_ready(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0005.toml")
        assumption = _load("registry/records/assumptions/ASM-VEH-0003.toml")["record"]
        model = _load("registry/records/models/MOD-VEH-0005.toml")["record"]
        benchmark = _load("registry/records/benchmarks/BENCH-VEH-0007.toml")["record"]

        self.assertEqual(auth["authorization_id"], "AUTH-VEH-0005")
        self.assertEqual(auth["status"], "review_ready")
        self.assertEqual(auth["scope"]["model_ids"], ["MOD-VEH-0005"])
        self.assertEqual(auth["scope"]["benchmark_ids"], ["BENCH-VEH-0007"])
        self.assertIn("ASM-VEH-0003", auth["scope"]["assumption_ids"])
        self.assertEqual(assumption["status"], "active")
        self.assertEqual(model["authorization_id"], "AUTH-VEH-0005")
        self.assertEqual(model["benchmark_ids"], ["BENCH-VEH-0007"])
        self.assertIn("MOD-VEH-0005", benchmark["target_ids"])

    def test_reviewed_allocation_reconciles_measured_axle_totals(self) -> None:
        source = _load("data_catalog/wufr27_static_gravity_allocation_v0.toml")
        masses = source["prototype_unsprung_allocation"]["corner_mass_kg"]
        self.assertEqual(masses, [5.0, 5.0, 5.0, 5.0])
        self.assertAlmostEqual(sum(masses[:2]), source["source"]["reviewed_front_unsprung_axle_mass_kg"], places=12)
        self.assertAlmostEqual(sum(masses[2:]), source["source"]["reviewed_rear_unsprung_axle_mass_kg"], places=12)
        self.assertAlmostEqual(sum(masses), 20.0, places=12)

    def test_mass_and_first_moment_decomposition_is_independent(self) -> None:
        source = _load("data_catalog/wufr27_static_gravity_allocation_v0.toml")
        total_mass = 675.0 * 0.45359237
        self.assertAlmostEqual(total_mass, source["source"]["total_mass_kg"], places=12)

        wheel_masses = source["prototype_unsprung_allocation"]["corner_mass_kg"]
        wheel_points = source["prototype_unsprung_allocation"]["nominal_wheel_center_source_m"]
        total_cg = source["derived_sprung_body"]["total_cg_source_m"]
        sprung_mass = total_mass - sum(wheel_masses)
        expected_sprung = []
        for axis in range(3):
            unsprung_first_moment = sum(mass * point[axis] for mass, point in zip(wheel_masses, wheel_points))
            expected_sprung.append((total_mass * total_cg[axis] - unsprung_first_moment) / sprung_mass)

        self.assertAlmostEqual(sprung_mass, source["derived_sprung_body"]["sprung_mass_kg"], places=12)
        for actual, expected in zip(source["derived_sprung_body"]["sprung_cg_source_m"], expected_sprung):
            self.assertAlmostEqual(actual, expected, places=12)

        sprung_cg = source["derived_sprung_body"]["sprung_cg_source_m"]
        for axis in range(3):
            reconstructed = sprung_mass * sprung_cg[axis] + sum(
                mass * point[axis] for mass, point in zip(wheel_masses, wheel_points)
            )
            self.assertAlmostEqual(reconstructed, total_mass * total_cg[axis], places=11)

    def test_gravity_magnitudes_and_authority_boundaries_are_frozen(self) -> None:
        source = _load("data_catalog/wufr27_static_gravity_allocation_v0.toml")
        g = source["gravity"]["g_mps2"]
        self.assertTrue(math.isfinite(g) and g > 0.0)
        self.assertAlmostEqual(
            source["gravity"]["sprung_weight_N"],
            source["derived_sprung_body"]["sprung_mass_kg"] * g,
            places=10,
        )
        self.assertAlmostEqual(source["gravity"]["nominal_each_unsprung_weight_N"], 5.0 * g, places=12)
        boundaries = source["authority_boundaries"]
        self.assertTrue(boundaries["static_gravity_prototype_authority"])
        self.assertFalse(boundaries["measured_per_corner_unsprung_mass"])
        self.assertFalse(boundaries["measured_unsprung_cg"])
        self.assertFalse(boundaries["installed_as_built_authority"])
        self.assertFalse(boundaries["road_compatibility_map_authority"])
        self.assertFalse(boundaries["full_wufr_equilibrium_authority"])
        prohibited = "\n".join(boundaries["prohibited_substitutions"]).lower()
        self.assertIn("10 kg per corner", prohibited)
        self.assertIn("207 kg", prohibited)
        self.assertIn("220 kg car + 100 kg driver", prohibited)

    def test_wheel_gravity_projection_is_not_silently_scalarized(self) -> None:
        source = _load("data_catalog/wufr27_static_gravity_allocation_v0.toml")
        rule = source["prototype_unsprung_allocation"]["wheel_generalized_force_rule"].lower()
        self.assertIn("virtual work", rule)
        self.assertIn("do not replace", rule)
        review = (ROOT / "docs/reviews/phase2_wufr_gravity_allocation_authorization_review.md").read_text(encoding="utf-8").lower()
        self.assertIn("constant `-49.05 n`", review)
        self.assertIn("road-compatible four-corner map", review)


if __name__ == "__main__":
    unittest.main()
