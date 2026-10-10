"""Provider-backed readiness diagnostics, separate from design authorization."""

from dataclasses import dataclass, replace
from math import radians

from pssd_tire.force_demand import LateralForceDemandResult, TireLateralForceBranchSet
from pssd_tire.lateral import TireDataError
from pssd_tire.steady_state_lateral import (
    SteadyStateLateralFailure, SteadyStateLateralInverseResult,
    SteadyStateLateralTable, invert_lateral_force,
)
from .operating_states import LATERAL_TIRE_DEMAND_FIELDS, WheelPosition
from .synced_state import SyncedStateSample
from .tire_bridge import tire_operating_point_from_wheel


@dataclass(frozen=True)
class WheelTireReadiness:
    position: WheelPosition
    status: str
    reasons: tuple[tuple[str, str], ...]
    provider_result: LateralForceDemandResult | SteadyStateLateralInverseResult | None = None
    provider_source: SteadyStateLateralTable | TireLateralForceBranchSet | None = None


def signed_runtime_readiness(
    sample: SyncedStateSample, table: SteadyStateLateralTable, *,
    source_tire_id: str, source_convention_id: str, branch_selector: str | None = None,
) -> tuple[WheelTireReadiness, ...]:
    """Use the complete-cell signed inverse; preserve failures and all roots."""
    results = []
    for position in (WheelPosition.FRONT_LEFT, WheelPosition.FRONT_RIGHT):
        wheel = sample.vehicle.wheel(position)
        missing = wheel.completeness_record(LATERAL_TIRE_DEMAND_FIELDS)
        if missing:
            results.append(WheelTireReadiness(position, "missing_inputs", tuple(missing.items())))
            continue
        try:
            point = tire_operating_point_from_wheel(wheel)
            result = invert_lateral_force(
                table, normal_load_N=point.normal_load_n,
                inclination_rad=radians(point.inclination_deg),
                pressure_Pa=1000.0 * point.pressure_kpa,
                requested_lateral_force_N=wheel.lateral_force_demand_n,
                source_id=source_tire_id, source_convention_id=source_convention_id,
                state_id=sample.vehicle_source.sample_id, branch_selector=branch_selector,
            )
        except SteadyStateLateralFailure as error:
            results.append(WheelTireReadiness(position, "provider_failure",
                                             ((error.failure_code, error.message),)))
        except ValueError as error:
            results.append(WheelTireReadiness(position, "invalid_contact", (("contact", str(error)),)))
        else:
            results.append(WheelTireReadiness(
                position, result.status,
                ((result.failure_code, result.message),) if result.failure_code else (), result,
            ))
    return tuple(replace(result, provider_source=table) for result in results)


def magnitude_branch_readiness(
    sample: SyncedStateSample, branch_set: TireLateralForceBranchSet,
) -> tuple[WheelTireReadiness, ...]:
    """Separate exact-state magnitude gate; never imply signed-model feasibility."""
    results = []
    for position in (WheelPosition.FRONT_LEFT, WheelPosition.FRONT_RIGHT):
        wheel = sample.vehicle.wheel(position)
        missing = wheel.completeness_record(LATERAL_TIRE_DEMAND_FIELDS)
        if missing:
            results.append(WheelTireReadiness(position, "missing_inputs", tuple(missing.items())))
            continue
        try:
            point = tire_operating_point_from_wheel(wheel)
            branch_set.branch_for(point)
        except (TireDataError, ValueError) as error:
            results.append(WheelTireReadiness(position, "exact_branch_unavailable",
                                             (("exact_branch_inverse", str(error)),)))
            continue
        try:
            # This is an explicitly labelled magnitude query, not a signed force repair.
            result = branch_set.invert(point, abs(wheel.lateral_force_demand_n))
        except TireDataError as error:
            results.append(WheelTireReadiness(position, "force_demand_infeasible",
                                             (("exact_branch_inverse", str(error)),)))
        else:
            results.append(WheelTireReadiness(position, "magnitude_branch_ready", (), result))
    return tuple(replace(result, provider_source=branch_set) for result in results)
