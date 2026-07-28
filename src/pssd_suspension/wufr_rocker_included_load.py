"""WUFR source adapter for the ideal rocker included-load contribution.

The adapter composes only the already-reviewed physical push/pull, conservative
spring, and physical ARB-link vectors.  ``AUTH-SUSP-0015`` keeps the KW V5
non-spring static contribution explicitly missing, so every v0.1 result remains
incomplete.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Sequence

from .rocker_included_load import (
    Point3,
    RockerIncludedLoadConfig,
    RockerIncludedLoadResult,
    RockerPointLoad,
    evaluate_rocker_included_load,
)
from .wufr_interface_statics import WufrInterfaceStaticsResult
from .wufr_spring_rocker_force import WufrSpringRockerForceResult
from .wufr_zbar import ZBarAxleFixture, ZBarMechanismResult
from .wufr_zbar_link_force import ZBarPhysicalLinkForceResult


class WufrRockerIncludedLoadStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class WufrRockerIncludedLoadFailureCode(str, Enum):
    UPSTREAM_INTERFACE_FAILURE = "upstream_interface_failure"
    UPSTREAM_SPRING_FAILURE = "upstream_spring_failure"
    UPSTREAM_ARB_FORCE_FAILURE = "upstream_arb_force_failure"
    UPSTREAM_ARB_MECHANISM_FAILURE = "upstream_arb_mechanism_failure"
    MISSING_UPSTREAM_VALUE = "missing_upstream_value"
    SOURCE_MISMATCH = "source_mismatch"
    GEOMETRY_MISMATCH = "geometry_mismatch"
    INCLUDED_LOAD_KERNEL_FAILURE = "included_load_kernel_failure"


@dataclass(frozen=True)
class WufrRockerIncludedLoadAdapterConfig:
    point_consistency_tolerance_m: float = 1.0e-9
    axis_consistency_tolerance: float = 1.0e-10

    def __post_init__(self) -> None:
        values = (self.point_consistency_tolerance_m, self.axis_consistency_tolerance)
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError("WUFR rocker adapter tolerances must be finite and positive")


@dataclass(frozen=True)
class WufrRockerIncludedLoadResult:
    status: WufrRockerIncludedLoadStatus
    axle: str = ""
    side: str = ""
    frame_id: str = ""
    configuration_id: str = ""
    geometry_source_id: str = ""
    load_case_id: str = ""
    external_wrench_source_id: str = ""
    arb_fixture_id: str = ""
    included_result: RockerIncludedLoadResult | None = None
    complete_hardware_reaction: bool = False
    missing_load_ids: tuple[str, ...] = ("KW_V5_non_spring_static_force",)
    authorization_id: str = "AUTH-SUSP-0016"
    damper_hold_authorization_id: str = "AUTH-SUSP-0015"
    failure_code: WufrRockerIncludedLoadFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WufrRockerIncludedLoadStatus.SUCCESS


def _p(values: Sequence[float]) -> Point3:
    if len(values) != 3:
        raise ValueError("Expected a three-component vector")
    return (float(values[0]), float(values[1]), float(values[2]))


def _sub(a: Point3, b: Point3) -> Point3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _norm(a: Point3) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _unit(a: Point3) -> Point3 | None:
    magnitude = _norm(a)
    if not math.isfinite(magnitude) or magnitude <= 1.0e-14:
        return None
    return (a[0] / magnitude, a[1] / magnitude, a[2] / magnitude)


def _failure(
    code: WufrRockerIncludedLoadFailureCode,
    message: str,
    *,
    interface: WufrInterfaceStaticsResult | None = None,
    spring: WufrSpringRockerForceResult | None = None,
    fixture: ZBarAxleFixture | None = None,
) -> WufrRockerIncludedLoadResult:
    return WufrRockerIncludedLoadResult(
        status=WufrRockerIncludedLoadStatus.FAILURE,
        axle=(spring.axle if spring is not None else (interface.axle if interface is not None else "")),
        side=(spring.side if spring is not None else (interface.side if interface is not None else "")),
        frame_id=(interface.frame_id if interface is not None else ""),
        configuration_id=(
            spring.configuration_id
            if spring is not None
            else (interface.configuration_id if interface is not None else "")
        ),
        geometry_source_id=(interface.geometry_source_id if interface is not None else ""),
        load_case_id=(interface.load_case_id if interface is not None else ""),
        external_wrench_source_id=(interface.external_wrench_source_id if interface is not None else ""),
        arb_fixture_id=(fixture.fixture_id if fixture is not None else ""),
        complete_hardware_reaction=False,
        failure_code=code,
        message=message,
    )


def compose_wufr_rocker_included_load(
    *,
    interface_result: WufrInterfaceStaticsResult,
    spring_result: WufrSpringRockerForceResult,
    arb_link_result: ZBarPhysicalLinkForceResult,
    arb_mechanism_result: ZBarMechanismResult,
    arb_fixture: ZBarAxleFixture,
    adapter_config: WufrRockerIncludedLoadAdapterConfig | None = None,
    kernel_config: RockerIncludedLoadConfig | None = None,
) -> WufrRockerIncludedLoadResult:
    """Compose the three authorized WUFR physical rocker point loads."""
    cfg = adapter_config or WufrRockerIncludedLoadAdapterConfig()

    if not interface_result.ok or interface_result.actuation is None:
        return _failure(
            WufrRockerIncludedLoadFailureCode.UPSTREAM_INTERFACE_FAILURE,
            interface_result.message or "Successful Level-1 actuation reaction is required",
            interface=interface_result,
            spring=spring_result,
            fixture=arb_fixture,
        )
    if not spring_result.ok:
        return _failure(
            WufrRockerIncludedLoadFailureCode.UPSTREAM_SPRING_FAILURE,
            spring_result.message or "Successful physical spring rocker force is required",
            interface=interface_result,
            spring=spring_result,
            fixture=arb_fixture,
        )
    if not arb_link_result.ok:
        return _failure(
            WufrRockerIncludedLoadFailureCode.UPSTREAM_ARB_FORCE_FAILURE,
            arb_link_result.message or "Successful physical ARB linkage force is required",
            interface=interface_result,
            spring=spring_result,
            fixture=arb_fixture,
        )
    if not arb_mechanism_result.ok:
        return _failure(
            WufrRockerIncludedLoadFailureCode.UPSTREAM_ARB_MECHANISM_FAILURE,
            arb_mechanism_result.message or "Successful current ARB mechanism state is required",
            interface=interface_result,
            spring=spring_result,
            fixture=arb_fixture,
        )

    required_spring_values = (
        spring_result.rocker_eye_m,
        spring_result.rocker_pivot_m,
        spring_result.rocker_axis_unit,
        spring_result.force_on_rocker_N,
    )
    if any(value is None for value in required_spring_values):
        return _failure(
            WufrRockerIncludedLoadFailureCode.MISSING_UPSTREAM_VALUE,
            "Spring result lacks current eye/pivot/axis/force data",
            interface=interface_result,
            spring=spring_result,
            fixture=arb_fixture,
        )

    axle = interface_result.axle
    side = interface_result.side
    if side not in {"left", "right"}:
        return _failure(
            WufrRockerIncludedLoadFailureCode.SOURCE_MISMATCH,
            "WUFR rocker side must be left or right",
            interface=interface_result,
            spring=spring_result,
            fixture=arb_fixture,
        )
    identities = (
        spring_result.axle,
        arb_link_result.axle,
        arb_mechanism_result.axle,
        arb_fixture.axle,
    )
    if any(value != axle for value in identities) or spring_result.side != side:
        return _failure(
            WufrRockerIncludedLoadFailureCode.SOURCE_MISMATCH,
            "Axle/side identities do not match across WUFR providers",
            interface=interface_result,
            spring=spring_result,
            fixture=arb_fixture,
        )
    configurations = (
        interface_result.configuration_id,
        spring_result.configuration_id,
        arb_link_result.configuration_id,
        arb_fixture.configuration_id,
    )
    if len(set(configurations)) != 1:
        return _failure(
            WufrRockerIncludedLoadFailureCode.SOURCE_MISMATCH,
            "Configuration identities do not match across WUFR providers",
            interface=interface_result,
            spring=spring_result,
            fixture=arb_fixture,
        )
    if arb_link_result.fixture_id != arb_fixture.fixture_id:
        return _failure(
            WufrRockerIncludedLoadFailureCode.SOURCE_MISMATCH,
            "ARB physical-force and fixture identities do not match",
            interface=interface_result,
            spring=spring_result,
            fixture=arb_fixture,
        )

    if side == "left":
        arb_side = arb_link_result.left
        arb_point = arb_mechanism_result.rocker_pickup_left_m
        fixture_pivot = arb_fixture.rocker_pivot_left_m
    else:
        arb_side = arb_link_result.right
        arb_point = arb_mechanism_result.rocker_pickup_right_m
        fixture_pivot = arb_fixture.rocker_pivot_right_m
    if arb_side is None or arb_point is None:
        return _failure(
            WufrRockerIncludedLoadFailureCode.MISSING_UPSTREAM_VALUE,
            f"Requested {side} ARB side force/current pickup is unavailable",
            interface=interface_result,
            spring=spring_result,
            fixture=arb_fixture,
        )

    spring_pivot = _p(spring_result.rocker_pivot_m)
    fixture_pivot_p = _p(fixture_pivot)
    if _norm(_sub(spring_pivot, fixture_pivot_p)) > cfg.point_consistency_tolerance_m:
        return _failure(
            WufrRockerIncludedLoadFailureCode.GEOMETRY_MISMATCH,
            "Spring and ARB fixture rocker pivots do not match",
            interface=interface_result,
            spring=spring_result,
            fixture=arb_fixture,
        )
    spring_axis = _unit(_p(spring_result.rocker_axis_unit))
    fixture_axis = _unit(_p(arb_fixture.rocker_axis_unit))
    if spring_axis is None or fixture_axis is None or _norm(_sub(spring_axis, fixture_axis)) > cfg.axis_consistency_tolerance:
        return _failure(
            WufrRockerIncludedLoadFailureCode.GEOMETRY_MISMATCH,
            "Spring and ARB rocker axes do not match with the same sign",
            interface=interface_result,
            spring=spring_result,
            fixture=arb_fixture,
        )

    actuation = interface_result.actuation
    load_case_id = interface_result.load_case_id
    frame_id = interface_result.frame_id
    configuration_id = interface_result.configuration_id
    loads = (
        RockerPointLoad(
            load_id="push_pull",
            application_point_m=_p(actuation.remote_point_m),
            force_N=_p(actuation.force_on_remote_N),
            source_id=actuation.source_id or "MOD-SUSP-0007",
            frame_id=frame_id,
            configuration_id=configuration_id,
            load_case_id=load_case_id,
        ),
        RockerPointLoad(
            load_id="conservative_spring",
            application_point_m=_p(spring_result.rocker_eye_m),
            force_N=_p(spring_result.force_on_rocker_N),
            source_id=spring_result.spring_source_id or spring_result.spring_id or "AUTH-SUSP-0014",
            frame_id=frame_id,
            configuration_id=configuration_id,
            load_case_id=load_case_id,
        ),
        RockerPointLoad(
            load_id="physical_arb_link",
            application_point_m=_p(arb_point),
            force_N=_p(arb_side.force_on_rocker_N),
            source_id=arb_link_result.fixture_id or "AUTH-SUSP-0013",
            frame_id=frame_id,
            configuration_id=configuration_id,
            load_case_id=load_case_id,
        ),
    )
    included = evaluate_rocker_included_load(
        rocker_pivot_m=spring_pivot,
        rocker_axis=spring_axis,
        loads=loads,
        missing_load_ids=("KW_V5_non_spring_static_force",),
        frame_id=frame_id,
        configuration_id=configuration_id,
        load_case_id=load_case_id,
        axle=axle,
        side=side,
        config=kernel_config,
    )
    if not included.ok:
        return WufrRockerIncludedLoadResult(
            status=WufrRockerIncludedLoadStatus.FAILURE,
            axle=axle,
            side=side,
            frame_id=frame_id,
            configuration_id=configuration_id,
            geometry_source_id=interface_result.geometry_source_id,
            load_case_id=load_case_id,
            external_wrench_source_id=interface_result.external_wrench_source_id,
            arb_fixture_id=arb_fixture.fixture_id,
            included_result=included,
            complete_hardware_reaction=False,
            failure_code=WufrRockerIncludedLoadFailureCode.INCLUDED_LOAD_KERNEL_FAILURE,
            message=included.message,
        )

    return WufrRockerIncludedLoadResult(
        status=WufrRockerIncludedLoadStatus.SUCCESS,
        axle=axle,
        side=side,
        frame_id=frame_id,
        configuration_id=configuration_id,
        geometry_source_id=interface_result.geometry_source_id,
        load_case_id=load_case_id,
        external_wrench_source_id=interface_result.external_wrench_source_id,
        arb_fixture_id=arb_fixture.fixture_id,
        included_result=included,
        complete_hardware_reaction=False,
    )
