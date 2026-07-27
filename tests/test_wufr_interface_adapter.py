from __future__ import annotations

import math
from pathlib import Path
import unittest

from pssd_suspension.actuation import solve_actuation_q_L_state
from pssd_suspension.geometry import load_optimumk_geometry_snapshot
from pssd_suspension.wheel_reference import build_nominal_wheel_reference, load_wufr26_wheel_reference_profile
from pssd_suspension.wufr_interface_adapter import (
    CurrentLateralLinkState,
    WufrInterfaceAdapterError,
    build_level1_geometry_from_current_states,
)


ROOT = Path(__file__).resolve().parents[1]
GEOMETRY_PATH = ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
WHEEL_PROFILE_PATH = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml"


def _unit(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    return tuple(value / magnitude for value in vector)  # type: ignore[return-value]


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(a[i] - b[i] for i in range(3))  # type: ignore[return-value]


class WufrInterfaceAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.geometry = load_optimumk_geometry_snapshot(GEOMETRY_PATH)
        cls.wheel_profile = load_wufr26_wheel_reference_profile(WHEEL_PROFILE_PATH)

    def _actuation_state(self, axle: str, side: str):
        corner = self.geometry.corner(axle, side)
        nominal = build_nominal_wheel_reference(self.wheel_profile, axle, side)
        actuation = solve_actuation_q_L_state(
            corner,
            nominal,
            0.0,
            geometry_id=self.geometry.geometry_id,
            source_authority=self.geometry.authority,
        )
        self.assertTrue(actuation.ok, actuation.message)
        self.assertIsNotNone(actuation.wheel_state)
        assert actuation.wheel_state is not None and actuation.wheel_state.upstream_state is not None
        return corner, actuation.wheel_state.upstream_state, actuation

    def test_rear_adapter_uses_reviewed_toe_closure_and_arm_mounted_pushrod(self) -> None:
        corner, suspension, actuation = self._actuation_state("rear", "left")
        adapted = build_level1_geometry_from_current_states(corner, suspension, actuation)
        self.assertEqual(adapted.axle, "rear")
        self.assertEqual(adapted.actuation_owner, "lower_a_arm")
        self.assertEqual(adapted.actuation_body_point_m, actuation.arm_attachment_m)
        self.assertEqual(adapted.actuation_remote_point_m, actuation.rocker_rod_point_m)
        self.assertEqual(adapted.upper_spherical_point_m, suspension.upper_upright_m)
        self.assertEqual(adapted.lower_spherical_point_m, suspension.lower_upright_m)
        self.assertEqual(adapted.lateral_source_id, "MOD-SUSP-0001:rear_toe_link_current")
        assert suspension.upright_transform is not None
        expected_toe_outboard = suspension.upright_transform.apply_point(corner.toe_link.outboard.position_m)
        for actual, expected in zip(adapted.lateral_body_point_m, expected_toe_outboard):
            self.assertAlmostEqual(actual, expected, places=12)
        self.assertEqual(adapted.lateral_remote_point_m, corner.toe_link.inboard.position_m)

    def test_adapter_builds_revolute_axes_from_exact_fore_aft_hardpoints(self) -> None:
        corner, suspension, actuation = self._actuation_state("rear", "right")
        adapted = build_level1_geometry_from_current_states(corner, suspension, actuation)
        expected_upper = _unit(
            _sub(corner.wishbone.upper_aft_inboard.position_m, corner.wishbone.upper_fore_inboard.position_m)
        )
        expected_lower = _unit(
            _sub(corner.wishbone.lower_aft_inboard.position_m, corner.wishbone.lower_fore_inboard.position_m)
        )
        for actual, expected in zip(adapted.upper_hinge_axis_unit, expected_upper):
            self.assertAlmostEqual(actual, expected, places=14)
        for actual, expected in zip(adapted.lower_hinge_axis_unit, expected_lower):
            self.assertAlmostEqual(actual, expected, places=14)

    def test_front_adapter_refuses_to_invent_steering_tie_rod_state(self) -> None:
        corner, suspension, actuation = self._actuation_state("front", "left")
        with self.assertRaisesRegex(WufrInterfaceAdapterError, "MOD-STEER-0001"):
            build_level1_geometry_from_current_states(corner, suspension, actuation)

    def test_front_adapter_accepts_explicit_current_steering_closure_endpoints(self) -> None:
        corner, suspension, actuation = self._actuation_state("front", "right")
        # The adapter does not own steering closure.  The test passes an explicit
        # current-state packet with MOD-STEER-0001 provenance and verifies that the
        # exact supplied points survive unchanged into statics geometry.
        assert suspension.upright_transform is not None
        body_point = suspension.upright_transform.apply_point(corner.toe_link.outboard.position_m)
        remote_point = corner.toe_link.inboard.position_m
        steering = CurrentLateralLinkState(
            body_point_m=body_point,
            remote_point_m=remote_point,
            source_id="MOD-STEER-0001:test_current_centered_rack_closure",
        )
        adapted = build_level1_geometry_from_current_states(
            corner,
            suspension,
            actuation,
            front_lateral_state=steering,
        )
        self.assertEqual(adapted.actuation_owner, "upper_a_arm")
        self.assertEqual(adapted.lateral_source_id, steering.source_id)
        self.assertEqual(adapted.lateral_body_point_m, body_point)
        self.assertEqual(adapted.lateral_remote_point_m, remote_point)
        self.assertEqual(adapted.actuation_body_point_m, actuation.arm_attachment_m)


if __name__ == "__main__":
    unittest.main()
