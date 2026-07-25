"""Source-bounded rigid suspension actuation kinematics.

Implements the equations authorized by ``AUTH-SUSP-0003``:

* EQ-SUSP-0009 arm-fixed push/pull-rod attachment transport;
* EQ-SUSP-0010 one-axis rocker closure with nominal-branch control;
* EQ-SUSP-0011 ideal coilover eye-to-eye length and displacement;
* EQ-SUSP-0012 explicitly signed local damper-over-wheel displacement derivative.

This module is geometric only.  It does not model spring or damper force, wheel
rate, damping, anti-roll bars, compliance, physical damper stroke/stops,
packaging, loads, or installed/as-built hardware.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import math
from typing import Iterable

from .geometry import ActuationAttachment, ActuationGeometry, Axle, Point3, SuspensionCornerGeometry
from .kinematics import KinematicsSolverConfig, SuspensionCornerStateResult, rotate_point_about_hinge
from .wheel_reference import (
    NominalWheelReference,
    PhysicalStateSolverConfig,
    WheelReferenceState,
    WheelReferenceStatus,
    solve_body_vertical_displacement,
    solve_wheel_reference_state,
)


class SuspensionActuationError(ValueError):
    """Raised for invalid direct actuation inputs or geometry."""


class ActuationStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class ActuationFailureCode(str, Enum):
    NONFINITE_INPUT = "nonfinite_input"
    SOURCE_MISMATCH = "source_mismatch"
    INVALID_ATTACHMENT_ROLE = "invalid_attachment_role"
    UPSTREAM_KINEMATICS_FAILURE = "upstream_kinematics_failure"
    DEGENERATE_ARM_HINGE_AXIS = "degenerate_arm_hinge_axis"
    DEGENERATE_ROCKER_AXIS = "degenerate_rocker_axis"
    NO_ROCKER_ROOT = "no_rocker_root"
    ROCKER_BRANCH_AMBIGUITY = "rocker_branch_ambiguity"
    ROCKER_ROOT_OUTSIDE_DOMAIN = "rocker_root_outside_domain"
    ROD_LENGTH_RESIDUAL = "rod_length_residual"
    PHYSICAL_STATE_FAILURE = "physical_state_failure"
    DERIVATIVE_UNAVAILABLE = "derivative_unavailable"


@dataclass(frozen=True)
class ActuationSolverConfig:
    """Explicit numerical limits for the AUTH-SUSP-0003 prototype."""

    rocker_angle_min_rad: float = -math.pi
    rocker_angle_max_rad: float = math.pi
    rocker_angle_tolerance_rad: float = 1.0e-12
    branch_tie_tolerance_rad: float = 1.0e-10
    trigonometric_reach_tolerance: float = 1.0e-12
    degenerate_axis_tolerance_m: float = 1.0e-12
    degenerate_closure_amplitude_m2: float = 1.0e-14
    rod_length_residual_tolerance_m: float = 1.0e-9
    derivative_step_m: float = 1.0e-4
    derivative_coordinate_tolerance_m: float = 1.0e-10
    reciprocal_conditioning_threshold: float = 1.0e-6

    def __post_init__(self) -> None:
        values = (
            self.rocker_angle_min_rad,
            self.rocker_angle_max_rad,
            self.rocker_angle_tolerance_rad,
            self.branch_tie_tolerance_rad,
            self.trigonometric_reach_tolerance,
            self.degenerate_axis_tolerance_m,
            self.degenerate_closure_amplitude_m2,
            self.rod_length_residual_tolerance_m,
            self.derivative_step_m,
            self.derivative_coordinate_tolerance_m,
            self.reciprocal_conditioning_threshold,
        )
        if not all(math.isfinite(value) for value in values):
            raise SuspensionActuationError("Actuation solver configuration values must be finite")
        if self.rocker_angle_min_rad >= self.rocker_angle_max_rad:
            raise SuspensionActuationError("Invalid rocker-angle domain")
        if any(
            value <= 0.0
            for value in (
                self.rocker_angle_tolerance_rad,
                self.branch_tie_tolerance_rad,
                self.trigonometric_reach_tolerance,
                self.degenerate_axis_tolerance_m,
                self.degenerate_closure_amplitude_m2,
                self.rod_length_residual_tolerance_m,
                self.derivative_step_m,
                self.derivative_coordinate_tolerance_m,
                self.reciprocal_conditioning_threshold,
            )
        ):
            raise SuspensionActuationError("Actuation numerical tolerances must be positive")


@dataclass(frozen=True)
class RockerClosureResult:
    status: ActuationStatus
    theta_R_rad: float | None = None
    candidate_roots_rad: tuple[float, ...] = ()
    selected_distance_from_predecessor_rad: float | None = None
    rod_length_m: float | None = None
    nominal_rod_length_m: float | None = None
    rod_length_residual_m: float | None = None
    rocker_axis_length_m: float | None = None
    closure_amplitude_m2: float | None = None
    predecessor_theta_R_rad: float = 0.0
    failure_code: ActuationFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is ActuationStatus.SUCCESS


@dataclass(frozen=True)
class ActuationStateResult:
    axle: Axle
    side: str
    status: ActuationStatus
    q_L_rad: float | None = None
    q_U_rad: float | None = None
    owning_arm: str = ""
    arm_attachment_m: Point3 | None = None
    rocker_theta_rad: float | None = None
    rocker_rod_point_m: Point3 | None = None
    rocker_coilover_point_m: Point3 | None = None
    nominal_push_pull_length_m: float | None = None
    current_push_pull_length_m: float | None = None
    rod_length_residual_m: float | None = None
    nominal_coilover_length_m: float | None = None
    current_coilover_length_m: float | None = None
    delta_L_d_m: float | None = None
    delta_z_wc_body_m: float | None = None
    rho_dw: float | None = None
    rho_wd: float | None = None
    derivative_method: str = ""
    derivative_step_m: float | None = None
    reciprocal_available: bool = False
    rocker_closure: RockerClosureResult | None = None
    wheel_state: WheelReferenceState | None = None
    failure_code: ActuationFailureCode | None = None
    message: str = ""
    source_fixture_id: str = ""
    configuration_id: str = ""
    source_authority: str = ""
    installed_limits_evaluated: bool = False

    @property
    def ok(self) -> bool:
        return self.status is ActuationStatus.SUCCESS


@dataclass(frozen=True)
class LocalDerivativeResult:
    status: ActuationStatus
    rho_dw: float | None = None
    rho_wd: float | None = None
    reciprocal_available: bool = False
    method: str = ""
    actual_step_m: float | None = None
    failure_code: ActuationFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is ActuationStatus.SUCCESS


def _add(a: Point3, b: Point3) -> Point3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _subtract(a: Point3, b: Point3) -> Point3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(a: Point3, scalar: float) -> Point3:
    return (a[0] * scalar, a[1] * scalar, a[2] * scalar)


def _dot(a: Point3, b: Point3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Point3, b: Point3) -> Point3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(a: Point3) -> float:
    return math.sqrt(_dot(a, a))


def _distance(a: Point3, b: Point3) -> float:
    return _norm(_subtract(a, b))


def _normalize(a: Point3, *, tolerance: float, message: str) -> Point3:
    magnitude = _norm(a)
    if not math.isfinite(magnitude) or magnitude <= tolerance:
        raise SuspensionActuationError(message)
    return _scale(a, 1.0 / magnitude)


def _finite_point(point: Point3) -> bool:
    return all(math.isfinite(value) for value in point)


def rocker_point_at_angle(
    point_m: Point3,
    actuation: ActuationGeometry,
    theta_R_rad: float,
) -> Point3:
    """Rigidly rotate a rocker-attached point about the frozen rocker axis."""

    return rotate_point_about_hinge(
        point_m,
        actuation.rocker_pivot.position_m,
        actuation.rocker_axis_reference.position_m,
        theta_R_rad,
    )


def transport_arm_attachment(
    corner: SuspensionCornerGeometry,
    upstream_state: SuspensionCornerStateResult,
) -> tuple[Point3 | None, ActuationFailureCode | None, str]:
    """EQ-SUSP-0009 transport the source-frozen arm-fixed actuation pickup."""

    if corner.axle is not upstream_state.axle or corner.side is not upstream_state.side:
        return None, ActuationFailureCode.SOURCE_MISMATCH, "Corner and upstream suspension identities do not match"
    if not upstream_state.ok:
        return (
            None,
            ActuationFailureCode.UPSTREAM_KINEMATICS_FAILURE,
            upstream_state.message or "Upstream MOD-SUSP-0001 state is unavailable",
        )

    wishbone = corner.wishbone
    nominal = corner.actuation.outboard_attachment.position_m
    if corner.axle is Axle.FRONT:
        if corner.actuation.attachment is not ActuationAttachment.UPPER_ARM:
            return None, ActuationFailureCode.INVALID_ATTACHMENT_ROLE, "Front actuation attachment must be source-frozen to the upper A-arm"
        if upstream_state.q_U_rad is None:
            return None, ActuationFailureCode.UPSTREAM_KINEMATICS_FAILURE, "Front upper-arm rotation is unavailable"
        fore = wishbone.upper_fore_inboard.position_m
        aft = wishbone.upper_aft_inboard.position_m
        angle = upstream_state.q_U_rad
    else:
        if corner.actuation.attachment is not ActuationAttachment.LOWER_ARM:
            return None, ActuationFailureCode.INVALID_ATTACHMENT_ROLE, "Rear actuation attachment must be source-frozen to the lower A-arm"
        fore = wishbone.lower_fore_inboard.position_m
        aft = wishbone.lower_aft_inboard.position_m
        angle = upstream_state.requested_q_L_rad

    try:
        point = rotate_point_about_hinge(nominal, fore, aft, angle)
    except ValueError as exc:
        return None, ActuationFailureCode.DEGENERATE_ARM_HINGE_AXIS, str(exc)
    return point, None, ""


def _deduplicate_angles(values: Iterable[float], tolerance: float) -> tuple[float, ...]:
    ordered = sorted(values)
    result: list[float] = []
    for value in ordered:
        if not result or abs(value - result[-1]) > tolerance:
            result.append(value)
    return tuple(result)


def _enumerate_periodic_root(base: float, lower: float, upper: float) -> list[float]:
    two_pi = 2.0 * math.pi
    n_min = math.ceil((lower - base) / two_pi)
    n_max = math.floor((upper - base) / two_pi)
    return [base + n * two_pi for n in range(n_min, n_max + 1)]


def solve_rocker_closure(
    actuation: ActuationGeometry,
    current_arm_attachment_m: Point3,
    *,
    predecessor_theta_R_rad: float = 0.0,
    config: ActuationSolverConfig | None = None,
) -> RockerClosureResult:
    """EQ-SUSP-0010 solve the one-axis rigid rocker closure.

    The scalar closure is reduced analytically to ``A*cos(theta)+B*sin(theta)+C=0``.
    All roots in the reviewed rocker domain are enumerated.  The selected root is
    the unique candidate nearest the supplied continuation predecessor; a tied
    continuation choice is reported as ambiguous rather than silently repaired.
    """

    solver = config or ActuationSolverConfig()
    if not math.isfinite(predecessor_theta_R_rad) or not _finite_point(current_arm_attachment_m):
        return RockerClosureResult(
            status=ActuationStatus.FAILURE,
            predecessor_theta_R_rad=predecessor_theta_R_rad,
            failure_code=ActuationFailureCode.NONFINITE_INPUT,
            message="Rocker predecessor and current arm attachment must be finite",
        )

    pivot = actuation.rocker_pivot.position_m
    axis_point = actuation.rocker_axis_reference.position_m
    rod0 = actuation.rocker_rod_point.position_m
    arm0 = actuation.outboard_attachment.position_m
    nominal_length = _distance(rod0, arm0)
    axis_vector = _subtract(axis_point, pivot)
    axis_length = _norm(axis_vector)
    try:
        k = _normalize(
            axis_vector,
            tolerance=solver.degenerate_axis_tolerance_m,
            message="Rocker pivot and axis-reference point define a degenerate axis",
        )
    except SuspensionActuationError as exc:
        return RockerClosureResult(
            status=ActuationStatus.FAILURE,
            nominal_rod_length_m=nominal_length,
            rocker_axis_length_m=axis_length,
            predecessor_theta_R_rad=predecessor_theta_R_rad,
            failure_code=ActuationFailureCode.DEGENERATE_ROCKER_AXIS,
            message=str(exc),
        )

    v = _subtract(rod0, pivot)
    v_parallel = _scale(k, _dot(k, v))
    u = _subtract(v, v_parallel)
    w = _cross(k, u)
    circle_center = _add(pivot, v_parallel)
    c = _subtract(circle_center, current_arm_attachment_m)

    a_coeff = 2.0 * _dot(c, u)
    b_coeff = 2.0 * _dot(c, w)
    c_coeff = _dot(c, c) + _dot(u, u) - nominal_length * nominal_length
    amplitude = math.hypot(a_coeff, b_coeff)

    if amplitude <= solver.degenerate_closure_amplitude_m2:
        if abs(c_coeff) <= solver.degenerate_closure_amplitude_m2:
            return RockerClosureResult(
                status=ActuationStatus.FAILURE,
                nominal_rod_length_m=nominal_length,
                rocker_axis_length_m=axis_length,
                closure_amplitude_m2=amplitude,
                predecessor_theta_R_rad=predecessor_theta_R_rad,
                failure_code=ActuationFailureCode.ROCKER_BRANCH_AMBIGUITY,
                message="Rocker closure is degenerate: every rocker angle satisfies the rod-length constraint",
            )
        return RockerClosureResult(
            status=ActuationStatus.FAILURE,
            nominal_rod_length_m=nominal_length,
            rocker_axis_length_m=axis_length,
            closure_amplitude_m2=amplitude,
            predecessor_theta_R_rad=predecessor_theta_R_rad,
            failure_code=ActuationFailureCode.NO_ROCKER_ROOT,
            message="Rocker closure has no angular dependence and cannot satisfy the frozen rod length",
        )

    normalized_rhs = -c_coeff / amplitude
    if normalized_rhs < -1.0 - solver.trigonometric_reach_tolerance or normalized_rhs > 1.0 + solver.trigonometric_reach_tolerance:
        return RockerClosureResult(
            status=ActuationStatus.FAILURE,
            nominal_rod_length_m=nominal_length,
            rocker_axis_length_m=axis_length,
            closure_amplitude_m2=amplitude,
            predecessor_theta_R_rad=predecessor_theta_R_rad,
            failure_code=ActuationFailureCode.NO_ROCKER_ROOT,
            message="Requested arm attachment is unreachable by the rigid rocker/push-pull geometry",
        )

    normalized_rhs = max(-1.0, min(1.0, normalized_rhs))
    phase = math.atan2(b_coeff, a_coeff)
    offset = math.acos(normalized_rhs)
    candidates: list[float] = []
    for base in (phase + offset, phase - offset):
        candidates.extend(
            _enumerate_periodic_root(base, solver.rocker_angle_min_rad, solver.rocker_angle_max_rad)
        )
    roots = _deduplicate_angles(candidates, solver.rocker_angle_tolerance_rad * 10.0)
    if not roots:
        return RockerClosureResult(
            status=ActuationStatus.FAILURE,
            nominal_rod_length_m=nominal_length,
            rocker_axis_length_m=axis_length,
            closure_amplitude_m2=amplitude,
            predecessor_theta_R_rad=predecessor_theta_R_rad,
            failure_code=ActuationFailureCode.ROCKER_ROOT_OUTSIDE_DOMAIN,
            message="Rocker closure roots exist only outside the reviewed rocker-angle domain",
        )

    distances = tuple(abs(root - predecessor_theta_R_rad) for root in roots)
    best_distance = min(distances)
    nearest = tuple(
        root
        for root, distance in zip(roots, distances)
        if abs(distance - best_distance) <= solver.branch_tie_tolerance_rad
    )
    if len(nearest) != 1:
        return RockerClosureResult(
            status=ActuationStatus.FAILURE,
            candidate_roots_rad=roots,
            selected_distance_from_predecessor_rad=best_distance,
            nominal_rod_length_m=nominal_length,
            rocker_axis_length_m=axis_length,
            closure_amplitude_m2=amplitude,
            predecessor_theta_R_rad=predecessor_theta_R_rad,
            failure_code=ActuationFailureCode.ROCKER_BRANCH_AMBIGUITY,
            message="Multiple rocker roots are equally compatible with the continuation predecessor",
        )

    theta = nearest[0]
    try:
        rod_point = rocker_point_at_angle(rod0, actuation, theta)
    except ValueError as exc:
        return RockerClosureResult(
            status=ActuationStatus.FAILURE,
            candidate_roots_rad=roots,
            nominal_rod_length_m=nominal_length,
            rocker_axis_length_m=axis_length,
            closure_amplitude_m2=amplitude,
            predecessor_theta_R_rad=predecessor_theta_R_rad,
            failure_code=ActuationFailureCode.DEGENERATE_ROCKER_AXIS,
            message=str(exc),
        )
    current_length = _distance(rod_point, current_arm_attachment_m)
    residual = current_length - nominal_length
    if abs(residual) > solver.rod_length_residual_tolerance_m:
        return RockerClosureResult(
            status=ActuationStatus.FAILURE,
            theta_R_rad=theta,
            candidate_roots_rad=roots,
            selected_distance_from_predecessor_rad=best_distance,
            rod_length_m=current_length,
            nominal_rod_length_m=nominal_length,
            rod_length_residual_m=residual,
            rocker_axis_length_m=axis_length,
            closure_amplitude_m2=amplitude,
            predecessor_theta_R_rad=predecessor_theta_R_rad,
            failure_code=ActuationFailureCode.ROD_LENGTH_RESIDUAL,
            message="Solved rocker root does not preserve push/pull-rod length within tolerance",
        )
    return RockerClosureResult(
        status=ActuationStatus.SUCCESS,
        theta_R_rad=theta,
        candidate_roots_rad=roots,
        selected_distance_from_predecessor_rad=best_distance,
        rod_length_m=current_length,
        nominal_rod_length_m=nominal_length,
        rod_length_residual_m=residual,
        rocker_axis_length_m=axis_length,
        closure_amplitude_m2=amplitude,
        predecessor_theta_R_rad=predecessor_theta_R_rad,
    )


def ideal_coilover_state(
    actuation: ActuationGeometry,
    theta_R_rad: float,
) -> tuple[float, float, Point3]:
    """EQ-SUSP-0011 return current length, signed displacement, and rocker eye."""

    coil0 = actuation.rocker_coil_point.position_m
    chassis = actuation.chassis_attachment.position_m
    current_coil = rocker_point_at_angle(coil0, actuation, theta_R_rad)
    nominal_length = _distance(coil0, chassis)
    current_length = _distance(current_coil, chassis)
    return current_length, current_length - nominal_length, current_coil


def _failure_state(
    corner: SuspensionCornerGeometry,
    code: ActuationFailureCode,
    message: str,
    *,
    q_L_rad: float | None = None,
    wheel_state: WheelReferenceState | None = None,
    rocker_closure: RockerClosureResult | None = None,
    source_fixture_id: str = "",
) -> ActuationStateResult:
    upstream = wheel_state.upstream_state if wheel_state is not None else None
    return ActuationStateResult(
        axle=corner.axle,
        side=corner.side.value,
        status=ActuationStatus.FAILURE,
        q_L_rad=q_L_rad,
        q_U_rad=(upstream.q_U_rad if upstream is not None else None),
        rocker_closure=rocker_closure,
        wheel_state=wheel_state,
        failure_code=code,
        message=message,
        source_fixture_id=source_fixture_id,
        configuration_id=(upstream.configuration_id if upstream is not None else ""),
        source_authority=(upstream.source_authority if upstream is not None else ""),
        installed_limits_evaluated=False,
    )


def solve_actuation_from_wheel_state(
    corner: SuspensionCornerGeometry,
    wheel_state: WheelReferenceState,
    *,
    predecessor_theta_R_rad: float = 0.0,
    config: ActuationSolverConfig | None = None,
    source_fixture_id: str = "WUFR26_OPTIMUMK_ACTUATION_V0",
) -> ActuationStateResult:
    """Compose EQ-SUSP-0009..0011 with an already reviewed wheel/suspension state."""

    solver = config or ActuationSolverConfig()
    if corner.axle is not wheel_state.axle or corner.side is not wheel_state.side:
        return _failure_state(
            corner,
            ActuationFailureCode.SOURCE_MISMATCH,
            "Corner geometry and wheel-state identities do not match",
            q_L_rad=wheel_state.q_L_rad,
            wheel_state=wheel_state,
            source_fixture_id=source_fixture_id,
        )
    if wheel_state.status is not WheelReferenceStatus.SUCCESS or wheel_state.upstream_state is None:
        return _failure_state(
            corner,
            ActuationFailureCode.UPSTREAM_KINEMATICS_FAILURE,
            wheel_state.message or "Upstream wheel/suspension state is unavailable",
            q_L_rad=wheel_state.q_L_rad,
            wheel_state=wheel_state,
            source_fixture_id=source_fixture_id,
        )

    arm_point, arm_failure, arm_message = transport_arm_attachment(corner, wheel_state.upstream_state)
    if arm_point is None:
        return _failure_state(
            corner,
            arm_failure or ActuationFailureCode.UPSTREAM_KINEMATICS_FAILURE,
            arm_message,
            q_L_rad=wheel_state.q_L_rad,
            wheel_state=wheel_state,
            source_fixture_id=source_fixture_id,
        )

    closure = solve_rocker_closure(
        corner.actuation,
        arm_point,
        predecessor_theta_R_rad=predecessor_theta_R_rad,
        config=solver,
    )
    if not closure.ok or closure.theta_R_rad is None:
        return _failure_state(
            corner,
            closure.failure_code or ActuationFailureCode.NO_ROCKER_ROOT,
            closure.message,
            q_L_rad=wheel_state.q_L_rad,
            wheel_state=wheel_state,
            rocker_closure=closure,
            source_fixture_id=source_fixture_id,
        )

    try:
        rod_point = rocker_point_at_angle(
            corner.actuation.rocker_rod_point.position_m,
            corner.actuation,
            closure.theta_R_rad,
        )
        current_coil_length, delta_l, coil_point = ideal_coilover_state(
            corner.actuation,
            closure.theta_R_rad,
        )
    except ValueError as exc:
        return _failure_state(
            corner,
            ActuationFailureCode.DEGENERATE_ROCKER_AXIS,
            str(exc),
            q_L_rad=wheel_state.q_L_rad,
            wheel_state=wheel_state,
            rocker_closure=closure,
            source_fixture_id=source_fixture_id,
        )

    nominal_coil_length = _distance(
        corner.actuation.rocker_coil_point.position_m,
        corner.actuation.chassis_attachment.position_m,
    )
    upstream = wheel_state.upstream_state
    return ActuationStateResult(
        axle=corner.axle,
        side=corner.side.value,
        status=ActuationStatus.SUCCESS,
        q_L_rad=wheel_state.q_L_rad,
        q_U_rad=upstream.q_U_rad,
        owning_arm=corner.actuation.attachment.value,
        arm_attachment_m=arm_point,
        rocker_theta_rad=closure.theta_R_rad,
        rocker_rod_point_m=rod_point,
        rocker_coilover_point_m=coil_point,
        nominal_push_pull_length_m=closure.nominal_rod_length_m,
        current_push_pull_length_m=closure.rod_length_m,
        rod_length_residual_m=closure.rod_length_residual_m,
        nominal_coilover_length_m=nominal_coil_length,
        current_coilover_length_m=current_coil_length,
        delta_L_d_m=delta_l,
        delta_z_wc_body_m=wheel_state.delta_z_wc_body_m,
        rocker_closure=closure,
        wheel_state=wheel_state,
        source_fixture_id=source_fixture_id,
        configuration_id=upstream.configuration_id,
        source_authority=upstream.source_authority,
        installed_limits_evaluated=False,
    )


def solve_actuation_q_L_state(
    corner: SuspensionCornerGeometry,
    nominal_wheel_reference: NominalWheelReference,
    q_L_rad: float,
    *,
    predecessor: ActuationStateResult | None = None,
    actuation_config: ActuationSolverConfig | None = None,
    kinematics_config: KinematicsSolverConfig | None = None,
    geometry_id: str = "",
    configuration_id: str = "WUFR27_SUSPENSION_BASELINE_V0",
    source_authority: str = "",
    source_fixture_id: str = "WUFR26_OPTIMUMK_ACTUATION_V0",
) -> ActuationStateResult:
    """Solve one actuation state from the internal lower-arm coordinate q_L."""

    predecessor_wheel_upstream = None
    predecessor_theta = 0.0
    if predecessor is not None and predecessor.ok:
        predecessor_theta = predecessor.rocker_theta_rad or 0.0
        if predecessor.wheel_state is not None:
            predecessor_wheel_upstream = predecessor.wheel_state.upstream_state

    wheel = solve_wheel_reference_state(
        corner,
        nominal_wheel_reference,
        q_L_rad,
        predecessor=predecessor_wheel_upstream,
        kinematics_config=kinematics_config,
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
    )
    if not wheel.ok:
        return _failure_state(
            corner,
            ActuationFailureCode.UPSTREAM_KINEMATICS_FAILURE,
            wheel.message,
            q_L_rad=q_L_rad,
            wheel_state=wheel,
            source_fixture_id=source_fixture_id,
        )
    return solve_actuation_from_wheel_state(
        corner,
        wheel,
        predecessor_theta_R_rad=predecessor_theta,
        config=actuation_config,
        source_fixture_id=source_fixture_id,
    )


def evaluate_local_derivative(
    *,
    z_center_m: float,
    delta_l_center_m: float,
    z_minus_m: float | None = None,
    delta_l_minus_m: float | None = None,
    z_plus_m: float | None = None,
    delta_l_plus_m: float | None = None,
    reciprocal_conditioning_threshold: float = 1.0e-6,
    coordinate_tolerance_m: float = 1.0e-12,
) -> LocalDerivativeResult:
    """EQ-SUSP-0012 evaluate a signed local damper-over-wheel derivative.

    Supplying both neighbor states uses a centered secant through the two physical
    wheel coordinates.  Supplying one neighbor uses a labelled one-sided secant.
    No absolute value is applied.  A near-zero derivative remains a valid ``rho_dw``
    but its reciprocal is intentionally unavailable.
    """

    values = (z_center_m, delta_l_center_m, reciprocal_conditioning_threshold, coordinate_tolerance_m)
    if not all(math.isfinite(value) for value in values) or reciprocal_conditioning_threshold <= 0.0 or coordinate_tolerance_m <= 0.0:
        return LocalDerivativeResult(
            status=ActuationStatus.FAILURE,
            failure_code=ActuationFailureCode.NONFINITE_INPUT,
            message="Derivative inputs and conditioning thresholds must be finite and positive where required",
        )

    has_minus = z_minus_m is not None and delta_l_minus_m is not None
    has_plus = z_plus_m is not None and delta_l_plus_m is not None
    if has_minus and has_plus:
        assert z_minus_m is not None and delta_l_minus_m is not None
        assert z_plus_m is not None and delta_l_plus_m is not None
        if not all(math.isfinite(value) for value in (z_minus_m, delta_l_minus_m, z_plus_m, delta_l_plus_m)):
            return LocalDerivativeResult(
                status=ActuationStatus.FAILURE,
                failure_code=ActuationFailureCode.NONFINITE_INPUT,
                message="Derivative neighbor states must be finite",
            )
        denominator = z_plus_m - z_minus_m
        numerator = delta_l_plus_m - delta_l_minus_m
        method = "centered_physical_wheel_coordinate"
        actual_step = 0.5 * abs(denominator)
    elif has_minus:
        assert z_minus_m is not None and delta_l_minus_m is not None
        if not all(math.isfinite(value) for value in (z_minus_m, delta_l_minus_m)):
            return LocalDerivativeResult(status=ActuationStatus.FAILURE, failure_code=ActuationFailureCode.NONFINITE_INPUT, message="Derivative neighbor state must be finite")
        denominator = z_center_m - z_minus_m
        numerator = delta_l_center_m - delta_l_minus_m
        method = "backward_one_sided_physical_wheel_coordinate"
        actual_step = abs(denominator)
    elif has_plus:
        assert z_plus_m is not None and delta_l_plus_m is not None
        if not all(math.isfinite(value) for value in (z_plus_m, delta_l_plus_m)):
            return LocalDerivativeResult(status=ActuationStatus.FAILURE, failure_code=ActuationFailureCode.NONFINITE_INPUT, message="Derivative neighbor state must be finite")
        denominator = z_plus_m - z_center_m
        numerator = delta_l_plus_m - delta_l_center_m
        method = "forward_one_sided_physical_wheel_coordinate"
        actual_step = abs(denominator)
    else:
        return LocalDerivativeResult(
            status=ActuationStatus.FAILURE,
            failure_code=ActuationFailureCode.DERIVATIVE_UNAVAILABLE,
            message="At least one branch-preserving physical-wheel neighbor is required",
        )

    if abs(denominator) <= coordinate_tolerance_m:
        return LocalDerivativeResult(
            status=ActuationStatus.FAILURE,
            method=method,
            actual_step_m=actual_step,
            failure_code=ActuationFailureCode.DERIVATIVE_UNAVAILABLE,
            message="Physical wheel-coordinate difference is too small for a conditioned derivative",
        )
    rho_dw = numerator / denominator
    if not math.isfinite(rho_dw):
        return LocalDerivativeResult(
            status=ActuationStatus.FAILURE,
            method=method,
            actual_step_m=actual_step,
            failure_code=ActuationFailureCode.DERIVATIVE_UNAVAILABLE,
            message="Computed local actuation derivative is nonfinite",
        )
    reciprocal_available = abs(rho_dw) > reciprocal_conditioning_threshold
    rho_wd = 1.0 / rho_dw if reciprocal_available else None
    return LocalDerivativeResult(
        status=ActuationStatus.SUCCESS,
        rho_dw=rho_dw,
        rho_wd=rho_wd,
        reciprocal_available=reciprocal_available,
        method=method,
        actual_step_m=actual_step,
    )


def solve_body_vertical_actuation_state(
    corner: SuspensionCornerGeometry,
    nominal_wheel_reference: NominalWheelReference,
    requested_delta_z_wc_body_m: float,
    physical_solver: PhysicalStateSolverConfig,
    *,
    actuation_config: ActuationSolverConfig | None = None,
    kinematics_config: KinematicsSolverConfig | None = None,
    geometry_id: str = "",
    configuration_id: str = "WUFR27_SUSPENSION_BASELINE_V0",
    source_authority: str = "",
    source_fixture_id: str = "WUFR26_OPTIMUMK_ACTUATION_V0",
) -> ActuationStateResult:
    """Solve actuation from the reviewed physical wheel coordinate and evaluate rho_dw."""

    solver = actuation_config or ActuationSolverConfig()
    physical = solve_body_vertical_displacement(
        corner,
        nominal_wheel_reference,
        requested_delta_z_wc_body_m,
        physical_solver,
        kinematics_config=kinematics_config,
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
    )
    if not physical.ok or physical.wheel_state is None:
        return _failure_state(
            corner,
            ActuationFailureCode.PHYSICAL_STATE_FAILURE,
            physical.message or "MOD-SUSP-0002 physical-state inversion failed",
            q_L_rad=physical.q_L_rad,
            wheel_state=physical.wheel_state,
            source_fixture_id=source_fixture_id,
        )
    center = solve_actuation_from_wheel_state(
        corner,
        physical.wheel_state,
        predecessor_theta_R_rad=0.0,
        config=solver,
        source_fixture_id=source_fixture_id,
    )
    if not center.ok or center.delta_L_d_m is None or center.rocker_theta_rad is None:
        return center

    reachable = physical.reachable_delta_z_range_m
    if reachable is None:
        return replace(
            center,
            status=ActuationStatus.FAILURE,
            failure_code=ActuationFailureCode.DERIVATIVE_UNAVAILABLE,
            message="Physical-state solver did not report a reachable displacement domain",
        )
    h = solver.derivative_step_m
    lower, upper = reachable
    z_center = requested_delta_z_wc_body_m
    z_minus = z_center - h
    z_plus = z_center + h
    use_minus = z_minus >= lower - physical_solver.displacement_tolerance_m
    use_plus = z_plus <= upper + physical_solver.displacement_tolerance_m

    neighbor_minus: ActuationStateResult | None = None
    neighbor_plus: ActuationStateResult | None = None
    for label, z_neighbor, enabled in (("minus", z_minus, use_minus), ("plus", z_plus, use_plus)):
        if not enabled:
            continue
        neighbor_physical = solve_body_vertical_displacement(
            corner,
            nominal_wheel_reference,
            z_neighbor,
            physical_solver,
            kinematics_config=kinematics_config,
            geometry_id=geometry_id,
            configuration_id=configuration_id,
            source_authority=source_authority,
        )
        if not neighbor_physical.ok or neighbor_physical.wheel_state is None:
            continue
        neighbor = solve_actuation_from_wheel_state(
            corner,
            neighbor_physical.wheel_state,
            predecessor_theta_R_rad=center.rocker_theta_rad,
            config=solver,
            source_fixture_id=source_fixture_id,
        )
        if not neighbor.ok or neighbor.delta_L_d_m is None or neighbor.delta_z_wc_body_m is None:
            continue
        if label == "minus":
            neighbor_minus = neighbor
        else:
            neighbor_plus = neighbor

    derivative = evaluate_local_derivative(
        z_center_m=float(center.delta_z_wc_body_m),
        delta_l_center_m=center.delta_L_d_m,
        z_minus_m=(neighbor_minus.delta_z_wc_body_m if neighbor_minus is not None else None),
        delta_l_minus_m=(neighbor_minus.delta_L_d_m if neighbor_minus is not None else None),
        z_plus_m=(neighbor_plus.delta_z_wc_body_m if neighbor_plus is not None else None),
        delta_l_plus_m=(neighbor_plus.delta_L_d_m if neighbor_plus is not None else None),
        reciprocal_conditioning_threshold=solver.reciprocal_conditioning_threshold,
        coordinate_tolerance_m=solver.derivative_coordinate_tolerance_m,
    )
    if not derivative.ok:
        return replace(
            center,
            status=ActuationStatus.FAILURE,
            derivative_method=derivative.method,
            derivative_step_m=derivative.actual_step_m,
            failure_code=derivative.failure_code,
            message=derivative.message,
        )
    return replace(
        center,
        rho_dw=derivative.rho_dw,
        rho_wd=derivative.rho_wd,
        derivative_method=derivative.method,
        derivative_step_m=derivative.actual_step_m,
        reciprocal_available=derivative.reciprocal_available,
    )
