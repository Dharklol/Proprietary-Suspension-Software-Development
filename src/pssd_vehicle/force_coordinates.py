"""Whole-vehicle force coordinates, wrench assembly, and rigid-contact classification.

Authorized by ``AUTH-VEH-0003``.  This module contains mechanics primitives only:

* rigid body-fixed point transport using ``Rz(psi) Ry(theta) Rx(phi)``;
* point-force/free-couple wrench translation and summation;
* signed generalized-force mapping for ``q=[z_s, phi, theta]`` through virtual work;
* flat-road, vertically rigid, all-four-contact admissibility classification;
* an explicit WUFR-26/27 design-intent adapter loaded from a frozen source record.

It intentionally does not evaluate spring, damper, anti-roll-bar, tire, aero, brake,
or inertia force laws and does not solve vehicle equilibrium or suspension linkage loads.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Iterable, Mapping, Sequence

Vector3 = tuple[float, float, float]
Matrix3 = tuple[Vector3, Vector3, Vector3]
Jacobian3 = tuple[Vector3, Vector3, Vector3]


class ForceCoordinateFailureCode(str, Enum):
    NONFINITE_INPUT = "nonfinite_input"
    INVALID_FRAME = "invalid_frame"
    INVALID_ORIGIN = "invalid_origin"
    FRAME_MISMATCH = "frame_mismatch"
    MISSING_TRANSFORM_AUTHORITY = "missing_transform_authority"
    INVALID_ROTATION = "invalid_rotation"
    INVALID_REFERENCE_POINT = "invalid_reference_point"
    INVALID_ROAD_NORMAL = "invalid_road_normal"
    UNSUPPORTED_CONTACT_MODEL = "unsupported_contact_model"
    OPEN_CONTACT_GAP = "open_contact_gap"
    PENETRATING_CONTACT_REFERENCE = "penetrating_contact_reference"
    NEGATIVE_NORMAL_REACTION = "negative_normal_reaction"
    CONTACT_MODE_INVALID = "contact_mode_invalid"
    JACOBIAN_UNAVAILABLE = "jacobian_unavailable"
    JACOBIAN_NOT_CONVERGED = "jacobian_not_converged"
    MISSING_AUTHORITY = "missing_authority"
    UNSUPPORTED_FORCE_LAW = "unsupported_force_law"
    UNSUPPORTED_EQUILIBRIUM_REQUEST = "unsupported_equilibrium_request"
    UNSUPPORTED_LINKAGE_FORCE_REQUEST = "unsupported_linkage_force_request"


class ForceCoordinateError(ValueError):
    """Structured error for invalid or unauthorized force-coordinate inputs."""

    def __init__(self, code: ForceCoordinateFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class ContactStatus(str, Enum):
    FOUR_CONTACT_ADMISSIBLE = "four_contact_admissible"
    OPEN_GAP = "open_gap"
    PENETRATION = "penetration"
    WHEEL_LIFT = "wheel_lift"
    CONTACT_MODE_INVALID = "contact_mode_invalid"
    UNSUPPORTED_CONTACT_MODEL = "unsupported_contact_model"
    MISSING_AUTHORITY = "missing_authority"


@dataclass(frozen=True)
class PointReference:
    point_id: str
    frame_id: str
    origin_id: str
    position_m: Vector3
    role: str
    source_id: str
    configuration_id: str
    authority: str
    fixed_role: str = "body_fixed"
    provenance: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_name(self.point_id, "point_id")
        _require_name(self.frame_id, "frame_id", ForceCoordinateFailureCode.INVALID_FRAME)
        _require_name(self.origin_id, "origin_id", ForceCoordinateFailureCode.INVALID_ORIGIN)
        _require_vector(self.position_m, "position_m")
        _require_name(self.role, "role")
        _require_name(self.source_id, "source_id", ForceCoordinateFailureCode.MISSING_AUTHORITY)
        _require_name(
            self.configuration_id,
            "configuration_id",
            ForceCoordinateFailureCode.MISSING_AUTHORITY,
        )
        _require_name(self.authority, "authority", ForceCoordinateFailureCode.MISSING_AUTHORITY)


@dataclass(frozen=True)
class BodyPose:
    inertial_frame_id: str
    inertial_origin_id: str
    body_frame_id: str
    body_origin_id: str
    body_origin_position_m: Vector3 = (0.0, 0.0, 0.0)
    z_s_m: float = 0.0
    phi_rad: float = 0.0
    theta_rad: float = 0.0
    psi_rad: float = 0.0
    authority: str = "explicit_pose"

    def __post_init__(self) -> None:
        _require_name(
            self.inertial_frame_id,
            "inertial_frame_id",
            ForceCoordinateFailureCode.INVALID_FRAME,
        )
        _require_name(
            self.inertial_origin_id,
            "inertial_origin_id",
            ForceCoordinateFailureCode.INVALID_ORIGIN,
        )
        _require_name(self.body_frame_id, "body_frame_id", ForceCoordinateFailureCode.INVALID_FRAME)
        _require_name(self.body_origin_id, "body_origin_id", ForceCoordinateFailureCode.INVALID_ORIGIN)
        _require_vector(self.body_origin_position_m, "body_origin_position_m")
        _require_finite((self.z_s_m, self.phi_rad, self.theta_rad, self.psi_rad), "body pose")
        _require_name(self.authority, "authority", ForceCoordinateFailureCode.MISSING_AUTHORITY)

    @property
    def coordinate_order(self) -> tuple[str, str, str]:
        return ("z_s_m", "phi_rad", "theta_rad")

    @property
    def coordinate_units(self) -> tuple[str, str, str]:
        return ("m", "rad", "rad")


@dataclass(frozen=True)
class AppliedWrench:
    wrench_id: str
    frame_id: str
    origin_id: str
    application_point: PointReference
    force_N: Vector3 = (0.0, 0.0, 0.0)
    free_couple_Nm: Vector3 = (0.0, 0.0, 0.0)
    source_id: str = "explicit_input"
    authority: str = "externally_supplied_action"

    def __post_init__(self) -> None:
        _require_name(self.wrench_id, "wrench_id")
        _require_name(self.frame_id, "frame_id", ForceCoordinateFailureCode.INVALID_FRAME)
        _require_name(self.origin_id, "origin_id", ForceCoordinateFailureCode.INVALID_ORIGIN)
        _require_vector(self.force_N, "force_N")
        _require_vector(self.free_couple_Nm, "free_couple_Nm")
        _require_name(self.source_id, "source_id", ForceCoordinateFailureCode.MISSING_AUTHORITY)
        _require_name(self.authority, "authority", ForceCoordinateFailureCode.MISSING_AUTHORITY)
        _require_same_frame_origin(self.application_point, self.frame_id, self.origin_id)


@dataclass(frozen=True)
class TranslatedWrench:
    wrench_id: str
    reference_point_id: str
    frame_id: str
    origin_id: str
    force_N: Vector3
    moment_Nm: Vector3
    moment_arm_m: Vector3
    force_moment_Nm: Vector3
    free_couple_Nm: Vector3
    source_id: str
    authority: str


@dataclass(frozen=True)
class ResultantWrench:
    reference_point_id: str
    frame_id: str
    origin_id: str
    resultant_force_N: Vector3
    resultant_moment_Nm: Vector3
    contributions: tuple[TranslatedWrench, ...]


@dataclass(frozen=True)
class GeneralizedForceResult:
    coordinate_order: tuple[str, str, str]
    coordinate_units: tuple[str, str, str]
    generalized_force: Vector3
    J_r: Jacobian3
    J_omega: Jacobian3
    jacobian_method: str
    requested_steps: Vector3 | None
    actual_steps: Vector3 | None
    convergence_error: float | None
    virtual_work_residual: float
    authority: str


@dataclass(frozen=True)
class RoadPlane:
    frame_id: str
    origin_id: str
    reference_point_m: Vector3
    normal: Vector3
    authority: str
    model: str = "flat_rigid_four_contact"

    def __post_init__(self) -> None:
        _require_name(self.frame_id, "frame_id", ForceCoordinateFailureCode.INVALID_FRAME)
        _require_name(self.origin_id, "origin_id", ForceCoordinateFailureCode.INVALID_ORIGIN)
        _require_vector(self.reference_point_m, "reference_point_m")
        _require_vector(self.normal, "normal")
        _require_name(self.authority, "authority", ForceCoordinateFailureCode.MISSING_AUTHORITY)
        magnitude = _norm(self.normal)
        if abs(magnitude - 1.0) > 1.0e-10:
            raise ForceCoordinateError(
                ForceCoordinateFailureCode.INVALID_ROAD_NORMAL,
                f"road normal must already be unit length; magnitude={magnitude:.16g}",
            )


@dataclass(frozen=True)
class ContactCornerInput:
    corner_id: str
    point: PointReference
    normal_reaction_N: float | None = None
    active_contact: bool = True

    def __post_init__(self) -> None:
        _require_name(self.corner_id, "corner_id")
        if self.normal_reaction_N is not None and not math.isfinite(float(self.normal_reaction_N)):
            raise ForceCoordinateError(
                ForceCoordinateFailureCode.NONFINITE_INPUT,
                f"{self.corner_id} normal reaction must be finite when supplied",
            )


@dataclass(frozen=True)
class ContactCornerResult:
    corner_id: str
    contact_reference_point: PointReference
    gap_m: float
    normal_reaction_N: float | None
    active_contact: bool
    status: ContactStatus
    failure_code: ForceCoordinateFailureCode | None


@dataclass(frozen=True)
class ContactModeResult:
    status: ContactStatus
    failure_code: ForceCoordinateFailureCode | None
    corners: tuple[ContactCornerResult, ...]
    gap_tolerance_m: float
    reaction_tolerance_N: float
    model: str

    @property
    def ok(self) -> bool:
        return self.status == ContactStatus.FOUR_CONTACT_ADMISSIBLE


@dataclass(frozen=True)
class WUFRWholeVehicleAdapter:
    adapter_id: str
    configuration_id: str
    source_frame_id: str
    source_origin_id: str
    body_frame_id: str
    body_origin_id: str
    road_frame_id: str
    road_origin_id: str
    source_to_body_translation_m: Vector3
    cg_source_position_m: Vector3
    front_axle_source_position_m: Vector3
    rear_axle_source_position_m: Vector3
    front_track_m: float
    rear_track_m: float
    wheel_center_height_m: float
    contact_points_body: Mapping[str, PointReference]
    axle_points_body: Mapping[str, PointReference]
    authority: str
    provenance: tuple[tuple[str, str], ...]
    installed_authority: bool = False

    @property
    def wheelbase_m(self) -> float:
        return self.front_axle_source_position_m[0] - self.rear_axle_source_position_m[0]

    @property
    def cg_to_front_axle_m(self) -> float:
        return self.axle_points_body["front_axle"].position_m[0]

    @property
    def cg_to_rear_axle_m(self) -> float:
        return -self.axle_points_body["rear_axle"].position_m[0]


def _require_name(
    value: str,
    label: str,
    code: ForceCoordinateFailureCode = ForceCoordinateFailureCode.MISSING_AUTHORITY,
) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ForceCoordinateError(code, f"{label} must be a non-empty string")


def _require_finite(values: Iterable[float], label: str) -> None:
    if not all(math.isfinite(float(value)) for value in values):
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.NONFINITE_INPUT,
            f"{label} must be finite",
        )


def _require_vector(value: Sequence[float], label: str) -> None:
    if len(value) != 3:
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.NONFINITE_INPUT,
            f"{label} must have three components",
        )
    _require_finite(value, label)


def _add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(s: float, a: Vector3) -> Vector3:
    return (s * a[0], s * a[1], s * a[2])


def _dot(a: Vector3, b: Vector3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vector3, b: Vector3) -> Vector3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(a: Vector3) -> float:
    return math.sqrt(_dot(a, a))


def _mat_mul(a: Matrix3, b: Matrix3) -> Matrix3:
    bt = tuple(zip(*b))
    return tuple(
        tuple(sum(a[i][k] * bt[j][k] for k in range(3)) for j in range(3))
        for i in range(3)
    )  # type: ignore[return-value]


def _mat_vec(a: Matrix3, v: Vector3) -> Vector3:
    return tuple(sum(a[i][k] * v[k] for k in range(3)) for i in range(3))  # type: ignore[return-value]


def _transpose(a: Matrix3) -> Matrix3:
    return tuple(zip(*a))  # type: ignore[return-value]


def _rotation_x(angle: float) -> Matrix3:
    c, s = math.cos(angle), math.sin(angle)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def _rotation_y(angle: float) -> Matrix3:
    c, s = math.cos(angle), math.sin(angle)
    return ((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c))


def _rotation_z(angle: float) -> Matrix3:
    c, s = math.cos(angle), math.sin(angle)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def rotation_matrix_yaw_pitch_roll(
    *,
    psi_rad: float,
    theta_rad: float,
    phi_rad: float,
) -> Matrix3:
    """Return ``R_IB = Rz(psi) Ry(theta) Rx(phi)`` after finite-input checks."""
    _require_finite((psi_rad, theta_rad, phi_rad), "rotation angles")
    result = _mat_mul(
        _mat_mul(_rotation_z(psi_rad), _rotation_y(theta_rad)),
        _rotation_x(phi_rad),
    )
    should_be_identity = _mat_mul(result, _transpose(result))
    max_error = max(
        abs(should_be_identity[i][j] - (1.0 if i == j else 0.0))
        for i in range(3)
        for j in range(3)
    )
    if max_error > 1.0e-12:
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.INVALID_ROTATION,
            "rotation matrix failed orthogonality check",
        )
    return result


def transport_body_fixed_point(point: PointReference, pose: BodyPose) -> PointReference:
    """Transport one body-fixed point into the declared inertial/road frame."""
    if point.frame_id != pose.body_frame_id:
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.FRAME_MISMATCH,
            f"point frame {point.frame_id!r} does not match body frame {pose.body_frame_id!r}",
        )
    if point.origin_id != pose.body_origin_id:
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.INVALID_ORIGIN,
            f"point origin {point.origin_id!r} does not match body origin {pose.body_origin_id!r}",
        )
    if point.fixed_role != "body_fixed":
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.MISSING_TRANSFORM_AUTHORITY,
            f"point {point.point_id!r} is not declared body_fixed",
        )
    rotation = rotation_matrix_yaw_pitch_roll(
        psi_rad=pose.psi_rad,
        theta_rad=pose.theta_rad,
        phi_rad=pose.phi_rad,
    )
    origin = _add(pose.body_origin_position_m, (0.0, 0.0, pose.z_s_m))
    position = _add(origin, _mat_vec(rotation, point.position_m))
    return PointReference(
        point_id=point.point_id,
        frame_id=pose.inertial_frame_id,
        origin_id=pose.inertial_origin_id,
        position_m=position,
        role=point.role,
        source_id=point.source_id,
        configuration_id=point.configuration_id,
        authority=point.authority,
        fixed_role="road_expressed_body_fixed",
        provenance=point.provenance + (("transport", "EQ-VEH-0004"),),
    )


def _require_same_frame_origin(point: PointReference, frame_id: str, origin_id: str) -> None:
    if point.frame_id != frame_id:
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.FRAME_MISMATCH,
            f"point {point.point_id!r} frame {point.frame_id!r} does not match {frame_id!r}",
        )
    if point.origin_id != origin_id:
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.INVALID_ORIGIN,
            f"point {point.point_id!r} origin {point.origin_id!r} does not match {origin_id!r}",
        )


def translate_wrench(wrench: AppliedWrench, reference_point: PointReference) -> TranslatedWrench:
    """Translate one point-force/free-couple wrench to ``reference_point``."""
    _require_same_frame_origin(reference_point, wrench.frame_id, wrench.origin_id)
    arm = _sub(wrench.application_point.position_m, reference_point.position_m)
    force_moment = _cross(arm, wrench.force_N)
    total_moment = _add(wrench.free_couple_Nm, force_moment)
    return TranslatedWrench(
        wrench_id=wrench.wrench_id,
        reference_point_id=reference_point.point_id,
        frame_id=wrench.frame_id,
        origin_id=wrench.origin_id,
        force_N=wrench.force_N,
        moment_Nm=total_moment,
        moment_arm_m=arm,
        force_moment_Nm=force_moment,
        free_couple_Nm=wrench.free_couple_Nm,
        source_id=wrench.source_id,
        authority=wrench.authority,
    )


def assemble_wrenches(
    wrenches: Iterable[AppliedWrench],
    reference_point: PointReference,
) -> ResultantWrench:
    contributions = tuple(translate_wrench(item, reference_point) for item in wrenches)
    force = (0.0, 0.0, 0.0)
    moment = (0.0, 0.0, 0.0)
    for item in contributions:
        force = _add(force, item.force_N)
        moment = _add(moment, item.moment_Nm)
    return ResultantWrench(
        reference_point_id=reference_point.point_id,
        frame_id=reference_point.frame_id,
        origin_id=reference_point.origin_id,
        resultant_force_N=force,
        resultant_moment_Nm=moment,
        contributions=contributions,
    )


def analytical_pose_jacobians(
    point_body_m: Vector3,
    pose: BodyPose,
) -> tuple[Jacobian3, Jacobian3]:
    """Return exact local ``J_r`` and inertial angular-variation ``J_omega``.

    Rows are inertial x/y/z components and columns are ``[z_s, phi, theta]``.
    """
    _require_vector(point_body_m, "point_body_m")
    rz = _rotation_z(pose.psi_rad)
    ry = _rotation_y(pose.theta_rad)
    rx = _rotation_x(pose.phi_rad)
    rotation = _mat_mul(_mat_mul(rz, ry), rx)

    cphi, sphi = math.cos(pose.phi_rad), math.sin(pose.phi_rad)
    d_rx = ((0.0, 0.0, 0.0), (0.0, -sphi, -cphi), (0.0, cphi, -sphi))
    ctheta, stheta = math.cos(pose.theta_rad), math.sin(pose.theta_rad)
    d_ry = ((-stheta, 0.0, ctheta), (0.0, 0.0, 0.0), (-ctheta, 0.0, -stheta))

    dr_dz = (0.0, 0.0, 1.0)
    dr_dphi = _mat_vec(_mat_mul(_mat_mul(rz, ry), d_rx), point_body_m)
    dr_dtheta = _mat_vec(_mat_mul(_mat_mul(rz, d_ry), rx), point_body_m)
    j_r: Jacobian3 = (
        (dr_dz[0], dr_dphi[0], dr_dtheta[0]),
        (dr_dz[1], dr_dphi[1], dr_dtheta[1]),
        (dr_dz[2], dr_dphi[2], dr_dtheta[2]),
    )

    roll_axis_I = _mat_vec(_mat_mul(rz, ry), (1.0, 0.0, 0.0))
    pitch_axis_I = _mat_vec(rz, (0.0, 1.0, 0.0))
    j_omega: Jacobian3 = (
        (0.0, roll_axis_I[0], pitch_axis_I[0]),
        (0.0, roll_axis_I[1], pitch_axis_I[1]),
        (0.0, roll_axis_I[2], pitch_axis_I[2]),
    )
    _require_finite((rotation[0][0], rotation[1][1], rotation[2][2]), "rotation")
    return j_r, j_omega


def _jt_times_vector(jacobian: Jacobian3, vector: Vector3) -> Vector3:
    return tuple(
        sum(jacobian[row][col] * vector[row] for row in range(3))
        for col in range(3)
    )  # type: ignore[return-value]


def generalized_force_from_jacobians(
    *,
    force_N: Vector3,
    free_couple_Nm: Vector3,
    J_r: Jacobian3,
    J_omega: Jacobian3,
) -> Vector3:
    _require_vector(force_N, "force_N")
    _require_vector(free_couple_Nm, "free_couple_Nm")
    force_term = _jt_times_vector(J_r, force_N)
    couple_term = _jt_times_vector(J_omega, free_couple_Nm)
    return _add(force_term, couple_term)


def analytical_generalized_force(
    point_body: PointReference,
    pose: BodyPose,
    *,
    force_N: Vector3,
    free_couple_Nm: Vector3 = (0.0, 0.0, 0.0),
) -> GeneralizedForceResult:
    if point_body.frame_id != pose.body_frame_id or point_body.origin_id != pose.body_origin_id:
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.FRAME_MISMATCH,
            "body point and pose do not share the declared body frame/origin",
        )
    j_r, j_omega = analytical_pose_jacobians(point_body.position_m, pose)
    q = generalized_force_from_jacobians(
        force_N=force_N,
        free_couple_Nm=free_couple_Nm,
        J_r=j_r,
        J_omega=j_omega,
    )
    check = generalized_force_from_jacobians(
        force_N=force_N,
        free_couple_Nm=free_couple_Nm,
        J_r=j_r,
        J_omega=j_omega,
    )
    residual = max(abs(a - b) for a, b in zip(q, check))
    return GeneralizedForceResult(
        coordinate_order=pose.coordinate_order,
        coordinate_units=("N", "N*m", "N*m"),
        generalized_force=q,
        J_r=j_r,
        J_omega=j_omega,
        jacobian_method="analytic_yaw_pitch_roll_local_virtual_work",
        requested_steps=None,
        actual_steps=None,
        convergence_error=None,
        virtual_work_residual=residual,
        authority="AUTH-VEH-0003 synthetic/general mechanics result",
    )


def _pose_with_coordinate(pose: BodyPose, index: int, delta: float) -> BodyPose:
    values = [pose.z_s_m, pose.phi_rad, pose.theta_rad]
    values[index] += delta
    return BodyPose(
        inertial_frame_id=pose.inertial_frame_id,
        inertial_origin_id=pose.inertial_origin_id,
        body_frame_id=pose.body_frame_id,
        body_origin_id=pose.body_origin_id,
        body_origin_position_m=pose.body_origin_position_m,
        z_s_m=values[0],
        phi_rad=values[1],
        theta_rad=values[2],
        psi_rad=pose.psi_rad,
        authority=pose.authority,
    )


def _rotation_log_vector(rotation: Matrix3) -> Vector3:
    trace = rotation[0][0] + rotation[1][1] + rotation[2][2]
    cosine = max(-1.0, min(1.0, 0.5 * (trace - 1.0)))
    angle = math.acos(cosine)
    skew = (
        rotation[2][1] - rotation[1][2],
        rotation[0][2] - rotation[2][0],
        rotation[1][0] - rotation[0][1],
    )
    if angle < 1.0e-8:
        return _scale(0.5, skew)
    sine = math.sin(angle)
    if abs(sine) <= 1.0e-14:
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.JACOBIAN_UNAVAILABLE,
            "rotation-log finite difference is singular near pi radians",
        )
    return _scale(angle / (2.0 * sine), skew)


def _finite_difference_jacobians(
    point_body: PointReference,
    pose: BodyPose,
    steps: Vector3,
) -> tuple[Jacobian3, Jacobian3]:
    columns_r: list[Vector3] = []
    columns_w: list[Vector3] = []
    for index, step in enumerate(steps):
        if not math.isfinite(step) or step <= 0.0:
            raise ForceCoordinateError(
                ForceCoordinateFailureCode.JACOBIAN_UNAVAILABLE,
                "all numerical Jacobian steps must be finite and positive",
            )
        minus = _pose_with_coordinate(pose, index, -step)
        plus = _pose_with_coordinate(pose, index, step)
        p_minus = transport_body_fixed_point(point_body, minus).position_m
        p_plus = transport_body_fixed_point(point_body, plus).position_m
        columns_r.append(_scale(1.0 / (2.0 * step), _sub(p_plus, p_minus)))

        r_minus = rotation_matrix_yaw_pitch_roll(
            psi_rad=minus.psi_rad,
            theta_rad=minus.theta_rad,
            phi_rad=minus.phi_rad,
        )
        r_plus = rotation_matrix_yaw_pitch_roll(
            psi_rad=plus.psi_rad,
            theta_rad=plus.theta_rad,
            phi_rad=plus.phi_rad,
        )
        relative = _mat_mul(r_plus, _transpose(r_minus))
        columns_w.append(
            _scale(1.0 / (2.0 * step), _rotation_log_vector(relative))
        )

    j_r: Jacobian3 = tuple(
        tuple(columns_r[col][row] for col in range(3)) for row in range(3)
    )  # type: ignore[assignment]
    j_omega: Jacobian3 = tuple(
        tuple(columns_w[col][row] for col in range(3)) for row in range(3)
    )  # type: ignore[assignment]
    return j_r, j_omega


def numerical_generalized_force(
    point_body: PointReference,
    pose: BodyPose,
    *,
    force_N: Vector3,
    free_couple_Nm: Vector3 = (0.0, 0.0, 0.0),
    steps: Vector3 = (1.0e-5, 1.0e-6, 1.0e-6),
    convergence_tolerance: float = 2.0e-7,
) -> GeneralizedForceResult:
    """Centered finite-difference generalized force with an h versus h/2 check."""
    _require_vector(steps, "steps")
    if not math.isfinite(convergence_tolerance) or convergence_tolerance <= 0.0:
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.JACOBIAN_UNAVAILABLE,
            "convergence_tolerance must be finite and positive",
        )
    coarse_r, coarse_w = _finite_difference_jacobians(point_body, pose, steps)
    half_steps: Vector3 = tuple(0.5 * value for value in steps)  # type: ignore[assignment]
    fine_r, fine_w = _finite_difference_jacobians(point_body, pose, half_steps)
    coarse_q = generalized_force_from_jacobians(
        force_N=force_N,
        free_couple_Nm=free_couple_Nm,
        J_r=coarse_r,
        J_omega=coarse_w,
    )
    fine_q = generalized_force_from_jacobians(
        force_N=force_N,
        free_couple_Nm=free_couple_Nm,
        J_r=fine_r,
        J_omega=fine_w,
    )
    error = max(abs(a - b) for a, b in zip(coarse_q, fine_q))
    scale = max(1.0, *(abs(value) for value in fine_q))
    if error > convergence_tolerance * scale:
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.JACOBIAN_NOT_CONVERGED,
            f"centered Jacobian h/h2 generalized-force difference {error:.6g} exceeds "
            f"scaled tolerance {convergence_tolerance * scale:.6g}",
        )
    return GeneralizedForceResult(
        coordinate_order=pose.coordinate_order,
        coordinate_units=("N", "N*m", "N*m"),
        generalized_force=fine_q,
        J_r=fine_r,
        J_omega=fine_w,
        jacobian_method="centered_pose_difference_with_rotation_log_h_over_2",
        requested_steps=steps,
        actual_steps=half_steps,
        convergence_error=error,
        virtual_work_residual=0.0,
        authority="AUTH-VEH-0003 synthetic/general mechanics numerical check",
    )


def classify_rigid_four_contact(
    road: RoadPlane,
    contacts: Sequence[ContactCornerInput],
    *,
    gap_tolerance_m: float = 1.0e-9,
    reaction_tolerance_N: float = 1.0e-9,
) -> ContactModeResult:
    """Classify the authorized flat-road, rigid, all-four-active contact mode."""
    if road.model != "flat_rigid_four_contact":
        return ContactModeResult(
            status=ContactStatus.UNSUPPORTED_CONTACT_MODEL,
            failure_code=ForceCoordinateFailureCode.UNSUPPORTED_CONTACT_MODEL,
            corners=tuple(),
            gap_tolerance_m=gap_tolerance_m,
            reaction_tolerance_N=reaction_tolerance_N,
            model=road.model,
        )
    if len(contacts) != 4 or len({item.corner_id for item in contacts}) != 4:
        return ContactModeResult(
            status=ContactStatus.CONTACT_MODE_INVALID,
            failure_code=ForceCoordinateFailureCode.CONTACT_MODE_INVALID,
            corners=tuple(),
            gap_tolerance_m=gap_tolerance_m,
            reaction_tolerance_N=reaction_tolerance_N,
            model=road.model,
        )
    if not math.isfinite(gap_tolerance_m) or gap_tolerance_m < 0.0:
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.NONFINITE_INPUT,
            "gap_tolerance_m must be finite and nonnegative",
        )
    if not math.isfinite(reaction_tolerance_N) or reaction_tolerance_N < 0.0:
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.NONFINITE_INPUT,
            "reaction_tolerance_N must be finite and nonnegative",
        )

    corner_results: list[ContactCornerResult] = []
    aggregate_status = ContactStatus.FOUR_CONTACT_ADMISSIBLE
    aggregate_failure: ForceCoordinateFailureCode | None = None
    for item in contacts:
        try:
            _require_same_frame_origin(item.point, road.frame_id, road.origin_id)
        except ForceCoordinateError:
            return ContactModeResult(
                status=ContactStatus.MISSING_AUTHORITY,
                failure_code=ForceCoordinateFailureCode.FRAME_MISMATCH,
                corners=tuple(corner_results),
                gap_tolerance_m=gap_tolerance_m,
                reaction_tolerance_N=reaction_tolerance_N,
                model=road.model,
            )
        gap = _dot(road.normal, _sub(item.point.position_m, road.reference_point_m))
        reaction = None if item.normal_reaction_N is None else float(item.normal_reaction_N)
        status = ContactStatus.FOUR_CONTACT_ADMISSIBLE
        failure: ForceCoordinateFailureCode | None = None
        if not item.active_contact:
            status = ContactStatus.CONTACT_MODE_INVALID
            failure = ForceCoordinateFailureCode.CONTACT_MODE_INVALID
        elif gap > gap_tolerance_m:
            status = ContactStatus.OPEN_GAP
            failure = ForceCoordinateFailureCode.OPEN_CONTACT_GAP
        elif gap < -gap_tolerance_m:
            status = ContactStatus.PENETRATION
            failure = ForceCoordinateFailureCode.PENETRATING_CONTACT_REFERENCE
        elif reaction is not None and reaction < -reaction_tolerance_N:
            status = ContactStatus.WHEEL_LIFT
            failure = ForceCoordinateFailureCode.NEGATIVE_NORMAL_REACTION

        corner_results.append(
            ContactCornerResult(
                corner_id=item.corner_id,
                contact_reference_point=item.point,
                gap_m=gap,
                normal_reaction_N=reaction,
                active_contact=item.active_contact,
                status=status,
                failure_code=failure,
            )
        )
        if status == ContactStatus.WHEEL_LIFT:
            aggregate_status = ContactStatus.WHEEL_LIFT
            aggregate_failure = ForceCoordinateFailureCode.CONTACT_MODE_INVALID
        elif (
            status != ContactStatus.FOUR_CONTACT_ADMISSIBLE
            and aggregate_status == ContactStatus.FOUR_CONTACT_ADMISSIBLE
        ):
            aggregate_status = status
            aggregate_failure = failure

    return ContactModeResult(
        status=aggregate_status,
        failure_code=aggregate_failure,
        corners=tuple(corner_results),
        gap_tolerance_m=gap_tolerance_m,
        reaction_tolerance_N=reaction_tolerance_N,
        model=road.model,
    )


def _point_from_body(
    adapter: Mapping[str, object],
    point_id: str,
    position: Vector3,
    role: str,
    source_id: str,
    authority: str,
) -> PointReference:
    return PointReference(
        point_id=point_id,
        frame_id=str(adapter["body_frame_id"]),
        origin_id=str(adapter["body_origin_id"]),
        position_m=position,
        role=role,
        source_id=source_id,
        configuration_id=str(adapter["configuration_id"]),
        authority=authority,
        fixed_role="body_fixed",
    )


def load_wufr_whole_vehicle_adapter(path: str | Path) -> WUFRWholeVehicleAdapter:
    """Load the reviewed WUFR-26/27 whole-vehicle design-intent adapter.

    This loader uses only values explicitly frozen in the adapter file.  It does
    not infer a rear translation from wheelbase, construct a CG from unrelated
    fields, or upgrade the data to installed/as-built authority.
    """
    with Path(path).open("rb") as stream:
        data = tomllib.load(stream)
    if data.get("adapter_id") != "WUFR26_WHOLE_VEHICLE_FRAME_V0":
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.MISSING_AUTHORITY,
            "unexpected WUFR adapter_id",
        )
    frame = data["frame"]
    cg = data["cg_reference"]
    geometry = data["geometry"]
    authority = data["authority_boundaries"]
    if authority.get("installed_authority", False):
        raise ForceCoordinateError(
            ForceCoordinateFailureCode.MISSING_AUTHORITY,
            "this design-intent adapter must not claim installed authority",
        )

    cg_source: Vector3 = tuple(float(x) for x in cg["source_position_m"])  # type: ignore[assignment]
    front_source: Vector3 = tuple(
        float(x) for x in geometry["front_axle_source_position_m"]
    )  # type: ignore[assignment]
    rear_source: Vector3 = tuple(
        float(x) for x in geometry["rear_axle_source_position_m"]
    )  # type: ignore[assignment]
    _require_vector(cg_source, "cg source position")
    _require_vector(front_source, "front axle source position")
    _require_vector(rear_source, "rear axle source position")
    translation = _scale(-1.0, cg_source)

    adapter_meta: dict[str, object] = {
        "body_frame_id": frame["body_frame_id"],
        "body_origin_id": frame["body_origin_id"],
        "configuration_id": data["configuration_id"],
    }
    source_id = str(data["source_record_id"])
    point_authority = str(authority["whole_vehicle_placement"])
    front_body = _add(front_source, translation)
    rear_body = _add(rear_source, translation)
    axle_points = {
        "front_axle": _point_from_body(
            adapter_meta,
            "front_axle_center",
            front_body,
            "axle_center",
            source_id,
            point_authority,
        ),
        "rear_axle": _point_from_body(
            adapter_meta,
            "rear_axle_center",
            rear_body,
            "axle_center",
            source_id,
            point_authority,
        ),
    }

    front_half = 0.5 * float(geometry["front_track_m"])
    rear_half = 0.5 * float(geometry["rear_track_m"])
    contact_source = {
        "front_left": (
            front_source[0],
            front_half,
            float(geometry["road_plane_z_source_m"]),
        ),
        "front_right": (
            front_source[0],
            -front_half,
            float(geometry["road_plane_z_source_m"]),
        ),
        "rear_left": (
            rear_source[0],
            rear_half,
            float(geometry["road_plane_z_source_m"]),
        ),
        "rear_right": (
            rear_source[0],
            -rear_half,
            float(geometry["road_plane_z_source_m"]),
        ),
    }
    contacts = {
        corner: _point_from_body(
            adapter_meta,
            f"{corner}_contact_reference",
            _add(position, translation),
            "rigid_tire_contact_reference",
            source_id,
            str(authority["contact_reference"]),
        )
        for corner, position in contact_source.items()
    }
    provenance = tuple(
        sorted((str(k), str(v)) for k, v in data["provenance"].items())
    )
    return WUFRWholeVehicleAdapter(
        adapter_id=str(data["adapter_id"]),
        configuration_id=str(data["configuration_id"]),
        source_frame_id=str(frame["source_frame_id"]),
        source_origin_id=str(frame["source_origin_id"]),
        body_frame_id=str(frame["body_frame_id"]),
        body_origin_id=str(frame["body_origin_id"]),
        road_frame_id=str(frame["road_frame_id"]),
        road_origin_id=str(frame["road_origin_id"]),
        source_to_body_translation_m=translation,
        cg_source_position_m=cg_source,
        front_axle_source_position_m=front_source,
        rear_axle_source_position_m=rear_source,
        front_track_m=float(geometry["front_track_m"]),
        rear_track_m=float(geometry["rear_track_m"]),
        wheel_center_height_m=float(geometry["wheel_center_height_m"]),
        contact_points_body=contacts,
        axle_points_body=axle_points,
        authority=point_authority,
        provenance=provenance,
        installed_authority=False,
    )


def road_plane_from_wufr_adapter(adapter: WUFRWholeVehicleAdapter) -> RoadPlane:
    """Return the nominal road plane expressed in the adapter's CG/body frame."""
    z_road_body = -adapter.cg_source_position_m[2]
    return RoadPlane(
        frame_id=adapter.body_frame_id,
        origin_id=adapter.body_origin_id,
        reference_point_m=(0.0, 0.0, z_road_body),
        normal=(0.0, 0.0, 1.0),
        authority="design-intent flat-road datum from WUFR26_WHOLE_VEHICLE_FRAME_V0",
    )
