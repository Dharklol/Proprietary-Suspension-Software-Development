from __future__ import annotations

import math
from pathlib import Path
import tomllib
import unittest

from pssd_steering import (
    AxisLine,
    FailureCode,
    GeometryError,
    SolverStatus,
    WarningCode,
    ackermann_error,
    assign_inside_outside,
    conventional_steering_ratio,
    evaluate_wheel_heading,
    exact_ackermann_outside_reference,
    implicit_upright_gain,
    load_geometry,
    local_road_wheel_gain,
    metres_per_radian_to_millimetres_per_revolution,
    solve_corner_position,
    solve_sweep,
    staged_transmission,
    turning_radii,
    wheel_heading,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "benchmarks" / "steering" / "GEO-STEER-BASIC-001.toml"
WUFR_PATH = ROOT / "configurations" / "steering" / "WUFR26_DESIGN_NOMINAL_V0.toml"


class FrozenFixtureTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.geometry = load_geometry(FIXTURE_PATH)
        with FIXTURE_PATH.open("rb") as stream:
            cls.document = tomllib.load(stream)
        cls.tolerances = cls.document["tolerances"]
        cls.expected_states = cls.document["expected_states"]


class TestBenchSteer0002(FrozenFixtureTestCase):
    """Exact Ackermann analytical angle pairs and radius identity."""

    def test_exact_ackermann_pairs_and_cotangent_identity(self) -> None:
        wheelbase = 1.6
        track = 1.2
        expected = {
            5.0: (4.693539843118893, 18.888083684418152),
            15.0: (12.577388257044907, 6.5712812921102035),
            25.0: (19.059109112714346, 4.031211072815294),
            35.0: (24.660121411405886, 2.885036810787384),
        }
        for inside_deg, (outside_deg, radius) in expected.items():
            inside = math.radians(inside_deg)
            outside = exact_ackermann_outside_reference(inside, wheelbase, track)
            self.assertAlmostEqual(outside, math.radians(outside_deg), delta=2.0e-10)
            cotangent_difference = 1.0 / math.tan(outside) - 1.0 / math.tan(inside)
            self.assertAlmostEqual(cotangent_difference, track / wheelbase, delta=1.0e-12)
            radii = turning_radii(inside, outside, wheelbase, track)
            self.assertAlmostEqual(
                radii.rear_axle_center_from_inside,
                radii.rear_axle_center_from_outside,
                delta=2.0e-9,
            )
            self.assertAlmostEqual(radii.rear_axle_center_from_inside, radius, delta=2.0e-9)


class TestBenchSteer0003(FrozenFixtureTestCase):
    """Reference closure, tie-rod length, and intended branch selection."""

    def test_reference_closure(self) -> None:
        expected_length = math.sqrt(0.12**2 + 0.29**2)
        self.assertAlmostEqual(self.geometry.left.tie_rod_length, expected_length, places=15)
        for side in ("left", "right"):
            result = solve_corner_position(self.geometry, side, 0.0)
            self.assertEqual(result.status, SolverStatus.SUCCESS)
            self.assertEqual(result.branch_signature, -1 if side == "left" else 1)
            self.assertAlmostEqual(result.upright_rotation or 0.0, 0.0, delta=2.0e-8)
            self.assertLess(abs(result.closure_length_residual or 0.0), 1.0e-10)
            corner = self.geometry.left if side == "left" else self.geometry.right
            total, incremental = wheel_heading(corner, result.upright_rotation or 0.0)
            self.assertAlmostEqual(total, 0.0, delta=2.0e-8)
            self.assertAlmostEqual(incremental, 0.0, delta=2.0e-8)


class TestBenchSteer0004(FrozenFixtureTestCase):
    """Sweep, mirror, branch, monotonicity, singularity, and failures."""

    def _headings(self, displacements: list[float]) -> dict[float, tuple[float, float]]:
        sweep = solve_sweep(self.geometry, displacements)
        output: dict[float, tuple[float, float]] = {}
        for index, displacement in enumerate(displacements):
            left_result = sweep["left"][index]
            right_result = sweep["right"][index]
            self.assertTrue(left_result.ok, left_result.message)
            self.assertTrue(right_result.ok, right_result.message)
            _, left_heading = wheel_heading(self.geometry.left, left_result.upright_rotation or 0.0)
            _, right_heading = wheel_heading(self.geometry.right, right_result.upright_rotation or 0.0)
            output[displacement] = (left_heading, right_heading)
        return output

    def test_frozen_states_mirror_and_monotonicity(self) -> None:
        displacements = [state["rack_displacement"] for state in self.expected_states]
        headings = self._headings(displacements)
        for state in self.expected_states:
            displacement = state["rack_displacement"]
            left, right = headings[displacement]
            self.assertAlmostEqual(left, math.radians(state["left_heading_deg"]), delta=2.0e-8)
            self.assertAlmostEqual(right, math.radians(state["right_heading_deg"]), delta=2.0e-8)
            mirror_left, mirror_right = headings[-displacement]
            self.assertAlmostEqual(left, -mirror_right, delta=2.0e-8)
            self.assertAlmostEqual(right, -mirror_left, delta=2.0e-8)

        left_values = [headings[value][0] for value in displacements]
        right_values = [headings[value][1] for value in displacements]
        self.assertTrue(all(a > b for a, b in zip(left_values, left_values[1:])))
        self.assertTrue(all(a > b for a, b in zip(right_values, right_values[1:])))

    def test_sweep_direction_independence(self) -> None:
        ascending = [-0.010, -0.005, 0.0, 0.005, 0.010]
        descending = list(reversed(ascending))
        a = self._headings(ascending)
        b = self._headings(descending)
        for displacement in ascending:
            self.assertAlmostEqual(a[displacement][0], b[displacement][0], delta=2.0e-8)
            self.assertAlmostEqual(a[displacement][1], b[displacement][1], delta=2.0e-8)

    def test_branch_limit_warning_and_domain_failures(self) -> None:
        left = solve_corner_position(self.geometry, "left", -0.010)
        right = solve_corner_position(self.geometry, "right", 0.010)
        self.assertIn(WarningCode.NEAR_GEOMETRIC_BRANCH_LIMIT, left.warnings)
        self.assertIn(WarningCode.NEAR_GEOMETRIC_BRANCH_LIMIT, right.warnings)
        for displacement in (-0.013, 0.013):
            for side in ("left", "right"):
                result = solve_corner_position(self.geometry, side, displacement)
                self.assertFalse(result.ok)
                self.assertEqual(result.failure_code, FailureCode.INPUT_OUTSIDE_DOMAIN)
                self.assertIsNone(result.upright_rotation)


class TestBenchSteer0005(unittest.TestCase):
    """Staged steering-wheel, pinion, and rack transmission identity."""

    def test_transmission_and_unit_conversion(self) -> None:
        for input_angle in (-1.0, 1.0):
            result = staged_transmission(input_angle, 1.0, 0.010)
            self.assertAlmostEqual(result.pinion_angle, input_angle, places=15)
            self.assertAlmostEqual(result.rack_displacement, input_angle * 0.010, places=15)
        self.assertAlmostEqual(
            metres_per_radian_to_millimetres_per_revolution(0.010),
            62.83185307179586,
            places=13,
        )


class TestBenchSteer0006(FrozenFixtureTestCase):
    """Local gain, finite-difference agreement, and conventional ratio."""

    def test_local_and_secant_ratio_quantities(self) -> None:
        for side in ("left", "right"):
            corner = self.geometry.left if side == "left" else self.geometry.right
            center = solve_corner_position(self.geometry, side, 0.0)
            self.assertTrue(center.ok)
            gain = implicit_upright_gain(corner, self.geometry.rack, 0.0, center.upright_rotation or 0.0)
            self.assertAlmostEqual(gain, -18.125, delta=abs(18.125) * 1.0e-8)
            step = 1.0e-6
            plus = solve_corner_position(self.geometry, side, step)
            minus = solve_corner_position(self.geometry, side, -step)
            finite_difference = ((plus.upright_rotation or 0.0) - (minus.upright_rotation or 0.0)) / (2.0 * step)
            self.assertAlmostEqual(finite_difference, gain, delta=abs(gain) * 1.0e-6)

        road_wheel_gain = local_road_wheel_gain(-18.125, 0.010, 1.0)
        self.assertAlmostEqual(road_wheel_gain, -0.18125, places=15)
        self.assertAlmostEqual(
            conventional_steering_ratio(road_wheel_gain),
            5.517241379310345,
            places=14,
        )
        with self.assertRaises(ZeroDivisionError):
            conventional_steering_ratio(0.0)


class TestBenchSteer0007(FrozenFixtureTestCase):
    """Named turning radii and non-Ackermann mismatch preservation."""

    def test_exact_and_non_ackermann_radius_behavior(self) -> None:
        exact_inside = math.radians(25.0)
        exact_outside = exact_ackermann_outside_reference(exact_inside, 1.6, 1.2)
        exact = turning_radii(exact_inside, exact_outside, 1.6, 1.2)
        self.assertAlmostEqual(exact.mismatch, 0.0, delta=2.0e-9)

        state = self.expected_states[1]
        synthetic = turning_radii(
            math.radians(state["inside_heading_deg"]),
            math.radians(state["outside_heading_deg"]),
            1.6,
            1.2,
        )
        self.assertAlmostEqual(
            synthetic.rear_axle_center_from_inside,
            state["rear_axle_radius_from_inside"],
            delta=2.0e-9,
        )
        self.assertGreater(abs(synthetic.mismatch), 1.0e-3)
        self.assertNotEqual(
            synthetic.rear_axle_center_from_inside,
            synthetic.rear_axle_center_from_outside,
        )


class TestBenchSteer0008(FrozenFixtureTestCase):
    """Ackermann-error sign, side assignment, and static-toe separation."""

    def test_frozen_errors(self) -> None:
        for state in self.expected_states:
            if state["rack_displacement"] == 0.0:
                continue
            assignment, reference, error = ackermann_error(
                math.radians(state["left_heading_deg"]),
                math.radians(state["right_heading_deg"]),
                1.6,
                1.2,
            )
            self.assertAlmostEqual(
                reference,
                math.radians(state["ackermann_outside_reference_deg"]),
                delta=2.0e-10,
            )
            self.assertAlmostEqual(
                error,
                math.radians(state["ackermann_error_deg"]),
                delta=2.0e-10,
            )
            expected_turn = "left" if state["rack_displacement"] < 0.0 else "right"
            self.assertEqual(assignment.turn_direction, expected_turn)

    def test_exact_error_zero_and_static_toe_invariance(self) -> None:
        inside = math.radians(15.0)
        outside = exact_ackermann_outside_reference(inside, 1.6, 1.2)
        _, _, exact_error = ackermann_error(inside, outside, 1.6, 1.2)
        self.assertAlmostEqual(exact_error, 0.0, delta=2.0e-10)

        left_incremental = math.radians(5.782318645713388)
        right_incremental = math.radians(4.81050423802314)
        _, _, baseline = ackermann_error(left_incremental, right_incremental, 1.6, 1.2)
        toe = math.radians(1.0)
        left_total = left_incremental - toe
        right_total = right_incremental + toe
        recovered_left_incremental = left_total - (-toe)
        recovered_right_incremental = right_total - toe
        _, _, recovered = ackermann_error(
            recovered_left_incremental,
            recovered_right_incremental,
            1.6,
            1.2,
        )
        self.assertAlmostEqual(recovered, baseline, delta=2.0e-10)

    def test_assignment_does_not_use_angle_magnitude(self) -> None:
        assignment = assign_inside_outside(math.radians(3.0), math.radians(7.0))
        self.assertEqual(assignment.turn_direction, "left")
        self.assertEqual(assignment.inside_side, "left")
        self.assertEqual(assignment.outside_side, "right")
        self.assertLess(
            assignment.inside_incremental_magnitude,
            assignment.outside_incremental_magnitude,
        )


class TestFailureSemantics(unittest.TestCase):
    def test_invalid_zero_axis_is_rejected(self) -> None:
        with self.assertRaises(GeometryError):
            AxisLine((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))

    def test_wufr_nominal_scope(self) -> None:
        geometry = load_geometry(WUFR_PATH)
        for side in ("left", "right"):
            center = solve_corner_position(geometry, side, 0.0)
            self.assertTrue(center.ok, center.message)
            self.assertLess(abs(center.closure_length_residual or 0.0), 1.0e-10)
            corner = geometry.left if side == "left" else geometry.right
            heading = evaluate_wheel_heading(corner, center.upright_rotation or 0.0)
            self.assertFalse(heading.available)
            self.assertEqual(heading.failure_code, FailureCode.DERIVED_OUTPUT_UNAVAILABLE)
            self.assertIn("unavailable", heading.message.lower())
        mirror_result = solve_corner_position(geometry, "right", 0.0)
        self.assertIn(WarningCode.MIRRORED_GEOMETRY, mirror_result.warnings)
        self.assertIn(WarningCode.PROVISIONAL_INPUT_DOMAIN, mirror_result.warnings)


if __name__ == "__main__":
    unittest.main()
