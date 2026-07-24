"""Motion-aware force-demand tire-slip steering target composition.

PR #30 deliberately used exact low-speed Ackermann as a development reference for
applying an inside/outside required-slip differential.  That is a useful limiting path,
but it implicitly fixes the wheel-center velocity-heading relation to a no-slip
kinematic construction.

This adapter accepts an explicit planar vehicle motion schedule ``(u, v, r)`` from a
separate provider.  It computes the exact front wheel-center velocity headings through
``pssd_vehicle.planar_kinematics``, independently inverts the already-reviewed tire
force branches for inside and outside required slip magnitudes, applies the turn sign,
and forms each wheel's required total heading from

    delta_j = beta_hat_j + alpha_required,j

The returned optimization target remains *incremental from the suspension-pose
reference heading*, matching the existing MOD-STEER-0001 operating-state evaluator.
No vehicle equilibrium, tire-force calculation, load transfer, sideslip response, or
yaw-rate response is solved here.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from pssd_tire import TireDataError, TireOperatingPoint
from pssd_tire.force_demand import TireLateralForceBranchSet
from pssd_vehicle import TurnDirection, WheelPosition
from pssd_vehicle.planar_kinematics import (
    FourWheelPlanarGeometry,
    PlanarKinematicsError,
    PlanarMotionSample,
    PlanarMotionSchedule,
    front_required_heading_pair,
    wrap_angle_rad,
)

from ..projection import reference_from_static_alignment, road_intersection_direction
from .force_demand_targets import SteeringDifferentialRegime, classify_heading_pair
from .operating_targets import (
    OperatingStateTarget,
    OperatingStateTargetSet,
    OperatingTargetRole,
)
from .poses import SteeringPoseState, SuspensionPoseSet, transform_wheel_plane
from .targets import SteeringTarget, TargetDefinitionError


@dataclass(frozen=True)
class MotionAwareForceDemandStateDefinition:
    """One explicit motion/force target state sharing the steering rack sample order."""

    state_id: str
    motion_schedule: PlanarMotionSchedule
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
            raise TargetDefinitionError("Motion-aware force-demand state requires state_id")
        if self.motion_schedule.state_id != self.state_id:
            raise TargetDefinitionError(
                "Motion schedule state_id must match the motion-aware force-demand state_id"
            )
        count = len(self.motion_schedule.samples)
        if count < 3:
            raise TargetDefinitionError("Motion-aware target state requires at least three samples")
        if len(self.inside_lateral_force_magnitude_by_sample) != count or len(
            self.outside_lateral_force_magnitude_by_sample
        ) != count:
            raise TargetDefinitionError(
                "Motion and inside/outside force-demand schedules must have equal lengths"
            )
        values = (
            *self.inside_lateral_force_magnitude_by_sample,
            *self.outside_lateral_force_magnitude_by_sample,
        )
        if not all(math.isfinite(value) and value >= 0.0 for value in values):
            raise TargetDefinitionError(
                "Motion-aware lateral-force demand magnitudes must be finite and nonnegative"
            )
        if not math.isfinite(self.objective_weight) or self.objective_weight <= 0.0:
            raise TargetDefinitionError("Motion-aware objective_weight must be positive")
        if not math.isfinite(self.normalization_scale_deg) or self.normalization_scale_deg <= 0.0:
            raise TargetDefinitionError("Motion-aware normalization_scale_deg must be positive")


@dataclass(frozen=True)
class MotionAwareHeadingResult:
    """One fully traceable motion + tire-slip heading target before output-sign mapping."""

    turn_direction: TurnDirection
    left_velocity_heading_deg: float
    right_velocity_heading_deg: float
    left_required_slip_deg: float
    right_required_slip_deg: float
    left_required_total_heading_deg: float
    right_required_total_heading_deg: float
    left_pose_reference_heading_deg: float
    right_pose_reference_heading_deg: float
    left_required_incremental_heading_deg: float
    right_required_incremental_heading_deg: float
    regime: SteeringDifferentialRegime | None


def _pose_reference_heading_rad(
    sampling_target: SteeringTarget,
    pose_state: SteeringPoseState,
    side: str,
) -> float:
    reference = reference_from_static_alignment(
        side,
        toe_out=math.radians(sampling_target.static_toe_out_deg),
        camber=math.radians(sampling_target.static_camber_deg),
        source_role=f"{sampling_target.target_id}:motion_aware_reference",
    )
    transform = pose_state.left_transform if side == "left" else pose_state.right_transform
    transformed = transform_wheel_plane(reference, transform)
    direction = road_intersection_direction(
        transformed.normal_at_center,
        forward_hint=transformed.forward_at_center,
    )
    return math.atan2(direction[1], direction[0])


def _regime_from_incremental_headings(
    turn_direction: TurnDirection,
    left_incremental_deg: float,
    right_incremental_deg: float,
    *,
    tolerance_deg: float = 1.0e-9,
) -> SteeringDifferentialRegime | None:
    """Classify normal same-direction steer; return None for countersteer/undefined pairs."""

    if turn_direction is TurnDirection.STRAIGHT:
        if max(abs(left_incremental_deg), abs(right_incremental_deg)) <= tolerance_deg:
            return SteeringDifferentialRegime.PARALLEL
        return None
    if turn_direction not in {TurnDirection.LEFT, TurnDirection.RIGHT}:
        return None

    turn_sign = 1.0 if turn_direction is TurnDirection.LEFT else -1.0
    left_directed = turn_sign * left_incremental_deg
    right_directed = turn_sign * right_incremental_deg
    if left_directed < -tolerance_deg or right_directed < -tolerance_deg:
        return None
    left_magnitude = max(0.0, left_directed)
    right_magnitude = max(0.0, right_directed)
    if turn_direction is TurnDirection.LEFT:
        inside, outside = left_magnitude, right_magnitude
    else:
        inside, outside = right_magnitude, left_magnitude
    return classify_heading_pair(inside, outside, tolerance_deg=tolerance_deg)


def motion_aware_force_demand_heading_pair(
    motion: PlanarMotionSample,
    geometry: FourWheelPlanarGeometry,
    branch_set: TireLateralForceBranchSet,
    inside_operating_point: TireOperatingPoint,
    outside_operating_point: TireOperatingPoint,
    *,
    inside_lateral_force_magnitude_n: float,
    outside_lateral_force_magnitude_n: float,
    left_pose_reference_heading_rad: float,
    right_pose_reference_heading_rad: float,
) -> MotionAwareHeadingResult:
    """Build one target pair from explicit motion and independently inverted tire demands."""

    if motion.turn_direction not in {TurnDirection.LEFT, TurnDirection.RIGHT}:
        raise TargetDefinitionError(
            "A noncenter motion-aware force-demand sample requires nonzero yaw rate so inside/outside tire roles are defined"
        )
    try:
        inside = branch_set.invert(
            inside_operating_point, inside_lateral_force_magnitude_n
        )
        outside = branch_set.invert(
            outside_operating_point, outside_lateral_force_magnitude_n
        )
    except TireDataError as exc:
        raise TargetDefinitionError(f"Motion-aware tire demand cannot be inverted: {exc}") from exc

    turn_sign = 1.0 if motion.turn_direction is TurnDirection.LEFT else -1.0
    inside_slip = turn_sign * math.radians(inside.required_slip_angle_magnitude_deg)
    outside_slip = turn_sign * math.radians(outside.required_slip_angle_magnitude_deg)
    if motion.turn_direction is TurnDirection.LEFT:
        left_slip, right_slip = inside_slip, outside_slip
    else:
        left_slip, right_slip = outside_slip, inside_slip

    try:
        pair = front_required_heading_pair(
            motion,
            geometry,
            left_required_slip_rad=left_slip,
            right_required_slip_rad=right_slip,
        )
    except PlanarKinematicsError as exc:
        raise TargetDefinitionError(f"Motion-aware wheel-slip kinematics failed: {exc}") from exc

    left_incremental = wrap_angle_rad(
        pair.left_required_wheel_heading_rad - left_pose_reference_heading_rad
    )
    right_incremental = wrap_angle_rad(
        pair.right_required_wheel_heading_rad - right_pose_reference_heading_rad
    )
    left_incremental_deg = math.degrees(left_incremental)
    right_incremental_deg = math.degrees(right_incremental)

    return MotionAwareHeadingResult(
        turn_direction=motion.turn_direction,
        left_velocity_heading_deg=math.degrees(pair.left_velocity_heading_rad),
        right_velocity_heading_deg=math.degrees(pair.right_velocity_heading_rad),
        left_required_slip_deg=math.degrees(left_slip),
        right_required_slip_deg=math.degrees(right_slip),
        left_required_total_heading_deg=math.degrees(pair.left_required_wheel_heading_rad),
        right_required_total_heading_deg=math.degrees(pair.right_required_wheel_heading_rad),
        left_pose_reference_heading_deg=math.degrees(left_pose_reference_heading_rad),
        right_pose_reference_heading_deg=math.degrees(right_pose_reference_heading_rad),
        left_required_incremental_heading_deg=left_incremental_deg,
        right_required_incremental_heading_deg=right_incremental_deg,
        regime=_regime_from_incremental_headings(
            motion.turn_direction,
            left_incremental_deg,
            right_incremental_deg,
        ),
    )


def build_motion_aware_force_demand_operating_target_set(
    sampling_target: SteeringTarget,
    pose_set: SuspensionPoseSet,
    planar_geometry: FourWheelPlanarGeometry,
    branch_set: TireLateralForceBranchSet,
    state_definitions: Iterable[MotionAwareForceDemandStateDefinition],
    *,
    target_set_id: str,
    version: str,
    authority: str,
    source_path: str = "",
) -> OperatingStateTargetSet:
    """Build motion-aware force-demand heading targets through the existing state contract."""

    definitions = tuple(state_definitions)
    if not definitions:
        raise TargetDefinitionError("At least one motion-aware force-demand state is required")
    known_states = set(pose_set.state_map)
    unknown = sorted({item.state_id for item in definitions} - known_states)
    if unknown:
        raise TargetDefinitionError(
            f"Motion-aware targets reference unknown suspension-pose states: {unknown}"
        )
    ids = [item.state_id for item in definitions]
    if len(ids) != len(set(ids)):
        raise TargetDefinitionError("Motion-aware force-demand definitions contain duplicate state IDs")

    count = len(sampling_target.rack_displacements)
    try:
        centered_index = sampling_target.rack_displacements.index(0.0)
    except ValueError as exc:
        raise TargetDefinitionError(
            "Motion-aware force-demand target requires an exact centered rack sample"
        ) from exc

    state_targets: list[OperatingStateTarget] = []
    for definition in definitions:
        if len(definition.motion_schedule.samples) != count:
            raise TargetDefinitionError(
                f"Motion-aware state {definition.state_id!r} schedule length does not match steering sampling"
            )
        if (
            abs(definition.inside_lateral_force_magnitude_by_sample[centered_index]) > 1.0e-12
            or abs(definition.outside_lateral_force_magnitude_by_sample[centered_index]) > 1.0e-12
        ):
            raise TargetDefinitionError(
                f"Motion-aware state {definition.state_id!r} must use zero center force demands"
            )
        center_motion = definition.motion_schedule.samples[centered_index]
        if abs(center_motion.yaw_rate_radps) > 1.0e-12:
            raise TargetDefinitionError(
                f"Motion-aware state {definition.state_id!r} center sample must have zero yaw rate"
            )

        pose_state = pose_set.state(definition.state_id)
        left_reference = _pose_reference_heading_rad(sampling_target, pose_state, "left")
        right_reference = _pose_reference_heading_rad(sampling_target, pose_state, "right")
        sign_adapter = sampling_target.canonical_to_target_output_sign

        left: list[float] = []
        right: list[float] = []
        regimes: list[str] = []
        velocity_center_s_m: list[str] = []
        left_velocity_headings: list[float] = []
        right_velocity_headings: list[float] = []
        left_required_slips: list[float] = []
        right_required_slips: list[float] = []

        for index, motion in enumerate(definition.motion_schedule.samples):
            inside_force = definition.inside_lateral_force_magnitude_by_sample[index]
            outside_force = definition.outside_lateral_force_magnitude_by_sample[index]
            if index == centered_index:
                # Preserve the rack-center definition exactly.  Static toe is part of the
                # pose reference and must not be silently "steered out" to enforce a
                # zero-slip straight-line idealization.
                left.append(sampling_target.left_outputs[index])
                right.append(sampling_target.right_outputs[index])
                regimes.append(SteeringDifferentialRegime.PARALLEL.value)
                velocity_center_s_m.append("undefined_straight")
                left_velocity_headings.append(0.0)
                right_velocity_headings.append(0.0)
                left_required_slips.append(0.0)
                right_required_slips.append(0.0)
                continue
            result = motion_aware_force_demand_heading_pair(
                motion,
                planar_geometry,
                branch_set,
                definition.inside_operating_point,
                definition.outside_operating_point,
                inside_lateral_force_magnitude_n=inside_force,
                outside_lateral_force_magnitude_n=outside_force,
                left_pose_reference_heading_rad=left_reference,
                right_pose_reference_heading_rad=right_reference,
            )
            left.append(sign_adapter * result.left_required_incremental_heading_deg)
            right.append(sign_adapter * result.right_required_incremental_heading_deg)
            regimes.append(result.regime.value if result.regime is not None else "not_classified")
            velocity_center_s_m.append(
                "undefined" if motion.velocity_center_longitudinal_m is None else f"{motion.velocity_center_longitudinal_m:.17g}"
            )
            left_velocity_headings.append(result.left_velocity_heading_deg)
            right_velocity_headings.append(result.right_velocity_heading_deg)
            left_required_slips.append(result.left_required_slip_deg)
            right_required_slips.append(result.right_required_slip_deg)

        regime_counts = {
            label: regimes.count(label)
            for label in (
                SteeringDifferentialRegime.PRO_ACKERMANN.value,
                SteeringDifferentialRegime.PARALLEL.value,
                SteeringDifferentialRegime.ANTI_ACKERMANN.value,
                "not_classified",
            )
        }
        state_targets.append(
            OperatingStateTarget(
                state_id=definition.state_id,
                role=OperatingTargetRole.OBJECTIVE,
                objective_id=f"motion_aware_tire_force_demand_heading:{definition.state_id}",
                output_quantity_id="incremental_projected_road_wheel_heading_from_pose",
                output_unit="deg",
                left_outputs=tuple(left),
                right_outputs=tuple(right),
                sample_weights=sampling_target.weights,
                normalization_scale_deg=definition.normalization_scale_deg,
                objective_weight=definition.objective_weight,
                canonical_to_target_output_sign=sign_adapter,
                require_monotonic_response=False,
                monotonic_tolerance_deg=sampling_target.monotonic_tolerance_deg,
                source_type="motion_aware_tire_force_demand",
                authority=definition.authority or authority,
                source_path=source_path,
                provenance=(
                    ("motion_provider_state_id", definition.motion_schedule.state_id),
                    ("motion_provider_authority", definition.motion_schedule.authority),
                    ("motion_provider_source_path", definition.motion_schedule.source_path),
                    ("tire_branch_set_id", branch_set.branch_set_id),
                    ("source_tire_id", branch_set.source_tire_id),
                    ("intended_tire_id", branch_set.intended_tire_id),
                    ("target_mapping", "wheel_velocity_heading_plus_required_tire_slip"),
                    ("tire_slip_convention", "alpha=wheel_heading-beta_hat"),
                    ("wheel_velocity_equations", "Vx=u-r*y; Vy=v+r*x"),
                    ("literature_basis", "Guiggiani_3e_eqs_3.53_to_3.58"),
                    ("ackermann_anchor_used", "false"),
                    (
                        "regime_counts",
                        ",".join(f"{key}:{regime_counts[key]}" for key in sorted(regime_counts)),
                    ),
                    ("velocity_center_S_m_by_sample", ",".join(velocity_center_s_m)),
                    (
                        "left_velocity_heading_deg_by_sample",
                        ",".join(f"{value:.17g}" for value in left_velocity_headings),
                    ),
                    (
                        "right_velocity_heading_deg_by_sample",
                        ",".join(f"{value:.17g}" for value in right_velocity_headings),
                    ),
                    (
                        "left_required_slip_deg_by_sample",
                        ",".join(f"{value:.17g}" for value in left_required_slips),
                    ),
                    (
                        "right_required_slip_deg_by_sample",
                        ",".join(f"{value:.17g}" for value in right_required_slips),
                    ),
                )
                + definition.motion_schedule.provenance
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
            ("planar_motion_model_id", "MOD-VEH-0002"),
            ("adapter", "motion_aware_force_demand_v0.1.0"),
            ("evaluator_model_id", "MOD-STEER-0001"),
        ),
    )
