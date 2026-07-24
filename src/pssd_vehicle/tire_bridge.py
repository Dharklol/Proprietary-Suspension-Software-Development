"""Bridge explicit vehicle wheel states into the reusable tire-data contract.

No load transfer, camber, pressure, or force-demand values are inferred here.  The
bridge only assigns front inside/outside identities from an explicit turn direction
and converts a wheel record to ``TireOperatingPoint`` when all required values were
supplied upstream.
"""

from __future__ import annotations

from dataclasses import dataclass

from pssd_tire import TireOperatingPoint

from .operating_states import (
    LATERAL_TIRE_DEMAND_FIELDS,
    TIRE_OPERATING_POINT_FIELDS,
    TurnDirection,
    VehicleOperatingState,
    VehicleStateError,
    WheelOperatingState,
    WheelPosition,
)


@dataclass(frozen=True)
class FrontWheelAssignment:
    inside_position: WheelPosition
    outside_position: WheelPosition
    inside_wheel: WheelOperatingState
    outside_wheel: WheelOperatingState


@dataclass(frozen=True)
class FrontTireOperatingPair:
    inside_position: WheelPosition
    outside_position: WheelPosition
    inside: TireOperatingPoint
    outside: TireOperatingPoint


def front_inside_outside_assignment(state: VehicleOperatingState) -> FrontWheelAssignment:
    """Assign front inside/outside wheels from the state's explicit turn direction."""

    if state.turn_direction is TurnDirection.LEFT:
        inside_position = WheelPosition.FRONT_LEFT
        outside_position = WheelPosition.FRONT_RIGHT
    elif state.turn_direction is TurnDirection.RIGHT:
        inside_position = WheelPosition.FRONT_RIGHT
        outside_position = WheelPosition.FRONT_LEFT
    else:
        raise VehicleStateError(
            f"State {state.state_id!r} must declare left or right turn direction "
            "before front inside/outside tire roles can be assigned"
        )
    return FrontWheelAssignment(
        inside_position=inside_position,
        outside_position=outside_position,
        inside_wheel=state.wheel(inside_position),
        outside_wheel=state.wheel(outside_position),
    )


def tire_operating_point_from_wheel(wheel: WheelOperatingState) -> TireOperatingPoint:
    """Convert one complete wheel state without adding any missing quantities."""

    missing = wheel.completeness_record(TIRE_OPERATING_POINT_FIELDS)
    if missing:
        detail = "; ".join(f"{name}: {reason}" for name, reason in missing.items())
        raise VehicleStateError(
            f"{wheel.position.value} cannot become TireOperatingPoint because {detail}"
        )
    assert wheel.normal_load_n is not None
    assert wheel.inclination_deg is not None
    assert wheel.pressure_kpa is not None
    if wheel.normal_load_n <= 0.0:
        raise VehicleStateError(
            f"{wheel.position.value} has no positive tire contact load; "
            "TireOperatingPoint requires normal_load_n > 0"
        )
    return TireOperatingPoint(
        normal_load_n=wheel.normal_load_n,
        inclination_deg=wheel.inclination_deg,
        pressure_kpa=wheel.pressure_kpa,
    )


def front_tire_operating_pair(state: VehicleOperatingState) -> FrontTireOperatingPair:
    assignment = front_inside_outside_assignment(state)
    return FrontTireOperatingPair(
        inside_position=assignment.inside_position,
        outside_position=assignment.outside_position,
        inside=tire_operating_point_from_wheel(assignment.inside_wheel),
        outside=tire_operating_point_from_wheel(assignment.outside_wheel),
    )


def front_tire_readiness(state: VehicleOperatingState) -> dict[str, dict[str, dict[str, str]]]:
    """Expose missing data for PR28 operating points and future Fy-demand inversion."""

    return {
        "tire_operating_point": state.missing_front_fields(TIRE_OPERATING_POINT_FIELDS),
        "lateral_tire_demand": state.missing_front_fields(LATERAL_TIRE_DEMAND_FIELDS),
    }
