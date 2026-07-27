"""WUFR flat-road wheel-coordinate compatibility using an ideal rigid circular tire.

Implements the bounded R&D provider authorized by AUTH-VEH-0008.  The module
composes existing suspension, steering, whole-vehicle frame, and static-gravity
providers.  Its contact geometry is the explicit ASM-VEH-0005/EQ-VEH-0014
zero-width rigid circle; the rejected ASM-VEH-0004 OptimumK Contact Patch
material-point interpretation is never used as runtime geometry.

This module does not solve or publish final WUFR road reactions.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Sequence

from pssd_suspension import (
    Axle,
    PhysicalStateSolverConfig,
    Side,
    SuspensionGeometrySet,
    WheelReferenceSourceProfile,
    build_nominal_wheel_reference,
    load_optimumk_geometry_snapshot,
    load_wufr26_wheel_reference_profile,
    solve_body_vertical_displacement,
)
from pssd_steering import AxisLine, SteeringCorner, SteeringGeometry, load_geometry, solve_corner_position
from pssd_steering.core import rotate_direction_about_axis

from .force_coordinates import (
    BodyPose,
    PointReference,
    RoadPlane,
    WUFRWholeVehicleAdapter,
    load_wufr_whole_vehicle_adapter,
    rotation_matrix_yaw_pitch_roll,
    transport_body_fixed_point,
)
from .wufr_gravity import GravityPointMass, WUFRStaticGravityAllocation


Vector3 = tuple[float, float, float]
Matrix43 = tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
]
CORNER_ORDER = ("front_left", "front_right", "rear_left", "rear_right")
REQUIRED_RECORD_ID = "WUFR26_ROAD_CONTACT_REFERENCE_V0"
REQUIRED_CONFIGURATION_ID = "WUFR27_SUSPENSION_BASELINE_V0"
REQUIRED_AUTHORIZATION_ID = "AUTH-VEH-0008"
REQUIRED_ASSUMPTION_ID = "ASM-VEH-0005"
REQUIRED_EQUATION_ID = "EQ-VEH-0014"


class WUFRRoadContactStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class WUFRRoadContactFailureCode(str, Enum):
    SOURCE_MISMATCH = "source_mismatch"
    NONFINITE_INPUT = "nonfinite_input"
    BODY_POSE_OUTSIDE_DOMAIN = "body_pose_outside_domain"
    SUSPENSION_FAILURE = "suspension_failure"
    STEERING_FAILURE = "steering_failure"
    CONTACT_NORMAL_INVALID = "contact_normal_invalid"
    CONTACT_GEOMETRY_DEGENERATE = "contact_geometry_degenerate"
    ROAD_ROOT_UNBRACKETED = "road_root_unbracketed"
    ROAD_ROOT_AMBIGUOUS = "road_root_ambiguous"
    ROAD_ROOT_NONCONVERGENCE = "road_root_nonconvergence"
    DERIVATIVE_PERTURBATION_FAILURE = "derivative_perturbation_failure"
    DERIVATIVE_NOT_CONVERGED = "derivative_not_converged"
    CONTACT_COEFFICIENT_DEGENERATE = "contact_coefficient_degenerate"
    GRAVITY_SOURCE_MISMATCH = "gravity_source_mismatch"


class WUFRRoadContactError(ValueError):
    def __init__(self, code: WUFRRoadContactFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class RigidCircleContactResult:
    contact_point_m: Vector3
    radial_direction_to_center: Vector3
    projection_magnitude: float
    radius_m: float
    wheel_plane_normal: Vector3
    road_normal: Vector3
    assumption_id: str = REQUIRED_ASSUMPTION_ID
    equation_id: str = REQUIRED_EQUATION_ID


@dataclass(frozen=True)
class WUFRRoadContactSource:
    record_id: str
    configuration_id: str
    authority: str
    authorization_id: str
    assumption_id: str
    equation_id: str
    radius_source: str
    declared_radius_m: float
    installed_as_built_authority: bool
    generic_tire_contact_patch_authority: bool
    rigid_upright_attached_contact_authority: bool


@dataclass(frozen=True)
class WUFRRoadContactSolverConfig:
    q_L_limit_rad: float = math.radians(4.5)
    physical_scan_intervals_per_side: int = 6
    wheel_coordinate_min_m: float = -0.020
    wheel_coordinate_max_m: float = 0.020
    road_scan_intervals: int = 8
    road_gap_tolerance_m: float = 5.0e-10
    wheel_coordinate_tolerance_m: float = 2.0e-10
    root_max_iterations: int = 80
    body_z_limit_m: float = 0.010
    body_roll_limit_rad: float = 0.010
    body_pitch_limit_rad: float = 0.010
    body_fd_steps: tuple[float, float, float] = (2.0e-4, 2.0e-4, 2.0e-4)
    wheel_fd_step_m: float = 2.0e-4
    derivative_relative_tolerance: float = 5.0e-3
    derivative_absolute_tolerance: float = 2.0e-5
    contact_coefficient_min_abs: float = 1.0e-3
    unit_normal_tolerance: float = 1.0e-10
    contact_projection_min: float = 1.0e-10

    def __post_init__(self) -> None:
        finite = (
            self.q_L_limit_rad,
            self.wheel_coordinate_min_m,
            self.wheel_coordinate_max_m,
            self.road_gap_tolerance_m,
            self.wheel_coordinate_tolerance_m,
            self.body_z_limit_m,
            self.body_roll_limit_rad,
            self.body_pitch_limit_rad,
            *self.body_fd_steps,
            self.wheel_fd_step_m,
            self.derivative_relative_tolerance,
            self.derivative_absolute_tolerance,
            self.contact_coefficient_min_abs,
            self.unit_normal_tolerance,
            self.contact_projection_min,
        )
        if not all(math.isfinite(v) for v in finite):
            raise WUFRRoadContactError(
                WUFRRoadContactFailureCode.NONFINITE_INPUT,
                "Road-contact solver settings must be finite",
            )
        if self.q_L_limit_rad <= 0.0 or self.wheel_coordinate_min_m >= 0.0 or self.wheel_coordinate_max_m <= 0.0:
            raise WUFRRoadContactError(
                WUFRRoadContactFailureCode.NONFINITE_INPUT,
                "Reviewed domains must bracket nominal zero",
            )
        if self.physical_scan_intervals_per_side < 2 or self.road_scan_intervals < 4 or self.root_max_iterations < 1:
            raise WUFRRoadContactError(
                WUFRRoadContactFailureCode.NONFINITE_INPUT,
                "Road-contact scan/iteration settings are invalid",
            )
        if min(self.body_fd_steps) <= 0.0 or self.wheel_fd_step_m <= 0.0:
            raise WUFRRoadContactError(
                WUFRRoadContactFailureCode.NONFINITE_INPUT,
                "Finite-difference steps must be positive",
            )
        if self.unit_normal_tolerance <= 0.0 or self.contact_projection_min <= 0.0:
            raise WUFRRoadContactError(
                WUFRRoadContactFailureCode.NONFINITE_INPUT,
                "Contact geometry tolerances must be positive",
            )

    @property
    def physical_state_solver(self) -> PhysicalStateSolverConfig:
        return PhysicalStateSolverConfig(
            q_L_min_rad=-self.q_L_limit_rad,
            q_L_max_rad=self.q_L_limit_rad,
            scan_intervals_per_side=self.physical_scan_intervals_per_side,
            q_L_tolerance_rad=2.0e-12,
            displacement_tolerance_m=1.0e-12,
            monotonic_step_tolerance_m=1.0e-12,
            max_iterations=self.root_max_iterations,
        )


@dataclass(frozen=True)
class WUFRRoadContactProvider:
    source: WUFRRoadContactSource
    suspension_geometry: SuspensionGeometrySet
    wheel_profile: WheelReferenceSourceProfile
    steering_geometry: SteeringGeometry
    whole_vehicle: WUFRWholeVehicleAdapter
    tire_radius_m: float
    config: WUFRRoadContactSolverConfig

    def nominal_body_pose(self) -> BodyPose:
        return BodyPose(
            inertial_frame_id=self.whole_vehicle.road_frame_id,
            inertial_origin_id=self.whole_vehicle.road_origin_id,
            body_frame_id=self.whole_vehicle.body_frame_id,
            body_origin_id=self.whole_vehicle.body_origin_id,
            authority="AUTH-VEH-0008 WUFR flat-road compatibility pose",
        )

    def road_plane(self, pose: BodyPose) -> RoadPlane:
        _validate_pose_identity(self, pose)
        return RoadPlane(
            frame_id=pose.inertial_frame_id,
            origin_id=pose.inertial_origin_id,
            reference_point_m=(0.0, 0.0, -self.whole_vehicle.cg_source_position_m[2]),
            normal=(0.0, 0.0, 1.0),
            authority="AUTH-VEH-0008 flat rigid source road datum",
        )


@dataclass(frozen=True)
class CornerPointState:
    corner_id: str
    wheel_coordinate_m: float
    q_L_rad: float
    wheel_center_source_m: Vector3
    wheel_plane_normal_body: Vector3
    wheel_center_body: PointReference
    steering_rotation_rad: float | None
    steering_closure_residual_m: float | None
    suspension_transform_role: str


@dataclass(frozen=True)
class CornerRoadState:
    point_state: CornerPointState
    contact_road: PointReference
    wheel_center_road: PointReference
    circle_contact: RigidCircleContactResult
    road_gap_m: float


@dataclass(frozen=True)
class RoadRootResult:
    corner_id: str
    status: WUFRRoadContactStatus
    wheel_coordinate_m: float | None = None
    state: CornerRoadState | None = None
    bracket_m: tuple[float, float] | None = None
    iterations: int = 0
    failure_code: WUFRRoadContactFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WUFRRoadContactStatus.SUCCESS


@dataclass(frozen=True)
class RoadCompatibilityResult:
    status: WUFRRoadContactStatus
    coordinate_order: tuple[str, str, str, str] = CORNER_ORDER
    wheel_coordinates_m: tuple[float, float, float, float] | None = None
    roots: tuple[RoadRootResult, ...] = ()
    failure_code: WUFRRoadContactFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WUFRRoadContactStatus.SUCCESS


@dataclass(frozen=True)
class RoadJacobianResult:
    status: WUFRRoadContactStatus
    coordinate_order: tuple[str, str, str] = ("z_s_m", "phi_rad", "theta_rad")
    wheel_order: tuple[str, str, str, str] = CORNER_ORDER
    jacobian: Matrix43 | None = None
    coarse_jacobian: Matrix43 | None = None
    coarse_steps: tuple[float, float, float] | None = None
    fine_steps: tuple[float, float, float] | None = None
    convergence_error: float | None = None
    failure_code: WUFRRoadContactFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WUFRRoadContactStatus.SUCCESS


@dataclass(frozen=True)
class ScalarProjectionResult:
    status: WUFRRoadContactStatus
    corner_id: str
    value: float | None = None
    coarse_value: float | None = None
    coarse_step_m: float | None = None
    fine_step_m: float | None = None
    convergence_error: float | None = None
    failure_code: WUFRRoadContactFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WUFRRoadContactStatus.SUCCESS


@dataclass(frozen=True)
class WUFRRoadContactEvaluation:
    status: WUFRRoadContactStatus
    compatibility: RoadCompatibilityResult
    jacobian: RoadJacobianResult | None = None
    contact_coefficients: tuple[ScalarProjectionResult, ...] = ()
    unsprung_gravity_forces: tuple[ScalarProjectionResult, ...] = ()
    failure_code: WUFRRoadContactFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WUFRRoadContactStatus.SUCCESS


def _vector3(values: Sequence[float], label: str) -> Vector3:
    if len(values) != 3:
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.NONFINITE_INPUT,
            f"{label} must contain three values",
        )
    result = tuple(float(v) for v in values)
    if not all(math.isfinite(v) for v in result):
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.NONFINITE_INPUT,
            f"{label} must be finite",
        )
    return result  # type: ignore[return-value]


def _add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(a: Vector3, scalar: float) -> Vector3:
    return (a[0] * scalar, a[1] * scalar, a[2] * scalar)


def _dot(a: Vector3, b: Vector3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a: Vector3) -> float:
    return math.sqrt(_dot(a, a))


def _mat_vec(matrix: tuple[Vector3, Vector3, Vector3], vector: Vector3) -> Vector3:
    return tuple(sum(matrix[row][col] * vector[col] for col in range(3)) for row in range(3))  # type: ignore[return-value]


def _max_matrix_difference(a: Matrix43, b: Matrix43) -> float:
    return max(abs(x - y) for row_a, row_b in zip(a, b) for x, y in zip(row_a, row_b))


def ideal_rigid_circle_contact(
    wheel_center_m: Vector3,
    wheel_plane_normal: Vector3,
    road_normal: Vector3,
    radius_m: float,
    *,
    unit_normal_tolerance: float = 1.0e-10,
    projection_min: float = 1.0e-10,
) -> RigidCircleContactResult:
    """EQ-VEH-0014 minimum-road-height point on an ideal zero-width circle."""
    center = _vector3(wheel_center_m, "wheel center")
    wheel_normal = _vector3(wheel_plane_normal, "wheel-plane normal")
    road = _vector3(road_normal, "road normal")
    if not math.isfinite(radius_m) or radius_m <= 0.0:
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.NONFINITE_INPUT,
            "Rigid-circle radius must be finite and positive",
        )
    for label, normal in (("wheel-plane", wheel_normal), ("road", road)):
        magnitude = _norm(normal)
        if not math.isfinite(magnitude) or abs(magnitude - 1.0) > unit_normal_tolerance:
            raise WUFRRoadContactError(
                WUFRRoadContactFailureCode.CONTACT_NORMAL_INVALID,
                f"{label} normal must already be unit length; magnitude={magnitude:.16g}",
            )
    projection = _sub(road, _scale(wheel_normal, _dot(road, wheel_normal)))
    magnitude = _norm(projection)
    if not math.isfinite(magnitude) or magnitude <= projection_min:
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.CONTACT_GEOMETRY_DEGENERATE,
            "Road normal projection into the wheel plane is degenerate",
        )
    radial_to_center = _scale(projection, 1.0 / magnitude)
    contact = _sub(center, _scale(radial_to_center, radius_m))
    return RigidCircleContactResult(
        contact_point_m=contact,
        radial_direction_to_center=radial_to_center,
        projection_magnitude=magnitude,
        radius_m=radius_m,
        wheel_plane_normal=wheel_normal,
        road_normal=road,
    )


def load_wufr_road_contact_source(path: str | Path) -> WUFRRoadContactSource:
    with Path(path).open("rb") as stream:
        document = tomllib.load(stream)
    if document.get("record_id") != REQUIRED_RECORD_ID or document.get("configuration_id") != REQUIRED_CONFIGURATION_ID:
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.SOURCE_MISMATCH,
            "Road-contact source identity does not match AUTH-VEH-0008",
        )
    replacement = document.get("replacement_contact_authority", {})
    boundaries = document.get("authority_boundaries", {})
    if (
        replacement.get("authorization_id") != REQUIRED_AUTHORIZATION_ID
        or replacement.get("assumption_id") != REQUIRED_ASSUMPTION_ID
        or replacement.get("equation_id") != REQUIRED_EQUATION_ID
    ):
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.SOURCE_MISMATCH,
            "Replacement contact authority does not match AUTH-VEH-0008/ASM-VEH-0005/EQ-VEH-0014",
        )
    result = WUFRRoadContactSource(
        record_id=str(document["record_id"]),
        configuration_id=str(document["configuration_id"]),
        authority=str(document["authority"]),
        authorization_id=str(replacement["authorization_id"]),
        assumption_id=str(replacement["assumption_id"]),
        equation_id=str(replacement["equation_id"]),
        radius_source=str(replacement["radius_source"]),
        declared_radius_m=float(replacement["radius_m"]),
        installed_as_built_authority=bool(boundaries["installed_as_built_authority"]),
        generic_tire_contact_patch_authority=bool(boundaries["generic_tire_contact_patch_authority"]),
        rigid_upright_attached_contact_authority=bool(boundaries["rigid_upright_attached_contact_authority"]),
    )
    if (
        result.installed_as_built_authority
        or result.generic_tire_contact_patch_authority
        or result.rigid_upright_attached_contact_authority
    ):
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.SOURCE_MISMATCH,
            "AUTH-VEH-0008 must not revive generic, installed, or ASM-VEH-0004 contact authority",
        )
    return result


def load_wufr_road_contact_provider(
    *,
    source_path: str | Path,
    suspension_geometry_path: str | Path,
    wheel_profile_path: str | Path,
    steering_geometry_path: str | Path,
    whole_vehicle_path: str | Path,
    config: WUFRRoadContactSolverConfig | None = None,
) -> WUFRRoadContactProvider:
    source = load_wufr_road_contact_source(source_path)
    suspension = load_optimumk_geometry_snapshot(suspension_geometry_path)
    profile = load_wufr26_wheel_reference_profile(wheel_profile_path)
    steering = load_geometry(steering_geometry_path)
    whole_vehicle = load_wufr_whole_vehicle_adapter(whole_vehicle_path)
    if whole_vehicle.configuration_id != source.configuration_id:
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.SOURCE_MISMATCH,
            "Whole-vehicle and contact-source configuration IDs differ",
        )
    radius = profile.front.tire_radius_m
    if not math.isclose(radius, profile.rear.tire_radius_m, rel_tol=0.0, abs_tol=1.0e-15):
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.SOURCE_MISMATCH,
            "Front/rear wheel-reference source radii differ",
        )
    if not math.isclose(radius, source.declared_radius_m, rel_tol=0.0, abs_tol=1.0e-15):
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.SOURCE_MISMATCH,
            "AUTH-VEH-0008 source record radius does not match the frozen wheel-reference radius",
        )
    return WUFRRoadContactProvider(
        source=source,
        suspension_geometry=suspension,
        wheel_profile=profile,
        steering_geometry=steering,
        whole_vehicle=whole_vehicle,
        tire_radius_m=radius,
        config=config or WUFRRoadContactSolverConfig(),
    )


def _corner_identity(corner_id: str) -> tuple[Axle, Side, str]:
    if corner_id == "front_left":
        return Axle.FRONT, Side.LEFT, "left"
    if corner_id == "front_right":
        return Axle.FRONT, Side.RIGHT, "right"
    if corner_id == "rear_left":
        return Axle.REAR, Side.LEFT, "left"
    if corner_id == "rear_right":
        return Axle.REAR, Side.RIGHT, "right"
    raise WUFRRoadContactError(
        WUFRRoadContactFailureCode.SOURCE_MISMATCH,
        f"Unknown corner {corner_id!r}",
    )


def _validate_pose_identity(provider: WUFRRoadContactProvider, pose: BodyPose) -> None:
    adapter = provider.whole_vehicle
    if (
        pose.body_frame_id != adapter.body_frame_id
        or pose.body_origin_id != adapter.body_origin_id
        or pose.inertial_frame_id != adapter.road_frame_id
        or pose.inertial_origin_id != adapter.road_origin_id
        or pose.psi_rad != 0.0
        or any(abs(v) > 0.0 for v in pose.body_origin_position_m)
    ):
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.SOURCE_MISMATCH,
            "BodyPose frame/origin/yaw contract does not match the AUTH-VEH-0008 WUFR map",
        )
    cfg = provider.config
    if (
        abs(pose.z_s_m) > cfg.body_z_limit_m
        or abs(pose.phi_rad) > cfg.body_roll_limit_rad
        or abs(pose.theta_rad) > cfg.body_pitch_limit_rad
    ):
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.BODY_POSE_OUTSIDE_DOMAIN,
            "Body pose lies outside the reviewed local compatibility domain",
        )


def _source_to_body_point(
    provider: WUFRRoadContactProvider,
    corner_id: str,
    role: str,
    source_position: Vector3,
) -> PointReference:
    adapter = provider.whole_vehicle
    return PointReference(
        point_id=f"{corner_id}_{role}",
        frame_id=adapter.body_frame_id,
        origin_id=adapter.body_origin_id,
        position_m=_add(source_position, adapter.source_to_body_translation_m),
        role=role,
        source_id=provider.source.record_id,
        configuration_id=provider.source.configuration_id,
        authority="AUTH-VEH-0008 / ASM-VEH-0005 design-intent R&D",
        fixed_role="body_fixed",
        provenance=(
            ("authorization", REQUIRED_AUTHORIZATION_ID),
            ("assumption", REQUIRED_ASSUMPTION_ID),
            ("equation", "EQ-VEH-0011"),
            ("corner", corner_id),
        ),
    )


def _front_centered_rack_plane(
    provider: WUFRRoadContactProvider,
    side_name: str,
    transform,
    presteer_plane_normal: Vector3,
) -> tuple[Vector3, float, float | None]:
    base = provider.steering_geometry
    original = base.left if side_name == "left" else base.right
    axis = AxisLine(
        point=transform.apply_point(original.steering_axis.point),
        direction=transform.apply_direction(original.steering_axis.direction),
    )
    transformed_corner = SteeringCorner(
        side=original.side,
        steering_axis=axis,
        rack_inner_joint_at_center=original.rack_inner_joint_at_center,
        outer_tie_rod_joint_at_center=transform.apply_point(original.outer_tie_rod_joint_at_center),
        tie_rod_length=original.tie_rod_length,
        reference_upright_rotation=0.0,
        mechanical_rotation_min=original.mechanical_rotation_min,
        mechanical_rotation_max=original.mechanical_rotation_max,
        wheel_forward_direction_at_center=(
            transform.apply_direction(original.wheel_forward_direction_at_center)
            if original.wheel_forward_direction_at_center is not None
            else None
        ),
        static_toe=original.static_toe,
        source_role=f"AUTH-VEH-0008:{original.source_role}",
    )
    posed_geometry = replace(
        base,
        geometry_id=f"{base.geometry_id}:ROAD_CONTACT_POSE",
        left=transformed_corner if side_name == "left" else base.left,
        right=transformed_corner if side_name == "right" else base.right,
        steering_axis_track=None,
    )
    solved = solve_corner_position(posed_geometry, side_name, 0.0)
    if not solved.ok or solved.upright_rotation is None:
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.STEERING_FAILURE,
            f"Centered-rack MOD-STEER-0001 closure failed for {side_name}: {solved.failure_code} {solved.message}",
        )
    plane = rotate_direction_about_axis(presteer_plane_normal, axis.direction, solved.upright_rotation)
    return plane, solved.upright_rotation, solved.closure_length_residual


def evaluate_corner_point_state(
    provider: WUFRRoadContactProvider,
    corner_id: str,
    wheel_coordinate_m: float,
) -> CornerPointState:
    if not math.isfinite(wheel_coordinate_m):
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.NONFINITE_INPUT,
            "Wheel coordinate must be finite",
        )
    if not (provider.config.wheel_coordinate_min_m <= wheel_coordinate_m <= provider.config.wheel_coordinate_max_m):
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.SUSPENSION_FAILURE,
            "Wheel coordinate lies outside the reviewed local map interval",
        )
    axle, side, side_name = _corner_identity(corner_id)
    geometry = provider.suspension_geometry.corner(axle, side)
    nominal = build_nominal_wheel_reference(provider.wheel_profile, axle, side)
    physical = solve_body_vertical_displacement(
        geometry,
        nominal,
        wheel_coordinate_m,
        provider.config.physical_state_solver,
        geometry_id=provider.suspension_geometry.geometry_id,
        configuration_id=provider.source.configuration_id,
        source_authority=provider.suspension_geometry.authority,
    )
    if not physical.ok or physical.wheel_state is None or physical.q_L_rad is None:
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.SUSPENSION_FAILURE,
            f"MOD-SUSP-0002 physical-state inversion failed for {corner_id}: {physical.failure_code} {physical.message}",
        )
    wheel_state = physical.wheel_state
    upstream = wheel_state.upstream_state
    if (
        upstream is None
        or wheel_state.current_center_m is None
        or wheel_state.current_plane_normal is None
    ):
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.SUSPENSION_FAILURE,
            f"Incomplete suspension wheel state for {corner_id}",
        )

    plane_normal = wheel_state.current_plane_normal
    steering_rotation: float | None = None
    steering_residual: float | None = None
    if axle is Axle.FRONT:
        transform = upstream.minimum_twist_transform
        if transform is None:
            raise WUFRRoadContactError(
                WUFRRoadContactFailureCode.SUSPENSION_FAILURE,
                f"Front minimum-twist transform unavailable for {corner_id}",
            )
        plane_normal, steering_rotation, steering_residual = _front_centered_rack_plane(
            provider,
            side_name,
            transform,
            plane_normal,
        )
        transform_role = "front_MOD-SUSP-0002_center_then_MOD-STEER-0001_centered_rack_plane"
    else:
        transform_role = "rear_MOD-SUSP-0002_toe_link_closed_center_and_plane"

    x_origin = (
        provider.whole_vehicle.front_axle_source_position_m[0]
        if axle is Axle.FRONT
        else provider.whole_vehicle.rear_axle_source_position_m[0]
    )
    wheel_center_source = _add(wheel_state.current_center_m, (x_origin, 0.0, 0.0))
    return CornerPointState(
        corner_id=corner_id,
        wheel_coordinate_m=wheel_coordinate_m,
        q_L_rad=physical.q_L_rad,
        wheel_center_source_m=wheel_center_source,
        wheel_plane_normal_body=plane_normal,
        wheel_center_body=_source_to_body_point(
            provider,
            corner_id,
            "physical_wheel_center",
            wheel_center_source,
        ),
        steering_rotation_rad=steering_rotation,
        steering_closure_residual_m=steering_residual,
        suspension_transform_role=transform_role,
    )


def evaluate_corner_road_state(
    provider: WUFRRoadContactProvider,
    pose: BodyPose,
    corner_id: str,
    wheel_coordinate_m: float,
) -> CornerRoadState:
    _validate_pose_identity(provider, pose)
    point_state = evaluate_corner_point_state(provider, corner_id, wheel_coordinate_m)
    wheel_road = transport_body_fixed_point(point_state.wheel_center_body, pose)
    rotation = rotation_matrix_yaw_pitch_roll(
        psi_rad=pose.psi_rad,
        theta_rad=pose.theta_rad,
        phi_rad=pose.phi_rad,
    )
    wheel_normal_road = _mat_vec(rotation, point_state.wheel_plane_normal_body)
    road = provider.road_plane(pose)
    circle = ideal_rigid_circle_contact(
        wheel_road.position_m,
        wheel_normal_road,
        road.normal,
        provider.tire_radius_m,
        unit_normal_tolerance=provider.config.unit_normal_tolerance,
        projection_min=provider.config.contact_projection_min,
    )
    contact_road = PointReference(
        point_id=f"{corner_id}_ideal_rigid_circle_contact",
        frame_id=road.frame_id,
        origin_id=road.origin_id,
        position_m=circle.contact_point_m,
        role="ideal_rigid_circle_road_contact_reference",
        source_id=provider.source.radius_source,
        configuration_id=provider.source.configuration_id,
        authority="AUTH-VEH-0008 / ASM-VEH-0005 / EQ-VEH-0014",
        fixed_role="road_contact_migrating",
        provenance=(
            ("authorization", REQUIRED_AUTHORIZATION_ID),
            ("assumption", REQUIRED_ASSUMPTION_ID),
            ("equation", REQUIRED_EQUATION_ID),
            ("radius_source", provider.source.radius_source),
            ("corner", corner_id),
        ),
    )
    gap = _dot(road.normal, _sub(contact_road.position_m, road.reference_point_m))
    return CornerRoadState(point_state, contact_road, wheel_road, circle, gap)


def _failure_root(
    corner_id: str,
    code: WUFRRoadContactFailureCode,
    message: str,
    *,
    bracket: tuple[float, float] | None = None,
    iterations: int = 0,
) -> RoadRootResult:
    return RoadRootResult(
        corner_id,
        WUFRRoadContactStatus.FAILURE,
        bracket_m=bracket,
        iterations=iterations,
        failure_code=code,
        message=message,
    )


def solve_corner_road_root(
    provider: WUFRRoadContactProvider,
    pose: BodyPose,
    corner_id: str,
) -> RoadRootResult:
    try:
        _validate_pose_identity(provider, pose)
    except WUFRRoadContactError as exc:
        return _failure_root(corner_id, exc.code, str(exc))
    cfg = provider.config
    samples: list[CornerRoadState] = []
    for index in range(cfg.road_scan_intervals + 1):
        z = cfg.wheel_coordinate_min_m + (
            cfg.wheel_coordinate_max_m - cfg.wheel_coordinate_min_m
        ) * index / cfg.road_scan_intervals
        try:
            samples.append(evaluate_corner_road_state(provider, pose, corner_id, z))
        except WUFRRoadContactError as exc:
            return _failure_root(
                corner_id,
                exc.code,
                f"Road-root sample failed at z={z:.9g} m: {exc}",
            )

    exact = [state for state in samples if abs(state.road_gap_m) <= cfg.road_gap_tolerance_m]
    if len(exact) == 1:
        state = exact[0]
        z = state.point_state.wheel_coordinate_m
        return RoadRootResult(
            corner_id,
            WUFRRoadContactStatus.SUCCESS,
            z,
            state,
            (z, z),
            0,
        )
    if len(exact) > 1:
        return _failure_root(
            corner_id,
            WUFRRoadContactFailureCode.ROAD_ROOT_AMBIGUOUS,
            "Multiple sampled wheel coordinates satisfy the road constraint",
        )

    brackets: list[tuple[CornerRoadState, CornerRoadState]] = []
    for left, right in zip(samples[:-1], samples[1:]):
        if left.road_gap_m * right.road_gap_m < 0.0:
            brackets.append((left, right))
    if len(brackets) != 1:
        code = (
            WUFRRoadContactFailureCode.ROAD_ROOT_AMBIGUOUS
            if len(brackets) > 1
            else WUFRRoadContactFailureCode.ROAD_ROOT_UNBRACKETED
        )
        return _failure_root(
            corner_id,
            code,
            f"Expected one road-gap bracket; found {len(brackets)}",
        )

    left, right = brackets[0]
    z_left = left.point_state.wheel_coordinate_m
    z_right = right.point_state.wheel_coordinate_m
    g_left = left.road_gap_m
    for iteration in range(1, cfg.root_max_iterations + 1):
        z_mid = 0.5 * (z_left + z_right)
        try:
            mid = evaluate_corner_road_state(provider, pose, corner_id, z_mid)
        except WUFRRoadContactError as exc:
            return _failure_root(
                corner_id,
                exc.code,
                f"Road-root refinement failed: {exc}",
                bracket=(z_left, z_right),
                iterations=iteration,
            )
        if (
            abs(mid.road_gap_m) <= cfg.road_gap_tolerance_m
            or 0.5 * abs(z_right - z_left) <= cfg.wheel_coordinate_tolerance_m
        ):
            return RoadRootResult(
                corner_id,
                WUFRRoadContactStatus.SUCCESS,
                z_mid,
                mid,
                (z_left, z_right),
                iteration,
            )
        if g_left * mid.road_gap_m <= 0.0:
            right = mid
            z_right = z_mid
        else:
            left = mid
            z_left = z_mid
            g_left = mid.road_gap_m
    return _failure_root(
        corner_id,
        WUFRRoadContactFailureCode.ROAD_ROOT_NONCONVERGENCE,
        "Road-gap bisection did not converge",
        bracket=(z_left, z_right),
        iterations=cfg.root_max_iterations,
    )


def solve_road_compatibility(
    provider: WUFRRoadContactProvider,
    pose: BodyPose,
) -> RoadCompatibilityResult:
    roots = tuple(solve_corner_road_root(provider, pose, corner) for corner in CORNER_ORDER)
    failed = next((item for item in roots if not item.ok), None)
    if failed is not None:
        return RoadCompatibilityResult(
            WUFRRoadContactStatus.FAILURE,
            roots=roots,
            failure_code=failed.failure_code,
            message=f"{failed.corner_id}: {failed.message}",
        )
    coordinates = tuple(float(item.wheel_coordinate_m) for item in roots)  # type: ignore[arg-type]
    return RoadCompatibilityResult(
        WUFRRoadContactStatus.SUCCESS,
        wheel_coordinates_m=coordinates,
        roots=roots,
    )


def _pose_with_coordinate(pose: BodyPose, index: int, delta: float) -> BodyPose:
    if index == 0:
        return replace(pose, z_s_m=pose.z_s_m + delta)
    if index == 1:
        return replace(pose, phi_rad=pose.phi_rad + delta)
    return replace(pose, theta_rad=pose.theta_rad + delta)


def _jacobian_at_steps(
    provider: WUFRRoadContactProvider,
    pose: BodyPose,
    steps: tuple[float, float, float],
) -> Matrix43:
    columns: list[tuple[float, float, float, float]] = []
    for axis, step in enumerate(steps):
        minus_pose = _pose_with_coordinate(pose, axis, -step)
        plus_pose = _pose_with_coordinate(pose, axis, step)
        try:
            _validate_pose_identity(provider, minus_pose)
            _validate_pose_identity(provider, plus_pose)
        except WUFRRoadContactError as exc:
            raise WUFRRoadContactError(
                WUFRRoadContactFailureCode.DERIVATIVE_PERTURBATION_FAILURE,
                f"Centered body perturbation leaves reviewed domain: {exc}",
            ) from exc
        minus = solve_road_compatibility(provider, minus_pose)
        plus = solve_road_compatibility(provider, plus_pose)
        if (
            not minus.ok
            or not plus.ok
            or minus.wheel_coordinates_m is None
            or plus.wheel_coordinates_m is None
        ):
            raise WUFRRoadContactError(
                WUFRRoadContactFailureCode.DERIVATIVE_PERTURBATION_FAILURE,
                f"Body Jacobian perturbation failed on coordinate {axis}",
            )
        columns.append(
            tuple(
                (p - m) / (2.0 * step)
                for p, m in zip(plus.wheel_coordinates_m, minus.wheel_coordinates_m)
            )
        )
    return tuple(
        tuple(columns[col][row] for col in range(3)) for row in range(4)
    )  # type: ignore[return-value]


def evaluate_body_to_wheel_jacobian(
    provider: WUFRRoadContactProvider,
    pose: BodyPose,
) -> RoadJacobianResult:
    coarse_steps = provider.config.body_fd_steps
    fine_steps = tuple(0.5 * value for value in coarse_steps)
    try:
        coarse = _jacobian_at_steps(provider, pose, coarse_steps)
        fine = _jacobian_at_steps(provider, pose, fine_steps)  # type: ignore[arg-type]
    except WUFRRoadContactError as exc:
        return RoadJacobianResult(
            WUFRRoadContactStatus.FAILURE,
            coarse_steps=coarse_steps,
            fine_steps=fine_steps,
            failure_code=exc.code,
            message=str(exc),
        )
    error = _max_matrix_difference(coarse, fine)
    scale = max(1.0, *(abs(v) for row in fine for v in row))
    tolerance = provider.config.derivative_absolute_tolerance + provider.config.derivative_relative_tolerance * scale
    if error > tolerance:
        return RoadJacobianResult(
            WUFRRoadContactStatus.FAILURE,
            coarse_jacobian=coarse,
            jacobian=fine,
            coarse_steps=coarse_steps,
            fine_steps=fine_steps,
            convergence_error=error,
            failure_code=WUFRRoadContactFailureCode.DERIVATIVE_NOT_CONVERGED,
            message=f"J_wb h/h2 difference {error:.6g} exceeds tolerance {tolerance:.6g}",
        )
    return RoadJacobianResult(
        WUFRRoadContactStatus.SUCCESS,
        jacobian=fine,
        coarse_jacobian=coarse,
        coarse_steps=coarse_steps,
        fine_steps=fine_steps,
        convergence_error=error,
    )


def _point_derivative(
    provider: WUFRRoadContactProvider,
    pose: BodyPose,
    root: RoadRootResult,
    step: float,
    *,
    wheel_center: bool,
) -> Vector3:
    if not root.ok or root.wheel_coordinate_m is None:
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.DERIVATIVE_PERTURBATION_FAILURE,
            "A converged road root is required for wheel differentiation",
        )
    z = root.wheel_coordinate_m
    if z - step < provider.config.wheel_coordinate_min_m or z + step > provider.config.wheel_coordinate_max_m:
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.DERIVATIVE_PERTURBATION_FAILURE,
            "Wheel finite difference would leave the reviewed interval",
        )
    try:
        minus = evaluate_corner_road_state(provider, pose, root.corner_id, z - step)
        plus = evaluate_corner_road_state(provider, pose, root.corner_id, z + step)
    except WUFRRoadContactError as exc:
        raise WUFRRoadContactError(
            WUFRRoadContactFailureCode.DERIVATIVE_PERTURBATION_FAILURE,
            f"Wheel derivative perturbation failed: {exc}",
        ) from exc
    p_minus = minus.wheel_center_road.position_m if wheel_center else minus.contact_road.position_m
    p_plus = plus.wheel_center_road.position_m if wheel_center else plus.contact_road.position_m
    return _scale(_sub(p_plus, p_minus), 1.0 / (2.0 * step))


def evaluate_contact_coefficient(
    provider: WUFRRoadContactProvider,
    pose: BodyPose,
    root: RoadRootResult,
) -> ScalarProjectionResult:
    coarse_step = provider.config.wheel_fd_step_m
    fine_step = 0.5 * coarse_step
    road = provider.road_plane(pose)
    try:
        coarse = _dot(
            road.normal,
            _point_derivative(provider, pose, root, coarse_step, wheel_center=False),
        )
        fine = _dot(
            road.normal,
            _point_derivative(provider, pose, root, fine_step, wheel_center=False),
        )
    except WUFRRoadContactError as exc:
        return ScalarProjectionResult(
            WUFRRoadContactStatus.FAILURE,
            root.corner_id,
            coarse_step_m=coarse_step,
            fine_step_m=fine_step,
            failure_code=exc.code,
            message=str(exc),
        )
    error = abs(coarse - fine)
    accepted = (4.0 * fine - coarse) / 3.0
    tolerance = provider.config.derivative_absolute_tolerance + provider.config.derivative_relative_tolerance * max(1.0, abs(accepted))
    if error > tolerance:
        return ScalarProjectionResult(
            WUFRRoadContactStatus.FAILURE,
            root.corner_id,
            accepted,
            coarse,
            coarse_step,
            fine_step,
            error,
            WUFRRoadContactFailureCode.DERIVATIVE_NOT_CONVERGED,
            f"Contact coefficient h/h2 difference {error:.6g} exceeds tolerance {tolerance:.6g}",
        )
    if not math.isfinite(accepted) or abs(accepted) < provider.config.contact_coefficient_min_abs:
        return ScalarProjectionResult(
            WUFRRoadContactStatus.FAILURE,
            root.corner_id,
            accepted,
            coarse,
            coarse_step,
            fine_step,
            error,
            WUFRRoadContactFailureCode.CONTACT_COEFFICIENT_DEGENERATE,
            "Contact coefficient is nonfinite or too close to zero",
        )
    return ScalarProjectionResult(
        WUFRRoadContactStatus.SUCCESS,
        root.corner_id,
        accepted,
        coarse,
        coarse_step,
        fine_step,
        error,
    )


def evaluate_unsprung_gravity_projection(
    provider: WUFRRoadContactProvider,
    pose: BodyPose,
    root: RoadRootResult,
    mass: GravityPointMass,
    g_mps2: float,
) -> ScalarProjectionResult:
    if mass.corner_id != root.corner_id or mass.configuration_id != provider.source.configuration_id:
        return ScalarProjectionResult(
            WUFRRoadContactStatus.FAILURE,
            root.corner_id,
            failure_code=WUFRRoadContactFailureCode.GRAVITY_SOURCE_MISMATCH,
            message="Unsprung gravity point does not match road-contact corner/configuration",
        )
    coarse_step = provider.config.wheel_fd_step_m
    fine_step = 0.5 * coarse_step
    force = mass.force_N(g_mps2)
    try:
        coarse = _dot(
            force,
            _point_derivative(provider, pose, root, coarse_step, wheel_center=True),
        )
        fine = _dot(
            force,
            _point_derivative(provider, pose, root, fine_step, wheel_center=True),
        )
    except WUFRRoadContactError as exc:
        return ScalarProjectionResult(
            WUFRRoadContactStatus.FAILURE,
            root.corner_id,
            coarse_step_m=coarse_step,
            fine_step_m=fine_step,
            failure_code=exc.code,
            message=str(exc),
        )
    error = abs(coarse - fine)
    accepted = (4.0 * fine - coarse) / 3.0
    tolerance = 1.0e-6 + provider.config.derivative_relative_tolerance * max(1.0, abs(accepted))
    if error > tolerance or not math.isfinite(accepted):
        return ScalarProjectionResult(
            WUFRRoadContactStatus.FAILURE,
            root.corner_id,
            accepted,
            coarse,
            coarse_step,
            fine_step,
            error,
            WUFRRoadContactFailureCode.DERIVATIVE_NOT_CONVERGED,
            f"Unsprung-gravity projection h/h2 difference {error:.6g} exceeds tolerance {tolerance:.6g}",
        )
    return ScalarProjectionResult(
        WUFRRoadContactStatus.SUCCESS,
        root.corner_id,
        accepted,
        coarse,
        coarse_step,
        fine_step,
        error,
    )


def evaluate_wufr_road_contact(
    provider: WUFRRoadContactProvider,
    pose: BodyPose,
    gravity: WUFRStaticGravityAllocation | None = None,
) -> WUFRRoadContactEvaluation:
    compatibility = solve_road_compatibility(provider, pose)
    if not compatibility.ok:
        return WUFRRoadContactEvaluation(
            WUFRRoadContactStatus.FAILURE,
            compatibility,
            failure_code=compatibility.failure_code,
            message=compatibility.message,
        )
    jacobian = evaluate_body_to_wheel_jacobian(provider, pose)
    if not jacobian.ok:
        return WUFRRoadContactEvaluation(
            WUFRRoadContactStatus.FAILURE,
            compatibility,
            jacobian,
            failure_code=jacobian.failure_code,
            message=jacobian.message,
        )
    coefficients = tuple(
        evaluate_contact_coefficient(provider, pose, root)
        for root in compatibility.roots
    )
    failed_coefficient = next((item for item in coefficients if not item.ok), None)
    if failed_coefficient is not None:
        return WUFRRoadContactEvaluation(
            WUFRRoadContactStatus.FAILURE,
            compatibility,
            jacobian,
            coefficients,
            failure_code=failed_coefficient.failure_code,
            message=failed_coefficient.message,
        )
    gravity_results: tuple[ScalarProjectionResult, ...] = ()
    if gravity is not None:
        masses = {item.corner_id: item for item in gravity.unsprung}
        missing = next((corner for corner in CORNER_ORDER if corner not in masses), None)
        if missing is not None:
            return WUFRRoadContactEvaluation(
                WUFRRoadContactStatus.FAILURE,
                compatibility,
                jacobian,
                coefficients,
                failure_code=WUFRRoadContactFailureCode.GRAVITY_SOURCE_MISMATCH,
                message=f"Missing unsprung gravity point for {missing}",
            )
        gravity_results = tuple(
            evaluate_unsprung_gravity_projection(
                provider,
                pose,
                root,
                masses[root.corner_id],
                gravity.g_mps2,
            )
            for root in compatibility.roots
        )
        failed_gravity = next((item for item in gravity_results if not item.ok), None)
        if failed_gravity is not None:
            return WUFRRoadContactEvaluation(
                WUFRRoadContactStatus.FAILURE,
                compatibility,
                jacobian,
                coefficients,
                gravity_results,
                failed_gravity.failure_code,
                failed_gravity.message,
            )
    return WUFRRoadContactEvaluation(
        WUFRRoadContactStatus.SUCCESS,
        compatibility,
        jacobian,
        coefficients,
        gravity_results,
    )
