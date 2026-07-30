"""Atomic four-corner WUFR static Level-1 interface-load composition.

Authorized by ``AUTH-SUSP-0017``. This module is intentionally thin: it
validates synchronized per-corner geometry and complete carrier wrenches, then
invokes the unchanged ``MOD-SUSP-0007`` solver exactly once for each corner.
It adds no force law, load redistribution, sign repair, or partial-publication
fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Mapping

from .wufr_interface_statics import (
    CompleteCarrierWrench,
    InterfaceStaticsSolverConfig,
    Level1CornerGeometry,
    WufrInterfaceStaticsResult,
    solve_wufr_level1_interface_statics,
)

CORNER_ORDER = ("front_left", "front_right", "rear_left", "rear_right")
REQUIRED_CONFIGURATION_ID = "WUFR27_SUSPENSION_BASELINE_V0"
REQUIRED_FRAME_ID = "WUFR26_OPTIMUMK_SUSPENSION_CANONICAL_AXLE_LOCAL"
RESULT_LABEL = "uncorrelated_design_intent_static_level1_interface_loads"


class StaticLevel1Status(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class StaticLevel1FailureCode(str, Enum):
    UPSTREAM_CARRIER_RESULT_FAILURE = "upstream_carrier_result_failure"
    CORNER_COUNT_OR_ORDER_MISMATCH = "corner_count_or_order_mismatch"
    STATE_IDENTITY_MISMATCH = "state_identity_mismatch"
    CONFIGURATION_MISMATCH = "configuration_mismatch"
    LOAD_CASE_MISMATCH = "load_case_mismatch"
    FRAME_OR_REFERENCE_MISMATCH = "frame_or_reference_mismatch"
    GEOMETRY_SOURCE_MISMATCH = "geometry_source_mismatch"
    CORNER_SOLVE_FAILURE = "corner_solve_failure"
    CORNER_RESIDUAL_FAILURE = "corner_residual_failure"
    COLLECTION_INCOMPLETE = "collection_incomplete"
    NONFINITE_OUTPUT = "nonfinite_output"


@dataclass(frozen=True)
class StaticLevel1CornerInput:
    corner_id: str
    static_state_id: str
    geometry: Level1CornerGeometry
    carrier_wrench: CompleteCarrierWrench


@dataclass(frozen=True)
class StaticLevel1CornerResult:
    corner_id: str
    static_state_id: str
    result: WufrInterfaceStaticsResult


@dataclass(frozen=True)
class StaticLevel1CollectionResult:
    status: StaticLevel1Status
    configuration_id: str
    static_state_id: str
    load_case_id: str
    corners: tuple[StaticLevel1CornerResult, ...] = ()
    failure_code: StaticLevel1FailureCode | None = None
    failed_corner_id: str | None = None
    message: str = ""
    maximum_force_residual_N: float | None = None
    maximum_moment_residual_Nm: float | None = None
    maximum_condition_number_inf: float | None = None
    result_label: str = RESULT_LABEL
    authorization_id: str = "AUTH-SUSP-0017"
    model_id: str = "MOD-SUSP-0009"
    atomic_collection: bool = True
    partial_publication_allowed: bool = False
    installed_as_built_authority: bool = False
    structural_load_case_authority: bool = False
    rocker_result_publication_authority: bool = False

    @property
    def ok(self) -> bool:
        return self.status is StaticLevel1Status.SUCCESS


def _corner_identity(geometry: Level1CornerGeometry) -> str:
    return f"{geometry.axle}_{geometry.side}"


def _failure(
    code: StaticLevel1FailureCode,
    message: str,
    *,
    configuration_id: str = "",
    static_state_id: str = "",
    load_case_id: str = "",
    failed_corner_id: str | None = None,
) -> StaticLevel1CollectionResult:
    return StaticLevel1CollectionResult(
        status=StaticLevel1Status.FAILURE,
        configuration_id=configuration_id,
        static_state_id=static_state_id,
        load_case_id=load_case_id,
        failure_code=code,
        failed_corner_id=failed_corner_id,
        message=message,
    )


def solve_wufr_static_level1_interface_loads(
    corner_inputs: Mapping[str, StaticLevel1CornerInput],
    *,
    solver_config: InterfaceStaticsSolverConfig | None = None,
    required_configuration_id: str = REQUIRED_CONFIGURATION_ID,
    required_frame_id: str = REQUIRED_FRAME_ID,
) -> StaticLevel1CollectionResult:
    """Solve and publish one all-or-nothing four-corner static Level-1 packet."""
    if tuple(corner_inputs.keys()) != CORNER_ORDER:
        return _failure(
            StaticLevel1FailureCode.CORNER_COUNT_OR_ORDER_MISMATCH,
            f"Expected exact corner order {CORNER_ORDER}; got {tuple(corner_inputs.keys())}",
        )

    first = corner_inputs[CORNER_ORDER[0]]
    configuration_id = first.geometry.configuration_id
    static_state_id = first.static_state_id
    load_case_id = first.carrier_wrench.load_case_id

    if configuration_id != required_configuration_id:
        return _failure(
            StaticLevel1FailureCode.CONFIGURATION_MISMATCH,
            f"Expected configuration {required_configuration_id}; got {configuration_id}",
            configuration_id=configuration_id,
            static_state_id=static_state_id,
            load_case_id=load_case_id,
        )
    if not static_state_id:
        return _failure(
            StaticLevel1FailureCode.STATE_IDENTITY_MISMATCH,
            "Static state identity is required",
            configuration_id=configuration_id,
            load_case_id=load_case_id,
        )
    if not load_case_id:
        return _failure(
            StaticLevel1FailureCode.LOAD_CASE_MISMATCH,
            "Load-case identity is required",
            configuration_id=configuration_id,
            static_state_id=static_state_id,
        )

    solved: list[StaticLevel1CornerResult] = []
    max_force = 0.0
    max_moment = 0.0
    max_condition = 0.0

    for corner_id in CORNER_ORDER:
        item = corner_inputs[corner_id]
        geometry = item.geometry
        wrench = item.carrier_wrench

        if item.corner_id != corner_id or _corner_identity(geometry) != corner_id:
            return _failure(
                StaticLevel1FailureCode.STATE_IDENTITY_MISMATCH,
                "Corner input identity does not match geometry identity",
                configuration_id=configuration_id,
                static_state_id=static_state_id,
                load_case_id=load_case_id,
                failed_corner_id=corner_id,
            )
        if item.static_state_id != static_state_id:
            return _failure(
                StaticLevel1FailureCode.STATE_IDENTITY_MISMATCH,
                "All corners must use one exact static state",
                configuration_id=configuration_id,
                static_state_id=static_state_id,
                load_case_id=load_case_id,
                failed_corner_id=corner_id,
            )
        if geometry.configuration_id != configuration_id:
            return _failure(
                StaticLevel1FailureCode.CONFIGURATION_MISMATCH,
                "All corners must use one exact configuration",
                configuration_id=configuration_id,
                static_state_id=static_state_id,
                load_case_id=load_case_id,
                failed_corner_id=corner_id,
            )
        if wrench.load_case_id != load_case_id:
            return _failure(
                StaticLevel1FailureCode.LOAD_CASE_MISMATCH,
                "All corners must use one exact load-case identity",
                configuration_id=configuration_id,
                static_state_id=static_state_id,
                load_case_id=load_case_id,
                failed_corner_id=corner_id,
            )
        if geometry.frame_id != required_frame_id or wrench.frame_id != required_frame_id:
            return _failure(
                StaticLevel1FailureCode.FRAME_OR_REFERENCE_MISMATCH,
                "Geometry and carrier wrench must share the reviewed Level-1 frame",
                configuration_id=configuration_id,
                static_state_id=static_state_id,
                load_case_id=load_case_id,
                failed_corner_id=corner_id,
            )
        if tuple(float(v) for v in geometry.carrier_reference_m) != tuple(float(v) for v in wrench.reference_point_m):
            return _failure(
                StaticLevel1FailureCode.FRAME_OR_REFERENCE_MISMATCH,
                "Carrier wrench reference must exactly match the current Level-1 carrier reference",
                configuration_id=configuration_id,
                static_state_id=static_state_id,
                load_case_id=load_case_id,
                failed_corner_id=corner_id,
            )
        if not geometry.geometry_source_id:
            return _failure(
                StaticLevel1FailureCode.GEOMETRY_SOURCE_MISMATCH,
                "Geometry source identity is required",
                configuration_id=configuration_id,
                static_state_id=static_state_id,
                load_case_id=load_case_id,
                failed_corner_id=corner_id,
            )
        if not wrench.complete:
            return _failure(
                StaticLevel1FailureCode.UPSTREAM_CARRIER_RESULT_FAILURE,
                "Carrier wrench is incomplete",
                configuration_id=configuration_id,
                static_state_id=static_state_id,
                load_case_id=load_case_id,
                failed_corner_id=corner_id,
            )

        result = solve_wufr_level1_interface_statics(geometry, wrench, config=solver_config)
        if not result.ok:
            return _failure(
                StaticLevel1FailureCode.CORNER_SOLVE_FAILURE,
                result.message or "Level-1 corner solve failed",
                configuration_id=configuration_id,
                static_state_id=static_state_id,
                load_case_id=load_case_id,
                failed_corner_id=corner_id,
            )
        if not result.body_residuals or result.condition_number_inf is None:
            return _failure(
                StaticLevel1FailureCode.COLLECTION_INCOMPLETE,
                "Successful corner result is missing required diagnostics",
                configuration_id=configuration_id,
                static_state_id=static_state_id,
                load_case_id=load_case_id,
                failed_corner_id=corner_id,
            )
        corner_force = max(body.force_inf_norm_N for body in result.body_residuals)
        corner_moment = max(body.moment_inf_norm_Nm for body in result.body_residuals)
        numeric_values = (corner_force, corner_moment, result.condition_number_inf)
        if not all(math.isfinite(value) for value in numeric_values):
            return _failure(
                StaticLevel1FailureCode.NONFINITE_OUTPUT,
                "Corner diagnostics contain a nonfinite value",
                configuration_id=configuration_id,
                static_state_id=static_state_id,
                load_case_id=load_case_id,
                failed_corner_id=corner_id,
            )
        max_force = max(max_force, corner_force)
        max_moment = max(max_moment, corner_moment)
        max_condition = max(max_condition, result.condition_number_inf)
        solved.append(StaticLevel1CornerResult(corner_id, static_state_id, result))

    return StaticLevel1CollectionResult(
        status=StaticLevel1Status.SUCCESS,
        configuration_id=configuration_id,
        static_state_id=static_state_id,
        load_case_id=load_case_id,
        corners=tuple(solved),
        maximum_force_residual_N=max_force,
        maximum_moment_residual_Nm=max_moment,
        maximum_condition_number_inf=max_condition,
        message="Complete atomic four-corner static Level-1 interface-load packet",
    )
