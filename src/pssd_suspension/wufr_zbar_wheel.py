"""WUFR Z-bar mapping from physical wheel-center vertical coordinates.

This module composes only reviewed geometry/state providers:

- MOD-SUSP-0002 physical wheel coordinate ``delta_z_wc_body_m`` (positive upward),
- MOD-SUSP-0003 one-axis rocker closure,
- AUTH-SUSP-0008 two-arm WUFR Z-bar map in rocker-angle coordinates, and
- AUTH-SUSP-0007 discrete per-arm SolidWorks blade stiffness.

The local chain is evaluated rather than replaced by a historical scalar motion
ratio.  For each side, ``rho_rw = d(theta_R)/d(delta_z_wc_body)`` is obtained from
branch-preserving physical-wheel perturbations.  The axle Jacobian then follows
from the chain rule

    J_dz = J_dtheta @ diag(rho_rw_left, rho_rw_right)

and the work-conjugate wheel-coordinate ARB force is

    Q_z = -J_dz.T @ F.

No body-roll, track-width, reduced-axle-stiffness, or historical motion-ratio
shortcut is used.  The result is a geometric/quasi-static elastic force mapping,
not a vehicle-equilibrium or installed/as-built claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .actuation import ActuationSolverConfig, ActuationStateResult, solve_actuation_from_wheel_state
from .geometry import SuspensionCornerGeometry
from .kinematics import KinematicsSolverConfig
from .wheel_reference import (
    NominalWheelReference,
    PhysicalStateResult,
    PhysicalStateSolverConfig,
    solve_body_vertical_displacement,
)
from .wufr_zbar import (
    WUFR_BLADE_STIFFNESS_N_PER_M,
    ZBarAxleFixture,
    ZBarForceResult,
    ZBarMechanismResult,
    evaluate_two_arm_force,
)
from .wufr_zbar_nominal import solve_nominal_zbar_mechanism


class ZBarWheelStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class ZBarWheelFailureCode(str, Enum):
    NONFINITE_INPUT = "nonfinite_input"
    SOURCE_MISMATCH = "source_mismatch"
    PHYSICAL_STATE_FAILURE = "physical_state_failure"
    ACTUATION_FAILURE = "actuation_failure"
    ROCKER_DERIVATIVE_UNAVAILABLE = "rocker_derivative_unavailable"
    ROCKER_DERIVATIVE_DISAGREEMENT = "rocker_derivative_disagreement"
    ZBAR_MECHANISM_FAILURE = "zbar_mechanism_failure"
    ZBAR_CONSTITUTIVE_FAILURE = "zbar_constitutive_failure"
    WHEEL_JACOBIAN_UNAVAILABLE = "wheel_jacobian_unavailable"


@dataclass(frozen=True)
class RockerWheelDerivativeConfig:
    step_m: float = 1.0e-4
    second_step_m: float = 5.0e-5
    agreement_tolerance_rad_per_m: float = 5.0e-2

    def __post_init__(self) -> None:
        values = (self.step_m, self.second_step_m, self.agreement_tolerance_rad_per_m)
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError("Rocker/wheel derivative steps and tolerance must be finite and positive")
        if self.second_step_m >= self.step_m:
            raise ValueError("Second rocker/wheel derivative step must be smaller than the first")


@dataclass(frozen=True)
class RockerWheelMapResult:
    status: ZBarWheelStatus
    axle: str
    side: str
    requested_delta_z_wc_body_m: float
    actuation_state: ActuationStateResult | None = None
    rocker_theta_rad: float | None = None
    dtheta_R_dz_wc_body_rad_per_m: float | None = None
    derivative_method: str = ""
    derivative_step_m: float | None = None
    derivative_second_step_m: float | None = None
    derivative_disagreement_rad_per_m: float | None = None
    failure_code: ZBarWheelFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is ZBarWheelStatus.SUCCESS


@dataclass(frozen=True)
class ZBarWheelStateResult:
    status: ZBarWheelStatus
    axle: str
    setting: int
    stiffness_N_per_m: float
    requested_delta_z_left_m: float
    requested_delta_z_right_m: float
    left_map: RockerWheelMapResult | None = None
    right_map: RockerWheelMapResult | None = None
    mechanism: ZBarMechanismResult | None = None
    force: ZBarForceResult | None = None
    J_d_wheel: tuple[tuple[float, float], tuple[float, float]] = ()
    generalized_wheel_force_N: tuple[float, float] = ()
    coordinate_order: tuple[str, str] = (
        "delta_z_wc_body_left_m",
        "delta_z_wc_body_right_m",
    )
    coordinate_units: tuple[str, str] = ("m", "m")
    failure_code: ZBarWheelFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is ZBarWheelStatus.SUCCESS


def _solve_actuation_at_physical_z(
    corner: SuspensionCornerGeometry,
    nominal: NominalWheelReference,
    requested_z_m: float,
    physical_solver: PhysicalStateSolverConfig,
    *,
    predecessor_theta_R_rad: float,
    actuation_config: ActuationSolverConfig | None,
    kinematics_config: KinematicsSolverConfig | None,
    geometry_id: str,
    configuration_id: str,
    source_authority: str,
    source_fixture_id: str,
) -> tuple[PhysicalStateResult, ActuationStateResult | None]:
    physical = solve_body_vertical_displacement(
        corner,
        nominal,
        requested_z_m,
        physical_solver,
        kinematics_config=kinematics_config,
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
    )
    if not physical.ok or physical.wheel_state is None:
        return physical, None
    actuation = solve_actuation_from_wheel_state(
        corner,
        physical.wheel_state,
        predecessor_theta_R_rad=predecessor_theta_R_rad,
        config=actuation_config,
        source_fixture_id=source_fixture_id,
    )
    return physical, actuation


def _derivative_at_step(
    corner: SuspensionCornerGeometry,
    nominal: NominalWheelReference,
    center_physical: PhysicalStateResult,
    center_actuation: ActuationStateResult,
    physical_solver: PhysicalStateSolverConfig,
    step_m: float,
    *,
    actuation_config: ActuationSolverConfig | None,
    kinematics_config: KinematicsSolverConfig | None,
    geometry_id: str,
    configuration_id: str,
    source_authority: str,
    source_fixture_id: str,
) -> tuple[float, str, float] | None:
    if (
        center_physical.reachable_delta_z_range_m is None
        or center_actuation.rocker_theta_rad is None
        or center_actuation.delta_z_wc_body_m is None
    ):
        return None
    lower, upper = center_physical.reachable_delta_z_range_m
    z_center = float(center_actuation.delta_z_wc_body_m)
    candidates: dict[str, ActuationStateResult] = {}
    for label, z_requested in (("minus", z_center - step_m), ("plus", z_center + step_m)):
        if z_requested < lower - physical_solver.displacement_tolerance_m or z_requested > upper + physical_solver.displacement_tolerance_m:
            continue
        _, neighbor = _solve_actuation_at_physical_z(
            corner,
            nominal,
            z_requested,
            physical_solver,
            predecessor_theta_R_rad=center_actuation.rocker_theta_rad,
            actuation_config=actuation_config,
            kinematics_config=kinematics_config,
            geometry_id=geometry_id,
            configuration_id=configuration_id,
            source_authority=source_authority,
            source_fixture_id=source_fixture_id,
        )
        if (
            neighbor is not None
            and neighbor.ok
            and neighbor.rocker_theta_rad is not None
            and neighbor.delta_z_wc_body_m is not None
        ):
            candidates[label] = neighbor

    minus = candidates.get("minus")
    plus = candidates.get("plus")
    if minus is not None and plus is not None:
        denominator = float(plus.delta_z_wc_body_m) - float(minus.delta_z_wc_body_m)
        numerator = float(plus.rocker_theta_rad) - float(minus.rocker_theta_rad)
        method = "centered_physical_wheel_coordinate"
        actual_step = 0.5 * abs(denominator)
    elif minus is not None:
        denominator = z_center - float(minus.delta_z_wc_body_m)
        numerator = float(center_actuation.rocker_theta_rad) - float(minus.rocker_theta_rad)
        method = "backward_one_sided_physical_wheel_coordinate"
        actual_step = abs(denominator)
    elif plus is not None:
        denominator = float(plus.delta_z_wc_body_m) - z_center
        numerator = float(plus.rocker_theta_rad) - float(center_actuation.rocker_theta_rad)
        method = "forward_one_sided_physical_wheel_coordinate"
        actual_step = abs(denominator)
    else:
        return None

    if abs(denominator) <= physical_solver.displacement_tolerance_m:
        return None
    derivative = numerator / denominator
    if not math.isfinite(derivative):
        return None
    return derivative, method, actual_step


def solve_rocker_wheel_map(
    corner: SuspensionCornerGeometry,
    nominal: NominalWheelReference,
    requested_delta_z_wc_body_m: float,
    physical_solver: PhysicalStateSolverConfig,
    *,
    derivative_config: RockerWheelDerivativeConfig | None = None,
    actuation_config: ActuationSolverConfig | None = None,
    kinematics_config: KinematicsSolverConfig | None = None,
    geometry_id: str = "",
    configuration_id: str = "WUFR27_SUSPENSION_BASELINE_V0",
    source_authority: str = "",
    source_fixture_id: str = "WUFR26_OPTIMUMK_ACTUATION_V0",
    with_derivative: bool = True,
) -> RockerWheelMapResult:
    """Solve one corner's signed rocker-angle / physical-wheel-coordinate map."""
    axle = corner.axle.value
    side = corner.side.value
    if not math.isfinite(requested_delta_z_wc_body_m):
        return RockerWheelMapResult(
            ZBarWheelStatus.FAILURE,
            axle,
            side,
            requested_delta_z_wc_body_m,
            failure_code=ZBarWheelFailureCode.NONFINITE_INPUT,
            message="Requested physical wheel displacement must be finite",
        )
    if corner.axle is not nominal.axle or corner.side is not nominal.side:
        return RockerWheelMapResult(
            ZBarWheelStatus.FAILURE,
            axle,
            side,
            requested_delta_z_wc_body_m,
            failure_code=ZBarWheelFailureCode.SOURCE_MISMATCH,
            message="Corner and nominal wheel-reference identities do not match",
        )

    center_physical, center = _solve_actuation_at_physical_z(
        corner,
        nominal,
        requested_delta_z_wc_body_m,
        physical_solver,
        predecessor_theta_R_rad=0.0,
        actuation_config=actuation_config,
        kinematics_config=kinematics_config,
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
        source_fixture_id=source_fixture_id,
    )
    if center is None:
        return RockerWheelMapResult(
            ZBarWheelStatus.FAILURE,
            axle,
            side,
            requested_delta_z_wc_body_m,
            failure_code=ZBarWheelFailureCode.PHYSICAL_STATE_FAILURE,
            message=center_physical.message or "Physical wheel-state inversion failed",
        )
    if not center.ok or center.rocker_theta_rad is None:
        return RockerWheelMapResult(
            ZBarWheelStatus.FAILURE,
            axle,
            side,
            requested_delta_z_wc_body_m,
            actuation_state=center,
            failure_code=ZBarWheelFailureCode.ACTUATION_FAILURE,
            message=center.message or "Rocker actuation state is unavailable",
        )
    if not with_derivative:
        return RockerWheelMapResult(
            ZBarWheelStatus.SUCCESS,
            axle,
            side,
            requested_delta_z_wc_body_m,
            actuation_state=center,
            rocker_theta_rad=center.rocker_theta_rad,
        )

    cfg = derivative_config or RockerWheelDerivativeConfig()
    first = _derivative_at_step(
        corner,
        nominal,
        center_physical,
        center,
        physical_solver,
        cfg.step_m,
        actuation_config=actuation_config,
        kinematics_config=kinematics_config,
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
        source_fixture_id=source_fixture_id,
    )
    second = _derivative_at_step(
        corner,
        nominal,
        center_physical,
        center,
        physical_solver,
        cfg.second_step_m,
        actuation_config=actuation_config,
        kinematics_config=kinematics_config,
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
        source_fixture_id=source_fixture_id,
    )
    if first is None or second is None:
        return RockerWheelMapResult(
            ZBarWheelStatus.FAILURE,
            axle,
            side,
            requested_delta_z_wc_body_m,
            actuation_state=center,
            rocker_theta_rad=center.rocker_theta_rad,
            failure_code=ZBarWheelFailureCode.ROCKER_DERIVATIVE_UNAVAILABLE,
            message="Branch-preserving rocker-over-wheel derivative is unavailable at both reviewed step sizes",
        )
    disagreement = abs(first[0] - second[0])
    if disagreement > cfg.agreement_tolerance_rad_per_m:
        return RockerWheelMapResult(
            ZBarWheelStatus.FAILURE,
            axle,
            side,
            requested_delta_z_wc_body_m,
            actuation_state=center,
            rocker_theta_rad=center.rocker_theta_rad,
            dtheta_R_dz_wc_body_rad_per_m=second[0],
            derivative_method=second[1],
            derivative_step_m=first[2],
            derivative_second_step_m=second[2],
            derivative_disagreement_rad_per_m=disagreement,
            failure_code=ZBarWheelFailureCode.ROCKER_DERIVATIVE_DISAGREEMENT,
            message="Two-step rocker-over-wheel derivative agreement exceeds tolerance",
        )
    return RockerWheelMapResult(
        ZBarWheelStatus.SUCCESS,
        axle,
        side,
        requested_delta_z_wc_body_m,
        actuation_state=center,
        rocker_theta_rad=center.rocker_theta_rad,
        dtheta_R_dz_wc_body_rad_per_m=second[0],
        derivative_method=second[1],
        derivative_step_m=first[2],
        derivative_second_step_m=second[2],
        derivative_disagreement_rad_per_m=disagreement,
    )


def solve_wufr_zbar_wheel_state(
    fixture: ZBarAxleFixture,
    left_corner: SuspensionCornerGeometry,
    right_corner: SuspensionCornerGeometry,
    left_nominal: NominalWheelReference,
    right_nominal: NominalWheelReference,
    requested_delta_z_left_m: float,
    requested_delta_z_right_m: float,
    physical_solver: PhysicalStateSolverConfig,
    *,
    setting: int,
    derivative_config: RockerWheelDerivativeConfig | None = None,
    actuation_config: ActuationSolverConfig | None = None,
    kinematics_config: KinematicsSolverConfig | None = None,
    geometry_id: str = "",
    configuration_id: str = "WUFR27_SUSPENSION_BASELINE_V0",
    source_authority: str = "",
    source_fixture_id: str = "WUFR26_OPTIMUMK_ACTUATION_V0",
    with_wheel_jacobian: bool = True,
) -> ZBarWheelStateResult:
    """Compose the reviewed corner/rocker/Z-bar chain into physical wheel coordinates."""
    stiffness = (
        WUFR_BLADE_STIFFNESS_N_PER_M[setting - 1]
        if isinstance(setting, int) and not isinstance(setting, bool) and 1 <= setting <= 5
        else math.nan
    )
    if not math.isfinite(stiffness):
        return ZBarWheelStateResult(
            ZBarWheelStatus.FAILURE,
            fixture.axle,
            setting,
            stiffness,
            requested_delta_z_left_m,
            requested_delta_z_right_m,
            failure_code=ZBarWheelFailureCode.SOURCE_MISMATCH,
            message="WUFR blade setting must be one of the discrete settings 1..5",
        )
    if (
        fixture.axle != left_corner.axle.value
        or fixture.axle != right_corner.axle.value
        or left_corner.side.value != "left"
        or right_corner.side.value != "right"
        or fixture.configuration_id != configuration_id
    ):
        return ZBarWheelStateResult(
            ZBarWheelStatus.FAILURE,
            fixture.axle,
            setting,
            stiffness,
            requested_delta_z_left_m,
            requested_delta_z_right_m,
            failure_code=ZBarWheelFailureCode.SOURCE_MISMATCH,
            message="Z-bar fixture, corner sides/axle, and configuration must match",
        )

    left = solve_rocker_wheel_map(
        left_corner,
        left_nominal,
        requested_delta_z_left_m,
        physical_solver,
        derivative_config=derivative_config,
        actuation_config=actuation_config,
        kinematics_config=kinematics_config,
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
        source_fixture_id=source_fixture_id,
        with_derivative=with_wheel_jacobian,
    )
    right = solve_rocker_wheel_map(
        right_corner,
        right_nominal,
        requested_delta_z_right_m,
        physical_solver,
        derivative_config=derivative_config,
        actuation_config=actuation_config,
        kinematics_config=kinematics_config,
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
        source_fixture_id=source_fixture_id,
        with_derivative=with_wheel_jacobian,
    )
    if not left.ok or not right.ok or left.rocker_theta_rad is None or right.rocker_theta_rad is None:
        failed = left if not left.ok else right
        return ZBarWheelStateResult(
            ZBarWheelStatus.FAILURE,
            fixture.axle,
            setting,
            stiffness,
            requested_delta_z_left_m,
            requested_delta_z_right_m,
            left_map=left,
            right_map=right,
            failure_code=failed.failure_code,
            message=failed.message or "Left/right rocker-wheel map unavailable",
        )

    mechanism = solve_nominal_zbar_mechanism(
        fixture,
        left.rocker_theta_rad,
        right.rocker_theta_rad,
        with_jacobian=with_wheel_jacobian,
    )
    if not mechanism.ok:
        return ZBarWheelStateResult(
            ZBarWheelStatus.FAILURE,
            fixture.axle,
            setting,
            stiffness,
            requested_delta_z_left_m,
            requested_delta_z_right_m,
            left_map=left,
            right_map=right,
            mechanism=mechanism,
            failure_code=ZBarWheelFailureCode.ZBAR_MECHANISM_FAILURE,
            message=mechanism.message,
        )
    force = evaluate_two_arm_force(mechanism, setting=setting, stiffness_N_per_m=stiffness)
    if not force.ok:
        return ZBarWheelStateResult(
            ZBarWheelStatus.FAILURE,
            fixture.axle,
            setting,
            stiffness,
            requested_delta_z_left_m,
            requested_delta_z_right_m,
            left_map=left,
            right_map=right,
            mechanism=mechanism,
            force=force,
            failure_code=ZBarWheelFailureCode.ZBAR_CONSTITUTIVE_FAILURE,
            message=force.message,
        )
    if not with_wheel_jacobian:
        return ZBarWheelStateResult(
            ZBarWheelStatus.SUCCESS,
            fixture.axle,
            setting,
            stiffness,
            requested_delta_z_left_m,
            requested_delta_z_right_m,
            left_map=left,
            right_map=right,
            mechanism=mechanism,
            force=force,
        )

    if (
        not mechanism.J_d_m_per_rad
        or left.dtheta_R_dz_wc_body_rad_per_m is None
        or right.dtheta_R_dz_wc_body_rad_per_m is None
        or force.force_left_N is None
        or force.force_right_N is None
    ):
        return ZBarWheelStateResult(
            ZBarWheelStatus.FAILURE,
            fixture.axle,
            setting,
            stiffness,
            requested_delta_z_left_m,
            requested_delta_z_right_m,
            left_map=left,
            right_map=right,
            mechanism=mechanism,
            force=force,
            failure_code=ZBarWheelFailureCode.WHEEL_JACOBIAN_UNAVAILABLE,
            message="Wheel-coordinate chain requires both rocker derivatives and the reviewed Z-bar Jacobian",
        )

    j_theta = mechanism.J_d_m_per_rad
    rho_l = left.dtheta_R_dz_wc_body_rad_per_m
    rho_r = right.dtheta_R_dz_wc_body_rad_per_m
    j_wheel = (
        (j_theta[0][0] * rho_l, j_theta[0][1] * rho_r),
        (j_theta[1][0] * rho_l, j_theta[1][1] * rho_r),
    )
    fl, fr = force.force_left_N, force.force_right_N
    q_wheel = (
        -(j_wheel[0][0] * fl + j_wheel[1][0] * fr),
        -(j_wheel[0][1] * fl + j_wheel[1][1] * fr),
    )
    if not all(math.isfinite(value) for row in j_wheel for value in row) or not all(math.isfinite(value) for value in q_wheel):
        return ZBarWheelStateResult(
            ZBarWheelStatus.FAILURE,
            fixture.axle,
            setting,
            stiffness,
            requested_delta_z_left_m,
            requested_delta_z_right_m,
            left_map=left,
            right_map=right,
            mechanism=mechanism,
            force=force,
            failure_code=ZBarWheelFailureCode.WHEEL_JACOBIAN_UNAVAILABLE,
            message="Wheel-coordinate Jacobian or generalized force is nonfinite",
        )
    return ZBarWheelStateResult(
        ZBarWheelStatus.SUCCESS,
        fixture.axle,
        setting,
        stiffness,
        requested_delta_z_left_m,
        requested_delta_z_right_m,
        left_map=left,
        right_map=right,
        mechanism=mechanism,
        force=force,
        J_d_wheel=j_wheel,
        generalized_wheel_force_N=q_wheel,
    )
