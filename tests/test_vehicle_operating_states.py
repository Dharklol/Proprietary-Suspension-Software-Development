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
    load_vehicle_operating_state_set,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    ROOT
    / "benchmarks"
    / "vehicle"
    / "WUFR27_SUSPENSION_CALCULATIONS_OPERATING_STATES_V0.toml"
)


class VehicleOperatingStateTests(unittest.TestCase):
    def test_current_source_fixture_preserves_exact_1p2g_loads(self) -> None:
        states = load_vehicle_operating_state_set(FIXTURE)
        self.assertEqual("WUFR27_SUSPENSION_CALCULATIONS_OPERATING_STATES_V0", states.state_set_id)
        self.assertEqual(2, len(states.states))

        right = states.state("SC26_EDGE3_1P2G_RIGHT_AERO_NO_ARB")
        self.assertEqual(TurnDirection.RIGHT, right.turn_direction)
        self.assertAlmostEqual(-1.2, right.ay_g, places=14)
        self.assertAlmostEqual(17.8816, right.speed_mps, places=14)
        self.assertAlmostEqual(1719.575445, right.wheel("front_left").normal_load_n, places=9)
        self.assertAlmostEqual(186.2139907, right.wheel("front_right").normal_load_n, places=9)
        self.assertAlmostEqual(1737.984573, right.wheel("rear_left").normal_load_n, places=9)
        self.assertAlmostEqual(173.2530798, right.wheel("rear_right").normal_load_n, places=9)
        self.assertAlmostEqual(3817.0270885, right.total_normal_load_n, places=7)

        left = states.state("SC26_EDGE4_1P2G_LEFT_AERO_NO_ARB")
        self.assertEqual(TurnDirection.LEFT, left.turn_direction)
        self.assertAlmostEqual(1.2, left.ay_g, places=14)
        self.assertAlmostEqual(516.8481725, left.wheel("front_left").normal_load_n, places=9)
        self.assertAlmostEqual(1388.941263, left.wheel("front_right").normal_load_n, places=9)
        self.assertAlmostEqual(510.345799, left.wheel("rear_left").normal_load_n, places=9)
        self.assertAlmostEqual(1400.891854, left.wheel("rear_right").normal_load_n, places=9)
        self.assertAlmostEqual(3817.0270885, left.total_normal_load_n, places=7)

    def test_source_fixture_remains_evidence_only(self) -> None:
        states = load_vehicle_operating_state_set(FIXTURE)
        for state in states.states:
            self.assertEqual(VehicleStateRole.EVIDENCE_ONLY, state.role)
            self.assertEqual(0.0, state.state_weight)
            self.assertIn("Development wheel-load evidence", state.authority)

    def test_negative_normal_load_is_rejected_not_clipped(self) -> None:
        with self.assertRaisesRegex(VehicleStateError, "cannot be negative"):
            WheelOperatingState(
                position=WheelPosition.REAR_LEFT,
                normal_load_n=-285.3358453,
            )

    def test_evidence_state_cannot_silently_gain_objective_weight(self) -> None:
        wheels = tuple(
            WheelOperatingState(position=position, normal_load_n=100.0)
            for position in WheelPosition
        )
        with self.assertRaisesRegex(VehicleStateError, "must use state_weight=0"):
            VehicleOperatingState(
                state_id="BAD_WEIGHT",
                role=VehicleStateRole.EVIDENCE_ONLY,
                turn_direction=TurnDirection.RIGHT,
                ax_g=0.0,
                ay_g=-1.0,
                speed_mps=10.0,
                wheels=wheels,
                state_weight=1.0,
            )

    def test_exactly_four_named_wheels_are_required(self) -> None:
        with self.assertRaisesRegex(VehicleStateError, "exactly one front_left"):
            VehicleOperatingState(
                state_id="MISSING_RR",
                role=VehicleStateRole.REPORT_ONLY,
                turn_direction=TurnDirection.LEFT,
                ax_g=0.0,
                ay_g=1.0,
                speed_mps=10.0,
                wheels=(
                    WheelOperatingState(WheelPosition.FRONT_LEFT, normal_load_n=100.0),
                    WheelOperatingState(WheelPosition.FRONT_RIGHT, normal_load_n=100.0),
                    WheelOperatingState(WheelPosition.REAR_LEFT, normal_load_n=100.0),
                ),
            )


if __name__ == "__main__":
    unittest.main()
