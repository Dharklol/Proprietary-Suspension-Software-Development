"""Synchronized four-corner WUFR static rocker included-load composition.

Implements ``AUTH-SUSP-0018`` / ``MOD-SUSP-0010``. The adapter consumes the
accepted ``MOD-SUSP-0009`` four-corner Level-1 result, regenerates the exact
matching conservative spring and physical Z-bar linkage states, and invokes the
unchanged incomplete ``MOD-SUSP-0008`` rocker adapter once per corner.

The result is deliberately incomplete. The KW V5 non-spring static force
remains unavailable under ``AUTH-SUSP-0015`` and is never assumed zero.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Sequence

from pssd_vehicle.wufr_static_equilibrium import evaluate_wufr_suspension_composition

from .rocker_included_load import RockerIncludedLoadResult
from .wufr_rocker_included_load import (
    WufrRockerIncludedLoadResult,
    compose_wufr_rocker_included_load,
)
from .wufr_spring_rocker_force import (
    WufrSpringRockerForceResult,
    recover_wufr_spring_rocker_force,
)
from .wufr_static_level1_interface_loads import (
    CORNER_ORDER,
    WUFRStaticLevel1CornerResult,
    WUFRStaticLevel1Provider,
    WUFRStaticLevel1Result,
    evaluate_wufr_static_level1_interface_loads,
    load_wufr_static_level1_provider,
)
from .wufr_zbar import ZBarAxleFixture, ZBarMechanismResult
from .wufr_zbar_link_force import (
    ZBarLinkForceConfig,
    ZBarPhysicalLinkForceResult,
    recover_wufr_zbar_physical_link_forces,
)

Point3 = tuple[float, float, float]
RESULT_LABEL = "uncorrelated_design_intent_static_rocker_included_loads"
REQUIRED_RECORD_ID = "WUFR27_STATIC_ROCKER_INCLUDED_LOADS_V0"
REQUIRED_AUTHORIZATION_ID = "AUTH-SUSP-0018"
REQUIRED_MODEL_ID = "MOD-SUSP-0010"
REQUIRED_CONFIGURATION_ID = "WUFR27_SUSPENSION_BASELINE_V0"
REQUIRED_STATIC_STATE_ID = "WUFR26_DRIVER_NO_FUEL_DESIGN_INTENT_REFERENCE"
REQUIRED_LEVEL1_RESULT_LABEL = "uncorrelated_design_intent_static_level1_interface_loads"
REQUIRED_LEVEL1_AUTHORIZATION_ID = "AUTH-SUSP-0017"
REQUIRED_LEVEL1_MODEL_ID = "MOD-SUSP-0009"
MISSING_LOAD_ID = "KW_V5_non_spring_static_force"
REQUIRED_INCLUDED_LOAD_IDS = ("push_pull", "conservative_spring", "physical_arb_link")


class WUFRStaticRockerStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class WUFRStaticRockerFailureCode(str, Enum):
    SOURCE_MISMATCH = "source_mismatch"
    UPSTREAM_LEVEL1_RESULT_FAILURE = "upstream_level1_result_failure"
    CORNER_COUNT_OR_ORDER_MISMATCH = "corner_count_or_order_mismatch"
    STATE_IDENTITY_MISMATCH = "state_identity_mismatch"
    CONFIGURATION_MISMATCH = "configuration_mismatch"
    LOAD_CASE_MISMATCH = "load_case_mismatch"
    FRAME_MISMATCH = "frame_mismatch"
    SPRING_STATE_FAILURE = "spring_state_failure"
    ARB_STATE_FAILURE = "arb_state_failure"
    ROCKER_GEOMETRY_MISMATCH = "rocker_geometry_mismatch"
    CORNER_COMPOSITION_FAILURE = "corner_composition_failure"
    UNIT_INFLUENCE_FAILURE = "unit_influence_failure"
    COLLECTION_INCOMPLETE = "collection_incomplete"
    NONFINITE_OUTPUT = "nonfinite_output"


class WUFRStaticRockerError(ValueError):
    def __init__(self, code: WUFRStaticRockerFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class WUFRStaticRockerSource:
    record_id: str
    configuration_id: str
    static_state_id: str
    result_label: str
    authorization_id: str
    model_id: str
    corner_order: tuple[str, str, str, str]
    level1_model_id: str
    level1_authorization_id: str
    level1_result_label: str
    rocker_model_id: str
    rocker_authorization_id: str
    spring_authorization_id: str
    arb_authorization_id: str
    damper_hold_authorization_id: str
    complete_hardware_reaction: bool
    complete_rocker_equilibrium: bool
    actual_damper_force_authorized: bool
    installed_as_built_authority: bool
    structural_release_authority: bool


@dataclass(frozen=True)
class WUFRStaticRockerConfig:
    state_match_tolerance: float = 1.0e-10
    point_match_tolerance_m: float = 1.0e-9
    axis_match_tolerance: float = 1.0e-10
    arb_torque_agreement_tolerance_Nm: float = 1.0e-6

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) and value > 0.0 for value in self.__dict__.values()):
            raise ValueError("Static rocker composition tolerances must be finite and positive")


@dataclass(frozen=True)
class DamperUnitInfluence:
    unit_force_N: float
    positive_direction_chassis_to_rocker: Point3
    application_point_m: Point3
    rocker_pivot_m: Point3
    rocker_axis_unit: Point3
    d_pivot_force_d_damper_force: Point3
    d_pivot_moment_d_damper_force_m: Point3
    d_free_axis_moment_d_damper_force_m: float
    actual_force_magnitude_assumed: bool = False
    actual_force_authorized: bool = False


@dataclass(frozen=True)
class WUFRStaticRockerCornerResult:
    corner_id: str
    axle: str
    side: str
    load_case_id: str
    interface_result: WUFRStaticLevel1CornerResult
    spring_result: WufrSpringRockerForceResult
    arb_link_result: ZBarPhysicalLinkForceResult
    arb_mechanism_result: ZBarMechanismResult
    arb_fixture: ZBarAxleFixture
    rocker_result: WufrRockerIncludedLoadResult
    damper_unit_influence: DamperUnitInfluence

    @property
    def included_result(self) -> RockerIncludedLoadResult | None:
        return self.rocker_result.included_result

    @property
    def ok(self) -> bool:
        return self.rocker_result.ok and self.included_result is not None


@dataclass(frozen=True)
class WUFRStaticRockerResult:
    status: WUFRStaticRockerStatus
    result_label: str
    authorization_id: str
    model_id: str
    configuration_id: str
    static_state_id: str
    upstream_level1_result_label: str
    upstream_level1_authorization_id: str
    upstream_level1_model_id: str
    corners: tuple[WUFRStaticRockerCornerResult, ...] = ()
    maximum_force_residual_N: float | None = None
    maximum_perpendicular_moment_residual_Nm: float | None = None
    maximum_support_axis_moment_component_Nm: float | None = None
    maximum_absolute_free_axis_moment_residual_Nm: float | None = None
    complete_for_named_included_load_set: bool = False
    complete_hardware_reaction: bool = False
    complete_rocker_equilibrium: bool = False
    actual_damper_force_applied: bool = False
    structural_release_authority: bool = False
    installed_as_built_authority: bool = False
    production_authority: bool = False
    failure_code: WUFRStaticRockerFailureCode | None = None
    failed_corner_id: str | None = None
    failed_stage: str | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WUFRStaticRockerStatus.SUCCESS


@dataclass(frozen=True)
class WUFRStaticRockerProvider:
    source: WUFRStaticRockerSource
    level1_provider: WUFRStaticLevel1Provider
    config: WUFRStaticRockerConfig


def _p(values: Sequence[float], label: str = "vector") -> Point3:
    if len(values) != 3:
        raise WUFRStaticRockerError(
            WUFRStaticRockerFailureCode.NONFINITE_OUTPUT,
            f"{label} must contain three components",
        )
    result = (float(values[0]), float(values[1]), float(values[2]))
    if not all(math.isfinite(value) for value in result):
        raise WUFRStaticRockerError(
            WUFRStaticRockerFailureCode.NONFINITE_OUTPUT,
            f"{label} must be finite",
        )
    return result


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


def _unit(vector: Point3, label: str = "vector") -> Point3:
    magnitude = _norm(vector)
    if not math.isfinite(magnitude) or magnitude <= 1.0e-12:
        raise WUFRStaticRockerError(
            WUFRStaticRockerFailureCode.UNIT_INFLUENCE_FAILURE,
            f"{label} is degenerate",
        )
    return _scale(1.0 / magnitude, vector)


def _max_difference(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        return math.inf
    return max(abs(float(a) - float(b)) for a, b in zip(left, right))


def _failure(
    provider: WUFRStaticRockerProvider,
    code: WUFRStaticRockerFailureCode,
    message: str,
    *,
    corner_id: str | None = None,
    stage: str | None = None,
) -> WUFRStaticRockerResult:
    source = provider.source
    return WUFRStaticRockerResult(
        status=WUFRStaticRockerStatus.FAILURE,
        result_label=source.result_label,
        authorization_id=source.authorization_id,
        model_id=source.model_id,
        configuration_id=source.configuration_id,
        static_state_id=source.static_state_id,
        upstream_level1_result_label=source.level1_result_label,
        upstream_level1_authorization_id=source.level1_authorization_id,
        upstream_level1_model_id=source.level1_model_id,
        corners=(),
        failure_code=code,
        failed_corner_id=corner_id,
        failed_stage=stage,
        message=message,
    )


def load_wufr_static_rocker_source(path: str | Path) -> WUFRStaticRockerSource:
    with Path(path).open("rb") as stream:
        document = tomllib.load(stream)
    source_tables = document.get("source", {})
    level1 = source_tables.get("static_level1", {})
    rocker = source_tables.get("rocker_kernel", {})
    spring = source_tables.get("spring", {})
    arb = source_tables.get("arb", source_tables.get("arb_link_force", {}))
    damper = source_tables.get("damper_hold", {})
    boundaries = document.get("boundaries", {})
    source = WUFRStaticRockerSource(
        record_id=str(document.get("record_id", "")),
        configuration_id=str(document.get("configuration_id", "")),
        static_state_id=str(document.get("static_state_id", "")),
        result_label=str(document.get("result_label", "")),
        authorization_id=str(document.get("authorization_id", "")),
        model_id=str(document.get("model_id", "")),
        corner_order=tuple(str(value) for value in document.get("corner_order", ())),  # type: ignore[arg-type]
        level1_model_id=str(level1.get("model_id", "")),
        level1_authorization_id=str(level1.get("authorization_id", "")),
        level1_result_label=str(level1.get("required_result_label", "")),
        rocker_model_id=str(rocker.get("model_id", "")),
        rocker_authorization_id=str(rocker.get("authorization_id", "")),
        spring_authorization_id=str(spring.get("physical_vector_authorization_id", "")),
        arb_authorization_id=str(arb.get("physical_vector_authorization_id", "")),
        damper_hold_authorization_id=str(damper.get("authorization_id", "")),
        complete_hardware_reaction=bool(boundaries.get("complete_hardware_reaction", True)),
        complete_rocker_equilibrium=bool(boundaries.get("complete_rocker_equilibrium", True)),
        actual_damper_force_authorized=bool(
            boundaries.get("actual_damper_force_authorized", boundaries.get("damper_static_force_model_authorized", True))
        ),
        installed_as_built_authority=bool(boundaries.get("installed_as_built_authority", True)),
        structural_release_authority=bool(
            boundaries.get("structural_release_authority", boundaries.get("structural_load_case_authority", True))
        ),
    )
    valid = (
        source.record_id == REQUIRED_RECORD_ID
        and source.configuration_id == REQUIRED_CONFIGURATION_ID
        and source.static_state_id == REQUIRED_STATIC_STATE_ID
        and source.result_label == RESULT_LABEL
        and source.authorization_id == REQUIRED_AUTHORIZATION_ID
        and source.model_id == REQUIRED_MODEL_ID
        and source.corner_order == CORNER_ORDER
        and source.level1_model_id == REQUIRED_LEVEL1_MODEL_ID
        and source.level1_authorization_id == REQUIRED_LEVEL1_AUTHORIZATION_ID
        and source.level1_result_label == REQUIRED_LEVEL1_RESULT_LABEL
        and source.rocker_model_id == "MOD-SUSP-0008"
        and source.rocker_authorization_id == "AUTH-SUSP-0016"
        and source.spring_authorization_id == "AUTH-SUSP-0014"
        and source.arb_authorization_id == "AUTH-SUSP-0013"
        and source.damper_hold_authorization_id == "AUTH-SUSP-0015"
        and not source.complete_hardware_reaction
        and not source.complete_rocker_equilibrium
        and not source.actual_damper_force_authorized
        and not source.installed_as_built_authority
        and not source.structural_release_authority
    )
    if not valid:
        raise WUFRStaticRockerError(
            WUFRStaticRockerFailureCode.SOURCE_MISMATCH,
            "Static rocker source identity/boundary does not match AUTH-SUSP-0018",
        )
    return source


def load_wufr_static_rocker_provider(
    *,
    source_path: str | Path,
    static_level1_source_path: str | Path,
    carrier_source_path: str | Path,
    static_equilibrium_result_path: str | Path,
    static_equilibrium_source_path: str | Path,
    road_contact_source_path: str | Path,
    suspension_geometry_path: str | Path,
    wheel_profile_path: str | Path,
    steering_geometry_path: str | Path,
    whole_vehicle_path: str | Path,
    gravity_path: str | Path,
    spring_package_path: str | Path,
    zbar_fixture_path: str | Path,
    config: WUFRStaticRockerConfig | None = None,
) -> WUFRStaticRockerProvider:
    return WUFRStaticRockerProvider(
        source=load_wufr_static_rocker_source(source_path),
        level1_provider=load_wufr_static_level1_provider(
            source_path=static_level1_source_path,
            carrier_source_path=carrier_source_path,
            static_equilibrium_result_path=static_equilibrium_result_path,
            static_equilibrium_source_path=static_equilibrium_source_path,
            road_contact_source_path=road_contact_source_path,
            suspension_geometry_path=suspension_geometry_path,
            wheel_profile_path=wheel_profile_path,
            steering_geometry_path=steering_geometry_path,
            whole_vehicle_path=whole_vehicle_path,
            gravity_path=gravity_path,
            spring_package_path=spring_package_path,
            zbar_fixture_path=zbar_fixture_path,
        ),
        config=config or WUFRStaticRockerConfig(),
    )


def _validate_level1_handoff(
    corner_id: str,
    level1_corner: WUFRStaticLevel1CornerResult,
    config: WUFRStaticRockerConfig,
) -> None:
    solved = level1_corner.solve
    axial = solved.actuation
    current = level1_corner.actuation_state
    if not solved.ok or axial is None:
        raise WUFRStaticRockerError(
            WUFRStaticRockerFailureCode.UPSTREAM_LEVEL1_RESULT_FAILURE,
            f"{corner_id} successful Level-1 actuation reaction is unavailable",
        )
    if current.arm_attachment_m is None or current.rocker_rod_point_m is None:
        raise WUFRStaticRockerError(
            WUFRStaticRockerFailureCode.STATE_IDENTITY_MISMATCH,
            f"{corner_id} current actuation endpoints are unavailable",
        )
    if solved.frame_id != level1_corner.geometry.frame_id:
        raise WUFRStaticRockerError(
            WUFRStaticRockerFailureCode.FRAME_MISMATCH,
            f"{corner_id} Level-1 solve and geometry frame mismatch",
        )
    if solved.configuration_id != current.configuration_id:
        raise WUFRStaticRockerError(
            WUFRStaticRockerFailureCode.CONFIGURATION_MISMATCH,
            f"{corner_id} Level-1 solve and actuation configuration mismatch",
        )
    if _max_difference(axial.body_point_m, current.arm_attachment_m) > config.point_match_tolerance_m:
        raise WUFRStaticRockerError(
            WUFRStaticRockerFailureCode.STATE_IDENTITY_MISMATCH,
            f"{corner_id} Level-1 actuation body point differs from the current arm attachment",
        )
    if _max_difference(axial.remote_point_m, current.rocker_rod_point_m) > config.point_match_tolerance_m:
        raise WUFRStaticRockerError(
            WUFRStaticRockerFailureCode.STATE_IDENTITY_MISMATCH,
            f"{corner_id} Level-1 actuation remote point differs from the current rocker pickup",
        )
    expected_axis = _unit(
        _sub(_p(current.rocker_rod_point_m), _p(current.arm_attachment_m)),
        f"{corner_id} actuation link axis",
    )
    if _max_difference(axial.unit_axis_body_to_remote, expected_axis) > config.axis_match_tolerance:
        raise WUFRStaticRockerError(
            WUFRStaticRockerFailureCode.STATE_IDENTITY_MISMATCH,
            f"{corner_id} Level-1 actuation axis differs from the current physical link axis",
        )
    if not solved.load_case_id or not solved.load_case_id.endswith(f":{corner_id}"):
        raise WUFRStaticRockerError(
            WUFRStaticRockerFailureCode.LOAD_CASE_MISMATCH,
            f"{corner_id} Level-1 load-case identity mismatch",
        )


def _damper_unit_influence(spring: WufrSpringRockerForceResult) -> DamperUnitInfluence:
    required = (
        spring.chassis_eye_m,
        spring.rocker_eye_m,
        spring.rocker_pivot_m,
        spring.rocker_axis_unit,
        spring.chassis_to_rocker_unit,
    )
    if any(value is None for value in required):
        raise WUFRStaticRockerError(
            WUFRStaticRockerFailureCode.UNIT_INFLUENCE_FAILURE,
            "Spring result lacks exact current eye/pivot/axis geometry",
        )
    direction = _unit(_p(spring.chassis_to_rocker_unit or (), "damper unit direction"), "damper eye line")
    pivot = _p(spring.rocker_pivot_m or (), "rocker pivot")
    eye = _p(spring.rocker_eye_m or (), "rocker eye")
    axis = _unit(_p(spring.rocker_axis_unit or (), "rocker axis"), "rocker axis")
    applied_moment_per_N = _cross(_sub(eye, pivot), direction)
    free_axis_coefficient = _dot(axis, applied_moment_per_N)
    perpendicular = _sub(applied_moment_per_N, _scale(free_axis_coefficient, axis))
    return DamperUnitInfluence(
        unit_force_N=1.0,
        positive_direction_chassis_to_rocker=direction,
        application_point_m=eye,
        rocker_pivot_m=pivot,
        rocker_axis_unit=axis,
        d_pivot_force_d_damper_force=_scale(-1.0, direction),
        d_pivot_moment_d_damper_force_m=_scale(-1.0, perpendicular),
        d_free_axis_moment_d_damper_force_m=free_axis_coefficient,
        actual_force_magnitude_assumed=False,
        actual_force_authorized=False,
    )


def evaluate_wufr_static_rocker_included_loads(
    provider: WUFRStaticRockerProvider,
    *,
    level1_result: WUFRStaticLevel1Result | None = None,
) -> WUFRStaticRockerResult:
    source = provider.source
    level1 = level1_result or evaluate_wufr_static_level1_interface_loads(provider.level1_provider)
    if not level1.ok:
        return _failure(
            provider,
            WUFRStaticRockerFailureCode.UPSTREAM_LEVEL1_RESULT_FAILURE,
            level1.message or "MOD-SUSP-0009 result is unsuccessful",
            stage="level1",
        )
    if (
        level1.result_label != source.level1_result_label
        or level1.authorization_id != source.level1_authorization_id
        or level1.model_id != source.level1_model_id
    ):
        return _failure(
            provider,
            WUFRStaticRockerFailureCode.SOURCE_MISMATCH,
            "MOD-SUSP-0009 result identity mismatch",
            stage="level1",
        )
    if level1.configuration_id != source.configuration_id:
        return _failure(
            provider,
            WUFRStaticRockerFailureCode.CONFIGURATION_MISMATCH,
            "MOD-SUSP-0009 configuration mismatch",
            stage="level1",
        )
    if level1.static_state_id != source.static_state_id:
        return _failure(
            provider,
            WUFRStaticRockerFailureCode.STATE_IDENTITY_MISMATCH,
            "MOD-SUSP-0009 static-state mismatch",
            stage="level1",
        )
    if tuple(corner.corner_id for corner in level1.corners) != source.corner_order:
        return _failure(
            provider,
            WUFRStaticRockerFailureCode.CORNER_COUNT_OR_ORDER_MISMATCH,
            "Level-1 corners must be fixed FL/FR/RL/RR",
            stage="level1",
        )

    carrier_provider = provider.level1_provider.carrier_provider
    accepted = carrier_provider.accepted_result
    equilibrium_provider = carrier_provider.equilibrium_provider
    composition = evaluate_wufr_suspension_composition(
        equilibrium_provider,
        accepted.wheel_coordinates_m,
        front_arb_setting=accepted.front_arb_setting,
        rear_arb_setting=accepted.rear_arb_setting,
    )
    if not composition.ok or len(composition.spring_states) != 4 or len(composition.spring_actuation_states) != 4:
        return _failure(
            provider,
            WUFRStaticRockerFailureCode.SPRING_STATE_FAILURE,
            composition.message or "Current spring/actuation composition failed",
            stage="suspension_composition",
        )
    front_arb = composition.front_arb_state
    rear_arb = composition.rear_arb_state
    if (
        front_arb is None
        or rear_arb is None
        or front_arb.mechanism is None
        or rear_arb.mechanism is None
        or front_arb.force is None
        or rear_arb.force is None
    ):
        return _failure(
            provider,
            WUFRStaticRockerFailureCode.ARB_STATE_FAILURE,
            "Current front/rear Z-bar states are incomplete",
            stage="suspension_composition",
        )

    link_config = ZBarLinkForceConfig(
        rocker_torque_agreement_tolerance_Nm=provider.config.arb_torque_agreement_tolerance_Nm
    )
    front_fixture = equilibrium_provider.front_zbar_fixture
    rear_fixture = equilibrium_provider.rear_zbar_fixture
    front_link = recover_wufr_zbar_physical_link_forces(
        front_fixture,
        front_arb.mechanism,
        front_arb.force,
        config=link_config,
    )
    rear_link = recover_wufr_zbar_physical_link_forces(
        rear_fixture,
        rear_arb.mechanism,
        rear_arb.force,
        config=link_config,
    )
    if not front_link.ok or not rear_link.ok:
        failed = front_link if not front_link.ok else rear_link
        return _failure(
            provider,
            WUFRStaticRockerFailureCode.ARB_STATE_FAILURE,
            failed.message or "Physical Z-bar linkage force recovery failed",
            stage="arb_physical_force",
        )

    geometry = equilibrium_provider.road_contact.suspension_geometry
    results: list[WUFRStaticRockerCornerResult] = []
    for index, corner_id in enumerate(CORNER_ORDER):
        level1_corner = level1.corners[index]
        axle = "front" if index < 2 else "rear"
        side = "left" if index % 2 == 0 else "right"
        try:
            if level1_corner.axle != axle or level1_corner.side != side:
                raise WUFRStaticRockerError(
                    WUFRStaticRockerFailureCode.STATE_IDENTITY_MISMATCH,
                    f"{corner_id} Level-1 corner identity mismatch",
                )
            _validate_level1_handoff(corner_id, level1_corner, provider.config)
            spring_actuation = composition.spring_actuation_states[index]
            spring_state = composition.spring_states[index]
            if (
                level1_corner.actuation_state.q_L_rad is None
                or spring_actuation.q_L_rad is None
                or abs(level1_corner.actuation_state.q_L_rad - spring_actuation.q_L_rad)
                > provider.config.state_match_tolerance
                or level1_corner.actuation_state.rocker_theta_rad is None
                or spring_actuation.rocker_theta_rad is None
                or abs(level1_corner.actuation_state.rocker_theta_rad - spring_actuation.rocker_theta_rad)
                > provider.config.state_match_tolerance
            ):
                raise WUFRStaticRockerError(
                    WUFRStaticRockerFailureCode.STATE_IDENTITY_MISMATCH,
                    f"{corner_id} Level-1 and spring/Z-bar actuation states differ",
                )
            corner_geometry = geometry.corner(axle, side)
            spring = recover_wufr_spring_rocker_force(
                corner_geometry,
                spring_actuation,
                spring_state,
            )
            if not spring.ok:
                raise WUFRStaticRockerError(
                    WUFRStaticRockerFailureCode.SPRING_STATE_FAILURE,
                    spring.message or f"{corner_id} physical spring force failed",
                )
            fixture = front_fixture if axle == "front" else rear_fixture
            mechanism = front_arb.mechanism if axle == "front" else rear_arb.mechanism
            link = front_link if axle == "front" else rear_link
            composed = compose_wufr_rocker_included_load(
                interface_result=level1_corner.solve,
                spring_result=spring,
                arb_link_result=link,
                arb_mechanism_result=mechanism,
                arb_fixture=fixture,
            )
            if not composed.ok or composed.included_result is None:
                raise WUFRStaticRockerError(
                    WUFRStaticRockerFailureCode.CORNER_COMPOSITION_FAILURE,
                    composed.message or f"{corner_id} incomplete rocker composition failed",
                )
            included = composed.included_result
            if (
                included.included_load_ids != REQUIRED_INCLUDED_LOAD_IDS
                or included.missing_load_ids != (MISSING_LOAD_ID,)
                or included.complete_hardware_reaction
                or composed.complete_hardware_reaction
            ):
                raise WUFRStaticRockerError(
                    WUFRStaticRockerFailureCode.CORNER_COMPOSITION_FAILURE,
                    f"{corner_id} included/missing load boundary mismatch",
                )
            push_pull = included.included_loads[0]
            axial = level1_corner.solve.actuation
            if (
                axial is None
                or push_pull.force_N != axial.force_on_remote_N
                or push_pull.application_point_m != axial.remote_point_m
                or push_pull.source_id != axial.source_id
            ):
                raise WUFRStaticRockerError(
                    WUFRStaticRockerFailureCode.LOAD_CASE_MISMATCH,
                    f"{corner_id} push/pull handoff changed sign, point, or source",
                )
            results.append(
                WUFRStaticRockerCornerResult(
                    corner_id=corner_id,
                    axle=axle,
                    side=side,
                    load_case_id=level1_corner.solve.load_case_id,
                    interface_result=level1_corner,
                    spring_result=spring,
                    arb_link_result=link,
                    arb_mechanism_result=mechanism,
                    arb_fixture=fixture,
                    rocker_result=composed,
                    damper_unit_influence=_damper_unit_influence(spring),
                )
            )
        except WUFRStaticRockerError as exc:
            return _failure(
                provider,
                exc.code,
                str(exc),
                corner_id=corner_id,
                stage="corner_composition",
            )
        except Exception as exc:
            return _failure(
                provider,
                WUFRStaticRockerFailureCode.CORNER_COMPOSITION_FAILURE,
                f"{corner_id} unexpected composition failure: {exc}",
                corner_id=corner_id,
                stage="corner_composition",
            )

    if tuple(corner.corner_id for corner in results) != CORNER_ORDER:
        return _failure(
            provider,
            WUFRStaticRockerFailureCode.COLLECTION_INCOMPLETE,
            "Four-corner rocker collection is incomplete or reordered",
            stage="collection",
        )
    included_results = [corner.included_result for corner in results]
    if any(result is None for result in included_results):
        return _failure(
            provider,
            WUFRStaticRockerFailureCode.COLLECTION_INCOMPLETE,
            "A corner lacks included-load diagnostics",
            stage="collection",
        )
    values = [result for result in included_results if result is not None]
    maximum_force = max(float(result.force_residual_inf_norm_N or 0.0) for result in values)
    maximum_moment = max(
        float(result.perpendicular_moment_residual_inf_norm_Nm or 0.0)
        for result in values
    )
    maximum_support_axis = max(
        abs(float(result.support_axis_moment_component_Nm or 0.0))
        for result in values
    )
    maximum_free_axis = max(
        abs(float(result.free_axis_moment_residual_Nm or 0.0))
        for result in values
    )
    coefficient_values = tuple(
        value
        for corner in results
        for value in (
            *corner.damper_unit_influence.d_pivot_force_d_damper_force,
            *corner.damper_unit_influence.d_pivot_moment_d_damper_force_m,
            corner.damper_unit_influence.d_free_axis_moment_d_damper_force_m,
        )
    )
    if not all(
        math.isfinite(value)
        for value in (
            maximum_force,
            maximum_moment,
            maximum_support_axis,
            maximum_free_axis,
            *coefficient_values,
        )
    ):
        return _failure(
            provider,
            WUFRStaticRockerFailureCode.NONFINITE_OUTPUT,
            "Static rocker collection contains nonfinite output",
            stage="collection",
        )
    return WUFRStaticRockerResult(
        status=WUFRStaticRockerStatus.SUCCESS,
        result_label=source.result_label,
        authorization_id=source.authorization_id,
        model_id=source.model_id,
        configuration_id=source.configuration_id,
        static_state_id=source.static_state_id,
        upstream_level1_result_label=source.level1_result_label,
        upstream_level1_authorization_id=source.level1_authorization_id,
        upstream_level1_model_id=source.level1_model_id,
        corners=tuple(results),
        maximum_force_residual_N=maximum_force,
        maximum_perpendicular_moment_residual_Nm=maximum_moment,
        maximum_support_axis_moment_component_Nm=maximum_support_axis,
        maximum_absolute_free_axis_moment_residual_Nm=maximum_free_axis,
        complete_for_named_included_load_set=True,
        complete_hardware_reaction=False,
        complete_rocker_equilibrium=False,
        actual_damper_force_applied=False,
        structural_release_authority=False,
        installed_as_built_authority=False,
        production_authority=False,
        message="Four synchronized incomplete WUFR rocker included-load compositions completed",
    )
