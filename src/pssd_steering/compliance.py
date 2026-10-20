"""Bounded, independent WUFR-27 steering elastic-compliance calculations.

This module deliberately does not alter rigid steering geometry, synthesize tire
moments, or treat clearance/backlash as elastic stiffness. All torques are explicit.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


class ComplianceDefinitionError(ValueError):
    """An input is nonphysical or insufficiently specified."""


@dataclass(frozen=True)
class CircularSpan:
    name: str
    length_in: float
    outer_diameter_in: float
    inner_diameter_in: float = 0.0
    shear_modulus_pa: float = 80e9
    torque_multiplier: float = 1.0

    def __post_init__(self) -> None:
        values = (self.length_in, self.outer_diameter_in, self.inner_diameter_in,
                  self.shear_modulus_pa, self.torque_multiplier)
        if not all(math.isfinite(x) for x in values):
            raise ComplianceDefinitionError("span values must be finite")
        if (not self.name or self.length_in < 0 or self.inner_diameter_in < 0
                or self.outer_diameter_in <= self.inner_diameter_in
                or self.shear_modulus_pa <= 0 or self.torque_multiplier <= 0):
            raise ComplianceDefinitionError("invalid span dimensions or properties")

    @property
    def polar_second_moment_m4(self) -> float:
        inch = 0.0254
        return math.pi / 32 * ((self.outer_diameter_in * inch) ** 4
                               - (self.inner_diameter_in * inch) ** 4)

    def input_referenced_twist_rad(self, input_torque_nm: float) -> float:
        """Signed twist for an explicitly specified torque multiplier.

        The multiplier accounts for torque in this span relative to input torque;
        use only after verifying gear ratio, direction, and efficiency conventions.
        """
        if not math.isfinite(input_torque_nm):
            raise ComplianceDefinitionError("torque must be finite")
        return (input_torque_nm * self.torque_multiplier * self.length_in * 0.0254
                / (self.shear_modulus_pa * self.polar_second_moment_m4))


@dataclass(frozen=True)
class ComplianceResult:
    torque_nm: float
    twist_rad: float
    span_twist_rad: tuple[tuple[str, float], ...]

    @property
    def twist_deg(self) -> float:
        return math.degrees(self.twist_rad)

    @property
    def stiffness_nm_per_deg(self) -> float:
        """Effective input torque per degree; infinity for an ideal rigid stack."""
        return math.inf if self.twist_rad == 0 else abs(self.torque_nm / self.twist_deg)


def evaluate_circular_spans(spans: tuple[CircularSpan, ...],
                            input_torque_nm: float) -> ComplianceResult:
    """Calculate elastic deflection; no joint/gear/rack compliance is inferred."""
    if not spans:
        raise ComplianceDefinitionError("at least one span is required")
    if len({s.name for s in spans}) != len(spans):
        raise ComplianceDefinitionError("span names must be unique")
    parts = tuple((s.name, s.input_referenced_twist_rad(input_torque_nm)) for s in spans)
    return ComplianceResult(input_torque_nm, sum(value for _, value in parts), parts)


def wufr27_provisional_circular_spans() -> tuple[CircularSpan, ...]:
    """Provisional 2026-10-20 geometry; shaft D-profile regions are NOT represented.

    Columns are circular tubes OD .750 / ID .625 in. Shaft circular-section
    diameter .590 in. G=80 GPa illustrative steel value. Torque multipliers
    equal one; caller must replace if gearbox torque propagation differs.
    """
    return (
        CircularSpan("upper_column", 4.878, .750, .625),
        CircularSpan("lower_column", 6.600, .750, .625),
        CircularSpan("upper_shaft_circular", .787, .590),
        CircularSpan("lower_shaft_circular", 2.753, .590),
    )


@dataclass(frozen=True)
class DoubleDProfile:
    radius_in: float = .295
    across_flats_in: float = .472
    engagement_in: float = .375

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in (
                self.radius_in, self.across_flats_in, self.engagement_in)):
            raise ComplianceDefinitionError("double-D profile values must be finite")
        if (self.radius_in <= 0 or not 0 < self.across_flats_in < 2 * self.radius_in
                or self.engagement_in <= 0):
            raise ComplianceDefinitionError("invalid double-D geometry")

    @property
    def flat_depth_in(self) -> float:
        return self.radius_in - self.across_flats_in / 2

    @property
    def flat_chord_in(self) -> float:
        return 2 * math.sqrt(self.radius_in ** 2 - (self.across_flats_in / 2) ** 2)


@dataclass(frozen=True)
class ToleranceEnvelope:
    """Independent absolute +/- tolerance on both mating across-flats sizes.

    Negative relative clearance represents interference. This is a dimensional
    envelope only and must NOT be interpreted as validated angular backlash.
    """
    nominal_across_flats_in: float
    male_plus_minus_in: float
    female_plus_minus_in: float

    def __post_init__(self) -> None:
        vals = (self.nominal_across_flats_in, self.male_plus_minus_in,
                self.female_plus_minus_in)
        if (not all(math.isfinite(v) for v in vals)
                or self.nominal_across_flats_in <= 0
                or self.male_plus_minus_in < 0 or self.female_plus_minus_in < 0):
            raise ComplianceDefinitionError("invalid tolerance envelope")

    @property
    def clearance_range_in(self) -> tuple[float, float]:
        delta = self.male_plus_minus_in + self.female_plus_minus_in
        return -delta, delta


@dataclass(frozen=True)
class ClevisPinScreen:
    """Simple pin shear screen, not complete retention-joint approval.

    18-8 pin stock yield strength below is an explicit ASSUMPTION, not a
    verified McMaster 90378A114 material certification.
    """
    diameter_min_in: float = .121
    shear_planes: int = 2
    assumed_yield_pa: float = 205e6
    factor_of_safety: float = 3.0

    def allowable_shear_force_n(self) -> float:
        if (not math.isfinite(self.diameter_min_in)
                or not math.isfinite(self.assumed_yield_pa)
                or not math.isfinite(self.factor_of_safety)
                or self.diameter_min_in <= 0 or self.shear_planes < 1
                or self.assumed_yield_pa <= 0 or self.factor_of_safety < 1):
            raise ComplianceDefinitionError("invalid pin screening assumptions")
        area = self.shear_planes * math.pi / 4 * (self.diameter_min_in * .0254) ** 2
        return area * self.assumed_yield_pa / (math.sqrt(3) * self.factor_of_safety)
