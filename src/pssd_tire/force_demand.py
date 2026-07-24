"""Provider-neutral steady lateral force-demand to slip-angle inversion.

This module deliberately does not fit or evaluate a Magic Formula model. It inverts an
explicit monotone force-versus-slip curve supplied by an upstream reviewed tire source.
That boundary lets raw TTC processing, fitted TIR evaluation, or another validated tire
provider share the same downstream steering interface.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from .lateral import TireDataError, TireOperatingPoint


@dataclass(frozen=True)
class LateralForceSlipCurve:
    """One explicit positive-magnitude Fy(alpha) curve at a named operating point."""

    curve_id: str
    operating_point: TireOperatingPoint
    slip_angle_magnitude_deg: tuple[float, ...]
    lateral_force_magnitude_n: tuple[float, ...]
    source_authority: str
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.curve_id or not self.source_authority:
            raise TireDataError("curve_id and source_authority are required")
        if len(self.slip_angle_magnitude_deg) != len(self.lateral_force_magnitude_n):
            raise TireDataError("Slip-angle and lateral-force arrays must have equal length")
        if len(self.slip_angle_magnitude_deg) < 2:
            raise TireDataError("At least two force-slip samples are required")
        if not all(math.isfinite(value) for value in self.slip_angle_magnitude_deg):
            raise TireDataError("Slip-angle samples must be finite")
        if not all(math.isfinite(value) for value in self.lateral_force_magnitude_n):
            raise TireDataError("Lateral-force samples must be finite")
        if self.slip_angle_magnitude_deg[0] != 0.0:
            raise TireDataError("The first slip-angle sample must be zero")
        if self.lateral_force_magnitude_n[0] != 0.0:
            raise TireDataError("The first lateral-force sample must be zero")
        if any(value < 0.0 for value in self.slip_angle_magnitude_deg):
            raise TireDataError("Slip-angle magnitudes cannot be negative")
        if any(value < 0.0 for value in self.lateral_force_magnitude_n):
            raise TireDataError("Lateral-force magnitudes cannot be negative")
        if any(b <= a for a, b in zip(self.slip_angle_magnitude_deg, self.slip_angle_magnitude_deg[1:])):
            raise TireDataError("Slip-angle samples must be strictly increasing")
        if any(b < a for a, b in zip(self.lateral_force_magnitude_n, self.lateral_force_magnitude_n[1:])):
            raise TireDataError("The invertible force branch must be nondecreasing")

    @property
    def maximum_lateral_force_n(self) -> float:
        return self.lateral_force_magnitude_n[-1]

    def required_slip_angle_magnitude_deg(self, lateral_force_demand_n: float) -> float:
        """Invert the supplied monotone branch by bounded linear interpolation."""

        demand = abs(float(lateral_force_demand_n))
        if not math.isfinite(demand):
            raise TireDataError("lateral_force_demand_n must be finite")
        if demand > self.maximum_lateral_force_n:
            raise TireDataError(
                f"Requested lateral force {demand:g} N exceeds reviewed curve maximum "
                f"{self.maximum_lateral_force_n:g} N"
            )
        for alpha, force in zip(self.slip_angle_magnitude_deg, self.lateral_force_magnitude_n):
            if math.isclose(demand, force, rel_tol=0.0, abs_tol=1.0e-12):
                return alpha
        for alpha_lo, alpha_hi, force_lo, force_hi in zip(
            self.slip_angle_magnitude_deg,
            self.slip_angle_magnitude_deg[1:],
            self.lateral_force_magnitude_n,
            self.lateral_force_magnitude_n[1:],
        ):
            if force_lo < demand < force_hi:
                fraction = (demand - force_lo) / (force_hi - force_lo)
                return alpha_lo + fraction * (alpha_hi - alpha_lo)
        raise TireDataError("Could not bracket lateral-force demand on the supplied branch")


@dataclass(frozen=True)
class FrontAxleSlipDemandResult:
    inside_slip_angle_magnitude_deg: float
    outside_slip_angle_magnitude_deg: float

    @property
    def outside_minus_inside_deg(self) -> float:
        return self.outside_slip_angle_magnitude_deg - self.inside_slip_angle_magnitude_deg

    @property
    def steering_correction_tendency(self) -> str:
        if self.outside_minus_inside_deg > 0.0:
            return "toward_less_ackermann_or_anti_ackermann"
        if self.outside_minus_inside_deg < 0.0:
            return "toward_more_ackermann"
        return "no_differential_slip_correction"


def invert_front_axle_force_demands(
    *,
    inside_curve: LateralForceSlipCurve,
    outside_curve: LateralForceSlipCurve,
    inside_lateral_force_demand_n: float,
    outside_lateral_force_demand_n: float,
) -> FrontAxleSlipDemandResult:
    """Return explicit required-slip magnitudes for the two front tires."""

    return FrontAxleSlipDemandResult(
        inside_slip_angle_magnitude_deg=inside_curve.required_slip_angle_magnitude_deg(
            inside_lateral_force_demand_n
        ),
        outside_slip_angle_magnitude_deg=outside_curve.required_slip_angle_magnitude_deg(
            outside_lateral_force_demand_n
        ),
    )
