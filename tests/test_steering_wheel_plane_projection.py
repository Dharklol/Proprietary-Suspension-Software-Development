import math
import unittest

from pssd_steering import (
    AxisLine,
    GeometryError,
    SteeringCorner,
    projected_wheel_heading,
    reference_from_static_alignment,
    road_intersection_direction,
)


def _corner(side: str, axis_direction=(0.0, 0.0, 1.0)) -> SteeringCorner:
    sign = 1.0 if side == "left" else -1.0
    return SteeringCorner(
        side=side,
        steering_axis=AxisLine((0.0, sign * 0.6, 0.0), axis_direction),
        rack_inner_joint_at_center=(0.0, sign * 0.2, 0.2),
        outer_tie_rod_joint_at_center=(0.0, sign * 0.5, 0.2),
        tie_rod_length=0.3,
    )


class WheelPlaneProjectionTests(unittest.TestCase):
    def test_static_toe_out_convention_is_side_local(self) -> None:
        toe = math.radians(-1.0)
        camber = math.radians(-2.25)
        left = reference_from_static_alignment("left", toe_out=toe, camber=camber)
        right = reference_from_static_alignment("right", toe_out=toe, camber=camber)

        left_total, left_incremental = projected_wheel_heading(_corner("left"), left, 0.0)
        right_total, right_incremental = projected_wheel_heading(_corner("right"), right, 0.0)

        self.assertAlmostEqual(math.degrees(left_total), -1.0, places=12)
        self.assertAlmostEqual(math.degrees(right_total), 1.0, places=12)
        self.assertAlmostEqual(left_incremental, 0.0, places=15)
        self.assertAlmostEqual(right_incremental, 0.0, places=15)

    def test_vertical_steering_axis_reduces_to_yaw_rotation(self) -> None:
        reference = reference_from_static_alignment(
            "left", toe_out=math.radians(-1.0), camber=math.radians(-2.25)
        )
        total, incremental = projected_wheel_heading(
            _corner("left"), reference, math.radians(12.0)
        )
        self.assertAlmostEqual(math.degrees(total), 11.0, places=12)
        self.assertAlmostEqual(math.degrees(incremental), 12.0, places=12)

    def test_inclined_axis_and_camber_use_plane_intersection_not_forward_projection(self) -> None:
        reference = reference_from_static_alignment(
            "left", toe_out=math.radians(-1.0), camber=math.radians(-2.25)
        )
        corner = _corner("left", axis_direction=(-0.0433, -0.1498, 0.9878))
        total, incremental = projected_wheel_heading(corner, reference, math.radians(20.0))

        self.assertTrue(math.isfinite(total))
        self.assertTrue(math.isfinite(incremental))
        # With camber and an inclined kingpin axis, projected heading is not exactly
        # the upright rotation plus static toe.
        self.assertNotAlmostEqual(math.degrees(total), 19.0, places=4)

    def test_plane_parallel_to_road_is_rejected(self) -> None:
        with self.assertRaisesRegex(GeometryError, "parallel to the road plane"):
            road_intersection_direction(
                (0.0, 0.0, 1.0), forward_hint=(1.0, 0.0, 0.0)
            )


if __name__ == "__main__":
    unittest.main()
