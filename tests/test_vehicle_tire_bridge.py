from __future__ import annotations

from pathlib import Path
import unittest

from pssd_vehicle import (
    TurnDirection,
    VehicleOperatingState,
    VehicleStateError,
    VehicleStateRole,
    WheelOperatingState,
    WheelPosition,
    front_inside_outside_assignment,
    front_tire_operating_pair,
    front_tire_readiness,
    load_vehicle_operating_state_set,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    ROOT
    / "benchmarks"
    / "vehicle"
    / "WUFR27_SUSPENSION_CALCULATIONS_OPERATING_STATES_V0.toml"
)


class VehicleTireBridgeTests(unittest.TestCase):
    def test_right_and_left_turn_inside_outside_mapping(self) -> None:
        states = load_vehicle_operating_state_set(FIXTURE)
        right = front_inside_outside_assignment(
            states.state("SC26_EDGE3_1P2G_RIGHT_AERO_NO_ARB")
        )
        self.assertEqual(WheelPosition.FRONT_RIGHT, right.inside_position)
        self.assertEqual(WheelPosition.FRONT_LEFT, right.outside_position)
        self.assertAlmostEqual(186.2139907, right.inside_wheel.normal_load_n, places=9)
        self.assertAlmostEqual(1719.575445, right.outside_wheel.normal_load_n, places=9)

        left = front_inside_outside_assignment(
            states.state("SC26_EDGE4_1P2G_LEFT_AERO_NO_ARB")
        )
        self.assertEqual(WheelPosition.FRONT_LEFT, left.inside_position)
        self.assertEqual(WheelPosition.FRONT_RIGHT, left.outside_position)
        self.assertAlmostEqual(516.8481725, left.inside_wheel.normal_load_n, places=9)
        self.assertAlmostEqual(1388.941263, left.outside_wheel.normal_load_n, places=9)

    def test_current_source_states_expose_missing_tire_inputs(self) -> None:
        states = load_vehicle_operating_state_set(FIXTURE)
        right = states.state("SC26_EDGE3_1P2G_RIGHT_AERO_NO_ARB")
        readiness = front_tire_readiness(right)
        for position in ("front_left", "front_right"):
            operating_missing = readiness["tire_operating_point"][position]
            self.assertNotIn("normal_load_n", operating_missing)
            self.assertIn("inclination_deg", operating_missing)
            self.assertIn("pressure_kpa", operating_missing)
            demand_missing = readiness["lateral_tire_demand"][position]
            self.assertIn("lateral_force_demand_n", demand_missing)

        with self.assertRaisesRegex(VehicleStateError, "cannot become TireOperatingPoint"):
            front_tire_operating_pair(right)

    def test_complete_explicit_state_converts_without_inference(self) -> None:
        wheels = (
            WheelOperatingState(
                WheelPosition.FRONT_LEFT,
                normal_load_n=500.0,
                inclination_deg=1.5,
                pressure_kpa=83.0,
                lateral_force_demand_n=900.0,
            ),
            WheelOperatingState(
                WheelPosition.FRONT_RIGHT,
                normal_load_n=900.0,
                inclination_deg=2.5,
                pressure_kpa=83.0,
                lateral_force_demand_n=1500.0,
            ),
            WheelOperatingState(WheelPosition.REAR_LEFT, normal_load_n=450.0),
            WheelOperatingState(WheelPosition.REAR_RIGHT, normal_load_n=850.0),
        )
        state = VehicleOperatingState(
            state_id="EXPLICIT_COMPLETE_LEFT",
            role=VehicleStateRole.DESIGN_INPUT,
            turn_direction=TurnDirection.LEFT,
            ax_g=0.0,
            ay_g=1.0,
            speed_mps=12.0,
            wheels=wheels,
            state_weight=1.0,
            authority="synthetic software-composition test only",
        )
        pair = front_tire_operating_pair(state)
        self.assertEqual(WheelPosition.FRONT_LEFT, pair.inside_position)
        self.assertEqual(WheelPosition.FRONT_RIGHT, pair.outside_position)
        self.assertEqual(500.0, pair.inside.normal_load_n)
        self.assertEqual(1.5, pair.inside.inclination_deg)
        self.assertEqual(83.0, pair.inside.pressure_kpa)
        self.assertEqual(900.0, pair.outside.normal_load_n)
        self.assertEqual(2.5, pair.outside.inclination_deg)
        self.assertEqual(83.0, pair.outside.pressure_kpa)

    def test_straight_state_has_no_inside_outside_assignment(self) -> None:
        state = VehicleOperatingState(
            state_id="STRAIGHT",
            role=VehicleStateRole.REPORT_ONLY,
            turn_direction=TurnDirection.STRAIGHT,
            ax_g=0.0,
            ay_g=0.0,
            speed_mps=10.0,
            wheels=tuple(
                WheelOperatingState(position, normal_load_n=100.0)
                for position in WheelPosition
            ),
        )
        with self.assertRaisesRegex(VehicleStateError, "must declare left or right"):
            front_inside_outside_assignment(state)


if __name__ == "__main__":
    unittest.main()
