from __future__ import annotations

import math
import unittest

from pssd_vehicle.operating_states import WheelPosition
from pssd_vehicle.planar_kinematics import (
    FourWheelPlanarGeometry,
    PlanarKinematicsError,
    PlanarMotionSample,
    front_required_heading_pair,
    tire_slip_kinematics,
    wheel_center_kinematics,
)


class PlanarSlipKinematicsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.geometry = FourWheelPlanarGeometry(
            cg_to_front_axle_m=0.8,
            cg_to_rear_axle_m=0.7,
            front_wheel_center_track_m=1.2,
            rear_wheel_center_track_m=1.2,
            authority="synthetic_test_geometry",
        )

    def test_rigid_body_wheel_center_velocity_field(self) -> None:
        motion = PlanarMotionSample(10.0, 0.3, 1.5)
        left = wheel_center_kinematics(
            motion, self.geometry.location(WheelPosition.FRONT_LEFT)
        )
        right = wheel_center_kinematics(
            motion, self.geometry.location(WheelPosition.FRONT_RIGHT)
        )
        self.assertAlmostEqual(left.velocity_x_mps, 10.0 - 1.5 * 0.6)
        self.assertAlmostEqual(right.velocity_x_mps, 10.0 + 1.5 * 0.6)
        self.assertAlmostEqual(left.velocity_y_mps, 0.3 + 1.5 * 0.8)
        self.assertAlmostEqual(right.velocity_y_mps, 0.3 + 1.5 * 0.8)

    def test_velocity_center_on_rear_axle_reproduces_zero_slip_ackermann_headings(self) -> None:
        radius_to_vehicle_axis_m = 8.0
        yaw_rate = 1.25
        # S = -v/r = -a2 -> v = r*a2.  With zero rear steer/slip the velocity
        # center lies on the rear axle, recovering the classical no-slip construction.
        motion = PlanarMotionSample(
            longitudinal_velocity_mps=radius_to_vehicle_axis_m * yaw_rate,
            lateral_velocity_mps=yaw_rate * self.geometry.cg_to_rear_axle_m,
            yaw_rate_radps=yaw_rate,
        )
        pair = front_required_heading_pair(
            motion,
            self.geometry,
            left_required_slip_rad=0.0,
            right_required_slip_rad=0.0,
        )
        wheelbase = self.geometry.wheelbase_m
        half_track = 0.5 * self.geometry.front_wheel_center_track_m
        expected_left = math.atan2(wheelbase, radius_to_vehicle_axis_m - half_track)
        expected_right = math.atan2(wheelbase, radius_to_vehicle_axis_m + half_track)
        self.assertAlmostEqual(pair.left_required_wheel_heading_rad, expected_left, places=12)
        self.assertAlmostEqual(pair.right_required_wheel_heading_rad, expected_right, places=12)
        self.assertGreater(pair.left_required_wheel_heading_rad, pair.right_required_wheel_heading_rad)

    def test_parallel_front_steer_relative_slip_changes_with_velocity_center_position(self) -> None:
        yaw_rate = 1.0
        radius_to_vehicle_axis_m = 10.0
        parallel_heading = math.radians(5.0)

        # Guiggiani case S = a1: front wheel-center velocity headings are equal.
        s_equal = self.geometry.cg_to_front_axle_m
        motion_equal = PlanarMotionSample(
            radius_to_vehicle_axis_m * yaw_rate,
            -s_equal * yaw_rate,
            yaw_rate,
        )
        left_equal = tire_slip_kinematics(
            motion_equal,
            self.geometry.location(WheelPosition.FRONT_LEFT),
            parallel_heading,
        )
        right_equal = tire_slip_kinematics(
            motion_equal,
            self.geometry.location(WheelPosition.FRONT_RIGHT),
            parallel_heading,
        )
        self.assertAlmostEqual(left_equal.slip_angle_rad, right_equal.slip_angle_rad, places=12)

        # S > a1, a condition Guiggiani notes is frequent in race cars: the inner
        # front wheel has the larger slip under parallel steering.
        s_forward = self.geometry.cg_to_front_axle_m + 0.5
        motion_forward = PlanarMotionSample(
            radius_to_vehicle_axis_m * yaw_rate,
            -s_forward * yaw_rate,
            yaw_rate,
        )
        left_forward = tire_slip_kinematics(
            motion_forward,
            self.geometry.location(WheelPosition.FRONT_LEFT),
            parallel_heading,
        )
        right_forward = tire_slip_kinematics(
            motion_forward,
            self.geometry.location(WheelPosition.FRONT_RIGHT),
            parallel_heading,
        )
        self.assertGreater(left_forward.slip_angle_rad, right_forward.slip_angle_rad)

        # -a2 < S < a1: the outer front wheel instead has the larger slip.
        s_mid = 0.0
        motion_mid = PlanarMotionSample(
            radius_to_vehicle_axis_m * yaw_rate,
            -s_mid * yaw_rate,
            yaw_rate,
        )
        left_mid = tire_slip_kinematics(
            motion_mid,
            self.geometry.location(WheelPosition.FRONT_LEFT),
            parallel_heading,
        )
        right_mid = tire_slip_kinematics(
            motion_mid,
            self.geometry.location(WheelPosition.FRONT_RIGHT),
            parallel_heading,
        )
        self.assertLess(left_mid.slip_angle_rad, right_mid.slip_angle_rad)

    def test_required_heading_inverts_slip_definition_for_both_front_wheels(self) -> None:
        motion = PlanarMotionSample(14.0, -0.5, 0.9)
        pair = front_required_heading_pair(
            motion,
            self.geometry,
            left_required_slip_rad=math.radians(4.0),
            right_required_slip_rad=math.radians(6.0),
        )
        left = tire_slip_kinematics(
            motion,
            self.geometry.location(WheelPosition.FRONT_LEFT),
            pair.left_required_wheel_heading_rad,
        )
        right = tire_slip_kinematics(
            motion,
            self.geometry.location(WheelPosition.FRONT_RIGHT),
            pair.right_required_wheel_heading_rad,
        )
        self.assertAlmostEqual(left.slip_angle_rad, math.radians(4.0), places=12)
        self.assertAlmostEqual(right.slip_angle_rad, math.radians(6.0), places=12)

    def test_rejects_undefined_zero_wheel_center_velocity_direction(self) -> None:
        motion = PlanarMotionSample(0.0, 0.0, 0.0)
        with self.assertRaisesRegex(PlanarKinematicsError, "too small"):
            wheel_center_kinematics(
                motion, self.geometry.location(WheelPosition.FRONT_LEFT)
            )


if __name__ == "__main__":
    unittest.main()
