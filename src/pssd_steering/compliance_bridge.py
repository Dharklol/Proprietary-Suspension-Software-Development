"""Opt-in, prescribed-torque elastic steering comparison composed with MOD-STEER-0001.

Uses the existing staged transmission and rigid corner solver without changing
their kinematics, source contracts, or force/tyre states. This does not solve
closed-loop tyre aligning moments or rotational backlash/hysteresis.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from .compliance import (
    CircularSpan, ComplianceDefinitionError, ComplianceResult, evaluate_circular_spans,
)
from .core import (
    FailureCode, HeadingResult, PositionResult, SolverSettings, SteeringGeometry,
    evaluate_wheel_heading, solve_sweep,
)
from .derived import TransmissionResult, staged_transmission


@dataclass(frozen=True)
class SteeringTransmission:
    """Explicit signed driver-to-pinion and pinion-to-rack transmission map.

    For the provisional WUFR-27 1:1 gearbox, pinion_angle_per_input_rad is
    nominally +/-1 depending on angle convention. Rack travel must come from
    a reviewed rack specification, not from a guessed steering ratio.
    """

    pinion_angle_per_input_rad: float
    rack_m_per_pinion_rad: float
    authority: str

    def __post_init__(self) -> None:
        if (not self.authority.strip()
                or not all(math.isfinite(x) for x in (
                    self.pinion_angle_per_input_rad, self.rack_m_per_pinion_rad))
                or self.pinion_angle_per_input_rad == 0
                or self.rack_m_per_pinion_rad == 0):
            raise ComplianceDefinitionError(
                "transmission requires nonzero signed ratios and an authority"
            )


@dataclass(frozen=True)
class PrescribedTorqueInput:
    """One explicit measured/calculated/synthetic *input shaft* torque case.

    Signed angle and signed torque are defined in the driver-input frame.
    Reversals and cases with negative torque are supported. The torque is
    external; no tire forces or driver behavior are inferred.
    """

    steering_wheel_rad: float
    input_torque_nm: float
    torque_authority: str

    def __post_init__(self) -> None:
        if (not self.torque_authority.strip()
                or not math.isfinite(self.steering_wheel_rad)
                or not math.isfinite(self.input_torque_nm)):
            raise ComplianceDefinitionError("case requires finite angle/torque and authority")


@dataclass(frozen=True)
class CornerComparison:
    rigid_position: PositionResult
    elastic_position: PositionResult
    rigid_heading: HeadingResult
    elastic_heading: HeadingResult

    @property
    def incremental_heading_difference_rad(self) -> float | None:
        if (not self.rigid_heading.available or not self.elastic_heading.available
                or self.rigid_heading.incremental_heading is None
                or self.elastic_heading.incremental_heading is None):
            return None
        return (self.elastic_heading.incremental_heading
                - self.rigid_heading.incremental_heading)


@dataclass(frozen=True)
class SteeringComplianceComparison:
    case: PrescribedTorqueInput
    elastic_twist: ComplianceResult
    effective_steering_wheel_rad: float
    rigid_transmission: TransmissionResult
    elastic_transmission: TransmissionResult
    left: CornerComparison
    right: CornerComparison

    @property
    def both_mechanisms_valid(self) -> bool:
        return all((
            self.left.rigid_position.ok, self.left.elastic_position.ok,
            self.right.rigid_position.ok, self.right.elastic_position.ok,
        ))


def _heading_or_failure(geometry: SteeringGeometry, side: str,
                        position: PositionResult) -> HeadingResult:
    if not position.ok or position.upright_rotation is None:
        return HeadingResult(
            available=False,
            failure_code=position.failure_code or FailureCode.DERIVED_OUTPUT_UNAVAILABLE,
            message=position.message or "rigid solution unavailable",
        )
    corner = geometry.left if side == "left" else geometry.right
    return evaluate_wheel_heading(corner, position.upright_rotation)


def evaluate_prescribed_torque_sweep(
    geometry: SteeringGeometry,
    cases: Sequence[PrescribedTorqueInput],
    transmission: SteeringTransmission,
    *,
    spans: tuple[CircularSpan, ...],
    settings: SolverSettings | None = None,
) -> tuple[SteeringComplianceComparison, ...]:
    """Compare rigid and loaded steering with explicit prescribed input torques.

    Each case produces TWO solutions at the same driver angle: no elastic
    twist, and with input-referenced twist subtracted *before* transmission.
    Existing rigid solve_sweep handles bounds, branch selection, and failures.
    Results are never silently clipped or extrapolated.

    Only elastic free-span torsion is included. For non-1:1 ratios, the caller
    must supply appropriately input-referenced span compliances (torque and
    angle multipliers) and justify their coordinate conversion. The current
    WUFR-27 fixture is justified only for nominal 1:1 bevel gearing.
    """
    if not cases:
        raise ComplianceDefinitionError("at least one input case is required")
    # Validate all configured spans and calculate their individual contributions
    # before asking either rigid solver to evaluate a sample.
    twists = tuple(evaluate_circular_spans(spans, case.input_torque_nm)
                   for case in cases)
    rigid = tuple(staged_transmission(
        case.steering_wheel_rad, transmission.pinion_angle_per_input_rad,
        transmission.rack_m_per_pinion_rad) for case in cases)
    elastic_angles = tuple(case.steering_wheel_rad - twist.twist_rad
                           for case, twist in zip(cases, twists))
    if not all(math.isfinite(x) for x in elastic_angles):
        raise ComplianceDefinitionError("computed effective input angle is nonfinite")
    elastic = tuple(staged_transmission(
        angle, transmission.pinion_angle_per_input_rad,
        transmission.rack_m_per_pinion_rad) for angle in elastic_angles)
    for item in (*rigid, *elastic):
        if not math.isfinite(item.rack_displacement):
            raise ComplianceDefinitionError("computed rack travel is nonfinite")
    rigid_positions = solve_sweep(
        geometry, [item.rack_displacement for item in rigid], settings=settings)
    elastic_positions = solve_sweep(
        geometry, [item.rack_displacement for item in elastic], settings=settings)
    response = []
    for index, case in enumerate(cases):
        comparisons = {}
        for side in ("left", "right"):
            rp = rigid_positions[side][index]
            ep = elastic_positions[side][index]
            comparisons[side] = CornerComparison(
                rigid_position=rp,
                elastic_position=ep,
                rigid_heading=_heading_or_failure(geometry, side, rp),
                elastic_heading=_heading_or_failure(geometry, side, ep),
            )
        response.append(SteeringComplianceComparison(
            case=case, elastic_twist=twists[index],
            effective_steering_wheel_rad=elastic_angles[index],
            rigid_transmission=rigid[index],
            elastic_transmission=elastic[index],
            left=comparisons["left"], right=comparisons["right"],
        ))
    return tuple(response)
