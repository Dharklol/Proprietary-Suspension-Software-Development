"""Compose supplied states without solving equilibrium or granting target authority.

Synchronization metadata is an upstream assertion, not independently measured
correlation. This module checks that assertion and preserves original objects.
Tire-domain and branch feasibility remain downstream provider checks.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

from .operating_states import (
    LATERAL_TIRE_DEMAND_FIELDS, VehicleOperatingState, VehicleStateError, WheelPosition,
)
from .planar_kinematics import PlanarMotionSample

if TYPE_CHECKING:
    from pssd_steering.optimization.poses import SteeringPoseState


CANONICAL_FRAME = "x_forward_y_left_z_up"


@dataclass(frozen=True)
class StateSourceStamp:
    """Explicit upstream synchronization key plus component source identity."""

    configuration_id: str
    state_id: str
    sample_id: str
    synchronization_revision: str
    frame: str
    source_path: str
    source_revision: str
    authority: str
    fidelity: str

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or not value.strip()
               for value in vars(self).values()):
            raise VehicleStateError("Synchronization and source identity fields are required")
        if self.frame != CANONICAL_FRAME:
            raise VehicleStateError("Source must declare the canonical body frame")

    @property
    def synchronization_key(self) -> tuple[str, ...]:
        return (self.configuration_id, self.state_id, self.sample_id,
                self.synchronization_revision, self.frame)


@dataclass(frozen=True)
class SyncedStateSample:
    """One atomic SI sample; input completeness is not tire/target readiness."""

    rack_displacement_m: float
    vehicle: VehicleOperatingState
    pose: SteeringPoseState
    motion: PlanarMotionSample
    vehicle_source: StateSourceStamp
    pose_source: StateSourceStamp
    motion_source: StateSourceStamp

    def __post_init__(self) -> None:
        if not math.isfinite(self.rack_displacement_m):
            raise VehicleStateError("Rack displacement must be finite in metres")
        key = self.vehicle_source.synchronization_key
        if any(source.synchronization_key != key
               for source in (self.pose_source, self.motion_source)):
            raise VehicleStateError("Cross-source synchronization mismatch")
        if self.vehicle.state_id != self.vehicle_source.state_id:
            raise VehicleStateError("Vehicle state does not match source stamp")
        if self.vehicle.suspension_pose_state_id != self.pose.state_id:
            raise VehicleStateError("Vehicle suspension pose identity does not match supplied pose")
        if not self.vehicle.authority.strip() or not self.pose.authority.strip():
            raise VehicleStateError("Underlying vehicle and pose authority must be preserved")
        # Speed here is the body speed, as defined by PlanarMotionSample.
        if not math.isclose(self.vehicle.speed_mps, self.motion.body_speed_mps,
                            rel_tol=1e-12, abs_tol=1e-12):
            raise VehicleStateError("Vehicle speed and supplied planar motion disagree")
        if self.vehicle.turn_direction != self.motion.turn_direction:
            raise VehicleStateError("Vehicle turn direction and supplied yaw rate disagree")

    @property
    def missing_front_inputs(self) -> tuple[tuple[str, str, str], ...]:
        """Keep source missing reasons; do not fill defaults or allocate demands."""
        missing = []
        for position in (WheelPosition.FRONT_LEFT, WheelPosition.FRONT_RIGHT):
            wheel = self.vehicle.wheel(position)
            for name, reason in wheel.completeness_record(LATERAL_TIRE_DEMAND_FIELDS).items():
                missing.append((position.value, name, reason))
            if wheel.normal_load_n == 0.0:
                missing.append((position.value, "normal_load_n", "no positive tire contact load"))
        return tuple(missing)

    @property
    def front_inputs_complete(self) -> bool:
        return not self.missing_front_inputs


def compose_synced_state_sample(
    *, rack_displacement_m: float, vehicle: VehicleOperatingState,
    pose: SteeringPoseState, motion: PlanarMotionSample,
    vehicle_source: StateSourceStamp, pose_source: StateSourceStamp,
    motion_source: StateSourceStamp,
) -> SyncedStateSample:
    """Publish only after all synchronization checks pass; retain source objects."""
    return SyncedStateSample(rack_displacement_m, vehicle, pose, motion,
                             vehicle_source, pose_source, motion_source)
