from __future__ import annotations

import math
from pathlib import Path
import tempfile
import textwrap
import unittest

from pssd_vehicle.reference import VehicleReferenceError, load_vehicle_reference


ROOT = Path(__file__).resolve().parents[1]
SELECTOR = ROOT / "configurations/education/WUFR27_EDUCATION_BASELINE_V0.toml"


class VehicleReferenceTests(unittest.TestCase):
    def test_reviewed_wufr27_reference_loads_without_duplicating_vehicle_values(self) -> None:
        vehicle = load_vehicle_reference(SELECTOR)

        self.assertEqual(vehicle.selector_id, "WUFR27_EDUCATION_BASELINE_V0")
        self.assertEqual(vehicle.vehicle_revision, "WUFR-27")
        self.assertEqual(vehicle.source_configuration_id, "WUFR27_SUSPENSION_BASELINE_V0")
        self.assertEqual(vehicle.whole_vehicle_adapter_id, "WUFR26_WHOLE_VEHICLE_FRAME_V0")
        self.assertEqual(vehicle.gravity_record_id, "WUFR27_STATIC_GRAVITY_ALLOCATION_V0")

        self.assertAlmostEqual(vehicle.total_mass_kg, 306.17484975, places=10)
        self.assertAlmostEqual(vehicle.g_mps2, 9.81, places=12)
        self.assertAlmostEqual(vehicle.geometry.wheelbase_m, 1.5624, places=12)
        self.assertAlmostEqual(vehicle.geometry.front_track_m, 1.231972, places=12)
        self.assertAlmostEqual(vehicle.geometry.rear_track_m, 1.206572, places=12)
        self.assertAlmostEqual(vehicle.cg.height_above_nominal_road_m, 0.290, places=12)
        self.assertEqual(
            vehicle.scale_state.corner_order,
            ("front_left", "front_right", "rear_left", "rear_right"),
        )
        self.assertEqual(vehicle.scale_state.corner_load_lb, (178.0, 175.0, 163.0, 159.0))
        self.assertAlmostEqual(vehicle.scale_state.total_load_lb, 675.0, places=12)

    def test_reference_has_basic_physical_invariants(self) -> None:
        vehicle = load_vehicle_reference(SELECTOR)

        self.assertGreater(vehicle.total_mass_kg, 0.0)
        self.assertGreater(vehicle.total_weight_N, 0.0)
        self.assertTrue(
            math.isclose(
                vehicle.geometry.cg_to_front_axle_m
                + vehicle.geometry.cg_to_rear_axle_m,
                vehicle.geometry.wheelbase_m,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
        )
        self.assertTrue(
            math.isclose(
                vehicle.total_weight_N,
                vehicle.total_mass_kg * vehicle.g_mps2,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
        )
        self.assertTrue(
            math.isclose(
                vehicle.scale_state.front_fraction,
                vehicle.geometry.cg_to_rear_axle_m / vehicle.geometry.wheelbase_m,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
        )
        self.assertTrue(
            math.isclose(
                vehicle.scale_state.rear_fraction,
                vehicle.geometry.cg_to_front_axle_m / vehicle.geometry.wheelbase_m,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
        )

    def test_selector_rejects_declared_source_identity_mismatch(self) -> None:
        original = SELECTOR.read_text(encoding="utf-8")
        modified = original.replace(
            'static_gravity_record_id = "WUFR27_STATIC_GRAVITY_ALLOCATION_V0"',
            'static_gravity_record_id = "NOT_THE_REVIEWED_RECORD"',
        )
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            selector_path = temporary_path / "selector.toml"
            selector_path.write_text(
                textwrap.dedent(modified)
                .replace(
                    'whole_vehicle_path = "data_catalog/wufr26_whole_vehicle_frame_v0.toml"',
                    f'whole_vehicle_path = "{(ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml").as_posix()}"',
                )
                .replace(
                    'static_gravity_path = "data_catalog/wufr27_static_gravity_allocation_v0.toml"',
                    f'static_gravity_path = "{(ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml").as_posix()}"',
                ),
                encoding="utf-8",
            )
            with self.assertRaises(VehicleReferenceError):
                load_vehicle_reference(selector_path)


if __name__ == "__main__":
    unittest.main()
