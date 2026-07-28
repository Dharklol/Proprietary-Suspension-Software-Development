from __future__ import annotations

from dataclasses import replace
import unittest

from pssd_suspension.wufr_interface_statics import (
    AxialReaction,
    WufrInterfaceStaticsFailureCode,
    WufrInterfaceStaticsResult,
    WufrInterfaceStaticsStatus,
)
from pssd_suspension.wufr_rocker_included_load import (
    WufrRockerIncludedLoadFailureCode,
    compose_wufr_rocker_included_load,
)
from pssd_suspension.wufr_spring_rocker_force import (
    WufrSpringRockerForceResult,
    WufrSpringRockerForceStatus,
)
from pssd_suspension.wufr_zbar import ZBarAxleFixture, ZBarMechanismResult, ZBarStatus
from pssd_suspension.wufr_zbar_link_force import (
    ZBarLinkForceStatus,
    ZBarLinkSideForce,
    ZBarPhysicalLinkForceResult,
)


CONFIG = "WUFR27_SUSPENSION_BASELINE_V0"
FRAME = "WUFR_TEST_FRAME"
CASE = "EXTERNAL_CASE"


def _fixture() -> ZBarAxleFixture:
    return ZBarAxleFixture(
        fixture_id="TEST_ZBAR_FIXTURE",
        configuration_id=CONFIG,
        axle="front",
        housing_pivot_m=(0.0, 0.0, 0.0),
        housing_axis_unit=(0.0, 0.0, 1.0),
        blade_link_joint_left_m=(0.0, 0.1, 0.0),
        blade_link_joint_right_m=(0.0, -0.1, 0.0),
        rocker_pickup_left_m=(0.0, 0.1, 0.1),
        rocker_pickup_right_m=(0.0, -0.1, 0.1),
        rocker_pivot_left_m=(0.0, 0.0, 0.0),
        rocker_pivot_right_m=(0.0, 0.0, 0.0),
        rocker_axis_unit=(1.0, 0.0, 0.0),
        link_length_left_m=0.1,
        link_length_right_m=0.1,
    )


def _interface() -> WufrInterfaceStaticsResult:
    actuation = AxialReaction(
        element_id="front_pullrod",
        body_id="upper_arm",
        body_point_m=(0.0, 0.0, -0.1),
        remote_point_m=(0.0, 0.0, 0.1),
        unit_axis_body_to_remote=(0.0, 0.0, 1.0),
        axial_force_N=50.0,
        force_on_body_N=(0.0, -50.0, 0.0),
        force_on_remote_N=(0.0, 50.0, 0.0),
        source_id="MOD-SUSP-0007_TEST",
    )
    return WufrInterfaceStaticsResult(
        status=WufrInterfaceStaticsStatus.SUCCESS,
        axle="front",
        side="left",
        frame_id=FRAME,
        configuration_id=CONFIG,
        geometry_source_id="GEOMETRY_SOURCE",
        load_case_id=CASE,
        external_wrench_source_id="EXTERNAL_WRENCH_SOURCE",
        actuation=actuation,
    )


def _spring() -> WufrSpringRockerForceResult:
    return WufrSpringRockerForceResult(
        status=WufrSpringRockerForceStatus.SUCCESS,
        axle="front",
        side="left",
        spring_id="FRONT_SPRING",
        spring_source_id="AUTH-SUSP-0014_TEST",
        configuration_id=CONFIG,
        rocker_eye_m=(0.0, 0.2, 0.0),
        rocker_pivot_m=(0.0, 0.0, 0.0),
        rocker_axis_unit=(1.0, 0.0, 0.0),
        spring_force_magnitude_N=100.0,
        force_on_rocker_N=(0.0, -100.0, 0.0),
        force_on_chassis_N=(0.0, 100.0, 0.0),
    )


def _arb_side(side: str, force_on_rocker=(0.0, 20.0, 0.0)) -> ZBarLinkSideForce:
    return ZBarLinkSideForce(
        side=side,
        link_axis_blade_to_rocker=(0.0, 1.0, 0.0),
        blade_transverse_unit=(0.0, 1.0, 0.0),
        projection_u_dot_n=1.0,
        elastic_transverse_force_N=-20.0,
        axial_force_N=-20.0,
        force_on_rocker_N=force_on_rocker,
        force_on_blade_N=tuple(-value for value in force_on_rocker),
        physical_rocker_torque_Nm=-2.0,
        expected_generalized_rocker_torque_Nm=-2.0,
        force_projection_residual_N=0.0,
        rocker_torque_residual_Nm=0.0,
        current_link_length_m=0.1,
        nominal_link_length_m=0.1,
        link_closure_residual_m=0.0,
    )


def _arb_result() -> ZBarPhysicalLinkForceResult:
    return ZBarPhysicalLinkForceResult(
        status=ZBarLinkForceStatus.SUCCESS,
        axle="front",
        fixture_id="TEST_ZBAR_FIXTURE",
        configuration_id=CONFIG,
        setting=1,
        stiffness_N_per_m=280000.0,
        left=_arb_side("left"),
        right=_arb_side("right", (0.0, -20.0, 0.0)),
    )


def _mechanism() -> ZBarMechanismResult:
    return ZBarMechanismResult(
        status=ZBarStatus.SUCCESS,
        axle="front",
        rocker_pickup_left_m=(0.0, 0.1, 0.1),
        rocker_pickup_right_m=(0.0, -0.1, 0.1),
    )


class WufrRockerIncludedLoadAdapterTests(unittest.TestCase):
    def test_exact_source_composition_and_incomplete_contract(self) -> None:
        result = compose_wufr_rocker_included_load(
            interface_result=_interface(),
            spring_result=_spring(),
            arb_link_result=_arb_result(),
            arb_mechanism_result=_mechanism(),
            arb_fixture=_fixture(),
        )
        self.assertTrue(result.ok, result.message)
        included = result.included_result
        self.assertIsNotNone(included)
        self.assertEqual(included.included_load_ids, ("push_pull", "conservative_spring", "physical_arb_link"))
        self.assertEqual(included.missing_load_ids, ("KW_V5_non_spring_static_force",))
        self.assertEqual(included.included_resultant_force_N, (0.0, -30.0, 0.0))
        self.assertEqual(included.pivot_force_contribution_N, (0.0, 30.0, 0.0))
        self.assertAlmostEqual(included.free_axis_moment_residual_Nm, -7.0)
        self.assertEqual(included.final_moment_residual_Nm, (-7.0, 0.0, 0.0))
        self.assertFalse(included.complete_hardware_reaction)
        self.assertFalse(result.complete_hardware_reaction)
        loads = {load.load_id: load for load in included.included_loads}
        self.assertEqual(loads["push_pull"].application_point_m, _interface().actuation.remote_point_m)
        self.assertEqual(loads["push_pull"].force_N, _interface().actuation.force_on_remote_N)
        self.assertEqual(loads["conservative_spring"].application_point_m, _spring().rocker_eye_m)
        self.assertEqual(loads["conservative_spring"].force_N, _spring().force_on_rocker_N)
        self.assertEqual(loads["physical_arb_link"].application_point_m, _mechanism().rocker_pickup_left_m)
        self.assertEqual(loads["physical_arb_link"].force_N, _arb_result().left.force_on_rocker_N)

    def test_failed_upstream_provider_fails_closed(self) -> None:
        failed_interface = replace(
            _interface(),
            status=WufrInterfaceStaticsStatus.FAILURE,
            failure_code=WufrInterfaceStaticsFailureCode.LINEAR_SOLVE_FAILURE,
            message="failed interface",
        )
        result = compose_wufr_rocker_included_load(
            interface_result=failed_interface,
            spring_result=_spring(),
            arb_link_result=_arb_result(),
            arb_mechanism_result=_mechanism(),
            arb_fixture=_fixture(),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WufrRockerIncludedLoadFailureCode.UPSTREAM_INTERFACE_FAILURE)

    def test_source_and_geometry_mismatch_fail_closed(self) -> None:
        mismatched_side = compose_wufr_rocker_included_load(
            interface_result=_interface(),
            spring_result=replace(_spring(), side="right"),
            arb_link_result=_arb_result(),
            arb_mechanism_result=_mechanism(),
            arb_fixture=_fixture(),
        )
        self.assertEqual(mismatched_side.failure_code, WufrRockerIncludedLoadFailureCode.SOURCE_MISMATCH)

        mismatched_fixture = compose_wufr_rocker_included_load(
            interface_result=_interface(),
            spring_result=_spring(),
            arb_link_result=_arb_result(),
            arb_mechanism_result=_mechanism(),
            arb_fixture=replace(_fixture(), rocker_pivot_left_m=(0.0, 0.0, 0.01)),
        )
        self.assertEqual(mismatched_fixture.failure_code, WufrRockerIncludedLoadFailureCode.GEOMETRY_MISMATCH)

        reversed_axis = compose_wufr_rocker_included_load(
            interface_result=_interface(),
            spring_result=_spring(),
            arb_link_result=_arb_result(),
            arb_mechanism_result=_mechanism(),
            arb_fixture=replace(_fixture(), rocker_axis_unit=(-1.0, 0.0, 0.0)),
        )
        self.assertEqual(reversed_axis.failure_code, WufrRockerIncludedLoadFailureCode.GEOMETRY_MISMATCH)

    def test_missing_requested_arb_side_fails_closed(self) -> None:
        result = compose_wufr_rocker_included_load(
            interface_result=_interface(),
            spring_result=_spring(),
            arb_link_result=replace(_arb_result(), left=None),
            arb_mechanism_result=_mechanism(),
            arb_fixture=_fixture(),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WufrRockerIncludedLoadFailureCode.MISSING_UPSTREAM_VALUE)


if __name__ == "__main__":
    unittest.main()
