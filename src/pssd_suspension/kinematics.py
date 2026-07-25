"""Bounded rigid double-wishbone suspension kinematics.

This module implements the equations authorized by ``AUTH-SUSP-0001``:

* exact A-arm rotation about the fore-to-aft chassis hinge axis;
* branch-controlled upper-arm closure from rigid upright joint separation;
* deterministic shortest-rotation/minimum-twist upright reference transport;
* rear-only chassis toe-link twist closure.

The independent coordinate is the signed lower-arm hinge rotation ``q_L``.  It is
an internal kinematic coordinate, not a wheel-jounce/heave definition.  Front
steering tie-rod closure remains owned by ``MOD-STEER-0001``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Callable, Iterable

from .geometry import (
    Axle,
    Mat3,
    Point3,
    Side,
    SuspensionCornerGeometry,
    SuspensionGeometrySet,
    ToeLinkRole,
)


class SuspensionKinematicsError(ValueError):
    """Raised for invalid direct equation inputs or geometry definitions."""


class KinematicsStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class KinematicsFailureCode(str, Enum):
    NONFINITE_INPUT = "nonfinite_input"
    INPUT_OUTSIDE_DOMAIN = "input_outside_operational_domain"
    DEGENERATE_HINGE_AXIS = "degenerate_hinge_axis"
    NO_CLOSURE_ROOT = "no_closure_root"
    BRANCH_AMBIGUITY = "branch_ambiguity"
    ROOT_NONCONVERGENCE = "root_nonconvergence"
    ZERO_KINGPIN_LENGTH = "zero_kingpin_length"
    ANTIPARALLEL_REFERENCE_AXIS = "antiparallel_reference_axis"
    INVALID_REAR_TOE_LINK_ROLE = "invalid_rear_toe_link_role"
    NEAR_SINGULAR = "near_singular"


class KinematicsWarningCode(str, Enum):
    NEAR_SINGULAR = "near_singular"
    PROVISIONAL_ANGULAR_DOMAIN = "provisional_angular_domain"


@dataclass(frozen=True)
class KinematicsSolverConfig:
    """Explicit numerical limits for the first rigid suspension prototype."""

    lower_angle_min_rad: float = -math.pi / 2.0
    lower_angle_max_rad: float = math.pi / 2.0
    upper_angle_min_rad: float = -math.pi / 2.0
    upper_angle_max_rad: float = math.pi / 2.0
    rear_twist_min_rad: float = -math.pi / 2.0
    rear_twist_max_rad: float = math.pi / 2.0
    initial_bracket_step_rad: float = math.radians(1.0)
    bracket_growth: float = 1.6
    root_angle_tolerance_rad: float = 1.0e-12
    length_residual_tolerance_m: float = 1.0e-10
    squared_residual_zero_tolerance_m2: float = 1.0e-16
    singular_derivative_threshold_m2_per_rad: float = 1.0e-10
    max_iterations: int = 120

    def __post_init__(self) -> None:
        finite_values = (
            self.lower_angle_min_rad,
            self.lower_angle_max_rad,
            self.upper_angle_min_rad,
            self.upper_angle_max_rad,
            self.rear_twist_min_rad,
            self.rear_twist_max_rad,
            self.initial_bracket_step_rad,
            self.bracket_growth,
            self.root_angle_tolerance_rad,
            self.length_residual_tolerance_m,
            self.squared_residual_zero_tolerance_m2,
            self.singular_derivative_threshold_m2_per_rad,
        )
        if not all(math.isfinite(value) for value in finite_values):
            raise SuspensionKinematicsError("Solver configuration values must be finite")
        for lower, upper, name in (
            (self.lower_angle_min_rad, self.lower_angle_max_rad, "lower arm"),
            (self.upper_angle_min_rad, self.upper_angle_max_rad, "upper arm"),
            (self.rear_twist_min_rad, self.rear_twist_max_rad, "rear twist"),
        ):
            if lower >= upper:
                raise SuspensionKinematicsError(f"Invalid {name} angular domain")
        if self.initial_bracket_step_rad <= 0.0:
            raise SuspensionKinematicsError("initial_bracket_step_rad must be positive")
        if self.bracket_growth <= 1.0:
            raise SuspensionKinematicsError("bracket_growth must be greater than one")
        if self.root_angle_tolerance_rad <= 0.0 or self.length_residual_tolerance_m <= 0.0:
            raise SuspensionKinematicsError("Root tolerances must be positive")
        if self.squared_residual_zero_tolerance_m2 <= 0.0:
            raise SuspensionKinematicsError("Squared residual tolerance must be positive")
        if self.singular_derivative_threshold_m2_per_rad <= 0.0:
            raise SuspensionKinematicsError("Singularity threshold must be positive")
        if self.max_iterations <= 0:
            raise SuspensionKinematicsError("max_iterations must be positive")


@dataclass(frozen=True)
class RootBracket:
    lower_rad: float
    upper_rad: float
    f_lower: float
    f_upper: float


@dataclass(frozen=True)
class ScalarRootResult:
    status: KinematicsStatus
    root_rad: float | None = None
    bracket: RootBracket | None = None
    iterations: int = 0
    failure_code: KinematicsFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is KinematicsStatus.SUCCESS


@dataclass(frozen=True)
class UprightReferenceTransform:
    """Rigid transform from nominal upright coordinates to one suspension state."""

    rotation: Mat3
    translation_m: Point3
    source_role: str = "minimum_twist_zero_steer_reference"

    def apply_point(self, point: Point3) -> Point3:
        return _add(_mat_vec(self.rotation, point), self.translation_m)

    def apply_direction(self, direction: Point3) -> Point3:
        return _normalize(_mat_vec(self.rotation, direction), failure="zero direction")


@dataclass(frozen=True)
class SuspensionCornerStateResult:
    axle: Axle
    side: Side
    requested_q_L_rad: float
    status: KinematicsStatus
    q_U_rad: float | None = None
    lower_upright_m: Point3 | None = None
    upper_upright_m: Point3 | None = None
    kingpin_direction: Point3 | None = None
    minimum_twist_transform: UprightReferenceTransform | None = None
    upright_transform: UprightReferenceTransform | None = None
    rear_twist_rad: float | None = None
    lower_fore_leg_residual_m: float | None = None
    lower_aft_leg_residual_m: float | None = None
    upper_fore_leg_residual_m: float | None = None
    upper_aft_leg_residual_m: float | None = None
    upright_separation_residual_m: float | None = None
    rear_toe_link_residual_m: float | None = None
    upper_closure_derivative_m2_per_rad: float | None = None
    rear_toe_derivative_m2_per_rad: float | None = None
    upper_root: ScalarRootResult | None = None
    rear_root: ScalarRootResult | None = None
    continuation_predecessor_q_U_rad: float | None = None
    continuation_predecessor_rear_twist_rad: float | None = None
    warnings: tuple[KinematicsWarningCode, ...] = ()
    failure_code: KinematicsFailureCode | None = None
    message: str = ""
    geometry_id: str = ""
    configuration_id: str = ""
    source_authority: str = ""

    @property
    def ok(self) -> bool:
        return self.status is KinematicsStatus.SUCCESS


IDENTITY_MAT3: Mat3 = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)


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


def _normalize(a: Point3, *, failure: str) -> Point3:
    magnitude = _norm(a)
    if not math.isfinite(magnitude) or magnitude <= 1.0e-14:
        raise SuspensionKinematicsError(failure)
    return _scale(a, 1.0 / magnitude)


def _mat_vec(matrix: Mat3, vector: Point3) -> Point3:
    return tuple(_dot(row, vector) for row in matrix)  # type: ignore[return-value]


def _mat_mul(left: Mat3, right: Mat3) -> Mat3:
    columns = tuple(zip(*right))
    return tuple(
        tuple(sum(left[i][k] * columns[j][k] for k in range(3)) for j in range(3))
        for i in range(3)
    )  # type: ignore[return-value]


def _axis_angle_matrix(axis: Point3, angle_rad: float) -> Mat3:
    e = _normalize(axis, failure="Axis direction is degenerate")
    x, y, z = e
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    one_c = 1.0 - c
    return (
        (c + x * x * one_c, x * y * one_c - z * s, x * z * one_c + y * s),
        (y * x * one_c + z * s, c + y * y * one_c, y * z * one_c - x * s),
        (z * x * one_c - y * s, z * y * one_c + x * s, c + z * z * one_c),
    )


def rotate_point_about_hinge(
    point_m: Point3,
    fore_inboard_m: Point3,
    aft_inboard_m: Point3,
    angle_rad: float,
) -> Point3:
    """EQ-SUSP-0001: rotate one outboard point about its A-arm hinge axis."""

    if not math.isfinite(angle_rad):
        raise SuspensionKinematicsError("A-arm rotation must be finite")
    axis = _subtract(aft_inboard_m, fore_inboard_m)
    if _norm(axis) <= 1.0e-14:
        raise SuspensionKinematicsError("A-arm fore/aft inboard points define a degenerate hinge axis")
    rotation = _axis_angle_matrix(axis, angle_rad)
    return _add(fore_inboard_m, _mat_vec(rotation, _subtract(point_m, fore_inboard_m)))


def _arm_rotation_derivative(
    current_outboard_m: Point3,
    fore_inboard_m: Point3,
    aft_inboard_m: Point3,
) -> Point3:
    axis = _normalize(
        _subtract(aft_inboard_m, fore_inboard_m),
        failure="A-arm fore/aft inboard points define a degenerate hinge axis",
    )
    return _cross(axis, _subtract(current_outboard_m, fore_inboard_m))


def _find_continuation_bracket(
    function: Callable[[float], float],
    *,
    predecessor_rad: float,
    lower_rad: float,
    upper_rad: float,
    config: KinematicsSolverConfig,
) -> ScalarRootResult:
    if not (lower_rad <= predecessor_rad <= upper_rad):
        return ScalarRootResult(
            status=KinematicsStatus.FAILURE,
            failure_code=KinematicsFailureCode.INPUT_OUTSIDE_DOMAIN,
            message="Continuation predecessor lies outside the declared angular domain",
        )

    f0 = function(predecessor_rad)
    if not math.isfinite(f0):
        return ScalarRootResult(
            status=KinematicsStatus.FAILURE,
            failure_code=KinematicsFailureCode.NONFINITE_INPUT,
            message="Closure function is nonfinite at the continuation predecessor",
        )
    if abs(f0) <= config.squared_residual_zero_tolerance_m2:
        bracket = RootBracket(predecessor_rad, predecessor_rad, f0, f0)
        return ScalarRootResult(
            status=KinematicsStatus.SUCCESS,
            root_rad=predecessor_rad,
            bracket=bracket,
            iterations=0,
        )

    step = config.initial_bracket_step_rad
    left_x = predecessor_rad
    right_x = predecessor_rad
    left_f = f0
    right_f = f0
    left_candidate: RootBracket | None = None
    right_candidate: RootBracket | None = None

    while left_candidate is None or right_candidate is None:
        progressed = False
        next_left = max(lower_rad, predecessor_rad - step)
        if left_candidate is None and next_left < left_x:
            progressed = True
            next_f = function(next_left)
            if not math.isfinite(next_f):
                return ScalarRootResult(
                    status=KinematicsStatus.FAILURE,
                    failure_code=KinematicsFailureCode.NONFINITE_INPUT,
                    message="Closure function became nonfinite while bracketing",
                )
            if abs(next_f) <= config.squared_residual_zero_tolerance_m2:
                left_candidate = RootBracket(next_left, next_left, next_f, next_f)
            elif next_f * left_f < 0.0:
                left_candidate = RootBracket(next_left, left_x, next_f, left_f)
            left_x, left_f = next_left, next_f

        next_right = min(upper_rad, predecessor_rad + step)
        if right_candidate is None and next_right > right_x:
            progressed = True
            next_f = function(next_right)
            if not math.isfinite(next_f):
                return ScalarRootResult(
                    status=KinematicsStatus.FAILURE,
                    failure_code=KinematicsFailureCode.NONFINITE_INPUT,
                    message="Closure function became nonfinite while bracketing",
                )
            if abs(next_f) <= config.squared_residual_zero_tolerance_m2:
                right_candidate = RootBracket(next_right, next_right, next_f, next_f)
            elif right_f * next_f < 0.0:
                right_candidate = RootBracket(right_x, next_right, right_f, next_f)
            right_x, right_f = next_right, next_f

        if left_candidate is not None or right_candidate is not None:
            break
        if not progressed or (left_x <= lower_rad and right_x >= upper_rad):
            break
        step *= config.bracket_growth

    candidates = [candidate for candidate in (left_candidate, right_candidate) if candidate is not None]
    if not candidates:
        return ScalarRootResult(
            status=KinematicsStatus.FAILURE,
            failure_code=KinematicsFailureCode.NO_CLOSURE_ROOT,
            message="No closure root was bracketed on the nominal-continuation branch",
        )
    if len(candidates) == 2:
        left_distance = min(
            abs(candidates[0].lower_rad - predecessor_rad),
            abs(candidates[0].upper_rad - predecessor_rad),
        )
        right_distance = min(
            abs(candidates[1].lower_rad - predecessor_rad),
            abs(candidates[1].upper_rad - predecessor_rad),
        )
        if abs(left_distance - right_distance) <= config.root_angle_tolerance_rad:
            return ScalarRootResult(
                status=KinematicsStatus.FAILURE,
                failure_code=KinematicsFailureCode.BRANCH_AMBIGUITY,
                message="Two closure roots are equally adjacent to the continuation predecessor",
            )
        bracket = candidates[0] if left_distance < right_distance else candidates[1]
    else:
        bracket = candidates[0]

    if bracket.lower_rad == bracket.upper_rad:
        return ScalarRootResult(
            status=KinematicsStatus.SUCCESS,
            root_rad=bracket.lower_rad,
            bracket=bracket,
            iterations=0,
        )
    return ScalarRootResult(status=KinematicsStatus.SUCCESS, bracket=bracket)


def _bisect_bracketed_root(
    function: Callable[[float], float],
    physical_residual: Callable[[float], float],
    bracket_result: ScalarRootResult,
    *,
    config: KinematicsSolverConfig,
) -> ScalarRootResult:
    if not bracket_result.ok or bracket_result.bracket is None:
        return bracket_result
    if bracket_result.root_rad is not None:
        return bracket_result

    bracket = bracket_result.bracket
    lower = bracket.lower_rad
    upper = bracket.upper_rad
    f_lower = bracket.f_lower
    f_upper = bracket.f_upper
    if f_lower * f_upper > 0.0:
        return ScalarRootResult(
            status=KinematicsStatus.FAILURE,
            bracket=bracket,
            failure_code=KinematicsFailureCode.NO_CLOSURE_ROOT,
            message="Supplied root bracket does not straddle a root",
        )

    for iteration in range(1, config.max_iterations + 1):
        midpoint = 0.5 * (lower + upper)
        f_mid = function(midpoint)
        residual = physical_residual(midpoint)
        if not math.isfinite(f_mid) or not math.isfinite(residual):
            return ScalarRootResult(
                status=KinematicsStatus.FAILURE,
                bracket=RootBracket(lower, upper, f_lower, f_upper),
                iterations=iteration,
                failure_code=KinematicsFailureCode.NONFINITE_INPUT,
                message="Closure function became nonfinite during bisection",
            )
        if (
            abs(residual) <= config.length_residual_tolerance_m
            or abs(upper - lower) <= config.root_angle_tolerance_rad
        ):
            return ScalarRootResult(
                status=KinematicsStatus.SUCCESS,
                root_rad=midpoint,
                bracket=RootBracket(lower, upper, f_lower, f_upper),
                iterations=iteration,
            )
        if f_lower * f_mid <= 0.0:
            upper, f_upper = midpoint, f_mid
        else:
            lower, f_lower = midpoint, f_mid

    return ScalarRootResult(
        status=KinematicsStatus.FAILURE,
        bracket=RootBracket(lower, upper, f_lower, f_upper),
        iterations=config.max_iterations,
        failure_code=KinematicsFailureCode.ROOT_NONCONVERGENCE,
        message="Bracketed closure solve exceeded max_iterations",
    )


def _upper_closure_functions(
    corner: SuspensionCornerGeometry,
    lower_upright_m: Point3,
) -> tuple[Callable[[float], float], Callable[[float], float], float]:
    wishbone = corner.wishbone
    upper_nominal = wishbone.upper_upright.position_m
    lower_nominal = wishbone.lower_upright.position_m
    kingpin_length = _distance(upper_nominal, lower_nominal)
    if kingpin_length <= 1.0e-14:
        raise SuspensionKinematicsError("Nominal upper/lower upright joint separation is zero")

    def upper_point(q_u: float) -> Point3:
        return rotate_point_about_hinge(
            upper_nominal,
            wishbone.upper_fore_inboard.position_m,
            wishbone.upper_aft_inboard.position_m,
            q_u,
        )

    def squared(q_u: float) -> float:
        delta = _subtract(upper_point(q_u), lower_upright_m)
        return 0.5 * (_dot(delta, delta) - kingpin_length * kingpin_length)

    def physical(q_u: float) -> float:
        return _distance(upper_point(q_u), lower_upright_m) - kingpin_length

    return squared, physical, kingpin_length


def minimum_twist_upright_transform(
    nominal_lower_m: Point3,
    nominal_upper_m: Point3,
    current_lower_m: Point3,
    current_upper_m: Point3,
) -> UprightReferenceTransform:
    """EQ-SUSP-0003 shortest-axis transport with no added kingpin twist."""

    nominal_axis = _subtract(nominal_upper_m, nominal_lower_m)
    current_axis = _subtract(current_upper_m, current_lower_m)
    if _norm(nominal_axis) <= 1.0e-14 or _norm(current_axis) <= 1.0e-14:
        raise SuspensionKinematicsError("Kingpin/upright joint separation is zero")
    k0 = _normalize(nominal_axis, failure="Nominal kingpin direction is undefined")
    k = _normalize(current_axis, failure="Current kingpin direction is undefined")
    cross_axis = _cross(k0, k)
    s = _norm(cross_axis)
    c = max(-1.0, min(1.0, _dot(k0, k)))
    if s <= 1.0e-13:
        if c < 0.0:
            raise SuspensionKinematicsError("Nominal and current kingpin axes are antiparallel")
        rotation = IDENTITY_MAT3
    else:
        rotation_axis = _scale(cross_axis, 1.0 / s)
        angle = math.atan2(s, c)
        rotation = _axis_angle_matrix(rotation_axis, angle)
    translation = _subtract(current_lower_m, _mat_vec(rotation, nominal_lower_m))
    return UprightReferenceTransform(rotation=rotation, translation_m=translation)


def _compose_twist_about_current_axis(
    reference: UprightReferenceTransform,
    *,
    current_lower_m: Point3,
    current_axis: Point3,
    nominal_lower_m: Point3,
    twist_rad: float,
    source_role: str,
) -> UprightReferenceTransform:
    twist_rotation = _axis_angle_matrix(current_axis, twist_rad)
    rotation = _mat_mul(twist_rotation, reference.rotation)
    translation = _subtract(current_lower_m, _mat_vec(rotation, nominal_lower_m))
    return UprightReferenceTransform(
        rotation=rotation,
        translation_m=translation,
        source_role=source_role,
    )


def solve_rear_toe_twist(
    corner: SuspensionCornerGeometry,
    minimum_twist_transform: UprightReferenceTransform,
    *,
    current_lower_m: Point3,
    current_upper_m: Point3,
    predecessor_twist_rad: float = 0.0,
    config: KinematicsSolverConfig | None = None,
) -> tuple[ScalarRootResult, float | None, float | None, UprightReferenceTransform | None]:
    """EQ-SUSP-0004 rear chassis toe-link closure."""

    solver = config or KinematicsSolverConfig()
    if corner.axle is not Axle.REAR or corner.toe_link.role is not ToeLinkRole.CHASSIS_LOCATING_TOE_LINK:
        return (
            ScalarRootResult(
                status=KinematicsStatus.FAILURE,
                failure_code=KinematicsFailureCode.INVALID_REAR_TOE_LINK_ROLE,
                message="Rear toe-link twist closure requires chassis_locating_toe_link role",
            ),
            None,
            None,
            None,
        )
    if not math.isfinite(predecessor_twist_rad):
        return (
            ScalarRootResult(
                status=KinematicsStatus.FAILURE,
                failure_code=KinematicsFailureCode.NONFINITE_INPUT,
                message="Rear twist predecessor must be finite",
            ),
            None,
            None,
            None,
        )

    nominal_lower = corner.wishbone.lower_upright.position_m
    toe_outboard_nominal = corner.toe_link.outboard.position_m
    toe_inboard = corner.toe_link.inboard.position_m
    nominal_length = _distance(toe_outboard_nominal, toe_inboard)
    current_axis = _normalize(
        _subtract(current_upper_m, current_lower_m),
        failure="Current kingpin direction is undefined",
    )
    toe_reference = minimum_twist_transform.apply_point(toe_outboard_nominal)

    def toe_point(psi: float) -> Point3:
        rotation = _axis_angle_matrix(current_axis, psi)
        return _add(
            current_lower_m,
            _mat_vec(rotation, _subtract(toe_reference, current_lower_m)),
        )

    def squared(psi: float) -> float:
        delta = _subtract(toe_point(psi), toe_inboard)
        return 0.5 * (_dot(delta, delta) - nominal_length * nominal_length)

    def physical(psi: float) -> float:
        return _distance(toe_point(psi), toe_inboard) - nominal_length

    bracket = _find_continuation_bracket(
        squared,
        predecessor_rad=predecessor_twist_rad,
        lower_rad=solver.rear_twist_min_rad,
        upper_rad=solver.rear_twist_max_rad,
        config=solver,
    )
    root = _bisect_bracketed_root(squared, physical, bracket, config=solver)
    if not root.ok or root.root_rad is None:
        return root, None, None, None
    psi = root.root_rad
    point = toe_point(psi)
    derivative = _dot(
        _subtract(point, toe_inboard),
        _cross(current_axis, _subtract(point, current_lower_m)),
    )
    final_transform = _compose_twist_about_current_axis(
        minimum_twist_transform,
        current_lower_m=current_lower_m,
        current_axis=current_axis,
        nominal_lower_m=nominal_lower,
        twist_rad=psi,
        source_role="rear_chassis_toe_link_closed_reference",
    )
    return root, physical(psi), derivative, final_transform


def _failure_result(
    corner: SuspensionCornerGeometry,
    q_L_rad: float,
    code: KinematicsFailureCode,
    message: str,
    *,
    predecessor_q_U_rad: float,
    predecessor_rear_twist_rad: float,
    upper_root: ScalarRootResult | None = None,
    geometry_id: str = "",
    configuration_id: str = "",
    source_authority: str = "",
) -> SuspensionCornerStateResult:
    return SuspensionCornerStateResult(
        axle=corner.axle,
        side=corner.side,
        requested_q_L_rad=q_L_rad,
        status=KinematicsStatus.FAILURE,
        failure_code=code,
        message=message,
        upper_root=upper_root,
        continuation_predecessor_q_U_rad=predecessor_q_U_rad,
        continuation_predecessor_rear_twist_rad=predecessor_rear_twist_rad,
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
    )


def solve_corner_state(
    corner: SuspensionCornerGeometry,
    q_L_rad: float,
    *,
    predecessor_q_U_rad: float = 0.0,
    predecessor_rear_twist_rad: float = 0.0,
    config: KinematicsSolverConfig | None = None,
    geometry_id: str = "",
    configuration_id: str = "",
    source_authority: str = "",
) -> SuspensionCornerStateResult:
    """Solve one rigid corner state on the branch connected to its predecessor."""

    solver = config or KinematicsSolverConfig()
    if not all(math.isfinite(value) for value in (q_L_rad, predecessor_q_U_rad, predecessor_rear_twist_rad)):
        return _failure_result(
            corner,
            q_L_rad,
            KinematicsFailureCode.NONFINITE_INPUT,
            "Requested/predecessor suspension angles must be finite",
            predecessor_q_U_rad=predecessor_q_U_rad,
            predecessor_rear_twist_rad=predecessor_rear_twist_rad,
            geometry_id=geometry_id,
            configuration_id=configuration_id,
            source_authority=source_authority,
        )
    if not solver.lower_angle_min_rad <= q_L_rad <= solver.lower_angle_max_rad:
        return _failure_result(
            corner,
            q_L_rad,
            KinematicsFailureCode.INPUT_OUTSIDE_DOMAIN,
            "Requested lower-arm rotation lies outside the declared prototype domain",
            predecessor_q_U_rad=predecessor_q_U_rad,
            predecessor_rear_twist_rad=predecessor_rear_twist_rad,
            geometry_id=geometry_id,
            configuration_id=configuration_id,
            source_authority=source_authority,
        )

    wishbone = corner.wishbone
    try:
        lower_current = rotate_point_about_hinge(
            wishbone.lower_upright.position_m,
            wishbone.lower_fore_inboard.position_m,
            wishbone.lower_aft_inboard.position_m,
            q_L_rad,
        )
        squared, physical, nominal_kingpin_length = _upper_closure_functions(corner, lower_current)
    except SuspensionKinematicsError as exc:
        code = (
            KinematicsFailureCode.ZERO_KINGPIN_LENGTH
            if "separation is zero" in str(exc)
            else KinematicsFailureCode.DEGENERATE_HINGE_AXIS
        )
        return _failure_result(
            corner,
            q_L_rad,
            code,
            str(exc),
            predecessor_q_U_rad=predecessor_q_U_rad,
            predecessor_rear_twist_rad=predecessor_rear_twist_rad,
            geometry_id=geometry_id,
            configuration_id=configuration_id,
            source_authority=source_authority,
        )

    bracket = _find_continuation_bracket(
        squared,
        predecessor_rad=predecessor_q_U_rad,
        lower_rad=solver.upper_angle_min_rad,
        upper_rad=solver.upper_angle_max_rad,
        config=solver,
    )
    upper_root = _bisect_bracketed_root(squared, physical, bracket, config=solver)
    if not upper_root.ok or upper_root.root_rad is None:
        return _failure_result(
            corner,
            q_L_rad,
            upper_root.failure_code or KinematicsFailureCode.NO_CLOSURE_ROOT,
            upper_root.message,
            predecessor_q_U_rad=predecessor_q_U_rad,
            predecessor_rear_twist_rad=predecessor_rear_twist_rad,
            upper_root=upper_root,
            geometry_id=geometry_id,
            configuration_id=configuration_id,
            source_authority=source_authority,
        )

    q_U = upper_root.root_rad
    try:
        upper_current = rotate_point_about_hinge(
            wishbone.upper_upright.position_m,
            wishbone.upper_fore_inboard.position_m,
            wishbone.upper_aft_inboard.position_m,
            q_U,
        )
        minimum_twist = minimum_twist_upright_transform(
            wishbone.lower_upright.position_m,
            wishbone.upper_upright.position_m,
            lower_current,
            upper_current,
        )
    except SuspensionKinematicsError as exc:
        code = (
            KinematicsFailureCode.ANTIPARALLEL_REFERENCE_AXIS
            if "antiparallel" in str(exc)
            else KinematicsFailureCode.ZERO_KINGPIN_LENGTH
        )
        return _failure_result(
            corner,
            q_L_rad,
            code,
            str(exc),
            predecessor_q_U_rad=predecessor_q_U_rad,
            predecessor_rear_twist_rad=predecessor_rear_twist_rad,
            upper_root=upper_root,
            geometry_id=geometry_id,
            configuration_id=configuration_id,
            source_authority=source_authority,
        )

    current_axis = _normalize(
        _subtract(upper_current, lower_current), failure="Current kingpin direction is undefined"
    )
    upper_derivative = _dot(
        _subtract(upper_current, lower_current),
        _arm_rotation_derivative(
            upper_current,
            wishbone.upper_fore_inboard.position_m,
            wishbone.upper_aft_inboard.position_m,
        ),
    )
    warnings: list[KinematicsWarningCode] = [KinematicsWarningCode.PROVISIONAL_ANGULAR_DOMAIN]
    if abs(upper_derivative) <= solver.singular_derivative_threshold_m2_per_rad:
        warnings.append(KinematicsWarningCode.NEAR_SINGULAR)

    lower_fore_nominal = _distance(
        wishbone.lower_upright.position_m, wishbone.lower_fore_inboard.position_m
    )
    lower_aft_nominal = _distance(
        wishbone.lower_upright.position_m, wishbone.lower_aft_inboard.position_m
    )
    upper_fore_nominal = _distance(
        wishbone.upper_upright.position_m, wishbone.upper_fore_inboard.position_m
    )
    upper_aft_nominal = _distance(
        wishbone.upper_upright.position_m, wishbone.upper_aft_inboard.position_m
    )

    rear_root: ScalarRootResult | None = None
    rear_residual: float | None = None
    rear_derivative: float | None = None
    rear_twist: float | None = None
    final_transform = minimum_twist
    if corner.axle is Axle.REAR:
        rear_root, rear_residual, rear_derivative, rear_transform = solve_rear_toe_twist(
            corner,
            minimum_twist,
            current_lower_m=lower_current,
            current_upper_m=upper_current,
            predecessor_twist_rad=predecessor_rear_twist_rad,
            config=solver,
        )
        if not rear_root.ok or rear_root.root_rad is None or rear_transform is None:
            return SuspensionCornerStateResult(
                axle=corner.axle,
                side=corner.side,
                requested_q_L_rad=q_L_rad,
                status=KinematicsStatus.FAILURE,
                q_U_rad=q_U,
                lower_upright_m=lower_current,
                upper_upright_m=upper_current,
                kingpin_direction=current_axis,
                minimum_twist_transform=minimum_twist,
                upper_root=upper_root,
                rear_root=rear_root,
                continuation_predecessor_q_U_rad=predecessor_q_U_rad,
                continuation_predecessor_rear_twist_rad=predecessor_rear_twist_rad,
                failure_code=rear_root.failure_code,
                message=rear_root.message,
                geometry_id=geometry_id,
                configuration_id=configuration_id,
                source_authority=source_authority,
            )
        rear_twist = rear_root.root_rad
        final_transform = rear_transform
        if rear_derivative is not None and abs(rear_derivative) <= solver.singular_derivative_threshold_m2_per_rad:
            warnings.append(KinematicsWarningCode.NEAR_SINGULAR)

    return SuspensionCornerStateResult(
        axle=corner.axle,
        side=corner.side,
        requested_q_L_rad=q_L_rad,
        status=KinematicsStatus.SUCCESS,
        q_U_rad=q_U,
        lower_upright_m=lower_current,
        upper_upright_m=upper_current,
        kingpin_direction=current_axis,
        minimum_twist_transform=minimum_twist,
        upright_transform=final_transform,
        rear_twist_rad=rear_twist,
        lower_fore_leg_residual_m=(
            _distance(lower_current, wishbone.lower_fore_inboard.position_m) - lower_fore_nominal
        ),
        lower_aft_leg_residual_m=(
            _distance(lower_current, wishbone.lower_aft_inboard.position_m) - lower_aft_nominal
        ),
        upper_fore_leg_residual_m=(
            _distance(upper_current, wishbone.upper_fore_inboard.position_m) - upper_fore_nominal
        ),
        upper_aft_leg_residual_m=(
            _distance(upper_current, wishbone.upper_aft_inboard.position_m) - upper_aft_nominal
        ),
        upright_separation_residual_m=(
            _distance(upper_current, lower_current) - nominal_kingpin_length
        ),
        rear_toe_link_residual_m=rear_residual,
        upper_closure_derivative_m2_per_rad=upper_derivative,
        rear_toe_derivative_m2_per_rad=rear_derivative,
        upper_root=upper_root,
        rear_root=rear_root,
        continuation_predecessor_q_U_rad=predecessor_q_U_rad,
        continuation_predecessor_rear_twist_rad=predecessor_rear_twist_rad,
        warnings=tuple(dict.fromkeys(warnings)),
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
    )


def solve_corner_sweep(
    corner: SuspensionCornerGeometry,
    q_L_values_rad: Iterable[float],
    *,
    config: KinematicsSolverConfig | None = None,
    geometry_id: str = "",
    configuration_id: str = "",
    source_authority: str = "",
) -> tuple[SuspensionCornerStateResult, ...]:
    """Solve an ordered branch-continuation sweep beginning from the nominal assembly.

    The caller should order each branch away from ``q_L=0``.  The function always
    initializes the continuation predecessor at the nominal ``q_U=psi=0`` and never
    substitutes an alternate assembly mode after a failure.
    """

    results: list[SuspensionCornerStateResult] = []
    predecessor_q_u = 0.0
    predecessor_psi = 0.0
    for q_l in q_L_values_rad:
        result = solve_corner_state(
            corner,
            float(q_l),
            predecessor_q_U_rad=predecessor_q_u,
            predecessor_rear_twist_rad=predecessor_psi,
            config=config,
            geometry_id=geometry_id,
            configuration_id=configuration_id,
            source_authority=source_authority,
        )
        results.append(result)
        if not result.ok:
            break
        assert result.q_U_rad is not None
        predecessor_q_u = result.q_U_rad
        if result.rear_twist_rad is not None:
            predecessor_psi = result.rear_twist_rad
    return tuple(results)


def solve_geometry_corner_state(
    geometry: SuspensionGeometrySet,
    axle: Axle | str,
    side: Side | str,
    q_L_rad: float,
    *,
    predecessor_q_U_rad: float = 0.0,
    predecessor_rear_twist_rad: float = 0.0,
    config: KinematicsSolverConfig | None = None,
    configuration_id: str = "WUFR27_SUSPENSION_BASELINE_V0",
) -> SuspensionCornerStateResult:
    """Source-preserving convenience wrapper around ``solve_corner_state``."""

    corner = geometry.corner(axle, side)
    return solve_corner_state(
        corner,
        q_L_rad,
        predecessor_q_U_rad=predecessor_q_U_rad,
        predecessor_rear_twist_rad=predecessor_rear_twist_rad,
        config=config,
        geometry_id=geometry.geometry_id,
        configuration_id=configuration_id,
        source_authority=geometry.authority,
    )
