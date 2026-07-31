"""Provider-neutral steady-state pure-lateral tire response kernel.

This module implements the first bounded subset of AUTH-TIRE-0001:
validation and exact/piecewise-linear evaluation of one signed source curve.
Operating-state interpolation and signed-force inversion are intentionally left
for the next commits so each behavior can be benchmarked independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Final

_KNOT_TOLERANCE_RAD: Final[float] = 1.0e-12


class SteadyStateLateralFailure(ValueError):
    """Structured failure raised by the bounded kernel."""

    def __init__(self, failure_code: str, message: str) -> None:
        super().__init__(message)
        self.failure_code = failure_code
        self.message = message


@dataclass(frozen=True, slots=True)
class SteadyStateLateralCurve:
    """Immutable signed Fy(alpha) source curve at one operating state."""

    curve_id: str
    normal_load_N: float
    inclination_rad: float
    pressure_Pa: float
    slip_angle_rad: tuple[float, ...]
    lateral_force_N: tuple[float, ...]
    source_tire_id: str
    intended_tire_id: str
    source_path: str
    source_hash: str
    source_convention_id: str
    adapter_id: str
    fidelity_label: str

    def __post_init__(self) -> None:
        if not self.curve_id:
            raise SteadyStateLateralFailure("source_curve_invalid", "curve_id is required")
        if not isfinite(self.normal_load_N) or self.normal_load_N <= 0.0:
            raise SteadyStateLateralFailure(
                "invalid_normal_load", "normal_load_N must be finite and positive"
            )
        if not isfinite(self.inclination_rad):
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "inclination_rad must be finite"
            )
        if not isfinite(self.pressure_Pa) or self.pressure_Pa <= 0.0:
            raise SteadyStateLateralFailure(
                "invalid_pressure", "pressure_Pa must be finite and positive"
            )
        if len(self.slip_angle_rad) < 2:
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "at least two slip samples are required"
            )
        if len(self.slip_angle_rad) != len(self.lateral_force_N):
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "slip and force arrays must have equal length"
            )
        if not all(isfinite(value) for value in self.slip_angle_rad):
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "all slip samples must be finite"
            )
        if not all(isfinite(value) for value in self.lateral_force_N):
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "all force samples must be finite"
            )
        if any(
            right <= left
            for left, right in zip(self.slip_angle_rad, self.slip_angle_rad[1:])
        ):
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "slip samples must be strictly increasing"
            )


@dataclass(frozen=True, slots=True)
class SteadyStateLateralResponse:
    """Successful one-curve forward evaluation result."""

    lateral_force_N: float
    left_segment_slope_N_per_rad: float
    right_segment_slope_N_per_rad: float
    derivative_unique: bool
    curve_id: str
    segment_ids: tuple[str, ...]
    interpolation_fraction: float
    exact_knot: bool
    source_convention_id: str
    adapter_id: str
    fidelity_label: str


def _segment_slope(curve: SteadyStateLateralCurve, index: int) -> float:
    return (
        curve.lateral_force_N[index + 1] - curve.lateral_force_N[index]
    ) / (curve.slip_angle_rad[index + 1] - curve.slip_angle_rad[index])


def evaluate_curve(
    curve: SteadyStateLateralCurve,
    slip_angle_rad: float,
    *,
    knot_tolerance_rad: float = _KNOT_TOLERANCE_RAD,
) -> SteadyStateLateralResponse:
    """Evaluate one validated source curve without clipping or extrapolation."""

    if not isfinite(slip_angle_rad):
        raise SteadyStateLateralFailure("nonfinite_input", "slip_angle_rad must be finite")
    if not isfinite(knot_tolerance_rad) or knot_tolerance_rad < 0.0:
        raise ValueError("knot_tolerance_rad must be finite and non-negative")

    minimum = curve.slip_angle_rad[0]
    maximum = curve.slip_angle_rad[-1]
    if slip_angle_rad < minimum - knot_tolerance_rad or slip_angle_rad > maximum + knot_tolerance_rad:
        raise SteadyStateLateralFailure(
            "slip_out_of_domain",
            f"slip_angle_rad={slip_angle_rad!r} is outside [{minimum!r}, {maximum!r}]",
        )

    for knot_index, knot in enumerate(curve.slip_angle_rad):
        if abs(slip_angle_rad - knot) <= knot_tolerance_rad:
            if knot_index == 0:
                slope = _segment_slope(curve, 0)
                left_slope = right_slope = slope
                segment_ids = (f"{curve.curve_id}:segment:0",)
            elif knot_index == len(curve.slip_angle_rad) - 1:
                slope = _segment_slope(curve, knot_index - 1)
                left_slope = right_slope = slope
                segment_ids = (f"{curve.curve_id}:segment:{knot_index - 1}",)
            else:
                left_slope = _segment_slope(curve, knot_index - 1)
                right_slope = _segment_slope(curve, knot_index)
                segment_ids = (
                    f"{curve.curve_id}:segment:{knot_index - 1}",
                    f"{curve.curve_id}:segment:{knot_index}",
                )
            return SteadyStateLateralResponse(
                lateral_force_N=curve.lateral_force_N[knot_index],
                left_segment_slope_N_per_rad=left_slope,
                right_segment_slope_N_per_rad=right_slope,
                derivative_unique=abs(left_slope - right_slope) <= 1.0e-12,
                curve_id=curve.curve_id,
                segment_ids=segment_ids,
                interpolation_fraction=0.0,
                exact_knot=True,
                source_convention_id=curve.source_convention_id,
                adapter_id=curve.adapter_id,
                fidelity_label=curve.fidelity_label,
            )

    for index, (left_alpha, right_alpha) in enumerate(
        zip(curve.slip_angle_rad, curve.slip_angle_rad[1:])
    ):
        if left_alpha < slip_angle_rad < right_alpha:
            fraction = (slip_angle_rad - left_alpha) / (right_alpha - left_alpha)
            left_force = curve.lateral_force_N[index]
            right_force = curve.lateral_force_N[index + 1]
            force = left_force + fraction * (right_force - left_force)
            slope = _segment_slope(curve, index)
            return SteadyStateLateralResponse(
                lateral_force_N=force,
                left_segment_slope_N_per_rad=slope,
                right_segment_slope_N_per_rad=slope,
                derivative_unique=True,
                curve_id=curve.curve_id,
                segment_ids=(f"{curve.curve_id}:segment:{index}",),
                interpolation_fraction=fraction,
                exact_knot=False,
                source_convention_id=curve.source_convention_id,
                adapter_id=curve.adapter_id,
                fidelity_label=curve.fidelity_label,
            )

    raise SteadyStateLateralFailure(
        "slip_out_of_domain", "no source segment contains the requested slip angle"
    )
