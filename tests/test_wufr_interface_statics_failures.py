from __future__ import annotations

from dataclasses import replace
import math
import unittest

from pssd_suspension.wufr_interface_statics import (
    InterfaceStaticsSolverConfig,
    WufrInterfaceStaticsFailureCode,
    solve_wufr_level1_interface_statics,
)
from tests.test_wufr_interface_statics import _front_geometry, _wrench


class WufrInterfaceStaticsFailureTests(unittest.TestCase):
    def test_wrong_arm_mounted_actuation_owner_fails_closed(self) -> None:
        result = solve_wufr_level1_interface_statics(
            replace(_front_geometry(), actuation_owner="outboard_carrier"),
            _wrench(),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WufrInterfaceStaticsFailureCode.SOURCE_OWNERSHIP_MISMATCH)
        self.assertEqual(result.solution, ())

    def test_incomplete_or_unprovenanced_external_wrench_is_rejected(self) -> None:
        for wrench in (
            replace(_wrench(), complete=False),
            replace(_wrench(), source_id=""),
            replace(_wrench(), load_case_id=""),
        ):
            with self.subTest(wrench=wrench):
                result = solve_wufr_level1_interface_statics(_front_geometry(), wrench)
                self.assertFalse(result.ok)
                self.assertEqual(result.failure_code, WufrInterfaceStaticsFailureCode.INCOMPLETE_EXTERNAL_WRENCH)

    def test_frame_and_source_identity_failures_are_explicit(self) -> None:
        frame = solve_wufr_level1_interface_statics(
            _front_geometry(),
            replace(_wrench(), frame_id="other_frame"),
        )
        self.assertEqual(frame.failure_code, WufrInterfaceStaticsFailureCode.FRAME_MISMATCH)

        source = solve_wufr_level1_interface_statics(
            replace(_front_geometry(), lateral_source_id=""),
            _wrench(),
        )
        self.assertEqual(source.failure_code, WufrInterfaceStaticsFailureCode.SOURCE_MISMATCH)

    def test_degenerate_hinge_and_axial_link_are_rejected_before_solve(self) -> None:
        hinge = solve_wufr_level1_interface_statics(
            replace(_front_geometry(), upper_hinge_axis_unit=(0.0, 0.0, 0.0)),
            _wrench(),
        )
        self.assertEqual(hinge.failure_code, WufrInterfaceStaticsFailureCode.DEGENERATE_HINGE_AXIS)

        geometry = _front_geometry()
        axial = solve_wufr_level1_interface_statics(
            replace(geometry, lateral_remote_point_m=geometry.lateral_body_point_m),
            _wrench(),
        )
        self.assertEqual(axial.failure_code, WufrInterfaceStaticsFailureCode.DEGENERATE_AXIAL_LINK)

    def test_nonfinite_input_is_rejected(self) -> None:
        result = solve_wufr_level1_interface_statics(
            replace(_front_geometry(), upper_spherical_point_m=(math.nan, 0.0, 0.0)),
            _wrench(),
        )
        self.assertEqual(result.failure_code, WufrInterfaceStaticsFailureCode.NONFINITE_INPUT)

    def test_condition_limit_is_fail_closed_without_approximate_solution(self) -> None:
        result = solve_wufr_level1_interface_statics(
            _front_geometry(),
            _wrench(),
            config=InterfaceStaticsSolverConfig(condition_limit=1.0),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WufrInterfaceStaticsFailureCode.ILL_CONDITIONED_EQUILIBRIUM)
        self.assertEqual(result.solution, ())
        self.assertIsNotNone(result.condition_number_inf)
        assert result.condition_number_inf is not None
        self.assertGreater(result.condition_number_inf, 1.0)

    def test_singular_upper_arm_topology_is_not_force_shared(self) -> None:
        geometry = _front_geometry()
        # Collapse both non-hinge UCA force application points onto the hinge.
        # The UCA then has no mechanism to balance a moment component about its
        # ideal hinge axis, so the exact Level-1 matrix loses rank.
        singular_geometry = replace(
            geometry,
            upper_spherical_point_m=geometry.upper_hinge_point_m,
            actuation_body_point_m=geometry.upper_hinge_point_m,
        )
        result = solve_wufr_level1_interface_statics(singular_geometry, _wrench())
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WufrInterfaceStaticsFailureCode.SINGULAR_EQUILIBRIUM)
        self.assertEqual(result.solution, ())


if __name__ == "__main__":
    unittest.main()
