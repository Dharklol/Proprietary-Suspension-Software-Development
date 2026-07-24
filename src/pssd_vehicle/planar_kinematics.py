"""Exact planar rigid-body wheel-center velocity and tire-slip kinematics.

This module is a kinematic provider only.  It does not calculate vehicle equilibrium,
load transfer, tire force, sideslip response, yaw-rate response, or steering mechanism
motion.  An upstream QSS/telemetry/vehicle model supplies body-frame longitudinal
velocity ``u``, lateral velocity ``v``, and yaw rate ``r``.  Given explicit wheel-center
locations, the module evaluates the rigid-body velocity field

    Vx = u - r*y
    Vy = v + r*x

and the corresponding wheel-center velocity heading.  A signed tire slip angle is then
defined in the project canonical frame as

    alpha = delta - beta_hat

where both ``delta`` and ``beta_hat`` are positive by the right-hand rule about +z.
This is the same geometric structure as Guiggiani, The Science of Vehicle Dynamics,
3rd ed., Eqs. 3.53-3.58; the sign convention is stated here explicitly in project terms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Mapping

from .operating_states import TurnDirection, VehicleStateError, WheelPosition


class PlanarKinematicsError(VehicleStateError):
    """Raised when a planar motion/geometry state is undefined or inconsistent."""


def _pairs(values: Mapping[object, object] | None) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(key), str(value)) for key, value in (values or {}).items()))


def wrap_angle_rad(angle_rad: float) -> float:
    """Wrap one finite angle to [-pi, pi), preserving no hidden degree conversion."""

    value = float(angle_rad)
    if not math.isfinite(value):
        raise PlanarKinematicsError("angle must be finite")
    wrapped = (value + math.pi) % (2.0 * math.pi) - math.pi
    # Avoid returning -pi for an input that is numerically +pi; this convention is
    # deterministic and keeps steering-sized angles far from the branch cut anyway.
    return wrapped


@dataclass(frozen=True)
class PlanarMotionSample:
    """One explicitly supplied body-frame planar motion state.

    Canonical body axes are +x forward, +y vehicle left, +z upward.  Positive yaw
    rate is therefore a left/CCW turn by the right-hand rule.
    """

    longitudinal_velocity_mps: float
    lateral_velocity_mps: float
    yaw_rate_radps: float

    def __post_init__(self) -> None:
        values = (
            self.longitudinal_velocity_mps,
            self.lateral_velocity_mps,
            self.yaw_rate_radps,
        )
        if not all(math.isfinite(value) for value in values):
            raise PlanarKinematicsError("planar motion values must be finite")

    @property
    def body_speed_mps(self) -> float:
        return math.hypot(self.longitudinal_velocity_mps, self.lateral_velocity_mps)

    @property
    def body_velocity_heading_rad(self) -> float | None:
        if self.body_speed_mps <= 1.0e-15:
            return None
        return math.atan2(self.lateral_velocity_mps, self.longitudinal_velocity_mps)

    @property
    def turn_direction(self) -> TurnDirection:
        if self.yaw_rate_radps > 1.0e-12:
            return TurnDirection.LEFT
        if self.yaw_rate_radps < -1.0e-12:
            return TurnDirection.RIGHT
        return TurnDirection.STRAIGHT

    @property
    def curvature_per_m(self) -> float | None:
        """Return r/u when body longitudinal velocity is nonzero."""

        if abs(self.longitudinal_velocity_mps) <= 1.0e-15:
            return None
        return self.yaw_rate_radps / self.longitudinal_velocity_mps

    @property
    def velocity_center_longitudinal_m(self) -> float | None:
        """Guiggiani coordinate S = -v/r; None for zero yaw rate."""

        if abs(self.yaw_rate_radps) <= 1.0e-15:
            return None
        return -self.lateral_velocity_mps / self.yaw_rate_radps

    @property
    def velocity_center_lateral_m(self) -> float | None:
        """Guiggiani coordinate R = u/r; None for zero yaw rate."""

        if abs(self.yaw_rate_radps) <= 1.0e-15:
            return None
        return self.longitudinal_velocity_mps / self.yaw_rate_radps


@dataclass(frozen=True)
class PlanarMotionSchedule:
    """Ordered motion samples sharing one steering-input/rack sampling contract."""

    state_id: str
    samples: tuple[PlanarMotionSample, ...]
    authority: str
    source_path: str = ""
    provenance: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.state_id:
            raise PlanarKinematicsError("planar motion schedule requires state_id")
        if len(self.samples) < 3:
            raise PlanarKinematicsError("planar motion schedule requires at least three samples")
        if not self.authority:
            raise PlanarKinematicsError("planar motion schedule requires authority")


@dataclass(frozen=True)
class WheelPlanarLocation:
    """Wheel-center location in the canonical body x-y plane relative to CG."""

    position: WheelPosition
    x_m: float
    y_m: float

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) for value in (self.x_m, self.y_m)):
            raise PlanarKinematicsError("wheel planar coordinates must be finite")


@dataclass(frozen=True)
class FourWheelPlanarGeometry:
    """Symmetric four-wheel center geometry referenced to vehicle CG.

    ``cg_to_front_axle_m`` and ``cg_to_rear_axle_m`` are positive distances.  The
    left wheel centers use positive y and right wheel centers negative y.
    """

    cg_to_front_axle_m: float
    cg_to_rear_axle_m: float
    front_wheel_center_track_m: float
    rear_wheel_center_track_m: float
    authority: str = ""
    provenance: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        values = (
            self.cg_to_front_axle_m,
            self.cg_to_rear_axle_m,
            self.front_wheel_center_track_m,
            self.rear_wheel_center_track_m,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise PlanarKinematicsError("axle distances and wheel-center tracks must be finite and positive")

    @property
    def wheelbase_m(self) -> float:
        return self.cg_to_front_axle_m + self.cg_to_rear_axle_m

    @property
    def locations(self) -> tuple[WheelPlanarLocation, ...]:
        front_half = 0.5 * self.front_wheel_center_track_m
        rear_half = 0.5 * self.rear_wheel_center_track_m
        return (
            WheelPlanarLocation(WheelPosition.FRONT_LEFT, self.cg_to_front_axle_m, front_half),
            WheelPlanarLocation(WheelPosition.FRONT_RIGHT, self.cg_to_front_axle_m, -front_half),
            WheelPlanarLocation(WheelPosition.REAR_LEFT, -self.cg_to_rear_axle_m, rear_half),
            WheelPlanarLocation(WheelPosition.REAR_RIGHT, -self.cg_to_rear_axle_m, -rear_half),
        )

    @property
    def location_map(self) -> dict[WheelPosition, WheelPlanarLocation]:
        return {item.position: item for item in self.locations}

    def location(self, position: WheelPosition | str) -> WheelPlanarLocation:
        key = position if isinstance(position, WheelPosition) else WheelPosition(position)
        return self.location_map[key]


@dataclass(frozen=True)
class WheelCenterKinematics:
    position: WheelPosition
    velocity_x_mps: float
    velocity_y_mps: float
    speed_mps: float
    velocity_heading_rad: float


@dataclass(frozen=True)
class TireSlipKinematics:
    position: WheelPosition
    velocity_heading_rad: float
    wheel_heading_rad: float
    slip_angle_rad: float


@dataclass(frozen=True)
class FrontRequiredHeadingPair:
    """Front velocity headings plus requested signed tire-slip angles/headings."""

    left_velocity_heading_rad: float
    right_velocity_heading_rad: float
    left_required_slip_rad: float
    right_required_slip_rad: float
    left_required_wheel_heading_rad: float
    right_required_wheel_heading_rad: float


def wheel_center_kinematics(
    motion: PlanarMotionSample,
    location: WheelPlanarLocation,
    *,
    minimum_speed_mps: float = 1.0e-9,
) -> WheelCenterKinematics:
    """Evaluate the exact planar rigid-body velocity at one wheel center."""

    if not math.isfinite(minimum_speed_mps) or minimum_speed_mps < 0.0:
        raise PlanarKinematicsError("minimum_speed_mps must be finite and nonnegative")
    vx = motion.longitudinal_velocity_mps - motion.yaw_rate_radps * location.y_m
    vy = motion.lateral_velocity_mps + motion.yaw_rate_radps * location.x_m
    speed = math.hypot(vx, vy)
    if speed <= minimum_speed_mps:
        raise PlanarKinematicsError(
            f"{location.position.value} wheel-center velocity magnitude {speed:g} m/s is too small "
            "to define a tire slip direction"
        )
    return WheelCenterKinematics(
        position=location.position,
        velocity_x_mps=vx,
        velocity_y_mps=vy,
        speed_mps=speed,
        velocity_heading_rad=math.atan2(vy, vx),
    )


def tire_slip_kinematics(
    motion: PlanarMotionSample,
    location: WheelPlanarLocation,
    wheel_heading_rad: float,
) -> TireSlipKinematics:
    """Compute signed project-canonical slip alpha = delta - velocity heading."""

    heading = float(wheel_heading_rad)
    if not math.isfinite(heading):
        raise PlanarKinematicsError("wheel heading must be finite")
    wheel_state = wheel_center_kinematics(motion, location)
    alpha = wrap_angle_rad(heading - wheel_state.velocity_heading_rad)
    return TireSlipKinematics(
        position=location.position,
        velocity_heading_rad=wheel_state.velocity_heading_rad,
        wheel_heading_rad=heading,
        slip_angle_rad=alpha,
    )


def required_wheel_heading_rad(velocity_heading_rad: float, required_slip_rad: float) -> float:
    """Invert alpha = delta - beta_hat without invoking tire or vehicle dynamics."""

    beta = float(velocity_heading_rad)
    alpha = float(required_slip_rad)
    if not math.isfinite(beta) or not math.isfinite(alpha):
        raise PlanarKinematicsError("velocity heading and required slip must be finite")
    return wrap_angle_rad(beta + alpha)


def front_required_heading_pair(
    motion: PlanarMotionSample,
    geometry: FourWheelPlanarGeometry,
    *,
    left_required_slip_rad: float,
    right_required_slip_rad: float,
) -> FrontRequiredHeadingPair:
    """Map explicitly signed left/right tire slips to exact front wheel headings."""

    left_velocity = wheel_center_kinematics(
        motion, geometry.location(WheelPosition.FRONT_LEFT)
    ).velocity_heading_rad
    right_velocity = wheel_center_kinematics(
        motion, geometry.location(WheelPosition.FRONT_RIGHT)
    ).velocity_heading_rad
    return FrontRequiredHeadingPair(
        left_velocity_heading_rad=left_velocity,
        right_velocity_heading_rad=right_velocity,
        left_required_slip_rad=left_required_slip_rad,
        right_required_slip_rad=right_required_slip_rad,
        left_required_wheel_heading_rad=required_wheel_heading_rad(
            left_velocity, left_required_slip_rad
        ),
        right_required_wheel_heading_rad=required_wheel_heading_rad(
            right_velocity, right_required_slip_rad
        ),
    )
