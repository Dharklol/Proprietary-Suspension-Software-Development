"""Tire-informed differential steering target adapter.

The adapter converts reviewed tire lateral summaries into an explicit correction to
geometric Ackermann. It does not solve tire forces, load transfer, suspension motion,
or vehicle equilibrium. A caller supplies the inside/outside tire operating points
and an explicit slip-utilization schedule; the existing steering target contract
supplies rack sampling and the inside-wheel heading trajectory.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from pssd_tire import (
    LateralSummaryEstimate,
    TireDataError,
    TireLateralSummaryGrid,
    TireOperatingPoint,
)

from ..derived import assign_inside_outside, exact_ackermann_outside_reference
from .operating_targets import (
    OperatingStateTarget,
    OperatingStateTargetSet,
    OperatingTargetRole,
)
from .poses import SuspensionPoseSet
from .targets import SteeringTarget, TargetDefinitionError


@dataclass(frozen=True)
class TireSlipDifferential:
    """Peak-slip summary for explicit inside/outside tire operating points."""

    inside: LateralSummaryEstimate
    outside: LateralSummaryEstimate

    @property
    def outside_minus_inside_peak_slip_deg(self) -> float:
        return (
            self.outside.peak_slip_angle_magnitude_deg
            - self.inside.peak_slip_angle_magnitude_deg
        )


@dataclass(frozen=True)
class TireDifferentialStateDefinition:
    """One steering state with externally supplied tire operating points."""

    state_id: str
    inside_operating_point: TireOperatingPoint
    outside_operating_point: TireOperatingPoint
    slip_utilization_by_sample: tuple[float, ...]
    objective_weight: float = 1.0
    normalization_scale_deg: float = 1.0
    authority: str = ""
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.state_id:
            raise TargetDefinitionError("Tire differential state requires state_id")
        if len(self.slip_utilization_by_sample) < 3:
            raise TargetDefinitionError(
                "Tire differential state requires at least three samples"
            )
        if not all(
            math.isfinite(value) and 0.0 <= value <= 1.0
            for value in self.slip_utilization_by_sample
        ):
            raise TargetDefinitionError(
                "slip_utilization_by_sample must be finite and inside [0, 1]"
            )
        if not math.isfinite(self.objective_weight) or self.objective_weight <= 0.0:
            raise TargetDefinitionError(
                "Tire differential objective_weight must be positive"
            )
        if (
            not math.isfinite(self.normalization_scale_deg)
            or self.normalization_scale_deg <= 0.0
        ):
            raise TargetDefinitionError(
                "Tire differential normalization_scale_deg must be positive"
            )


def peak_grip_slip_angle_differential(
    grid: TireLateralSummaryGrid,
    inside_operating_point: TireOperatingPoint,
    outside_operating_point: TireOperatingPoint,
) -> TireSlipDifferential:
    """Return uncensored peak-slip magnitudes for an explicit tire state pair."""

    inside = grid.estimate(inside_operating_point, require_uncensored_peak=True)
    outside = grid.estimate(outside_operating_point, require_uncensored_peak=True)
    return TireSlipDifferential(inside=inside, outside=outside)


def _tire_informed_pair(
    sampling_target: SteeringTarget,
    index: int,
    *,
    wheelbase_m: float,
    steering_axis_track_m: float,
    peak_slip_differential_deg: float,
    slip_utilization: float,
) -> tuple[float, float]:
    sign_adapter = sampling_target.canonical_to_target_output_sign
    left_canonical = sign_adapter * sampling_target.left_outputs[index]
    right_canonical = sign_adapter * sampling_target.right_outputs[index]
    if abs(left_canonical) + abs(right_canonical) <= 1.0e-12:
        return sampling_target.left_outputs[index], sampling_target.right_outputs[index]

    assignment = assign_inside_outside(
        math.radians(left_canonical), math.radians(right_canonical)
    )
    outside_ackermann = exact_ackermann_outside_reference(
        assignment.inside_incremental_magnitude,
        wheelbase_m,
        steering_axis_track_m,
    )
    corrected_outside_magnitude = outside_ackermann + math.radians(
        slip_utilization * peak_slip_differential_deg
    )
    if corrected_outside_magnitude <= 0.0:
        raise TargetDefinitionError(
            "Tire differential correction produced a nonpositive outside-wheel heading magnitude"
        )

    turn_sign = 1.0 if assignment.turn_direction == "left" else -1.0
    inside_canonical_deg = (
        left_canonical if assignment.inside_side == "left" else right_canonical
    )
    outside_canonical_deg = math.degrees(turn_sign * corrected_outside_magnitude)

    if assignment.inside_side == "left":
        desired_left_canonical = inside_canonical_deg
        desired_right_canonical = outside_canonical_deg
    else:
        desired_left_canonical = outside_canonical_deg
        desired_right_canonical = inside_canonical_deg
    return (
        sign_adapter * desired_left_canonical,
        sign_adapter * desired_right_canonical,
    )


def build_tire_informed_operating_target_set(
    sampling_target: SteeringTarget,
    pose_set: SuspensionPoseSet,
    tire_grid: TireLateralSummaryGrid,
    state_definitions: Iterable[TireDifferentialStateDefinition],
    *,
    target_set_id: str,
    version: str,
    wheelbase_m: float,
    steering_axis_track_m: float,
    authority: str,
    source_path: str = "",
) -> OperatingStateTargetSet:
    """Build state targets from geometric Ackermann plus explicit tire slip differential.

    The model is deliberately differential. For each nonzero sample it preserves the
    base target's inside-wheel incremental heading, computes the exact zero-slip
    Ackermann outside reference from that magnitude, then applies

        delta_out = delta_out,Ackermann + u * (alpha*_out - alpha*_in)

    where ``u`` is a caller-supplied [0, 1] slip-utilization schedule. Thus load,
    camber, pressure states and force-demand scheduling remain provider inputs rather
    than hidden steering assumptions. This is not a full steady-state vehicle solve.
    """

    numeric = (wheelbase_m, steering_axis_track_m)
    if not all(math.isfinite(value) and value > 0.0 for value in numeric):
        raise TargetDefinitionError(
            "wheelbase_m and steering_axis_track_m must be positive"
        )
    definitions = tuple(state_definitions)
    if not definitions:
        raise TargetDefinitionError(
            "At least one tire-informed objective state is required"
        )
    known_states = set(pose_set.state_map)
    unknown = sorted({item.state_id for item in definitions} - known_states)
    if unknown:
        raise TargetDefinitionError(
            f"Tire-informed targets reference unknown pose states: {unknown}"
        )
    ids = [item.state_id for item in definitions]
    if len(ids) != len(set(ids)):
        raise TargetDefinitionError(
            "Tire-informed target definitions contain duplicate state IDs"
        )

    count = len(sampling_target.rack_displacements)
    try:
        centered_index = sampling_target.rack_displacements.index(0.0)
    except ValueError as exc:
        raise TargetDefinitionError(
            "Tire-informed target requires an exact centered rack sample"
        ) from exc

    state_targets: list[OperatingStateTarget] = []
    for definition in definitions:
        if len(definition.slip_utilization_by_sample) != count:
            raise TargetDefinitionError(
                f"Tire state {definition.state_id!r} utilization length does not match rack sampling"
            )
        if abs(definition.slip_utilization_by_sample[centered_index]) > 1.0e-12:
            raise TargetDefinitionError(
                f"Tire state {definition.state_id!r} must use zero slip utilization at rack center"
            )
        try:
            differential = peak_grip_slip_angle_differential(
                tire_grid,
                definition.inside_operating_point,
                definition.outside_operating_point,
            )
        except TireDataError as exc:
            raise TargetDefinitionError(
                f"Tire state {definition.state_id!r} cannot produce an uncensored peak-slip target: {exc}"
            ) from exc

        left: list[float] = []
        right: list[float] = []
        for index, utilization in enumerate(
            definition.slip_utilization_by_sample
        ):
            left_value, right_value = _tire_informed_pair(
                sampling_target,
                index,
                wheelbase_m=wheelbase_m,
                steering_axis_track_m=steering_axis_track_m,
                peak_slip_differential_deg=(
                    differential.outside_minus_inside_peak_slip_deg
                ),
                slip_utilization=utilization,
            )
            left.append(left_value)
            right.append(right_value)

        state_targets.append(
            OperatingStateTarget(
                state_id=definition.state_id,
                role=OperatingTargetRole.OBJECTIVE,
                objective_id=(
                    f"tire_informed_differential_heading:{definition.state_id}"
                ),
                output_quantity_id=(
                    "incremental_projected_road_wheel_heading_from_pose"
                ),
                output_unit="deg",
                left_outputs=tuple(left),
                right_outputs=tuple(right),
                sample_weights=sampling_target.weights,
                normalization_scale_deg=definition.normalization_scale_deg,
                objective_weight=definition.objective_weight,
                canonical_to_target_output_sign=(
                    sampling_target.canonical_to_target_output_sign
                ),
                require_monotonic_response=(
                    sampling_target.require_monotonic_response
                ),
                monotonic_tolerance_deg=sampling_target.monotonic_tolerance_deg,
                source_type="tire_informed_peak_slip_differential",
                authority=definition.authority or authority,
                source_path=source_path,
                provenance=(
                    ("tire_grid_id", tire_grid.grid_id),
                    ("source_tire_id", tire_grid.source_tire_id),
                    ("intended_tire_id", tire_grid.intended_tire_id),
                    (
                        "inside_peak_slip_deg",
                        f"{differential.inside.peak_slip_angle_magnitude_deg:.17g}",
                    ),
                    (
                        "outside_peak_slip_deg",
                        f"{differential.outside.peak_slip_angle_magnitude_deg:.17g}",
                    ),
                    (
                        "outside_minus_inside_peak_slip_deg",
                        f"{differential.outside_minus_inside_peak_slip_deg:.17g}",
                    ),
                    (
                        "correction_model",
                        "inside_angle_anchored_ackermann_plus_explicit_slip_differential",
                    ),
                )
                + definition.provenance,
            )
        )

    return OperatingStateTargetSet(
        target_set_id=target_set_id,
        version=version,
        pose_set_id=pose_set.pose_set_id,
        sampling_target=sampling_target,
        state_targets=tuple(state_targets),
        aggregation_method="sum_weighted_normalized_state_rms",
        unlisted_state_role=OperatingTargetRole.REPORT_ONLY,
        authority=authority,
        source_path=source_path,
        provenance=(
            ("sampling_target_id", sampling_target.target_id),
            ("tire_grid_id", tire_grid.grid_id),
            ("source_tire_id", tire_grid.source_tire_id),
            ("intended_tire_id", tire_grid.intended_tire_id),
            (
                "adapter",
                "geometric_ackermann_plus_tire_peak_slip_differential_v0.1.0",
            ),
            ("evaluator_model_id", "MOD-STEER-0001"),
        ),
    )
