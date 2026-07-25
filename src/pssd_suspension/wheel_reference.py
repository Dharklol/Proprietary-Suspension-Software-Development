"""WUFR source-bounded wheel reference and physical suspension-state adapter.

Implements the equations authorized by AUTH-SUSP-0002:
- EQ-SUSP-0005 nominal wheel-center / wheel-plane source construction;
- EQ-SUSP-0006 rigid upright transport;
- EQ-SUSP-0007 bounded body-frame wheel-center vertical-state inversion;
- EQ-SUSP-0008 historical OptimumK front source-steering removal.

The v0.1 source adapter is intentionally limited to the frozen WUFR OptimumK
setup with zero wheel offsets.  Front steering closure remains owned by
MOD-STEER-0001.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
import tomllib

from pssd_steering.projection import reference_from_static_alignment

from .geometry import Axle, Point3, Side, SuspensionCornerGeometry
from .kinematics import (
    KinematicsSolverConfig,
    KinematicsStatus,
    SuspensionCornerStateResult,
    UprightReferenceTransform,
    solve_corner_state,
    solve_corner_sweep,
)


class WheelReferenceError(ValueError):
    """Raised for invalid direct wheel-reference inputs."""


class WheelReferenceStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class WheelReferenceFailureCode(str, Enum):
    NONFINITE_INPUT = "nonfinite_input"
    UNSUPPORTED_WHEEL_OFFSETS = "unsupported_wheel_offsets"
    SOURCE_MISMATCH = "source_mismatch"
    UPSTREAM_KINEMATICS_FAILURE = "upstream_kinematics_failure"
    REQUEST_OUTSIDE_REACHABLE_DOMAIN = "request_outside_reachable_domain"
    NO_ROOT_BRACKET = "no_root_bracket"
    AMBIGUOUS_MAPPING = "ambiguous_mapping"
    ROOT_NONCONVERGENCE = "root_nonconvergence"
    DEGENERATE_STEERING_AXIS = "degenerate_steering_axis"
    DEGENERATE_TIE_LEVER_ARM = "degenerate_tie_lever_arm"


@dataclass(frozen=True)
class AxleWheelReferenceSource:
    half_track_m: float
    static_camber_rad: float
    static_toe_out_rad: float
    tire_radius_m: float
    longitudinal_offset_m: float = 0.0
    lateral_offset_m: float = 0.0
    vertical_offset_m: float = 0.0

    def __post_init__(self) -> None:
        values = (
            self.half_track_m,
            self.static_camber_rad,
            self.static_toe_out_rad,
            self.tire_radius_m,
            self.longitudinal_offset_m,
            self.lateral_offset_m,
            self.vertical_offset_m,
        )
        if not all(math.isfinite(value) for value in values):
            raise WheelReferenceError("Wheel-reference source values must be finite")
        if self.half_track_m <= 0.0 or self.tire_radius_m <= 0.0:
            raise WheelReferenceError("Wheel-reference half-track and tire radius must be positive")

    @property
    def has_zero_offsets(self) -> bool:
        return (
            self.longitudinal_offset_m == 0.0
            and self.lateral_offset_m == 0.0
            and self.vertical_offset_m == 0.0
        )


@dataclass(frozen=True)
class WheelReferenceSourceProfile:
    fixture_id: str
    authority: str
    source_setup: str
    source_result: str
    front: AxleWheelReferenceSource
    rear: AxleWheelReferenceSource

    def axle(self, axle: Axle | str) -> AxleWheelReferenceSource:
        axle_key = axle if isinstance(axle, Axle) else Axle(axle)
        return self.front if axle_key is Axle.FRONT else self.rear


@dataclass(frozen=True)
class NominalWheelReference:
    axle: Axle
    side: Side
    center_m: Point3
    plane_normal: Point3
    forward_reference: Point3
    source_profile_id: str
    source_authority: str


@dataclass(frozen=True)
class WheelReferenceState:
    axle: Axle
    side: Side
    status: WheelReferenceStatus
    nominal: NominalWheelReference
    q_L_rad: float | None = None
    current_center_m: Point3 | None = None
    current_plane_normal: Point3 | None = None
    current_forward_reference: Point3 | None = None
    delta_center_m: Point3 | None = None
    delta_z_wc_body_m: float | None = None
    transform_role: str = ""
    upstream_state: SuspensionCornerStateResult | None = None
    failure_code: WheelReferenceFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WheelReferenceStatus.SUCCESS


@dataclass(frozen=True)
class PhysicalStateSolverConfig:
    q_L_min_rad: float
    q_L_max_rad: float
    scan_intervals_per_side: int = 24
    q_L_tolerance_rad: float = 1.0e-10
    displacement_tolerance_m: float = 1.0e-10
    monotonic_step_tolerance_m: float = 1.0e-12
    max_iterations: int = 100

    def __post_init__(self) -> None:
        values = (
            self.q_L_min_rad,
            self.q_L_max_rad,
            self.q_L_tolerance_rad,
            self.displacement_tolerance_m,
            self.monotonic_step_tolerance_m,
        )
        if not all(math.isfinite(value) for value in values):
            raise WheelReferenceError("Physical-state solver configuration must be finite")
        if not self.q_L_min_rad < 0.0 < self.q_L_max_rad:
            raise WheelReferenceError("Physical-state q_L domain must explicitly bracket nominal q_L=0")
        if self.scan_intervals_per_side < 2:
            raise WheelReferenceError("scan_intervals_per_side must be at least two")
        if self.q_L_tolerance_rad <= 0.0 or self.displacement_tolerance_m <= 0.0:
            raise WheelReferenceError("Physical-state root tolerances must be positive")
        if self.monotonic_step_tolerance_m < 0.0:
            raise WheelReferenceError("monotonic_step_tolerance_m cannot be negative")
        if self.max_iterations <= 0:
            raise WheelReferenceError("max_iterations must be positive")


@dataclass(frozen=True)
class PhysicalStateResult:
    status: WheelReferenceStatus
    requested_delta_z_wc_body_m: float
    q_L_rad: float | None = None
    wheel_state: WheelReferenceState | None = None
    bracket_q_L_rad: tuple[float, float] | None = None
    reachable_delta_z_range_m: tuple[float, float] | None = None
    monotonic_direction: str = ""
    iterations: int = 0
    residual_m: float | None = None
    failure_code: WheelReferenceFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WheelReferenceStatus.SUCCESS


@dataclass(frozen=True)
class SourceSteeringRemovalResult:
    status: WheelReferenceStatus
    twist_rad: float | None = None
    reference_lever_arm_m: float | None = None
    source_lever_arm_m: float | None = None
    unresolved_point_m: Point3 | None = None
    scalar_steer_angle_used_as_rotation: bool = False
    failure_code: WheelReferenceFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WheelReferenceStatus.SUCCESS


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


def _normalize(a: Point3, *, code: WheelReferenceFailureCode, message: str) -> Point3:
    magnitude = _norm(a)
    if not math.isfinite(magnitude) or magnitude <= 1.0e-14:
        raise WheelReferenceError(f"{code.value}: {message}")
    return _scale(a, 1.0 / magnitude)


def _axis_angle_rotate(vector: Point3, axis: Point3, angle_rad: float) -> Point3:
    k = _normalize(
        axis,
        code=WheelReferenceFailureCode.DEGENERATE_STEERING_AXIS,
        message="Rotation axis is degenerate",
    )
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return _add(
        _add(_scale(vector, c), _scale(_cross(k, vector), s)),
        _scale(k, _dot(k, vector) * (1.0 - c)),
    )


def _source_axle(table: dict[str, object], *, tire_radius_m: float) -> AxleWheelReferenceSource:
    return AxleWheelReferenceSource(
        half_track_m=0.001 * float(table["half_track_mm"]),
        static_camber_rad=math.radians(float(table["static_camber_deg"])),
        static_toe_out_rad=math.radians(float(table["static_toe_out_deg"])),
        tire_radius_m=tire_radius_m,
        longitudinal_offset_m=0.001 * float(table["longitudinal_offset_mm"]),
        lateral_offset_m=0.001 * float(table["lateral_offset_mm"]),
        vertical_offset_m=0.001 * float(table["vertical_offset_mm"]),
    )


def load_wufr26_wheel_reference_profile(path: str | Path) -> WheelReferenceSourceProfile:
    """Load the frozen WUFR zero-offset OptimumK wheel-reference source profile."""

    with Path(path).open("rb") as stream:
        document = tomllib.load(stream)
    nominal = document["nominal_source"]
    tire_radius_m = 0.001 * float(nominal["tire_radius_mm"])
    profile = WheelReferenceSourceProfile(
        fixture_id=str(document["fixture_id"]),
        authority=str(document["authority"]),
        source_setup=str(document["source_setup"]),
        source_result=str(document["source_result"]),
        front=_source_axle(nominal["front"], tire_radius_m=tire_radius_m),
        rear=_source_axle(nominal["rear"], tire_radius_m=tire_radius_m),
    )
    if not profile.front.has_zero_offsets or not profile.rear.has_zero_offsets:
        raise WheelReferenceError(
            f"{WheelReferenceFailureCode.UNSUPPORTED_WHEEL_OFFSETS.value}: "
            "v0.1 supports only the frozen zero-offset OptimumK source"
        )
    return profile


def build_nominal_wheel_reference(
    profile: WheelReferenceSourceProfile,
    axle: Axle | str,
    side: Side | str,
) -> NominalWheelReference:
    """EQ-SUSP-0005 source-bounded nominal wheel reference."""

    axle_key = axle if isinstance(axle, Axle) else Axle(axle)
    side_key = side if isinstance(side, Side) else Side(side)
    source = profile.axle(axle_key)
    if not source.has_zero_offsets:
        raise WheelReferenceError(
            f"{WheelReferenceFailureCode.UNSUPPORTED_WHEEL_OFFSETS.value}: "
            "nonzero OptimumK wheel offsets are not authorized in v0.1"
        )
    side_sign = 1.0 if side_key is Side.LEFT else -1.0
    center = (
        0.0,
        side_sign
        * (source.half_track_m + source.tire_radius_m * math.sin(source.static_camber_rad)),
        source.tire_radius_m * math.cos(source.static_camber_rad),
    )
    plane = reference_from_static_alignment(
        side_key.value,
        toe_out=source.static_toe_out_rad,
        camber=source.static_camber_rad,
        source_role="AUTH-SUSP-0002_source_static_alignment",
    )
    return NominalWheelReference(
        axle=axle_key,
        side=side_key,
        center_m=center,
        plane_normal=plane.normal_at_center,
        forward_reference=plane.forward_at_center,
        source_profile_id=profile.fixture_id,
        source_authority=profile.authority,
    )


def transport_wheel_reference(
    nominal: NominalWheelReference,
    upstream_state: SuspensionCornerStateResult,
) -> WheelReferenceState:
    """EQ-SUSP-0006 rigidly transport wheel center and plane with the upright."""

    if upstream_state.axle is not nominal.axle or upstream_state.side is not nominal.side:
        return WheelReferenceState(
            axle=nominal.axle,
            side=nominal.side,
            status=WheelReferenceStatus.FAILURE,
            nominal=nominal,
            failure_code=WheelReferenceFailureCode.SOURCE_MISMATCH,
            message="Nominal wheel reference and upstream corner identity do not match",
            upstream_state=upstream_state,
        )
    if not upstream_state.ok:
        return WheelReferenceState(
            axle=nominal.axle,
            side=nominal.side,
            status=WheelReferenceStatus.FAILURE,
            nominal=nominal,
            q_L_rad=upstream_state.requested_q_L_rad,
            failure_code=WheelReferenceFailureCode.UPSTREAM_KINEMATICS_FAILURE,
            message=upstream_state.message or "Upstream MOD-SUSP-0001 state is unavailable",
            upstream_state=upstream_state,
        )
    transform: UprightReferenceTransform | None
    if nominal.axle is Axle.FRONT:
        transform = upstream_state.minimum_twist_transform
        role = "front_minimum_twist_unresolved_steering"
    else:
        transform = upstream_state.upright_transform
        role = "rear_chassis_toe_link_closed"
    if transform is None:
        return WheelReferenceState(
            axle=nominal.axle,
            side=nominal.side,
            status=WheelReferenceStatus.FAILURE,
            nominal=nominal,
            q_L_rad=upstream_state.requested_q_L_rad,
            failure_code=WheelReferenceFailureCode.UPSTREAM_KINEMATICS_FAILURE,
            message="Required upstream upright transform is unavailable",
            upstream_state=upstream_state,
        )
    center = transform.apply_point(nominal.center_m)
    normal = transform.apply_direction(nominal.plane_normal)
    forward = transform.apply_direction(nominal.forward_reference)
    delta = _subtract(center, nominal.center_m)
    return WheelReferenceState(
        axle=nominal.axle,
        side=nominal.side,
        status=WheelReferenceStatus.SUCCESS,
        nominal=nominal,
        q_L_rad=upstream_state.requested_q_L_rad,
        current_center_m=center,
        current_plane_normal=normal,
        current_forward_reference=forward,
        delta_center_m=delta,
        delta_z_wc_body_m=delta[2],
        transform_role=role,
        upstream_state=upstream_state,
    )


def solve_wheel_reference_state(
    corner: SuspensionCornerGeometry,
    nominal: NominalWheelReference,
    q_L_rad: float,
    *,
    predecessor: SuspensionCornerStateResult | None = None,
    kinematics_config: KinematicsSolverConfig | None = None,
    geometry_id: str = "",
    configuration_id: str = "",
    source_authority: str = "",
) -> WheelReferenceState:
    """Compose MOD-SUSP-0001 with EQ-SUSP-0006 for one q_L state."""

    if corner.axle is not nominal.axle or corner.side is not nominal.side:
        return WheelReferenceState(
            axle=nominal.axle,
            side=nominal.side,
            status=WheelReferenceStatus.FAILURE,
            nominal=nominal,
            failure_code=WheelReferenceFailureCode.SOURCE_MISMATCH,
            message="Corner geometry and nominal wheel-reference identity do not match",
        )
    predecessor_q_u = 0.0
    predecessor_psi = 0.0
    if predecessor is not None and predecessor.ok:
        predecessor_q_u = predecessor.q_U_rad or 0.0
        predecessor_psi = predecessor.rear_twist_rad or 0.0
    state = solve_corner_state(
        corner,
        q_L_rad,
        predecessor_q_U_rad=predecessor_q_u,
        predecessor_rear_twist_rad=predecessor_psi,
        config=kinematics_config,
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
    )
    return transport_wheel_reference(nominal, state)


def _branch_samples(
    corner: SuspensionCornerGeometry,
    nominal: NominalWheelReference,
    solver: PhysicalStateSolverConfig,
    *,
    kinematics_config: KinematicsSolverConfig | None,
    geometry_id: str,
    configuration_id: str,
    source_authority: str,
) -> tuple[WheelReferenceState, ...] | PhysicalStateResult:
    count = solver.scan_intervals_per_side
    negative_q = tuple(solver.q_L_min_rad * i / count for i in range(0, count + 1))
    positive_q = tuple(solver.q_L_max_rad * i / count for i in range(0, count + 1))
    negative_upstream = solve_corner_sweep(
        corner,
        negative_q,
        config=kinematics_config,
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
    )
    positive_upstream = solve_corner_sweep(
        corner,
        positive_q,
        config=kinematics_config,
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
    )
    if len(negative_upstream) != len(negative_q) or len(positive_upstream) != len(positive_q):
        failed = (
            next((state for state in negative_upstream if not state.ok), None)
            or next((state for state in positive_upstream if not state.ok), None)
        )
        return PhysicalStateResult(
            status=WheelReferenceStatus.FAILURE,
            requested_delta_z_wc_body_m=math.nan,
            failure_code=WheelReferenceFailureCode.UPSTREAM_KINEMATICS_FAILURE,
            message=(failed.message if failed is not None else "Upstream branch sweep terminated"),
        )
    negative = tuple(transport_wheel_reference(nominal, state) for state in negative_upstream)
    positive = tuple(transport_wheel_reference(nominal, state) for state in positive_upstream)
    failed_wheel = next((state for state in negative + positive if not state.ok), None)
    if failed_wheel is not None:
        return PhysicalStateResult(
            status=WheelReferenceStatus.FAILURE,
            requested_delta_z_wc_body_m=math.nan,
            failure_code=failed_wheel.failure_code,
            message=failed_wheel.message,
        )
    return tuple(reversed(negative)) + positive[1:]


def solve_body_vertical_displacement(
    corner: SuspensionCornerGeometry,
    nominal: NominalWheelReference,
    requested_delta_z_wc_body_m: float,
    solver: PhysicalStateSolverConfig,
    *,
    kinematics_config: KinematicsSolverConfig | None = None,
    geometry_id: str = "",
    configuration_id: str = "",
    source_authority: str = "",
) -> PhysicalStateResult:
    """EQ-SUSP-0007 invert body-frame wheel-center vertical displacement to q_L."""

    if not math.isfinite(requested_delta_z_wc_body_m):
        return PhysicalStateResult(
            status=WheelReferenceStatus.FAILURE,
            requested_delta_z_wc_body_m=requested_delta_z_wc_body_m,
            failure_code=WheelReferenceFailureCode.NONFINITE_INPUT,
            message="Requested body-frame wheel-center displacement must be finite",
        )
    samples_or_failure = _branch_samples(
        corner,
        nominal,
        solver,
        kinematics_config=kinematics_config,
        geometry_id=geometry_id,
        configuration_id=configuration_id,
        source_authority=source_authority,
    )
    if isinstance(samples_or_failure, PhysicalStateResult):
        return PhysicalStateResult(
            status=WheelReferenceStatus.FAILURE,
            requested_delta_z_wc_body_m=requested_delta_z_wc_body_m,
            failure_code=samples_or_failure.failure_code,
            message=samples_or_failure.message,
        )
    samples = samples_or_failure
    dz = [float(state.delta_z_wc_body_m) for state in samples if state.delta_z_wc_body_m is not None]
    if len(dz) != len(samples):
        return PhysicalStateResult(
            status=WheelReferenceStatus.FAILURE,
            requested_delta_z_wc_body_m=requested_delta_z_wc_body_m,
            failure_code=WheelReferenceFailureCode.UPSTREAM_KINEMATICS_FAILURE,
            message="Wheel-reference branch sampling did not produce complete displacement states",
        )
    differences = [dz[i + 1] - dz[i] for i in range(len(dz) - 1)]
    significant = [
        value for value in differences if abs(value) > solver.monotonic_step_tolerance_m
    ]
    if not significant:
        return PhysicalStateResult(
            status=WheelReferenceStatus.FAILURE,
            requested_delta_z_wc_body_m=requested_delta_z_wc_body_m,
            failure_code=WheelReferenceFailureCode.AMBIGUOUS_MAPPING,
            message="Wheel-center vertical state mapping is flat over the reviewed q_L domain",
        )
    direction_sign = 1.0 if significant[0] > 0.0 else -1.0
    if any(value * direction_sign <= 0.0 for value in significant) or len(significant) != len(differences):
        return PhysicalStateResult(
            status=WheelReferenceStatus.FAILURE,
            requested_delta_z_wc_body_m=requested_delta_z_wc_body_m,
            reachable_delta_z_range_m=(min(dz), max(dz)),
            failure_code=WheelReferenceFailureCode.AMBIGUOUS_MAPPING,
            message="Wheel-center vertical state mapping is nonmonotonic or contains an unresolved plateau",
        )
    direction = "increasing" if direction_sign > 0.0 else "decreasing"
    reachable = (min(dz), max(dz))
    if (
        requested_delta_z_wc_body_m < reachable[0] - solver.displacement_tolerance_m
        or requested_delta_z_wc_body_m > reachable[1] + solver.displacement_tolerance_m
    ):
        return PhysicalStateResult(
            status=WheelReferenceStatus.FAILURE,
            requested_delta_z_wc_body_m=requested_delta_z_wc_body_m,
            reachable_delta_z_range_m=reachable,
            monotonic_direction=direction,
            failure_code=WheelReferenceFailureCode.REQUEST_OUTSIDE_REACHABLE_DOMAIN,
            message="Requested displacement lies outside the reviewed q_L-domain image",
        )
    exact = [
        state
        for state in samples
        if state.delta_z_wc_body_m is not None
        and abs(state.delta_z_wc_body_m - requested_delta_z_wc_body_m)
        <= solver.displacement_tolerance_m
    ]
    if len(exact) == 1:
        state = exact[0]
        return PhysicalStateResult(
            status=WheelReferenceStatus.SUCCESS,
            requested_delta_z_wc_body_m=requested_delta_z_wc_body_m,
            q_L_rad=state.q_L_rad,
            wheel_state=state,
            bracket_q_L_rad=(float(state.q_L_rad), float(state.q_L_rad)),
            reachable_delta_z_range_m=reachable,
            monotonic_direction=direction,
            residual_m=float(state.delta_z_wc_body_m) - requested_delta_z_wc_body_m,
        )
    if len(exact) > 1:
        return PhysicalStateResult(
            status=WheelReferenceStatus.FAILURE,
            requested_delta_z_wc_body_m=requested_delta_z_wc_body_m,
            reachable_delta_z_range_m=reachable,
            monotonic_direction=direction,
            failure_code=WheelReferenceFailureCode.AMBIGUOUS_MAPPING,
            message="Requested displacement matches multiple sampled q_L states",
        )

    brackets: list[tuple[WheelReferenceState, WheelReferenceState]] = []
    for left, right in zip(samples[:-1], samples[1:]):
        f_left = float(left.delta_z_wc_body_m) - requested_delta_z_wc_body_m
        f_right = float(right.delta_z_wc_body_m) - requested_delta_z_wc_body_m
        if f_left * f_right < 0.0:
            brackets.append((left, right))
    if len(brackets) != 1:
        code = (
            WheelReferenceFailureCode.AMBIGUOUS_MAPPING
            if len(brackets) > 1
            else WheelReferenceFailureCode.NO_ROOT_BRACKET
        )
        return PhysicalStateResult(
            status=WheelReferenceStatus.FAILURE,
            requested_delta_z_wc_body_m=requested_delta_z_wc_body_m,
            reachable_delta_z_range_m=reachable,
            monotonic_direction=direction,
            failure_code=code,
            message=f"Expected exactly one root bracket; found {len(brackets)}",
        )

    left, right = brackets[0]
    q_left = float(left.q_L_rad)
    q_right = float(right.q_L_rad)
    f_left = float(left.delta_z_wc_body_m) - requested_delta_z_wc_body_m
    iterations = 0
    best = left
    while iterations < solver.max_iterations:
        q_mid = 0.5 * (q_left + q_right)
        predecessor_state = (
            left.upstream_state
            if abs(q_mid - q_left) <= abs(q_right - q_mid)
            else right.upstream_state
        )
        mid = solve_wheel_reference_state(
            corner,
            nominal,
            q_mid,
            predecessor=predecessor_state,
            kinematics_config=kinematics_config,
            geometry_id=geometry_id,
            configuration_id=configuration_id,
            source_authority=source_authority,
        )
        iterations += 1
        if not mid.ok or mid.delta_z_wc_body_m is None:
            return PhysicalStateResult(
                status=WheelReferenceStatus.FAILURE,
                requested_delta_z_wc_body_m=requested_delta_z_wc_body_m,
                bracket_q_L_rad=(q_left, q_right),
                reachable_delta_z_range_m=reachable,
                monotonic_direction=direction,
                iterations=iterations,
                failure_code=WheelReferenceFailureCode.UPSTREAM_KINEMATICS_FAILURE,
                message=mid.message or "Upstream kinematics failed during displacement inversion",
            )
        f_mid = mid.delta_z_wc_body_m - requested_delta_z_wc_body_m
        best = mid
        if abs(f_mid) <= solver.displacement_tolerance_m or abs(q_right - q_left) <= solver.q_L_tolerance_rad:
            return PhysicalStateResult(
                status=WheelReferenceStatus.SUCCESS,
                requested_delta_z_wc_body_m=requested_delta_z_wc_body_m,
                q_L_rad=q_mid,
                wheel_state=mid,
                bracket_q_L_rad=(q_left, q_right),
                reachable_delta_z_range_m=reachable,
                monotonic_direction=direction,
                iterations=iterations,
                residual_m=f_mid,
            )
        if f_left * f_mid <= 0.0:
            right = mid
            q_right = q_mid
        else:
            left = mid
            q_left = q_mid
            f_left = f_mid

    residual = (
        None
        if best.delta_z_wc_body_m is None
        else best.delta_z_wc_body_m - requested_delta_z_wc_body_m
    )
    return PhysicalStateResult(
        status=WheelReferenceStatus.FAILURE,
        requested_delta_z_wc_body_m=requested_delta_z_wc_body_m,
        q_L_rad=best.q_L_rad,
        wheel_state=best,
        bracket_q_L_rad=(q_left, q_right),
        reachable_delta_z_range_m=reachable,
        monotonic_direction=direction,
        iterations=iterations,
        residual_m=residual,
        failure_code=WheelReferenceFailureCode.ROOT_NONCONVERGENCE,
        message="Body-frame wheel-center displacement inversion did not converge",
    )


def reconstruct_source_steering_twist(
    minimum_twist_transform: UprightReferenceTransform,
    nominal_tie_point_m: Point3,
    current_lower_m: Point3,
    current_upper_m: Point3,
    source_tie_point_m: Point3,
) -> SourceSteeringRemovalResult:
    """EQ-SUSP-0008 recover source upright twist from three-dimensional tie geometry."""

    try:
        axis = _normalize(
            _subtract(current_upper_m, current_lower_m),
            code=WheelReferenceFailureCode.DEGENERATE_STEERING_AXIS,
            message="Current lower/upper upright points define a degenerate steering axis",
        )
    except WheelReferenceError as exc:
        return SourceSteeringRemovalResult(
            status=WheelReferenceStatus.FAILURE,
            failure_code=WheelReferenceFailureCode.DEGENERATE_STEERING_AXIS,
            message=str(exc),
        )
    reference_tie = minimum_twist_transform.apply_point(nominal_tie_point_m)
    a = _subtract(reference_tie, current_lower_m)
    b = _subtract(source_tie_point_m, current_lower_m)
    a_perp = _subtract(a, _scale(axis, _dot(axis, a)))
    b_perp = _subtract(b, _scale(axis, _dot(axis, b)))
    a_norm = _norm(a_perp)
    b_norm = _norm(b_perp)
    if a_norm <= 1.0e-12 or b_norm <= 1.0e-12:
        return SourceSteeringRemovalResult(
            status=WheelReferenceStatus.FAILURE,
            reference_lever_arm_m=a_norm,
            source_lever_arm_m=b_norm,
            failure_code=WheelReferenceFailureCode.DEGENERATE_TIE_LEVER_ARM,
            message="Projected tie-point lever arm about the current steering axis is degenerate",
        )
    twist = math.atan2(_dot(axis, _cross(a_perp, b_perp)), _dot(a_perp, b_perp))
    return SourceSteeringRemovalResult(
        status=WheelReferenceStatus.SUCCESS,
        twist_rad=twist,
        reference_lever_arm_m=a_norm,
        source_lever_arm_m=b_norm,
        scalar_steer_angle_used_as_rotation=False,
    )


def remove_source_steering_from_point(
    source_point_m: Point3,
    current_lower_m: Point3,
    current_upper_m: Point3,
    twist_rad: float,
) -> Point3:
    """EQ-SUSP-0008 apply the inverse recovered source twist to an upright-attached point."""

    if not math.isfinite(twist_rad):
        raise WheelReferenceError("Source steering twist must be finite")
    axis = _subtract(current_upper_m, current_lower_m)
    radius = _subtract(source_point_m, current_lower_m)
    return _add(current_lower_m, _axis_angle_rotate(radius, axis, -twist_rad))


def remove_source_steering_from_direction(
    source_direction: Point3,
    current_lower_m: Point3,
    current_upper_m: Point3,
    twist_rad: float,
) -> Point3:
    """EQ-SUSP-0008 inverse-twist an upright-attached direction vector."""

    if not math.isfinite(twist_rad):
        raise WheelReferenceError("Source steering twist must be finite")
    result = _axis_angle_rotate(
        source_direction,
        _subtract(current_upper_m, current_lower_m),
        -twist_rad,
    )
    return _normalize(
        result,
        code=WheelReferenceFailureCode.NONFINITE_INPUT,
        message="Unsteered source direction is degenerate",
    )
