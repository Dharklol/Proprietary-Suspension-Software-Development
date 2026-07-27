from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from scripts.run_wufr_static_gravity_benchmarks import build_report


ROOT = Path(__file__).resolve().parents[1]


class WUFRStaticGravityResultRecordTests(unittest.TestCase):
    def test_frozen_result_matches_live_benchmark(self) -> None:
        with (ROOT / "benchmarks/vehicle/wufr_static_gravity_result_v0.1.0.toml").open("rb") as stream:
            frozen = tomllib.load(stream)
        live = build_report()["BENCH-VEH-0007"]
        expected = frozen["BENCH-VEH-0007"]

        self.assertTrue(live["pass"])
        self.assertEqual(live["record_id"], expected["record_id"])
        self.assertEqual(live["assumption_id"], expected["assumption_id"])
        self.assertEqual(live["unsprung_corner_mass_kg"], expected["unsprung_corner_mass_kg"])
        self.assertAlmostEqual(live["total_mass_kg"], expected["total_mass_kg"], places=12)
        self.assertAlmostEqual(live["sprung_mass_kg"], expected["sprung_mass_kg"], places=12)
        for actual, target in zip(live["sprung_cg_source_m"], expected["sprung_cg_source_m"]):
            self.assertAlmostEqual(actual, target, places=12)
        for actual, target in zip(live["sprung_cg_body_offset_m"], expected["sprung_cg_body_offset_m"]):
            self.assertAlmostEqual(actual, target, places=12)
        self.assertLessEqual(live["mass_recombination_error_kg"], 1.0e-12)
        self.assertLessEqual(live["maximum_first_moment_error_kg_m"], 1.0e-11)
        self.assertAlmostEqual(live["sprung_weight_N"], expected["sprung_weight_N"], places=9)
        self.assertAlmostEqual(
            live["each_nominal_unsprung_weight_N"],
            expected["each_nominal_unsprung_weight_N"],
            places=12,
        )
        for actual, target in zip(
            live["sprung_body_generalized_gravity_nominal"],
            expected["sprung_body_generalized_gravity_nominal"],
        ):
            self.assertAlmostEqual(actual, target, places=9)
        self.assertFalse(live["installed_as_built_authority"])
        self.assertFalse(live["maneuver_unsprung_inertia_authority"])
        self.assertFalse(live["wheel_gravity_generalized_force_hardcoded"])
        self.assertFalse(live["road_reactions_available"])


if __name__ == "__main__":
    unittest.main()
