from dataclasses import replace
from pathlib import Path
import math
import unittest

from pssd_suspension import Axle, Side, build_nominal_wheel_reference
from pssd_suspension.wheel_reference import solve_wheel_reference_state
from pssd_steering.core import rotate_point_about_axis, rotate_direction_about_axis, dot
from pssd_vehicle.wufr_road_contact import load_wufr_road_contact_provider
from pssd_vehicle.steady_cornering_upright import close_native_upright

ROOT = Path(__file__).resolve().parents[1]


class NativeUprightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = load_wufr_road_contact_provider(
            source_path=ROOT / 'data_catalog/wufr26_road_contact_reference_v0.toml',
            suspension_geometry_path=ROOT / 'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml',
            wheel_profile_path=ROOT / 'benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml',
            steering_geometry_path=ROOT / 'configurations/steering/WUFR27_STEERING_BASELINE_V0.toml',
            whole_vehicle_path=ROOT / 'data_catalog/wufr26_whole_vehicle_frame_v0.toml',
        )

    def state(self, axle, side):
        provider = self.provider
        return solve_wheel_reference_state(
            provider.suspension_geometry.corner(axle, side),
            build_nominal_wheel_reference(provider.wheel_profile, axle, side),
            math.radians(1), geometry_id=provider.suspension_geometry.geometry_id,
            configuration_id=provider.source.configuration_id,
        )

    def test_front_full_rigid_transport_and_heading(self):
        for side in Side:
            state = self.state(Axle.FRONT, side)
            pose = close_native_upright(state, self.provider.steering_geometry, .003)
            self.assertEqual(pose.steering_owner, 'front_tie_rod_once')
            self.assertLess(abs(pose.closure_residual_m), 1e-9)
            center = rotate_point_about_axis(state.current_center_m, pose.steering_axis,
                                            pose.steering_rotation_rad)
            plane = rotate_direction_about_axis(state.current_plane_normal,
                pose.steering_axis.direction, pose.steering_rotation_rad)
            for actual, expected in zip(pose.center_m, center):
                self.assertAlmostEqual(actual, expected, places=13)
            for actual, expected in zip(pose.plane_normal, plane):
                self.assertAlmostEqual(actual, expected, places=13)
            self.assertGreater(math.dist(pose.center_m, state.current_center_m), 1e-5)
            heading = pose.road_heading()
            self.assertAlmostEqual(heading[2], 0, places=13)
            self.assertAlmostEqual(dot(heading, plane), 0, places=13)
            # One rigid transform preserves distances between material points.
            point = tuple(v + d for v, d in zip(state.nominal.center_m, (.02, .03, .04)))
            self.assertAlmostEqual(math.dist(pose.transport_point(point), pose.center_m),
                                   math.dist(point, state.nominal.center_m), places=13)

    def test_rear_is_rack_independent_native_toe_closed(self):
        for side in Side:
            state = self.state(Axle.REAR, side)
            a = close_native_upright(state, self.provider.steering_geometry, -.003)
            b = close_native_upright(state, self.provider.steering_geometry, .003)
            self.assertEqual(a.center_m, state.current_center_m)
            self.assertEqual(a.plane_normal, state.current_plane_normal)
            self.assertEqual(a.center_m, b.center_m)
            self.assertEqual(a.steering_owner, 'rear_native_toe_link')

    def test_unresolved_role_and_source_domain_gates(self):
        state = self.state(Axle.FRONT, Side.LEFT)
        with self.assertRaises(ValueError):
            close_native_upright(replace(state, transform_role='already_steered'),
                                 self.provider.steering_geometry, 0)
        for rack in (float('nan'), 1.0):
            with self.assertRaises(ValueError):
                close_native_upright(state, self.provider.steering_geometry, rack)


if __name__ == '__main__':
    unittest.main()
