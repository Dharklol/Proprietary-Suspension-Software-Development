"""Ideal-revolute rocker included-load reaction contribution.

Implements ``EQ-SUSP-0029`` through ``EQ-SUSP-0031`` under
``AUTH-SUSP-0016``.  The result is deliberately limited to the explicitly
named point-load set.  It is not a complete rocker equilibrium or total pivot
reaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Sequence

Point3 = tuple[float, float, float]


class RockerIncludedLoadStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class RockerIncludedLoadFailureCode(str, Enum):
    EMPTY_INCLUDED_SET = "empty_included_set"
    NONFINITE_INPUT = "nonfinite_input"
    MISSING_LOAD_IDENTITY = "missing_load_identity"
    DUPLICATE_LOAD_IDENTITY = "duplicate_load_identity"
    LOAD_SET_IDENTITY_CONFLICT = "load_set_identity_conflict"
    FRAME_MISMATCH = "frame_mismatch"
    CONFIGURATION_MISMATCH = "configuration_mismatch"
    LOAD_CASE_MISMATCH = "load_case_mismatch"
    DEGENERATE_ROCKER_AXIS = "degenerate_rocker_axis"
    FORCE_RESIDUAL_EXCEEDED = "force_residual_exceeded"
    MOMENT_RESIDUAL_EXCEEDED = "moment_residual_exceeded"
    SUPPORT_AXIS_MOMENT_VIOLATION = "support_axis_moment_violation"


@dataclass(frozen=True)
class RockerIncludedLoadConfig:
    axis_norm_absolute_threshold: float = 1.0e-12
    force_residual_tolerance_N: float = 1.0e-10
    perpendicular_moment_residual_tolerance_Nm: float = 1.0e-10
    support_axis_moment_tolerance_Nm: float = 1.0e-10

    def __post_init__(self) -> None:
        values = tuple(float(value) for value in self.__dict__.values())
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError("Rocker included-load tolerances must be finite and positive")


@dataclass(frozen=True)
class RockerPointLoad:
    load_id: str
    application_point_m: Point3
    force_N: Point3
    source_id: str
    frame_id: str
    configuration_id: str
    load_case_id: str


@dataclass(frozen=True)
class RockerIncludedLoadResult:
    status: RockerIncludedLoadStatus
    frame_id: str = ""
    configuration_id: str = ""
    load_case_id: str = ""
    axle: str = ""
    side: str = ""
    rocker_pivot_m: Point3 | None = None
    rocker_axis_unit: Point3 | None = None
    included_load_ids: tuple[str, ...] = ()
    missing_load_ids: tuple[str, ...] = ()
    included_loads: tuple[RockerPointLoad, ...] = ()
    included_resultant_force_N: Point3 | None = None
    included_resultant_moment_Nm: Point3 | None = None
    pivot_force_contribution_N: Point3 | None = None
    pivot_moment_contribution_Nm: Point3 | None = None
    free_axis_moment_residual_Nm: float | None = None
    final_force_residual_N: Point3 | None = None
    final_moment_residual_Nm: Point3 | None = None
    perpendicular_moment_residual_Nm: Point3 | None = None
    support_axis_moment_component_Nm: float | None = None
    force_residual_inf_norm_N: float | None = None
    perpendicular_moment_residual_inf_norm_Nm: float | None = None
    complete_hardware_reaction: bool = False
    authorization_id: str = "AUTH-SUSP-0016"
    assumption_id: str = "ASM-SUSP-0008"
    failure_code: RockerIncludedLoadFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is RockerIncludedLoadStatus.SUCCESS

    @property
    def included_set_balances_about_free_axis(self) -> bool:
        return self.ok and self.free_axis_moment_residual_Nm == 0.0


def _p(values: Sequence[float]) -> Point3:
    if len(values) != 3:
        raise ValueError("Expected a three-component vector")
    return (float(values[0]), float(values[1]), float(values[2]))


def _finite3(values: Sequence[float]) -> bool:
    return len(values) == 3 and all(math.isfinite(float(value)) for value in values)


def _add(a: Point3, b: Point3) -> Point3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Point3, b: Point3) -> Point3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(scalar: float, vector: Point3) -> Point3:
    return (scalar * vector[0], scalar * vector[1], scalar * vector[2])


def _dot(a: Point3, b: Point3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Point3, b: Point3) -> Point3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(vector: Point3) -> float:
    return math.sqrt(_dot(vector, vector))


def _unit(vector: Point3, tolerance: float) -> Point3 | None:
    magnitude = _norm(vector)
    if not math.isfinite(magnitude) or magnitude <= tolerance:
        return None
    return _scale(1.0 / magnitude, vector)


def _inf_norm(vector: Point3) -> float:
    return max(abs(value) for value in vector)


def _failure(
    code: RockerIncludedLoadFailureCode,
    message: str,
    *,
    frame_id: str,
    configuration_id: str,
    load_case_id: str,
    axle: str,
    side: str,
    pivot: Point3 | None = None,
    axis: Point3 | None = None,
    included_loads: tuple[RockerPointLoad, ...] = (),
    missing_load_ids: tuple[str, ...] = (),
) -> RockerIncludedLoadResult:
    return RockerIncludedLoadResult(
        status=RockerIncludedLoadStatus.FAILURE,
        frame_id=frame_id,
        configuration_id=configuration_id,
        load_case_id=load_case_id,
        axle=axle,
        side=side,
        rocker_pivot_m=pivot,
        rocker_axis_unit=axis,
        included_load_ids=tuple(load.load_id for load in included_loads),
        missing_load_ids=missing_load_ids,
        included_loads=included_loads,
        complete_hardware_reaction=False,
        failure_code=code,
        message=message,
    )


def evaluate_rocker_included_load(
    *,
    rocker_pivot_m: Point3,
    rocker_axis: Point3,
    loads: Sequence[RockerPointLoad],
    missing_load_ids: Sequence[str],
    frame_id: str,
    configuration_id: str,
    load_case_id: str,
    axle: str = "",
    side: str = "",
    config: RockerIncludedLoadConfig | None = None,
) -> RockerIncludedLoadResult:
    """Evaluate the exact ideal-support contribution for a named load subset."""
    cfg = config or RockerIncludedLoadConfig()
    included = tuple(loads)
    missing = tuple(str(value) for value in missing_load_ids)

    if not included:
        return _failure(
            RockerIncludedLoadFailureCode.EMPTY_INCLUDED_SET,
            "At least one physical point load is required",
            frame_id=frame_id,
            configuration_id=configuration_id,
            load_case_id=load_case_id,
            axle=axle,
            side=side,
            missing_load_ids=missing,
        )
    if not _finite3(rocker_pivot_m) or not _finite3(rocker_axis):
        return _failure(
            RockerIncludedLoadFailureCode.NONFINITE_INPUT,
            "Rocker pivot and axis must be finite three-component vectors",
            frame_id=frame_id,
            configuration_id=configuration_id,
            load_case_id=load_case_id,
            axle=axle,
            side=side,
            included_loads=included,
            missing_load_ids=missing,
        )

    pivot = _p(rocker_pivot_m)
    axis = _unit(_p(rocker_axis), cfg.axis_norm_absolute_threshold)
    if axis is None:
        return _failure(
            RockerIncludedLoadFailureCode.DEGENERATE_ROCKER_AXIS,
            "Rocker axis is degenerate",
            frame_id=frame_id,
            configuration_id=configuration_id,
            load_case_id=load_case_id,
            axle=axle,
            side=side,
            pivot=pivot,
            included_loads=included,
            missing_load_ids=missing,
        )

    ids = tuple(load.load_id for load in included)
    if any(not value for value in (*ids, *missing)) or any(not load.source_id for load in included):
        return _failure(
            RockerIncludedLoadFailureCode.MISSING_LOAD_IDENTITY,
            "Every included/missing load and included source must have a nonempty identity",
            frame_id=frame_id,
            configuration_id=configuration_id,
            load_case_id=load_case_id,
            axle=axle,
            side=side,
            pivot=pivot,
            axis=axis,
            included_loads=included,
            missing_load_ids=missing,
        )
    if len(set(ids)) != len(ids) or len(set(missing)) != len(missing):
        return _failure(
            RockerIncludedLoadFailureCode.DUPLICATE_LOAD_IDENTITY,
            "Included and missing load identities must each be unique",
            frame_id=frame_id,
            configuration_id=configuration_id,
            load_case_id=load_case_id,
            axle=axle,
            side=side,
            pivot=pivot,
            axis=axis,
            included_loads=included,
            missing_load_ids=missing,
        )
    if set(ids).intersection(missing):
        return _failure(
            RockerIncludedLoadFailureCode.LOAD_SET_IDENTITY_CONFLICT,
            "A load identity cannot be both included and missing",
            frame_id=frame_id,
            configuration_id=configuration_id,
            load_case_id=load_case_id,
            axle=axle,
            side=side,
            pivot=pivot,
            axis=axis,
            included_loads=included,
            missing_load_ids=missing,
        )

    for load in included:
        if not _finite3(load.application_point_m) or not _finite3(load.force_N):
            return _failure(
                RockerIncludedLoadFailureCode.NONFINITE_INPUT,
                f"Load {load.load_id} point and force must be finite",
                frame_id=frame_id,
                configuration_id=configuration_id,
                load_case_id=load_case_id,
                axle=axle,
                side=side,
                pivot=pivot,
                axis=axis,
                included_loads=included,
                missing_load_ids=missing,
            )
        if load.frame_id != frame_id:
            return _failure(
                RockerIncludedLoadFailureCode.FRAME_MISMATCH,
                f"Load {load.load_id} frame does not match rocker frame",
                frame_id=frame_id,
                configuration_id=configuration_id,
                load_case_id=load_case_id,
                axle=axle,
                side=side,
                pivot=pivot,
                axis=axis,
                included_loads=included,
                missing_load_ids=missing,
            )
        if load.configuration_id != configuration_id:
            return _failure(
                RockerIncludedLoadFailureCode.CONFIGURATION_MISMATCH,
                f"Load {load.load_id} configuration does not match rocker configuration",
                frame_id=frame_id,
                configuration_id=configuration_id,
                load_case_id=load_case_id,
                axle=axle,
                side=side,
                pivot=pivot,
                axis=axis,
                included_loads=included,
                missing_load_ids=missing,
            )
        if load.load_case_id != load_case_id:
            return _failure(
                RockerIncludedLoadFailureCode.LOAD_CASE_MISMATCH,
                f"Load {load.load_id} load-case identity does not match",
                frame_id=frame_id,
                configuration_id=configuration_id,
                load_case_id=load_case_id,
                axle=axle,
                side=side,
                pivot=pivot,
                axis=axis,
                included_loads=included,
                missing_load_ids=missing,
            )

    resultant_force: Point3 = (0.0, 0.0, 0.0)
    resultant_moment: Point3 = (0.0, 0.0, 0.0)
    for load in included:
        point = _p(load.application_point_m)
        force = _p(load.force_N)
        resultant_force = _add(resultant_force, force)
        resultant_moment = _add(resultant_moment, _cross(_sub(point, pivot), force))

    tau_axis = _dot(axis, resultant_moment)
    pivot_force = _scale(-1.0, resultant_force)
    moment_perpendicular = _sub(resultant_moment, _scale(tau_axis, axis))
    pivot_moment = _scale(-1.0, moment_perpendicular)

    force_residual = _add(resultant_force, pivot_force)
    moment_residual = _add(resultant_moment, pivot_moment)
    residual_axis_component = _dot(axis, moment_residual)
    perpendicular_residual = _sub(moment_residual, _scale(residual_axis_component, axis))
    support_axis_component = _dot(axis, pivot_moment)
    force_inf = _inf_norm(force_residual)
    perpendicular_inf = _inf_norm(perpendicular_residual)

    if force_inf > cfg.force_residual_tolerance_N:
        return _failure(
            RockerIncludedLoadFailureCode.FORCE_RESIDUAL_EXCEEDED,
            "Ideal support force residual exceeds tolerance",
            frame_id=frame_id,
            configuration_id=configuration_id,
            load_case_id=load_case_id,
            axle=axle,
            side=side,
            pivot=pivot,
            axis=axis,
            included_loads=included,
            missing_load_ids=missing,
        )
    if perpendicular_inf > cfg.perpendicular_moment_residual_tolerance_Nm:
        return _failure(
            RockerIncludedLoadFailureCode.MOMENT_RESIDUAL_EXCEEDED,
            "Ideal support perpendicular-moment residual exceeds tolerance",
            frame_id=frame_id,
            configuration_id=configuration_id,
            load_case_id=load_case_id,
            axle=axle,
            side=side,
            pivot=pivot,
            axis=axis,
            included_loads=included,
            missing_load_ids=missing,
        )
    if abs(support_axis_component) > cfg.support_axis_moment_tolerance_Nm:
        return _failure(
            RockerIncludedLoadFailureCode.SUPPORT_AXIS_MOMENT_VIOLATION,
            "Ideal revolute support moment contains a forbidden axis component",
            frame_id=frame_id,
            configuration_id=configuration_id,
            load_case_id=load_case_id,
            axle=axle,
            side=side,
            pivot=pivot,
            axis=axis,
            included_loads=included,
            missing_load_ids=missing,
        )

    return RockerIncludedLoadResult(
        status=RockerIncludedLoadStatus.SUCCESS,
        frame_id=frame_id,
        configuration_id=configuration_id,
        load_case_id=load_case_id,
        axle=axle,
        side=side,
        rocker_pivot_m=pivot,
        rocker_axis_unit=axis,
        included_load_ids=ids,
        missing_load_ids=missing,
        included_loads=included,
        included_resultant_force_N=resultant_force,
        included_resultant_moment_Nm=resultant_moment,
        pivot_force_contribution_N=pivot_force,
        pivot_moment_contribution_Nm=pivot_moment,
        free_axis_moment_residual_Nm=tau_axis,
        final_force_residual_N=force_residual,
        final_moment_residual_Nm=moment_residual,
        perpendicular_moment_residual_Nm=perpendicular_residual,
        support_axis_moment_component_Nm=support_axis_component,
        force_residual_inf_norm_N=force_inf,
        perpendicular_moment_residual_inf_norm_Nm=perpendicular_inf,
        complete_hardware_reaction=False,
    )
