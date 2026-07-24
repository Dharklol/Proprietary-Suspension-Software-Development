"""Force-demand tire-slip steering target adapter and Ackermann-regime diagnostics.

The adapter consumes explicit monotonic tire force-response branches from
``pssd_tire``.  It does not decide wheel loads, camber, pressure, or lateral-force
demand, and it does not solve vehicle equilibrium.  For each explicitly supplied
steering sample it inverts inside/outside ``|Fy|`` demands to required slip-angle
magnitudes, computes their differential, and applies that differential to the exact
zero-slip Ackermann outside-wheel reference.

A positive ``alpha_out - alpha_in`` moves the outside wheel farther into the turn:
it therefore moves the target from Ackermann toward parallel and, if the tire-slip
differential exceeds the geometric Ackermann split, into anti-Ackermann.  The
regime is an output, never a prescribed assumption.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Iterable

from pssd_tire import TireDataError, TireOperatingPoint
from pssd_tire.force_demand import (
    LateralForceDemandResult,
    TireLateralForceBranchSet,
)

from ..derived import assign_inside_outside, exact_ackermann_outside_reference
from .operating_targets import (
    OperatingStateTarget,
    OperatingStateTargetSet,
    OperatingTargetRole,
)
from .poses import SuspensionPoseSet
from .targets import SteeringTarget, TargetDefinitionError


class SteeringDifferentialRegime(str, Enum):
    PRO_ACKERMANN = "pro_ackermann"
    PARALLEL = "parallel"
    ANTI_ACKERMANN = "anti_ackermann"


@dataclass(frozen=True)
class ForceDemandSlipDifferential:
    """Inside/outside tire-slip inversion at one explicit force-demand state."""

    inside: LateralForceDemandResult
    outside: LateralForceDemandResult

    @property
    def outside_minus_inside_slip_deg(self) -> float:
        return (
            self.outside.required_slip_angle_magnitude_deg
            - self.inside.required_slip_angle_magnitude_deg
        )


@dataclass(frozen=True)
class DifferentialHeadingReference:
    """Geometric Ackermann reference plus a supplied tire-slip differential."""

    inside_heading_magnitude_deg: float
    ackermann_outside_heading_magnitude_deg: float
    slip_differential_deg: float
    corrected_outside_heading_magnitude_deg: float
    ackermann_inside_minus_outside_gap_deg: float
    corrected_inside_minus_outside_gap_deg: float
    regime: SteeringDifferentialRegime


@dataclass(frozen=True)
class ForceDemandStateDefinition:
    """One target state with explicit tire operating points and force schedules."""

    state_id: str
    inside_operating_point: TireOperatingPoint
    outside_operating_point: TireOperatingPoint
    inside_lateral_force_magnitude_by_sample: tuple[float, ...]
    outside_lateral_force_magnitude_by_sample: tuple[float, ...]
    objective_weight: float = 1.0
    normalization_scale_deg: float = 1.0
    authority: str = ""
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.state_id:
            raise TargetDefinitionError("Force-demand target state requires state_id")
        if len(self.inside_lateral_force_magnitude_by_sample) < 3:
            raise TargetDefinitionError(
                "Force-demand target state requires at least three steering samples"
            )
        if len(self.inside_lateral_force_magnitude_by_sample) != len(
            self.outside_lateral_force_magnitude_by_sample
        ):
            raise TargetDefinitionError(
                "Inside/outside force-demand schedules must have equal length"
            )
        values = (
            *self.inside_lateral_force_magnitude_by_sample,
            *self.outside_lateral_force_magnitude_by_sample,
        )
        if not all(math.isfinite(value) and value >= 0.0 for value in values):
            raise TargetDefinitionError(
                "Lateral-force demand magnitudes must be finite and nonnegative"
            )
        if not math.isfinite(self.objective_weight) or self.objective_weight <= 0.0:
            raise TargetDefinitionError("Force-demand objective_weight must be positive")
        if (
            not math.isfinite(self.normalization_scale_deg)
            or self.normalization_scale_deg <= 0.0
        ):
            raise TargetDefinitionError(
                "Force-demand normalization_scale_deg must be positive"
            )


def classify_heading_pair(
    inside_heading_magnitude_deg: float,
    outside_heading_magnitude_deg: float,
    *,
    tolerance_deg: float = 1.0e-9,
) -> SteeringDifferentialRegime:
    """Classify the left/right steering split without assuming the desired regime."""

    values = (
        inside_heading_magnitude_deg,
        outside_heading_magnitude_deg,
        tolerance_deg,
    )
    if not all(math.isfinite(value) for value in values):
        raise TargetDefinitionError("Steering-regime inputs must be finite")
    if inside_heading_magnitude_deg < 0.0 or outside_heading_magnitude_deg < 0.0:
        raise TargetDefinitionError("Steering-regime heading magnitudes cannot be negative")
    if tolerance_deg < 0.0:
        raise TargetDefinitionError("Steering-regime tolerance cannot be negative")

    difference = inside_heading_magnitude_deg - outside_heading_magnitude_deg
    if abs(difference) <= tolerance_deg:
        return SteeringDifferentialRegime.PARALLEL
    if difference > 0.0:
        return SteeringDifferentialRegime.PRO_ACKERMANN
    return SteeringDifferentialRegime.ANTI_ACKERMANN


def differential_heading_reference(
    inside_heading_magnitude_deg: float,
    *,
    wheelbase_m: float,
    steering_axis_track_m: float,
    slip_differential_deg: float,
    regime_tolerance_deg: float = 1.0e-9,
) -> DifferentialHeadingReference:
    """Apply ``alpha_out-alpha_in`` to the exact Ackermann outside reference."""

    numeric = (
        inside_heading_magnitude_deg,
        wheelbase_m,
        steering_axis_track_m,
        slip_differential_deg,
    )
    if not all(math.isfinite(value) for value in numeric):
        raise TargetDefinitionError("Differential heading inputs must be finite")
    if inside_heading_magnitude_deg < 0.0:
        raise TargetDefinitionError("Inside heading magnitude cannot be negative")
    if wheelbase_m <= 0.0 or steering_axis_track_m <= 0.0:
        raise TargetDefinitionError("Wheelbase and steering-axis track must be positive")

    if inside_heading_magnitude_deg <= 1.0e-15:
        ackermann_outside_deg = 0.0
    else:
        ackermann_outside_deg = math.degrees(
            exact_ackermann_outside_reference(
                math.radians(inside_heading_magnitude_deg),
                wheelbase_m,
                steering_axis_track_m,
            )
        )
    corrected_outside_deg = ackermann_outside_deg + slip_differential_deg
    if corrected_outside_deg < 0.0:
        raise TargetDefinitionError(
            "Tire-slip differential produced a negative outside-wheel heading magnitude"
        )
    return DifferentialHeadingReference(
        inside_heading_magnitude_deg=inside_heading_magnitude_deg,
        ackermann_outside_heading_magnitude_deg=ackermann_outside_deg,
        slip_differential_deg=slip_differential_deg,
        corrected_outside_heading_magnitude_deg=corrected_outside_deg,
        ackermann_inside_minus_outside_gap_deg=(
            inside_heading_magnitude_deg - ackermann_outside_deg
        ),
        corrected_inside_minus_outside_gap_deg=(
            inside_heading_magnitude_deg - corrected_outside_deg
        ),
        regime=classify_heading_pair(
            inside_heading_magnitude_deg,
            corrected_outside_deg,
            tolerance_deg=regime_tolerance_deg,
        ),
    )


def force_demand_slip_differential(
    branch_set: TireLateralForceBranchSet,
    inside_operating_point: TireOperatingPoint,
    outside_operating_point: TireOperatingPoint,
    *,
    inside_lateral_force_magnitude_n: float,
    outside_lateral_force_magnitude_n: float,
) -> ForceDemandSlipDifferential:
    """Invert explicit inside/outside force demands without a tire-force solver."""

    inside = branch_set.invert(
        inside_operating_point, inside_lateral_force_magnitude_n
    )
    outside = branch_set.invert(
        outside_operating_point, outside_lateral_force_magnitude_n
    )
    return ForceDemandSlipDifferential(inside=inside, outside=outside)


def _force_demand_pair(
    sampling_target: SteeringTarget,
    index: int,
    *,
    wheelbase_m: float,
    steering_axis_track_m: float,
    slip_differential_deg: float,
) -> tuple[float, float, DifferentialHeadingReference]:
    """Preserve the base inside heading and correct the exact Ackermann outside side."""

    sign_adapter = sampling_target.canonical_to_target_output_sign
    left_canonical = sign_adapter * sampling_target.left_outputs[index]
    right_canonical = sign_adapter * sampling_target.right_outputs[index]
    if abs(left_canonical) + abs(right_canonical) <= 1.0e-12:
        reference = differential_heading_reference(
            0.0,
            wheelbase_m=wheelbase_m,
            steering_axis_track_m=steering_axis_track_m,
            slip_differential_deg=0.0,
        )
        return (
            sampling_target.left_outputs[index],
            sampling_target.right_outputs[index],
            reference,
        )

    assignment = assign_inside_outside(
        math.radians(left_canonical), math.radians(right_canonical)
    )
    inside_canonical_deg = (
        left_canonical if assignment.inside_side == "left" else right_canonical
    )
    inside_magnitude_deg = abs(inside_canonical_deg)
    reference = differential_heading_reference(
        inside_magnitude_deg,
        wheelbase_m=wheelbase_m,
        steering_axis_track_m=steering_axis_track_m,
        slip_differential_deg=slip_differential_deg,
    )

    turn_sign = 1.0 if assignment.turn_direction == "left" else -1.0
    outside_canonical_deg = turn_sign * reference.corrected_outside_heading_magnitude_deg
    if assignment.inside_side == "left":
        desired_left_canonical = inside_canonical_deg
        desired_right_canonical = outside_canonical_deg
    else:
        desired_left_canonical = outside_canonical_deg
        desired_right_canonical = inside_canonical_deg
    return (
        sign_adapter * desired_left_canonical,
        sign_adapter * desired_right_canonical,
        reference,
    )


def build_force_demand_operating_target_set(
    sampling_target: SteeringTarget,
    pose_set: SuspensionPoseSet,
    branch_set: TireLateralForceBranchSet,
    state_definitions: Iterable[ForceDemandStateDefinition],
    *,
    target_set_id: str,
    version: str,
    wheelbase_m: float,
    steering_axis_track_m: float,
    authority: str,
    source_path: str = "",
) -> OperatingStateTargetSet:
    """Build steering targets from explicit force demand -> required slip inversion.

    Force demand is supplied independently for every steering sample.  The centered
    sample must use zero demands as the explicit no-turn sentinel; it is copied from
    the sampling target without querying a directional tire branch.  All nonzero
    samples are bounded by the exact source branches and fail rather than extrapolate.
    """

    if not all(
        math.isfinite(value) and value > 0.0
        for value in (wheelbase_m, steering_axis_track_m)
    ):
        raise TargetDefinitionError("Wheelbase and steering-axis track must be positive")
    definitions = tuple(state_definitions)
    if not definitions:
        raise TargetDefinitionError("At least one force-demand target state is required")
    known_states = set(pose_set.state_map)
    unknown = sorted({item.state_id for item in definitions} - known_states)
    if unknown:
        raise TargetDefinitionError(
            f"Force-demand targets reference unknown pose states: {unknown}"
        )
    ids = [item.state_id for item in definitions]
    if len(ids) != len(set(ids)):
        raise TargetDefinitionError("Force-demand target definitions contain duplicate state IDs")

    count = len(sampling_target.rack_displacements)
    try:
        centered_index = sampling_target.rack_displacements.index(0.0)
    except ValueError as exc:
        raise TargetDefinitionError(
            "Force-demand target requires an exact centered rack sample"
        ) from exc

    state_targets: list[OperatingStateTarget] = []
    for definition in definitions:
        if len(definition.inside_lateral_force_magnitude_by_sample) != count:
            raise TargetDefinitionError(
                f"Force-demand state {definition.state_id!r} schedule length does not match rack sampling"
            )
        if (
            abs(definition.inside_lateral_force_magnitude_by_sample[centered_index])
            > 1.0e-12
            or abs(definition.outside_lateral_force_magnitude_by_sample[centered_index])
            > 1.0e-12
        ):
            raise TargetDefinitionError(
                f"Force-demand state {definition.state_id!r} must use zero center demands"
            )

        left: list[float] = []
        right: list[float] = []
        regimes: list[str] = []
        slip_differentials: list[float] = []
        for index, (inside_force, outside_force) in enumerate(
            zip(
                definition.inside_lateral_force_magnitude_by_sample,
                definition.outside_lateral_force_magnitude_by_sample,
            )
        ):
            if index == centered_index:
                left.append(sampling_target.left_outputs[index])
                right.append(sampling_target.right_outputs[index])
                regimes.append(SteeringDifferentialRegime.PARALLEL.value)
                slip_differentials.append(0.0)
                continue
            try:
                differential = force_demand_slip_differential(
                    branch_set,
                    definition.inside_operating_point,
                    definition.outside_operating_point,
                    inside_lateral_force_magnitude_n=inside_force,
                    outside_lateral_force_magnitude_n=outside_force,
                )
            except TireDataError as exc:
                raise TargetDefinitionError(
                    f"Force-demand state {definition.state_id!r} sample {index} cannot invert tire demand: {exc}"
                ) from exc
            slip_differential = differential.outside_minus_inside_slip_deg
            left_value, right_value, reference = _force_demand_pair(
                sampling_target,
                index,
                wheelbase_m=wheelbase_m,
                steering_axis_track_m=steering_axis_track_m,
                slip_differential_deg=slip_differential,
            )
            left.append(left_value)
            right.append(right_value)
            regimes.append(reference.regime.value)
            slip_differentials.append(slip_differential)

        regime_counts = {
            regime.value: regimes.count(regime.value)
            for regime in SteeringDifferentialRegime
        }
        state_targets.append(
            OperatingStateTarget(
                state_id=definition.state_id,
                role=OperatingTargetRole.OBJECTIVE,
                objective_id=f"tire_force_demand_heading:{definition.state_id}",
                output_quantity_id="incremental_projected_road_wheel_heading_from_pose",
                output_unit="deg",
                left_outputs=tuple(left),
                right_outputs=tuple(right),
                sample_weights=sampling_target.weights,
                normalization_scale_deg=definition.normalization_scale_deg,
                objective_weight=definition.objective_weight,
                canonical_to_target_output_sign=sampling_target.canonical_to_target_output_sign,
                require_monotonic_response=sampling_target.require_monotonic_response,
                monotonic_tolerance_deg=sampling_target.monotonic_tolerance_deg,
                source_type="tire_force_demand_slip_differential",
                authority=definition.authority or authority,
                source_path=source_path,
                provenance=(
                    ("tire_branch_set_id", branch_set.branch_set_id),
                    ("source_tire_id", branch_set.source_tire_id),
                    ("intended_tire_id", branch_set.intended_tire_id),
                    (
                        "correction_model",
                        "inside_angle_anchored_ackermann_plus_explicit_force_demand_slip_differential",
                    ),
                    (
                        "regime_counts",
                        ",".join(f"{key}:{regime_counts[key]}" for key in sorted(regime_counts)),
                    ),
                    (
                        "slip_differential_deg_by_sample",
                        ",".join(f"{value:.17g}" for value in slip_differentials),
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
            ("tire_branch_set_id", branch_set.branch_set_id),
            ("source_tire_id", branch_set.source_tire_id),
            ("intended_tire_id", branch_set.intended_tire_id),
            ("adapter", "force_demand_slip_differential_v0.1.0"),
            ("evaluator_model_id", "MOD-STEER-0001"),
        ),
    )
