"""Physical spring-only force vector at the WUFR direct-coilover rocker eye.

Implements ``EQ-SUSP-0028`` under ``AUTH-SUSP-0014``.  The constitutive spring
law remains owned by :mod:`pssd_suspension.spring_force`; this module only maps
the already-reviewed compression-force magnitude onto the exact current
chassis-eye/rocker-eye line and verifies its rocker-axis virtual-work identity.

No damper gas/velocity/friction/stop force, rocker equilibrium, pivot reaction,
ARB composition, stress, or installed/as-built authority is introduced here.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Sequence

from .actuation import ActuationStateResult
from .geometry import Point3, SuspensionCornerGeometry
from .spring_force import SpringStateResult


class WufrSpringRockerForceStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class WufrSpringRockerForceFailureCode(str, Enum):
    UPSTREAM_ACTUATION_FAILURE = "upstream_actuation_failure"
    UPSTREAM_SPRING_FAILURE = "upstream_spring_failure"
    SOURCE_MISMATCH = "source_mismatch"
    NONFINITE_GEOMETRY = "nonfinite_geometry"
    NEGATIVE_SPRING_FORCE = "negative_spring_force"
    DEGENERATE_EYE_LINE = "degenerate_eye_line"
    DEGENERATE_ROCKER_AXIS = "degenerate_rocker_axis"
    EYE_LENGTH_MISMATCH = "eye_length_mismatch"
    ACTION_REACTION_RESIDUAL = "action_reaction_residual"
    ROCKER_TORQUE_IDENTITY_MISMATCH = "rocker_torque_identity_mismatch"


@dataclass(frozen=True)
class WufrSpringRockerForceConfig:
    eye_length_tolerance_m: float = 1.0e-12
    rocker_axis_tolerance_m: float = 1.0e-12
    eye_length_consistency_tolerance_m: float = 1.0e-9
    action_reaction_tolerance_N: float = 1.0e-10
    rocker_torque_identity_tolerance_Nm: float = 1.0e-10

    def __post_init__(self) -> None:
        values = (
            self.eye_length_tolerance_m,
            self.rocker_axis_tolerance_m,
            self.eye_length_consistency_tolerance_m,
            self.action_reaction_tolerance_N,
            self.rocker_torque_identity_tolerance_Nm,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError("Spring rocker-force tolerances must be finite and positive")


@dataclass(frozen=True)
class WufrSpringRockerForceResult:
    status: WufrSpringRockerForceStatus
    axle: str = ""
    side: str = ""
    spring_id: str = ""
    spring_source_id: str = ""
    configuration_id: str = ""
    assumption_ids: tuple[str, ...] = ()
    chassis_eye_m: Point3 | None = None
    rocker_eye_m: Point3 | None = None
    rocker_pivot_m: Point3 | None = None
    rocker_axis_unit: Point3 | None = None
    eye_to_eye_length_m: float | None = None
    chassis_to_rocker_unit: Point3 | None = None
    spring_force_magnitude_N: float | None = None
    force_on_rocker_N: Point3 | None = None
    force_on_chassis_N: Point3 | None = None
    rocker_axis_torque_Nm: float | None = None
    dL_dtheta_m_per_rad: float | None = None
    generalized_rocker_torque_from_virtual_work_Nm: float | None = None
    action_reaction_residual_N: Point3 | None = None
    action_reaction_inf_norm_N: float | None = None
    rocker_torque_identity_residual_Nm: float | None = None
    spring_only: bool = True
    installed_as_built_authority: bool = False
    authorization_id: str = "AUTH-SUSP-0014"
    assumption_id: str = "ASM-SUSP-0007"
    failure_code: WufrSpringRockerForceFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WufrSpringRockerForceStatus.SUCCESS


def _p(values: Sequence[float]) -> Point3:
    if len(values) != 3:
        raise ValueError("Expected a three-component Cartesian vector")
    return (float(values[0]), float(values[1]), float(values[2]))


def _finite3(values: Sequence[float]) -> bool:
    return len(values) == 3 and all(math.isfinite(float(value)) for value in values)


def _add(a: Point3, b: Point3) -> Point3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Point3, b: Point3) -> Point3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(scalar: float, a: Point3) -> Point3:
    return (scalar * a[0], scalar * a[1], scalar * a[2])


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


def _unit(a: Point3, *, tolerance: float) -> Point3 | None:
    magnitude = _norm(a)
    if not math.isfinite(magnitude) or magnitude <= tolerance:
        return None
    return _scale(1.0 / magnitude, a)


def _inf3(a: Point3) -> float:
    return max(abs(value) for value in a)


def _failure(
    code: WufrSpringRockerForceFailureCode,
    message: str,
    *,
    axle: str = "",
    side: str = "",
    spring_id: str = "",
    spring_source_id: str = "",
    configuration_id: str = "",
    assumption_ids: tuple[str, ...] = (),
    chassis_eye_m: Point3 | None = None,
    rocker_eye_m: Point3 | None = None,
    rocker_pivot_m: Point3 | None = None,
    spring_force_magnitude_N: float | None = None,
) -> WufrSpringRockerForceResult:
    return WufrSpringRockerForceResult(
        status=WufrSpringRockerForceStatus.FAILURE,
        axle=axle,
        side=side,
        spring_id=spring_id,
        spring_source_id=spring_source_id,
        configuration_id=configuration_id,
        assumption_ids=assumption_ids,
        chassis_eye_m=chassis_eye_m,
        rocker_eye_m=rocker_eye_m,
        rocker_pivot_m=rocker_pivot_m,
        spring_force_magnitude_N=spring_force_magnitude_N,
        installed_as_built_authority=False,
        failure_code=code,
        message=message,
    )


def physical_spring_force_at_rocker(
    *,
    chassis_eye_m: Point3,
    rocker_eye_m: Point3,
    rocker_pivot_m: Point3,
    rocker_axis: Point3,
    spring_force_magnitude_N: float,
    axle: str = "",
    side: str = "",
    spring_id: str = "",
    spring_source_id: str = "",
    configuration_id: str = "",
    assumption_ids: Sequence[str] = (),
    config: WufrSpringRockerForceConfig | None = None,
) -> WufrSpringRockerForceResult:
    """Evaluate EQ-SUSP-0028 directly from current physical geometry."""
    cfg = config or WufrSpringRockerForceConfig()
    assumptions = tuple(assumption_ids)
    vectors = (chassis_eye_m, rocker_eye_m, rocker_pivot_m, rocker_axis)
    if not all(_finite3(vector) for vector in vectors) or not math.isfinite(spring_force_magnitude_N):
        return _failure(
            WufrSpringRockerForceFailureCode.NONFINITE_GEOMETRY,
            "Spring force and all current eye/pivot/axis vectors must be finite",
            axle=axle,
            side=side,
            spring_id=spring_id,
            spring_source_id=spring_source_id,
            configuration_id=configuration_id,
            assumption_ids=assumptions,
        )
    if spring_force_magnitude_N < 0.0:
        return _failure(
            WufrSpringRockerForceFailureCode.NEGATIVE_SPRING_FORCE,
            "MOD-SUSP-0004 spring compression-force magnitude must be nonnegative and is not clipped",
            axle=axle,
            side=side,
            spring_id=spring_id,
            spring_source_id=spring_source_id,
            configuration_id=configuration_id,
            assumption_ids=assumptions,
            spring_force_magnitude_N=spring_force_magnitude_N,
        )

    chassis = _p(chassis_eye_m)
    rocker = _p(rocker_eye_m)
    pivot = _p(rocker_pivot_m)
    eye_vector = _sub(rocker, chassis)
    eye_length = _norm(eye_vector)
    eye_unit = _unit(eye_vector, tolerance=cfg.eye_length_tolerance_m)
    if eye_unit is None:
        return _failure(
            WufrSpringRockerForceFailureCode.DEGENERATE_EYE_LINE,
            "Current chassis and rocker spring eyes are coincident/degenerate",
            axle=axle,
            side=side,
            spring_id=spring_id,
            spring_source_id=spring_source_id,
            configuration_id=configuration_id,
            assumption_ids=assumptions,
            chassis_eye_m=chassis,
            rocker_eye_m=rocker,
            rocker_pivot_m=pivot,
            spring_force_magnitude_N=spring_force_magnitude_N,
        )
    axis = _unit(_p(rocker_axis), tolerance=cfg.rocker_axis_tolerance_m)
    if axis is None:
        return _failure(
            WufrSpringRockerForceFailureCode.DEGENERATE_ROCKER_AXIS,
            "Rocker axis is degenerate",
            axle=axle,
            side=side,
            spring_id=spring_id,
            spring_source_id=spring_source_id,
            configuration_id=configuration_id,
            assumption_ids=assumptions,
            chassis_eye_m=chassis,
            rocker_eye_m=rocker,
            rocker_pivot_m=pivot,
            spring_force_magnitude_N=spring_force_magnitude_N,
        )

    force_rocker = _scale(spring_force_magnitude_N, eye_unit)
    force_chassis = _scale(-1.0, force_rocker)
    action_reaction = _add(force_rocker, force_chassis)
    action_reaction_inf = _inf3(action_reaction)
    if action_reaction_inf > cfg.action_reaction_tolerance_N:
        return _failure(
            WufrSpringRockerForceFailureCode.ACTION_REACTION_RESIDUAL,
            "Spring eye-force action/reaction residual exceeds tolerance",
            axle=axle,
            side=side,
            spring_id=spring_id,
            spring_source_id=spring_source_id,
            configuration_id=configuration_id,
            assumption_ids=assumptions,
            chassis_eye_m=chassis,
            rocker_eye_m=rocker,
            rocker_pivot_m=pivot,
            spring_force_magnitude_N=spring_force_magnitude_N,
        )

    rocker_radius = _sub(rocker, pivot)
    torque = _dot(axis, _cross(rocker_radius, force_rocker))
    point_velocity_per_rad = _cross(axis, rocker_radius)
    dL_dtheta = _dot(eye_unit, point_velocity_per_rad)
    virtual_work_torque = spring_force_magnitude_N * dL_dtheta
    torque_residual = torque - virtual_work_torque
    if abs(torque_residual) > cfg.rocker_torque_identity_tolerance_Nm:
        return _failure(
            WufrSpringRockerForceFailureCode.ROCKER_TORQUE_IDENTITY_MISMATCH,
            "Physical rocker spring torque does not match exact eye-length virtual work",
            axle=axle,
            side=side,
            spring_id=spring_id,
            spring_source_id=spring_source_id,
            configuration_id=configuration_id,
            assumption_ids=assumptions,
            chassis_eye_m=chassis,
            rocker_eye_m=rocker,
            rocker_pivot_m=pivot,
            spring_force_magnitude_N=spring_force_magnitude_N,
        )

    return WufrSpringRockerForceResult(
        status=WufrSpringRockerForceStatus.SUCCESS,
        axle=axle,
        side=side,
        spring_id=spring_id,
        spring_source_id=spring_source_id,
        configuration_id=configuration_id,
        assumption_ids=assumptions,
        chassis_eye_m=chassis,
        rocker_eye_m=rocker,
        rocker_pivot_m=pivot,
        rocker_axis_unit=axis,
        eye_to_eye_length_m=eye_length,
        chassis_to_rocker_unit=eye_unit,
        spring_force_magnitude_N=spring_force_magnitude_N,
        force_on_rocker_N=force_rocker,
        force_on_chassis_N=force_chassis,
        rocker_axis_torque_Nm=torque,
        dL_dtheta_m_per_rad=dL_dtheta,
        generalized_rocker_torque_from_virtual_work_Nm=virtual_work_torque,
        action_reaction_residual_N=action_reaction,
        action_reaction_inf_norm_N=action_reaction_inf,
        rocker_torque_identity_residual_Nm=torque_residual,
        spring_only=True,
        installed_as_built_authority=False,
    )


def recover_wufr_spring_rocker_force(
    corner: SuspensionCornerGeometry,
    actuation_state: ActuationStateResult,
    spring_state: SpringStateResult,
    *,
    config: WufrSpringRockerForceConfig | None = None,
) -> WufrSpringRockerForceResult:
    """Compose successful MOD-SUSP-0003 and MOD-SUSP-0004 states under AUTH-SUSP-0014."""
    cfg = config or WufrSpringRockerForceConfig()
    axle = corner.axle.value
    side = corner.side.value
    provenance = dict(
        axle=axle,
        side=side,
        spring_id=spring_state.spring_id,
        spring_source_id=spring_state.source_id,
        configuration_id=spring_state.configuration_id,
        assumption_ids=tuple(dict.fromkeys((*spring_state.assumption_ids, "ASM-SUSP-0007"))),
    )
    if not actuation_state.ok or actuation_state.rocker_coilover_point_m is None:
        return _failure(
            WufrSpringRockerForceFailureCode.UPSTREAM_ACTUATION_FAILURE,
            actuation_state.message or "MOD-SUSP-0003 actuation state is unavailable",
            **provenance,
        )
    if not spring_state.ok or spring_state.force_N is None:
        return _failure(
            WufrSpringRockerForceFailureCode.UPSTREAM_SPRING_FAILURE,
            spring_state.message or "MOD-SUSP-0004 spring state is unavailable",
            **provenance,
        )
    if actuation_state.axle is not corner.axle or actuation_state.side != side:
        return _failure(
            WufrSpringRockerForceFailureCode.SOURCE_MISMATCH,
            "Corner and actuation state identities do not match",
            **provenance,
        )
    if (
        not actuation_state.configuration_id
        or actuation_state.configuration_id != spring_state.configuration_id
    ):
        return _failure(
            WufrSpringRockerForceFailureCode.SOURCE_MISMATCH,
            "Actuation and spring configuration identities do not match",
            **provenance,
        )

    chassis_eye = corner.actuation.chassis_attachment.position_m
    rocker_eye = actuation_state.rocker_coilover_point_m
    current_length = _norm(_sub(rocker_eye, chassis_eye))
    if (
        spring_state.current_coilover_length_m is None
        or not math.isfinite(spring_state.current_coilover_length_m)
        or abs(current_length - spring_state.current_coilover_length_m)
        > cfg.eye_length_consistency_tolerance_m
    ):
        return _failure(
            WufrSpringRockerForceFailureCode.EYE_LENGTH_MISMATCH,
            "Spring state coilover length does not match current MOD-SUSP-0003 eye geometry",
            chassis_eye_m=chassis_eye,
            rocker_eye_m=rocker_eye,
            rocker_pivot_m=corner.actuation.rocker_pivot.position_m,
            spring_force_magnitude_N=spring_state.force_N,
            **provenance,
        )

    rocker_axis = _sub(
        corner.actuation.rocker_axis_reference.position_m,
        corner.actuation.rocker_pivot.position_m,
    )
    return physical_spring_force_at_rocker(
        chassis_eye_m=chassis_eye,
        rocker_eye_m=rocker_eye,
        rocker_pivot_m=corner.actuation.rocker_pivot.position_m,
        rocker_axis=rocker_axis,
        spring_force_magnitude_N=spring_state.force_N,
        config=cfg,
        **provenance,
    )
