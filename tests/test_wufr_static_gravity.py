from __future__ import annotations

from pathlib import Path
import math
import tempfile
import unittest

from pssd_vehicle.force_coordinates import BodyPose
from pssd_vehicle.wufr_gravity import (
    CORNER_ORDER,
    WUFRGravityError,
    WUFRGravityFailureCode,
    load_wufr_static_gravity_allocation,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml"


class WUFRStaticGravityTests(unittest.TestCase):
    def test_loader_reconstructs_reviewed_mass_and_first_moments(self) -> None:
        allocation = load_wufr_static_gravity_allocation(SOURCE)
        self.assertEqual(tuple(item.corner_id for item in allocation.unsprung), CORNER_ORDER)
        self.assertEqual(tuple(item.mass_kg for item in allocation.unsprung), (5.0, 5.0, 5.0, 5.0))
        self.assertAlmostEqual(allocation.total_mass_kg, 306.17484975, places=12)
        self.assertAlmostEqual(allocation.total_unsprung_mass_kg, 20.0, places=12)
        self.assertAlmostEqual(allocation.sprung.mass_kg, 286.17484975, places=12)
        expected = (-0.7428152951513378, 0.006753924590788551, 0.29429108288542044)
        for actual, target in zip(allocation.sprung.source_position_m, expected):
            self.assertAlmostEqual(actual, target, places=12)
        self.assertLessEqual(max(abs(v) for v in allocation.first_moment_residual_kg_m()), 1.0e-11)

    def test_gravity_actions_preserve_point_force_semantics(self) -> None:
        allocation = load_wufr_static_gravity_allocation(SOURCE)
        for item in allocation.unsprung:
            force = item.force_N(allocation.g_mps2)
            self.assertEqual(force[:2], (0.0, 0.0))
            self.assertAlmostEqual(force[2], -49.05, places=12)
            self.assertIsNone(item.body_position_m)
        self.assertAlmostEqual(
            -allocation.sprung.force_N(allocation.g_mps2)[2],
            2807.3752760475004,
            places=9,
        )

    def test_sprung_body_generalized_gravity_uses_derived_cg_offset(self) -> None:
        allocation = load_wufr_static_gravity_allocation(SOURCE)
        pose = BodyPose(
            "WUFR27_NOMINAL_ROAD",
            "WUFR27_NOMINAL_ROAD_ORIGIN",
            "WUFR27_BODY_DRIVER_NO_FUEL_REFERENCE",
            "WUFR27_CG_DRIVER_NO_FUEL_REFERENCE",
        )
        result = allocation.sprung_body_generalized_gravity(pose)
        weight = allocation.sprung.mass_kg * allocation.g_mps2
        x, y, _ = allocation.sprung.body_position_m or (math.nan, math.nan, math.nan)
        self.assertAlmostEqual(result.generalized_force[0], -weight, places=9)
        self.assertAlmostEqual(result.generalized_force[1], -weight * y, places=9)
        self.assertAlmostEqual(result.generalized_force[2], weight * x, places=9)
        self.assertEqual(result.coordinate_order, ("z_s_m", "phi_rad", "theta_rad"))

    def test_authority_exceedance_is_structured(self) -> None:
        allocation = load_wufr_static_gravity_allocation(SOURCE)
        with self.assertRaises(WUFRGravityError) as installed:
            allocation.require_static_rnd_authority(installed_as_built=True)
        self.assertEqual(installed.exception.code, WUFRGravityFailureCode.AUTHORITY_EXCEEDED)
        with self.assertRaises(WUFRGravityError) as maneuver:
            allocation.require_static_rnd_authority(maneuver_inertia=True)
        self.assertEqual(maneuver.exception.code, WUFRGravityFailureCode.AUTHORITY_EXCEEDED)

    def test_source_mismatch_and_allocation_mismatch_fail_without_fallback(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            bad_source = Path(temp) / "bad_source.toml"
            bad_source.write_text(
                text.replace(
                    'record_id = "WUFR27_STATIC_GRAVITY_ALLOCATION_V0"',
                    'record_id = "OTHER"',
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(WUFRGravityError) as mismatch:
                load_wufr_static_gravity_allocation(bad_source)
            self.assertEqual(mismatch.exception.code, WUFRGravityFailureCode.SOURCE_MISMATCH)

            bad_mass = Path(temp) / "bad_mass.toml"
            bad_mass.write_text(
                text.replace(
                    'corner_mass_kg = [5.0, 5.0, 5.0, 5.0]',
                    'corner_mass_kg = [6.0, 4.0, 5.0, 5.0]',
                    1,
                ),
                encoding="utf-8",
            )
            # Axle sum remains 10 kg; first-moment consistency still rejects the mutation.
            with self.assertRaises(WUFRGravityError) as first_moment:
                load_wufr_static_gravity_allocation(bad_mass)
            self.assertEqual(
                first_moment.exception.code,
                WUFRGravityFailureCode.FIRST_MOMENT_MISMATCH,
            )

            bad_axle = Path(temp) / "bad_axle.toml"
            bad_axle.write_text(
                text.replace(
                    'corner_mass_kg = [5.0, 5.0, 5.0, 5.0]',
                    'corner_mass_kg = [6.0, 5.0, 5.0, 5.0]',
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(WUFRGravityError) as axle:
                load_wufr_static_gravity_allocation(bad_axle)
            self.assertEqual(axle.exception.code, WUFRGravityFailureCode.AXLE_ALLOCATION_MISMATCH)


if __name__ == "__main__":
    unittest.main()
