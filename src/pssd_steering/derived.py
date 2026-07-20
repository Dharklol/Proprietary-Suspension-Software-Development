"""Derived rigid-steering reference quantities for EQ-STEER-0001 and 0005-0007."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class InsideOutside:
    turn_direction: str
    inside_side: str
    outside_side: str
    inside_incremental_magnitude: float
    outside_incremental_magnitude: float


@dataclass(frozen=True)
class TurningRadii:
    rear_axle_center_from_inside: float
    rear_axle_center_from_outside: float

    @property
    def mismatch(self) -> float:
        return self.rear_axle_center_from_outside - self.rear_axle_center_from_inside


@dataclass(frozen=True)
class TransmissionResult:
    steering_wheel_angle: float
    pinion_angle: float
    rack_displacement: float


def exact_ackermann_outside_reference(
    inside_incremental_angle: float,
    wheelbase: float,
    steering_axis_track: float,
) -> float:
    """Return the exact low-speed Ackermann outside angle magnitude.

    Implements ``cot(delta_o)-cot(delta_i)=t/l`` using an ``atan2`` form.
    Angles are radians. Ideal Ackermann is a reference, not a universal race
    objective.
    """

    if not all(math.isfinite(value) for value in (inside_incremental_angle, wheelbase, steering_axis_track)):
        raise ValueError("Ackermann inputs must be finite")
    if wheelbase <= 0.0 or steering_axis_track <= 0.0:
        raise ValueError("Wheelbase and steering-axis track must be positive")
    inside = abs(inside_incremental_angle)
    if inside == 0.0:
        return 0.0
    numerator = wheelbase * math.sin(inside)
    denominator = wheelbase * math.cos(inside) + steering_axis_track * math.sin(inside)
    outside = math.atan2(numerator, denominator)
    if outside <= 0.0:
        raise ValueError("Ackermann reference is outside the supported forward-turn quadrant")
    return outside


def assign_inside_outside(
    left_incremental_heading: float,
    right_incremental_heading: float,
    *,
    straight_tolerance: float = 1.0e-12,
) -> InsideOutside:
    """Assign inside/outside from turn direction and side, never angle magnitude."""

    if not all(math.isfinite(value) for value in (left_incremental_heading, right_incremental_heading)):
        raise ValueError("Wheel headings must be finite")
    mean_heading = 0.5 * (left_incremental_heading + right_incremental_heading)
    if abs(mean_heading) <= straight_tolerance:
        raise ValueError("Inside/outside is undefined for a straight or ambiguous state")
    if mean_heading > 0.0:
        return InsideOutside(
            turn_direction="left",
            inside_side="left",
            outside_side="right",
            inside_incremental_magnitude=abs(left_incremental_heading),
            outside_incremental_magnitude=abs(right_incremental_heading),
        )
    return InsideOutside(
        turn_direction="right",
        inside_side="right",
        outside_side="left",
        inside_incremental_magnitude=abs(right_incremental_heading),
        outside_incremental_magnitude=abs(left_incremental_heading),
    )


def ackermann_error(
    left_incremental_heading: float,
    right_incremental_heading: float,
    wheelbase: float,
    steering_axis_track: float,
) -> tuple[InsideOutside, float, float]:
    """Return assignment, outside reference, and outside-minus-reference error."""

    assignment = assign_inside_outside(left_incremental_heading, right_incremental_heading)
    reference = exact_ackermann_outside_reference(
        assignment.inside_incremental_magnitude,
        wheelbase,
        steering_axis_track,
    )
    error = assignment.outside_incremental_magnitude - reference
    return assignment, reference, error


def turning_radii(
    inside_incremental_angle: float,
    outside_incremental_angle: float,
    wheelbase: float,
    steering_axis_track: float,
) -> TurningRadii:
    """Return named rear-axle-center radii from inside and outside wheels.

    The two values are intentionally separate for non-Ackermann mechanisms.
    They must not be silently averaged into one authoritative radius.
    """

    values = (inside_incremental_angle, outside_incremental_angle, wheelbase, steering_axis_track)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Turning-radius inputs must be finite")
    inside = abs(inside_incremental_angle)
    outside = abs(outside_incremental_angle)
    if inside <= 0.0 or outside <= 0.0:
        raise ValueError("Turning radius is undefined at zero wheel angle")
    if wheelbase <= 0.0 or steering_axis_track <= 0.0:
        raise ValueError("Wheelbase and steering-axis track must be positive")
    return TurningRadii(
        rear_axle_center_from_inside=wheelbase / math.tan(inside) + steering_axis_track / 2.0,
        rear_axle_center_from_outside=wheelbase / math.tan(outside) - steering_axis_track / 2.0,
    )


def staged_transmission(
    steering_wheel_angle: float,
    pinion_angle_per_steering_wheel_angle: float,
    rack_displacement_per_pinion_angle: float,
) -> TransmissionResult:
    """Evaluate the explicit steering-wheel -> pinion -> rack chain."""

    values = (
        steering_wheel_angle,
        pinion_angle_per_steering_wheel_angle,
        rack_displacement_per_pinion_angle,
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Transmission inputs must be finite")
    pinion = steering_wheel_angle * pinion_angle_per_steering_wheel_angle
    rack = pinion * rack_displacement_per_pinion_angle
    return TransmissionResult(steering_wheel_angle, pinion, rack)


def metres_per_radian_to_millimetres_per_revolution(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("Transmission value must be finite")
    return value * 1000.0 * 2.0 * math.pi


def local_road_wheel_gain(
    upright_gain_rad_per_m: float,
    rack_displacement_per_pinion_angle: float,
    pinion_angle_per_steering_wheel_angle: float,
) -> float:
    """Chain local mechanism and transmission derivatives explicitly."""

    values = (
        upright_gain_rad_per_m,
        rack_displacement_per_pinion_angle,
        pinion_angle_per_steering_wheel_angle,
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Local gain inputs must be finite")
    return (
        upright_gain_rad_per_m
        * rack_displacement_per_pinion_angle
        * pinion_angle_per_steering_wheel_angle
    )


def conventional_steering_ratio(local_gain: float, *, magnitude: bool = True) -> float:
    """Return steering-wheel radians per road-wheel radian for a named gain."""

    if not math.isfinite(local_gain):
        raise ValueError("Local gain must be finite")
    if local_gain == 0.0:
        raise ZeroDivisionError("Conventional ratio is undefined for zero road-wheel gain")
    ratio = 1.0 / local_gain
    return abs(ratio) if magnitude else ratio


def secant_ratio(input_angle: float, output_angle: float, *, magnitude: bool = True) -> float:
    """Return an explicit finite-displacement input/output angle ratio."""

    if not all(math.isfinite(value) for value in (input_angle, output_angle)):
        raise ValueError("Secant-ratio angles must be finite")
    if output_angle == 0.0:
        raise ZeroDivisionError("Secant ratio is undefined for zero output angle")
    value = input_angle / output_angle
    return abs(value) if magnitude else value
