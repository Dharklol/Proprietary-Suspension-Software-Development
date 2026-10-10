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
from .planar_kinematics import PlanarMotionSample, PlanarMotionSchedule

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


@dataclass(frozen=True)
class SyncedStateSweep:
    """Explicit ordered sampling contract; never sort or resample upstream data."""

    sweep_id: str
    rack_displacements_m: tuple[float, ...]
    samples: tuple[SyncedStateSample, ...]
    authority: str

    def __post_init__(self) -> None:
        if not self.sweep_id.strip() or not self.authority.strip():
            raise VehicleStateError("Sweep identity and authority are required")
        if len(self.samples) < 3 or len(self.samples) != len(self.rack_displacements_m):
            raise VehicleStateError("Sweep requires at least three aligned samples")
        racks = tuple(sample.rack_displacement_m for sample in self.samples)
        if racks != self.rack_displacements_m or len(set(racks)) != len(racks):
            raise VehicleStateError("Rack sampling must match exactly with no duplicate positions")
        sources = tuple(sample.vehicle_source for sample in self.samples)
        if len({source.sample_id for source in sources}) != len(sources):
            raise VehicleStateError("Sweep contains duplicate sample IDs")
        def shared_key(source: StateSourceStamp) -> tuple[str, ...]:
            return (source.configuration_id, source.state_id,
                    source.synchronization_revision, source.frame)
        if any(shared_key(source) != shared_key(sources[0]) for source in sources):
            raise VehicleStateError("Sweep mixes configurations, states, frames, or revisions")
        first = self.samples[0].vehicle
        if any((sample.vehicle.role, sample.vehicle.state_weight, sample.vehicle.authority)
               != (first.role, first.state_weight, first.authority) for sample in self.samples):
            raise VehicleStateError("Sweep must preserve a single role, weight, and vehicle authority")

    @property
    def state_id(self) -> str:
        return self.samples[0].vehicle.state_id

    def motion_schedule(self) -> PlanarMotionSchedule:
        return PlanarMotionSchedule(
            self.state_id, tuple(sample.motion for sample in self.samples), self.authority,
            provenance=tuple((sample.motion_source.sample_id,
                              repr(sample.motion_source)) for sample in self.samples),
        )
