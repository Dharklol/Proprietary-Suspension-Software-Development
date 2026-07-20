"""Bounded rigid-steering mechanism evaluator.

The public calculations in this module implement the equation and behavior
contract authorized by AUTH-STEER-0001:

* rigid translation of rack joints;
* Rodrigues axis-angle rotation of an upright joint;
* rigid tie-rod joint-center distance closure;
* branch-preserving scalar position solution;
* explicit residual, derivative, singularity, and failure diagnostics.

No tire, compliance, effort, optimization, or as-built authority is implied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Iterable, Sequence

Vec3 = tuple[float, float, float]


class GeometryError(ValueError):
    """Raised when a geometry definition is invalid before evaluation."""


class SolverStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class FailureCode(str, Enum):
    INVALID_GEOMETRY = "invalid_geometry"
    NONFINITE_INPUT = "nonfinite_input"
    INPUT_OUTSIDE_DOMAIN = "input_outside_operational_domain"
    NO_CLOSURE_ROOT = "no_closure_root"
    MISSING_ROOT_BRACKET = "missing_root_bracket"
    BRANCH_AMBIGUITY = "branch_ambiguity"
    BRANCH_CHANGE = "branch_change"
    NEAR_SINGULAR = "near_singular"
    ROOT_NONCONVERGENCE = "root_nonconvergence"
    DERIVED_OUTPUT_UNAVAILABLE = "derived_output_unavailable"
    UNSUPPORTED_EXTRAPOLATION = "unsupported_extrapolation"


class WarningCode(str, Enum):
    NEAR_SINGULAR = "near_singular"
    NEAR_GEOMETRIC_BRANCH_LIMIT = "near_geometric_branch_limit"
    PROVISIONAL_INPUT_DOMAIN = "provisional_input_domain"
    MIRRORED_GEOMETRY = "mirrored_geometry"


def _is_finite_vec(value: Sequence[float]) -> bool:
    return len(value) == 3 and all(math.isfinite(float(item)) for item in value)


def _vec(value: Sequence[float]) -> Vec3:
    if not _is_finite_vec(value):
        raise GeometryError(f"Expected three finite coordinates, got {value!r}")
    return (float(value[0]), float(value[1]), float(value[2]))


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def subtract(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a: Vec3, scalar: float) -> Vec3:
    return (a[0] * scalar, a[1] * scalar, a[2] * scalar)


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a: Vec3) -> float:
    return math.sqrt(dot(a, a))


def normalize(a: Vec3, *, minimum_norm: float = 1.0e-15) -> Vec3:
    magnitude = norm(a)
    if not math.isfinite(magnitude) or magnitude <= minimum_norm:
        raise GeometryError("Axis direction must have a finite nonzero magnitude")
    return scale(a, 1.0 / magnitude)


def distance(a: Vec3, b: Vec3) -> float:
    return norm(subtract(a, b))


@dataclass(frozen=True)
class AxisLine:
    """A point and unit direction defining an infinite spatial axis."""

    point: Vec3
    direction: Vec3

    def __post_init__(self) -> None:
        object.__setattr__(self, "point", _vec(self.point))
        object.__setattr__(self, "direction", normalize(_vec(self.direction)))


@dataclass(frozen=True)
class RackGeometry:
    """Rack translation axis and reviewed operational displacement domain."""

    axis: AxisLine
    displacement_min: float
    displacement_max: float
    geometric_branch_limit_magnitude: float | None = None
    domain_role: str = "reviewed"

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) for value in (self.displacement_min, self.displacement_max)):
            raise GeometryError("Rack displacement bounds must be finite")
        if self.displacement_min >= self.displacement_max:
            raise GeometryError("Rack displacement_min must be less than displacement_max")
        if self.geometric_branch_limit_magnitude is not None:
            if (
                not math.isfinite(self.geometric_branch_limit_magnitude)
                or self.geometric_branch_limit_magnitude <= 0.0
            ):
                raise GeometryError("Geometric branch limit must be finite and positive")


@dataclass(frozen=True)
class SteeringCorner:
    """One rigid steering corner at its declared rack-center reference state."""

    side: str
    steering_axis: AxisLine
    rack_inner_joint_at_center: Vec3
    outer_tie_rod_joint_at_center: Vec3
    tie_rod_length: float
    reference_upright_rotation: float = 0.0
    mechanical_rotation_min: float = -1.0
    mechanical_rotation_max: float = 1.0
    wheel_forward_direction_at_center: Vec3 | None = None
    static_toe: float | None = None
    source_role: str = "direct"

    def __post_init__(self) -> None:
        if self.side not in {"left", "right"}:
            raise GeometryError("Corner side must be 'left' or 'right'")
        object.__setattr__(
            self, "rack_inner_joint_at_center", _vec(self.rack_inner_joint_at_center)
        )
        object.__setattr__(
            self, "outer_tie_rod_joint_at_center", _vec(self.outer_tie_rod_joint_at_center)
        )
        if not math.isfinite(self.tie_rod_length) or self.tie_rod_length <= 0.0:
            raise GeometryError("Tie-rod joint-center length must be finite and positive")
        if not all(
            math.isfinite(value)
            for value in (
                self.reference_upright_rotation,
                self.mechanical_rotation_min,
                self.mechanical_rotation_max,
            )
        ):
            raise GeometryError("Corner rotation values must be finite")
        if self.mechanical_rotation_min >= self.mechanical_rotation_max:
            raise GeometryError("Mechanical rotation bounds are invalid")
        if not (
            self.mechanical_rotation_min
            <= self.reference_upright_rotation
            <= self.mechanical_rotation_max
        ):
            raise GeometryError("Reference rotation must lie inside mechanical bounds")
        if self.wheel_forward_direction_at_center is not None:
            direction = normalize(_vec(self.wheel_forward_direction_at_center))
            object.__setattr__(self, "wheel_forward_direction_at_center", direction)
        if self.static_toe is not None and not math.isfinite(self.static_toe):
            raise GeometryError("Static toe must be finite when supplied")


@dataclass(frozen=True)
class SteeringGeometry:
    """Two-corner rigid steering geometry in one declared coordinate frame."""

    geometry_id: str
    version: str
    rack: RackGeometry
    left: SteeringCorner
    right: SteeringCorner
    wheelbase: float | None = None
    steering_axis_track: float | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.geometry_id:
            raise GeometryError("geometry_id is required")
        if self.left.side != "left" or self.right.side != "right":
            raise GeometryError("Geometry corners must retain explicit left/right identities")
        for name, value in (
            ("wheelbase", self.wheelbase),
            ("steering_axis_track", self.steering_axis_track),
        ):
            if value is not None and (not math.isfinite(value) or value <= 0.0):
                raise GeometryError(f"{name} must be finite and positive when supplied")


@dataclass(frozen=True)
class RootBracket:
    lower: float
    upper: float
    f_lower: float
    f_upper: float


@dataclass(frozen=True)
class PositionResult:
    geometry_id: str
    geometry_version: str
    side: str
    rack_displacement: float
    status: SolverStatus
    upright_rotation: float | None = None
    rack_inner_joint: Vec3 | None = None
    rotated_outer_joint: Vec3 | None = None
    closure_squared_residual: float | None = None
    closure_length_residual: float | None = None
    closure_rotation_derivative: float | None = None
    closure_length_rotation_derivative: float | None = None
    local_upright_gain_rad_per_m: float | None = None
    branch_signature: int | None = None
    bracket: RootBracket | None = None
    iterations: int = 0
    singularity_ratio_to_reference: float | None = None
    geometric_branch_margin: float | None = None
    warnings: tuple[WarningCode, ...] = ()
    failure_code: FailureCode | None = None
    message: str = ""
    continuation_predecessor: float | None = None
    source_role: str = ""

    @property
    def ok(self) -> bool:
        return self.status is SolverStatus.SUCCESS


@dataclass(frozen=True)
class HeadingResult:
    """Availability-aware projected wheel-heading output."""

    available: bool
    total_heading: float | None = None
    incremental_heading: float | None = None
    failure_code: FailureCode | None = None
    message: str = ""


@dataclass(frozen=True)
class SolverSettings:
    """Deterministic scalar-root controls for the bounded prototype."""

    angle_tolerance: float = 1.0e-13
    squared_residual_tolerance: float = 1.0e-14
    max_iterations: int = 120
    bracket_samples: int = 1601
    derivative_step: float = 1.0e-7
    branch_derivative_sign_tolerance: float = 1.0e-12
    singularity_ratio_warning: float = 0.25
    singularity_ratio_failure: float = 1.0e-6
    branch_limit_warning_fraction: float = 0.25
    maximum_rotation_jump: float = math.pi / 2.0

    def __post_init__(self) -> None:
        if self.bracket_samples < 3:
            raise GeometryError("At least three bracket samples are required")
        if self.max_iterations < 1:
            raise GeometryError("max_iterations must be positive")


def translate_rack_joint(joint_at_center: Vec3, rack_axis: AxisLine, displacement: float) -> Vec3:
    """Translate a rack joint by ``displacement`` along the declared rack axis.

    Basis: Euclidean rigid translation, corresponding to EQ-STEER-0003.
    Valid only when the rack axis and displacement share the declared frame/unit.
    """

    if not math.isfinite(displacement):
        raise ValueError("Rack displacement must be finite")
    return add(joint_at_center, scale(rack_axis.direction, displacement))


def rotate_point_about_axis(point: Vec3, axis: AxisLine, angle: float) -> Vec3:
    """Rotate a point around an infinite axis using Rodrigues' formula.

    Basis: exact Euclidean rigid-body axis-angle rotation, EQ-STEER-0003.
    The axis is fixed and the rotated body is assumed rigid.
    """

    if not math.isfinite(angle):
        raise ValueError("Rotation angle must be finite")
    relative = subtract(point, axis.point)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    term_1 = scale(relative, cosine)
    term_2 = scale(cross(axis.direction, relative), sine)
    term_3 = scale(axis.direction, dot(axis.direction, relative) * (1.0 - cosine))
    return add(axis.point, add(add(term_1, term_2), term_3))


def rotate_direction_about_axis(direction: Vec3, axis_direction: Vec3, angle: float) -> Vec3:
    """Rotate a free direction vector with Rodrigues' formula."""

    unit_axis = normalize(axis_direction)
    unit_direction = normalize(direction)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return normalize(
        add(
            add(scale(unit_direction, cosine), scale(cross(unit_axis, unit_direction), sine)),
            scale(unit_axis, dot(unit_axis, unit_direction) * (1.0 - cosine)),
        )
    )


def closure_squared_residual(
    corner: SteeringCorner,
    rack: RackGeometry,
    rack_displacement: float,
    upright_rotation: float,
) -> float:
    """Return ``||p_outer(theta)-p_inner(s)||^2-L^2``.

    This is the rigid holonomic tie-rod closure equation EQ-STEER-0002.
    A zero is a closed rigid mechanism state; the function is not a fit.
    """

    outer = rotate_point_about_axis(
        corner.outer_tie_rod_joint_at_center,
        corner.steering_axis,
        upright_rotation,
    )
    inner = translate_rack_joint(
        corner.rack_inner_joint_at_center,
        rack.axis,
        rack_displacement,
    )
    delta = subtract(outer, inner)
    return dot(delta, delta) - corner.tie_rod_length**2


def closure_length_residual(
    corner: SteeringCorner,
    rack: RackGeometry,
    rack_displacement: float,
    upright_rotation: float,
) -> float:
    """Return the physical tie-rod length residual in metres."""

    outer = rotate_point_about_axis(
        corner.outer_tie_rod_joint_at_center,
        corner.steering_axis,
        upright_rotation,
    )
    inner = translate_rack_joint(
        corner.rack_inner_joint_at_center,
        rack.axis,
        rack_displacement,
    )
    return distance(outer, inner) - corner.tie_rod_length


def closure_rotation_derivative(
    corner: SteeringCorner,
    rack: RackGeometry,
    rack_displacement: float,
    upright_rotation: float,
) -> float:
    """Analytical ``partial g / partial theta`` for squared closure residual."""

    outer = rotate_point_about_axis(
        corner.outer_tie_rod_joint_at_center,
        corner.steering_axis,
        upright_rotation,
    )
    inner = translate_rack_joint(
        corner.rack_inner_joint_at_center,
        rack.axis,
        rack_displacement,
    )
    outer_velocity = cross(corner.steering_axis.direction, subtract(outer, corner.steering_axis.point))
    return 2.0 * dot(subtract(outer, inner), outer_velocity)


def closure_rack_derivative(
    corner: SteeringCorner,
    rack: RackGeometry,
    rack_displacement: float,
    upright_rotation: float,
) -> float:
    """Analytical ``partial g / partial s`` for squared closure residual."""

    outer = rotate_point_about_axis(
        corner.outer_tie_rod_joint_at_center,
        corner.steering_axis,
        upright_rotation,
    )
    inner = translate_rack_joint(
        corner.rack_inner_joint_at_center,
        rack.axis,
        rack_displacement,
    )
    return -2.0 * dot(subtract(outer, inner), rack.axis.direction)


def closure_length_rotation_derivative(
    corner: SteeringCorner,
    rack: RackGeometry,
    rack_displacement: float,
    upright_rotation: float,
) -> float:
    """Analytical derivative of physical length residual with rotation."""

    outer = rotate_point_about_axis(
        corner.outer_tie_rod_joint_at_center,
        corner.steering_axis,
        upright_rotation,
    )
    inner = translate_rack_joint(
        corner.rack_inner_joint_at_center,
        rack.axis,
        rack_displacement,
    )
    delta = subtract(outer, inner)
    current_length = norm(delta)
    if current_length <= 1.0e-15:
        raise GeometryError("Inner and outer joints coincide; length derivative is undefined")
    outer_velocity = cross(corner.steering_axis.direction, subtract(outer, corner.steering_axis.point))
    return dot(delta, outer_velocity) / current_length


def implicit_upright_gain(
    corner: SteeringCorner,
    rack: RackGeometry,
    rack_displacement: float,
    upright_rotation: float,
    *,
    derivative_tolerance: float = 1.0e-14,
) -> float:
    """Return ``d(theta_upright)/d(rack displacement)`` by implicit differentiation.

    For ``g(theta,s)=0``, ``dtheta/ds = -g_s/g_theta``. This is the local
    mechanism-gain component of EQ-STEER-0005 and is invalid at a singular
    closure Jacobian.
    """

    g_theta = closure_rotation_derivative(corner, rack, rack_displacement, upright_rotation)
    if abs(g_theta) <= derivative_tolerance:
        raise ZeroDivisionError("Closure Jacobian is singular or too small for local gain")
    g_s = closure_rack_derivative(corner, rack, rack_displacement, upright_rotation)
    return -g_s / g_theta


def _sign(value: float, tolerance: float) -> int:
    if value > tolerance:
        return 1
    if value < -tolerance:
        return -1
    return 0


def _reference_branch_signature(
    corner: SteeringCorner,
    rack: RackGeometry,
    settings: SolverSettings,
) -> tuple[int, float]:
    derivative = closure_rotation_derivative(
        corner,
        rack,
        0.0,
        corner.reference_upright_rotation,
    )
    signature = _sign(derivative, settings.branch_derivative_sign_tolerance)
    if signature == 0:
        raise GeometryError("Reference state is singular; branch signature is undefined")
    return signature, derivative


def _bisect(
    function,
    lower: float,
    upper: float,
    f_lower: float,
    f_upper: float,
    settings: SolverSettings,
) -> tuple[float, float, int]:
    if f_lower == 0.0:
        return lower, f_lower, 0
    if f_upper == 0.0:
        return upper, f_upper, 0
    if f_lower * f_upper > 0.0:
        raise ValueError("Bisection requires a sign-changing bracket")

    left, right = lower, upper
    fl, fr = f_lower, f_upper
    midpoint = 0.5 * (left + right)
    fm = function(midpoint)
    for iteration in range(1, settings.max_iterations + 1):
        midpoint = 0.5 * (left + right)
        fm = function(midpoint)
        if not math.isfinite(fm):
            raise ArithmeticError("Root residual became nonfinite")
        if (
            abs(fm) <= settings.squared_residual_tolerance
            or 0.5 * abs(right - left) <= settings.angle_tolerance
        ):
            return midpoint, fm, iteration
        if fl * fm <= 0.0:
            right, fr = midpoint, fm
        else:
            left, fl = midpoint, fm
    raise TimeoutError("Bisection did not converge within max_iterations")


def _candidate_brackets(
    corner: SteeringCorner,
    rack: RackGeometry,
    rack_displacement: float,
    settings: SolverSettings,
) -> list[RootBracket]:
    lower = corner.mechanical_rotation_min
    upper = corner.mechanical_rotation_max
    count = settings.bracket_samples
    step = (upper - lower) / (count - 1)
    values: list[tuple[float, float]] = []
    for index in range(count):
        angle = lower + index * step
        residual = closure_squared_residual(corner, rack, rack_displacement, angle)
        if not math.isfinite(residual):
            continue
        values.append((angle, residual))

    brackets: list[RootBracket] = []
    exact_threshold = settings.squared_residual_tolerance
    for index, (angle, residual) in enumerate(values):
        if abs(residual) <= exact_threshold:
            half = 0.5 * step
            local_lower = max(lower, angle - half)
            local_upper = min(upper, angle + half)
            brackets.append(
                RootBracket(
                    local_lower,
                    local_upper,
                    closure_squared_residual(corner, rack, rack_displacement, local_lower),
                    closure_squared_residual(corner, rack, rack_displacement, local_upper),
                )
            )
        if index == 0:
            continue
        previous_angle, previous_residual = values[index - 1]
        if previous_residual * residual < 0.0:
            brackets.append(RootBracket(previous_angle, angle, previous_residual, residual))

    deduplicated: list[RootBracket] = []
    for bracket in brackets:
        midpoint = 0.5 * (bracket.lower + bracket.upper)
        if not any(
            abs(midpoint - 0.5 * (existing.lower + existing.upper)) <= 1.5 * step
            for existing in deduplicated
        ):
            deduplicated.append(bracket)
    return deduplicated


def _failure_result(
    geometry: SteeringGeometry,
    corner: SteeringCorner,
    rack_displacement: float,
    code: FailureCode,
    message: str,
    *,
    predecessor: float | None = None,
) -> PositionResult:
    return PositionResult(
        geometry_id=geometry.geometry_id,
        geometry_version=geometry.version,
        side=corner.side,
        rack_displacement=rack_displacement,
        status=SolverStatus.FAILURE,
        failure_code=code,
        message=message,
        continuation_predecessor=predecessor,
        source_role=corner.source_role,
    )


def solve_corner_position(
    geometry: SteeringGeometry,
    side: str,
    rack_displacement: float,
    *,
    continuation_predecessor: float | None = None,
    settings: SolverSettings | None = None,
) -> PositionResult:
    """Solve one corner on the reference assembly branch using safeguarded bisection.

    The solver enumerates sign-changing brackets within the declared mechanical
    angle range, solves each bracket deterministically, and accepts only a root
    whose closure-Jacobian sign matches the reference branch. It never replaces
    a failed intended branch with the alternate assembly root.
    """

    settings = settings or SolverSettings()
    corner = geometry.left if side == "left" else geometry.right if side == "right" else None
    if corner is None:
        raise ValueError("side must be 'left' or 'right'")
    if not math.isfinite(rack_displacement):
        return _failure_result(
            geometry,
            corner,
            rack_displacement,
            FailureCode.NONFINITE_INPUT,
            "Rack displacement is nonfinite",
            predecessor=continuation_predecessor,
        )
    if not (
        geometry.rack.displacement_min
        <= rack_displacement
        <= geometry.rack.displacement_max
    ):
        return _failure_result(
            geometry,
            corner,
            rack_displacement,
            FailureCode.INPUT_OUTSIDE_DOMAIN,
            "Rack displacement is outside the declared operational domain; extrapolation is prohibited",
            predecessor=continuation_predecessor,
        )

    try:
        branch_signature, reference_derivative = _reference_branch_signature(
            corner, geometry.rack, settings
        )
        brackets = _candidate_brackets(corner, geometry.rack, rack_displacement, settings)
    except (GeometryError, ValueError, ArithmeticError) as exc:
        return _failure_result(
            geometry,
            corner,
            rack_displacement,
            FailureCode.INVALID_GEOMETRY,
            str(exc),
            predecessor=continuation_predecessor,
        )
    if not brackets:
        return _failure_result(
            geometry,
            corner,
            rack_displacement,
            FailureCode.NO_CLOSURE_ROOT,
            "No sign-changing closure bracket exists inside the declared mechanical range",
            predecessor=continuation_predecessor,
        )

    solved: list[tuple[float, float, int, RootBracket, float]] = []
    for bracket in brackets:
        function = lambda angle: closure_squared_residual(
            corner, geometry.rack, rack_displacement, angle
        )
        try:
            if bracket.f_lower * bracket.f_upper > 0.0:
                midpoint = 0.5 * (bracket.lower + bracket.upper)
                candidates = [
                    (bracket.lower, bracket.f_lower),
                    (midpoint, function(midpoint)),
                    (bracket.upper, bracket.f_upper),
                ]
                root, residual = min(candidates, key=lambda item: abs(item[1]))
                if abs(residual) > settings.squared_residual_tolerance:
                    continue
                iterations = 0
            else:
                root, residual, iterations = _bisect(
                    function,
                    bracket.lower,
                    bracket.upper,
                    bracket.f_lower,
                    bracket.f_upper,
                    settings,
                )
            derivative = closure_rotation_derivative(
                corner, geometry.rack, rack_displacement, root
            )
            solved.append((root, residual, iterations, bracket, derivative))
        except (ValueError, ArithmeticError, TimeoutError):
            continue

    matching = [
        item
        for item in solved
        if _sign(item[4], settings.branch_derivative_sign_tolerance) == branch_signature
    ]
    if not matching:
        if solved:
            return _failure_result(
                geometry,
                corner,
                rack_displacement,
                FailureCode.BRANCH_CHANGE,
                "Closure roots exist, but none retain the reference branch signature",
                predecessor=continuation_predecessor,
            )
        return _failure_result(
            geometry,
            corner,
            rack_displacement,
            FailureCode.ROOT_NONCONVERGENCE,
            "Candidate brackets were found but no root converged",
            predecessor=continuation_predecessor,
        )

    seed = (
        continuation_predecessor
        if continuation_predecessor is not None
        else corner.reference_upright_rotation
    )
    matching.sort(key=lambda item: abs(item[0] - seed))
    if len(matching) > 1:
        first_distance = abs(matching[0][0] - seed)
        second_distance = abs(matching[1][0] - seed)
        if abs(second_distance - first_distance) <= 10.0 * settings.angle_tolerance:
            return _failure_result(
                geometry,
                corner,
                rack_displacement,
                FailureCode.BRANCH_AMBIGUITY,
                "Multiple branch-compatible roots are equally close to the continuation seed",
                predecessor=continuation_predecessor,
            )

    root, residual, iterations, bracket, derivative = matching[0]
    if abs(root - seed) > settings.maximum_rotation_jump:
        return _failure_result(
            geometry,
            corner,
            rack_displacement,
            FailureCode.BRANCH_CHANGE,
            "Solved root exceeds the permitted continuation rotation jump",
            predecessor=continuation_predecessor,
        )

    reference_abs = abs(reference_derivative)
    singularity_ratio = abs(derivative) / reference_abs if reference_abs > 0.0 else 0.0
    if singularity_ratio <= settings.singularity_ratio_failure:
        return _failure_result(
            geometry,
            corner,
            rack_displacement,
            FailureCode.NEAR_SINGULAR,
            "Closure Jacobian is below the permitted singularity threshold",
            predecessor=continuation_predecessor,
        )

    outer = rotate_point_about_axis(
        corner.outer_tie_rod_joint_at_center, corner.steering_axis, root
    )
    inner = translate_rack_joint(
        corner.rack_inner_joint_at_center, geometry.rack.axis, rack_displacement
    )
    length_residual = distance(outer, inner) - corner.tie_rod_length
    length_derivative = closure_length_rotation_derivative(
        corner, geometry.rack, rack_displacement, root
    )
    try:
        gain = implicit_upright_gain(corner, geometry.rack, rack_displacement, root)
    except (ZeroDivisionError, GeometryError):
        gain = None

    warnings: list[WarningCode] = []
    if singularity_ratio <= settings.singularity_ratio_warning:
        warnings.append(WarningCode.NEAR_SINGULAR)
    branch_margin: float | None = None
    branch_limit = geometry.rack.geometric_branch_limit_magnitude
    if branch_limit is not None:
        branch_margin = branch_limit - abs(rack_displacement)
        warning_margin = settings.branch_limit_warning_fraction * branch_limit
        if branch_margin <= warning_margin:
            warnings.append(WarningCode.NEAR_GEOMETRIC_BRANCH_LIMIT)
    if "provisional" in geometry.rack.domain_role.lower():
        warnings.append(WarningCode.PROVISIONAL_INPUT_DOMAIN)
    if "mirror" in corner.source_role.lower():
        warnings.append(WarningCode.MIRRORED_GEOMETRY)

    return PositionResult(
        geometry_id=geometry.geometry_id,
        geometry_version=geometry.version,
        side=corner.side,
        rack_displacement=rack_displacement,
        status=SolverStatus.SUCCESS,
        upright_rotation=root,
        rack_inner_joint=inner,
        rotated_outer_joint=outer,
        closure_squared_residual=residual,
        closure_length_residual=length_residual,
        closure_rotation_derivative=derivative,
        closure_length_rotation_derivative=length_derivative,
        local_upright_gain_rad_per_m=gain,
        branch_signature=branch_signature,
        bracket=bracket,
        iterations=iterations,
        singularity_ratio_to_reference=singularity_ratio,
        geometric_branch_margin=branch_margin,
        warnings=tuple(dict.fromkeys(warnings)),
        message="Solved on the declared reference assembly branch",
        continuation_predecessor=continuation_predecessor,
        source_role=corner.source_role,
    )


def solve_sweep(
    geometry: SteeringGeometry,
    rack_displacements: Iterable[float],
    *,
    settings: SolverSettings | None = None,
) -> dict[str, list[PositionResult]]:
    """Solve both corners in the supplied order while retaining predecessors."""

    settings = settings or SolverSettings()
    results = {"left": [], "right": []}
    predecessors: dict[str, float | None] = {"left": None, "right": None}
    for displacement in rack_displacements:
        for side in ("left", "right"):
            result = solve_corner_position(
                geometry,
                side,
                float(displacement),
                continuation_predecessor=predecessors[side],
                settings=settings,
            )
            results[side].append(result)
            if result.ok and result.upright_rotation is not None:
                predecessors[side] = result.upright_rotation
    return results


def wheel_heading(corner: SteeringCorner, upright_rotation: float) -> tuple[float, float]:
    """Return total and incremental projected wheel headings.

    The wheel-forward basis must be supplied. Total heading retains the imported
    static-toe orientation. Incremental heading subtracts the heading at the
    declared reference upright rotation.
    """

    if corner.wheel_forward_direction_at_center is None:
        raise GeometryError("Wheel-forward direction is unavailable for this configuration")
    current = rotate_direction_about_axis(
        corner.wheel_forward_direction_at_center,
        corner.steering_axis.direction,
        upright_rotation - corner.reference_upright_rotation,
    )
    reference = corner.wheel_forward_direction_at_center
    current_planar = math.hypot(current[0], current[1])
    reference_planar = math.hypot(reference[0], reference[1])
    if current_planar <= 1.0e-15 or reference_planar <= 1.0e-15:
        raise GeometryError("Wheel-forward direction has no usable road-plane projection")
    total = math.atan2(current[1], current[0])
    reference_heading = math.atan2(reference[1], reference[0])
    incremental = math.atan2(math.sin(total - reference_heading), math.cos(total - reference_heading))
    return total, incremental


def evaluate_wheel_heading(corner: SteeringCorner, upright_rotation: float) -> HeadingResult:
    """Return wheel heading or an explicit unavailable reason.

    This wrapper is the required result-contract behavior for configurations
    such as WUFR26_DESIGN_NOMINAL_V0 whose wheel-plane basis has not yet been
    exported. It never guesses a basis or static-toe value.
    """

    try:
        total, incremental = wheel_heading(corner, upright_rotation)
    except (GeometryError, ValueError) as exc:
        return HeadingResult(
            available=False,
            failure_code=FailureCode.DERIVED_OUTPUT_UNAVAILABLE,
            message=str(exc),
        )
    return HeadingResult(
        available=True,
        total_heading=total,
        incremental_heading=incremental,
        message="Projected heading evaluated from the declared wheel-forward basis",
    )
