"""Bounded adapter from synchronized sweeps to the existing motion target consumer."""

from pssd_vehicle.operating_states import TurnDirection, VehicleStateRole
from pssd_vehicle.planar_kinematics import FourWheelPlanarGeometry
from pssd_vehicle.synced_state import SyncedStateSweep
from pssd_vehicle.tire_bridge import front_tire_operating_pair, front_inside_outside_assignment
from pssd_tire.force_demand import TireLateralForceBranchSet
from .motion_force_targets import (
    MotionAwareForceDemandStateDefinition, build_motion_aware_force_demand_operating_target_set,
)
from .targets import SteeringTarget, TargetDefinitionError
from .poses import SuspensionPoseSet
from .operating_targets import OperatingStateTargetSet


def build_synced_sweep_target_set(
    sweep: SyncedStateSweep, sampling_target: SteeringTarget, pose_set: SuspensionPoseSet,
    planar_geometry: FourWheelPlanarGeometry, branch_set: TireLateralForceBranchSet, *,
    target_set_id: str, version: str, normalization_scale_deg: float,
) -> OperatingStateTargetSet:
    """No evidence promotion or freezing of sample-varying points/poses.

    The current motion consumer supports one zero-steer pose and one pair of tire
    operating points per sweep. Incompatible sweeps fail before target publication.
    Its centered sample preserves static alignment, not a fabricated tire inverse.
    """
    if tuple(sampling_target.rack_displacements) != sweep.rack_displacements_m:
        raise TargetDefinitionError("Synchronized rack grid does not match steering sampling")
    if sweep.samples[0].vehicle.role is not VehicleStateRole.DESIGN_INPUT:
        raise TargetDefinitionError("Target publication requires explicit design_input role and weight")
    pose = pose_set.state(sweep.state_id)
    if any(sample.pose != pose for sample in sweep.samples):
        raise TargetDefinitionError("Current consumer requires one unchanged pose per sweep")
    inside_point = outside_point = None
    inside_demands, outside_demands = [], []
    for sample in sweep.samples:
        if not sample.front_inputs_complete:
            raise TargetDefinitionError(f"Missing front tire inputs: {sample.missing_front_inputs}")
        if sample.rack_displacement_m == 0.0:
            if sample.motion.turn_direction is not TurnDirection.STRAIGHT:
                raise TargetDefinitionError("Centered rack must use straight motion")
            for position in ("front_left", "front_right"):
                if sample.vehicle.wheel(position).lateral_force_demand_n != 0.0:
                    raise TargetDefinitionError("Centered rack must supply zero front demands")
            inside_demands.append(0.0)
            outside_demands.append(0.0)
            continue
        pair = front_tire_operating_pair(sample.vehicle)
        assignment = front_inside_outside_assignment(sample.vehicle)
        if inside_point is None:
            inside_point, outside_point = pair.inside, pair.outside
        elif pair.inside != inside_point or pair.outside != outside_point:
            raise TargetDefinitionError("Current consumer cannot freeze sample-varying tire points")
        sign = 1.0 if sample.vehicle.turn_direction is TurnDirection.LEFT else -1.0
        demands = (assignment.inside_wheel.lateral_force_demand_n,
                   assignment.outside_wheel.lateral_force_demand_n)
        if any(value * sign < 0.0 for value in demands):
            raise TargetDefinitionError("Magnitude consumer requires turn-consistent signed demands")
        inside_demands.append(abs(demands[0]))
        outside_demands.append(abs(demands[1]))
    if inside_point is None:
        raise TargetDefinitionError("Sweep requires turning samples")
    definition = MotionAwareForceDemandStateDefinition(
        state_id=sweep.state_id, motion_schedule=sweep.motion_schedule(),
        inside_operating_point=inside_point, outside_operating_point=outside_point,
        inside_lateral_force_magnitude_by_sample=tuple(inside_demands),
        outside_lateral_force_magnitude_by_sample=tuple(outside_demands),
        objective_weight=sweep.samples[0].vehicle.state_weight,
        normalization_scale_deg=normalization_scale_deg, authority=sweep.authority,
        provenance=tuple((sample.vehicle_source.sample_id,
                          repr((sample.vehicle_source, sample.pose_source, sample.motion_source)))
                         for sample in sweep.samples),
    )
    return build_motion_aware_force_demand_operating_target_set(
        sampling_target, pose_set, planar_geometry, branch_set, (definition,),
        target_set_id=target_set_id, version=version, authority=sweep.authority,
    )
