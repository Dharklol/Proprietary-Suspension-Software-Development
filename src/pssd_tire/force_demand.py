"""Bounded inversion of explicit lateral tire force-response branches.

This module does not implement Magic Formula, a polynomial tire surrogate, or a
vehicle equilibrium model.  It inverts already-supplied, monotonic pre-peak
``|Fy|`` versus ``|alpha|`` samples at an exact tire operating point.  Linear
interpolation occurs only between adjacent supplied samples; operating-point
interpolation and extrapolation are deliberately excluded from the first contract.

The magnitude formulation is intentional.  A source/exporter is responsible for
selecting a physically consistent branch (for example, the branch corresponding to
the tire leaning into the turn) and for preserving its original sign convention in
provenance.  Steering may then use the required slip-angle magnitudes to form an
inside/outside differential without inventing a tire-force sign adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
import tomllib
from typing import Mapping

from .lateral import TireDataError, TireOperatingPoint


@dataclass(frozen=True)
class LateralForceCurveSample:
    """One explicit point on a monotonic pre-peak lateral-force branch."""

    slip_angle_magnitude_deg: float
    lateral_force_magnitude_n: float

    def __post_init__(self) -> None:
        values = (self.slip_angle_magnitude_deg, self.lateral_force_magnitude_n)
        if not all(math.isfinite(value) for value in values):
            raise TireDataError("Lateral-force branch samples must be finite")
        if self.slip_angle_magnitude_deg < 0.0:
            raise TireDataError("slip_angle_magnitude_deg cannot be negative")
        if self.lateral_force_magnitude_n < 0.0:
            raise TireDataError("lateral_force_magnitude_n cannot be negative")


@dataclass(frozen=True)
class LateralForceBranch:
    """Explicit monotonic ``|Fy|`` versus ``|alpha|`` data at one operating point."""

    branch_id: str
    operating_point: TireOperatingPoint
    samples: tuple[LateralForceCurveSample, ...]
    authority: str
    source_branch_description: str
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.branch_id or not self.authority or not self.source_branch_description:
            raise TireDataError(
                "Lateral-force branch requires identity, authority, and branch description"
            )
        if len(self.samples) < 2:
            raise TireDataError("Lateral-force branch requires at least two samples")

        slips = [sample.slip_angle_magnitude_deg for sample in self.samples]
        forces = [sample.lateral_force_magnitude_n for sample in self.samples]
        if any(upper <= lower for lower, upper in zip(slips, slips[1:])):
            raise TireDataError(
                "Lateral-force branch slip magnitudes must increase strictly"
            )
        if any(upper <= lower for lower, upper in zip(forces, forces[1:])):
            raise TireDataError(
                "Lateral-force branch force magnitudes must increase strictly on the pre-peak branch"
            )

    @property
    def minimum_force_magnitude_n(self) -> float:
        return self.samples[0].lateral_force_magnitude_n

    @property
    def maximum_force_magnitude_n(self) -> float:
        return self.samples[-1].lateral_force_magnitude_n

    @property
    def maximum_slip_angle_magnitude_deg(self) -> float:
        return self.samples[-1].slip_angle_magnitude_deg


@dataclass(frozen=True)
class LateralForceDemandResult:
    """Result of one bounded force-demand inversion."""

    branch_id: str
    demand_magnitude_n: float
    required_slip_angle_magnitude_deg: float
    lower_sample: LateralForceCurveSample
    upper_sample: LateralForceCurveSample
    interpolation_fraction: float
    exact_sample: bool
    force_utilization_of_branch_max: float


@dataclass(frozen=True)
class TireLateralForceBranchSet:
    """Collection of explicit force-response branches with source identity preserved."""

    branch_set_id: str
    version: str
    source_tire_id: str
    intended_tire_id: str
    authority: str
    source_path: str
    branches: tuple[LateralForceBranch, ...]
    provenance: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        required = (
            self.branch_set_id,
            self.version,
            self.source_tire_id,
            self.intended_tire_id,
            self.authority,
            self.source_path,
        )
        if not all(required):
            raise TireDataError("Lateral-force branch set identity/source fields are required")
        if not self.branches:
            raise TireDataError("Lateral-force branch set requires at least one branch")
        ids = [branch.branch_id for branch in self.branches]
        if len(ids) != len(set(ids)):
            raise TireDataError("Lateral-force branch set contains duplicate branch IDs")

        operating_keys = [
            (
                branch.operating_point.normal_load_n,
                branch.operating_point.inclination_deg,
                branch.operating_point.pressure_kpa,
            )
            for branch in self.branches
        ]
        if len(operating_keys) != len(set(operating_keys)):
            raise TireDataError(
                "First force-demand contract permits only one branch per exact operating point"
            )

    def branch_for(
        self,
        operating_point: TireOperatingPoint,
        *,
        tolerance: float = 1.0e-9,
    ) -> LateralForceBranch:
        """Return the exact reviewed branch; never interpolate operating points."""

        matches = []
        for branch in self.branches:
            candidate = branch.operating_point
            if all(
                math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance)
                for actual, expected in (
                    (candidate.normal_load_n, operating_point.normal_load_n),
                    (candidate.inclination_deg, operating_point.inclination_deg),
                    (candidate.pressure_kpa, operating_point.pressure_kpa),
                )
            ):
                matches.append(branch)
        if not matches:
            raise TireDataError(
                "No explicit lateral-force branch exists at "
                f"Fz={operating_point.normal_load_n:g} N, "
                f"IA={operating_point.inclination_deg:g} deg, "
                f"P={operating_point.pressure_kpa:g} kPa; operating-point extrapolation/interpolation "
                "is not authorized by this provider"
            )
        if len(matches) != 1:
            raise TireDataError("Ambiguous lateral-force branch operating point")
        return matches[0]

    def invert(
        self,
        operating_point: TireOperatingPoint,
        lateral_force_magnitude_n: float,
    ) -> LateralForceDemandResult:
        return invert_lateral_force_magnitude(
            self.branch_for(operating_point), lateral_force_magnitude_n
        )


def invert_lateral_force_magnitude(
    branch: LateralForceBranch,
    lateral_force_magnitude_n: float,
    *,
    tolerance: float = 1.0e-9,
) -> LateralForceDemandResult:
    """Invert one monotonic source branch with bounded piecewise-linear interpolation."""

    demand = float(lateral_force_magnitude_n)
    if not math.isfinite(demand) or demand < 0.0:
        raise TireDataError("Lateral-force demand magnitude must be finite and nonnegative")
    minimum = branch.minimum_force_magnitude_n
    maximum = branch.maximum_force_magnitude_n
    if demand < minimum - tolerance or demand > maximum + tolerance:
        raise TireDataError(
            f"Lateral-force demand {demand:g} N is outside explicit branch range "
            f"[{minimum:g}, {maximum:g}] N for {branch.branch_id}; no extrapolation is permitted"
        )

    for sample in branch.samples:
        if math.isclose(
            demand,
            sample.lateral_force_magnitude_n,
            rel_tol=0.0,
            abs_tol=tolerance,
        ):
            return LateralForceDemandResult(
                branch_id=branch.branch_id,
                demand_magnitude_n=demand,
                required_slip_angle_magnitude_deg=sample.slip_angle_magnitude_deg,
                lower_sample=sample,
                upper_sample=sample,
                interpolation_fraction=0.0,
                exact_sample=True,
                force_utilization_of_branch_max=demand / maximum if maximum > 0.0 else 0.0,
            )

    for lower, upper in zip(branch.samples, branch.samples[1:]):
        if lower.lateral_force_magnitude_n < demand < upper.lateral_force_magnitude_n:
            fraction = (
                demand - lower.lateral_force_magnitude_n
            ) / (
                upper.lateral_force_magnitude_n - lower.lateral_force_magnitude_n
            )
            slip = lower.slip_angle_magnitude_deg + fraction * (
                upper.slip_angle_magnitude_deg - lower.slip_angle_magnitude_deg
            )
            return LateralForceDemandResult(
                branch_id=branch.branch_id,
                demand_magnitude_n=demand,
                required_slip_angle_magnitude_deg=slip,
                lower_sample=lower,
                upper_sample=upper,
                interpolation_fraction=fraction,
                exact_sample=False,
                force_utilization_of_branch_max=demand / maximum,
            )
    raise TireDataError(
        f"Could not bracket lateral-force demand {demand:g} N on branch {branch.branch_id}"
    )


def _pairs(values: Mapping[object, object] | None) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted((str(key), str(value)) for key, value in (values or {}).items())
    )


def load_lateral_force_branch_set(path: str | Path) -> TireLateralForceBranchSet:
    """Load explicit pre-peak force branches from a source-preserving TOML exchange file."""

    source_path = Path(path)
    with source_path.open("rb") as stream:
        document = tomllib.load(stream)
    if str(document.get("source_type", "")) != "explicit_lateral_force_branches":
        raise TireDataError("source_type must be explicit_lateral_force_branches")

    branches: list[LateralForceBranch] = []
    for table in document.get("branches", []):
        if not isinstance(table, dict):
            raise TireDataError("Each lateral-force branch must be a TOML table")
        point = table.get("operating_point", {})
        if not isinstance(point, dict):
            raise TireDataError("Lateral-force branch operating_point must be a table")
        sample_tables = table.get("samples", [])
        if not isinstance(sample_tables, list):
            raise TireDataError("Lateral-force branch samples must be an array of tables")
        samples = tuple(
            LateralForceCurveSample(
                slip_angle_magnitude_deg=float(sample["slip_angle_magnitude_deg"]),
                lateral_force_magnitude_n=float(sample["lateral_force_magnitude_n"]),
            )
            for sample in sample_tables
        )
        provenance = table.get("provenance", {})
        branches.append(
            LateralForceBranch(
                branch_id=str(table.get("id", "")),
                operating_point=TireOperatingPoint(
                    normal_load_n=float(point["normal_load_n"]),
                    inclination_deg=float(point["inclination_deg"]),
                    pressure_kpa=float(point["pressure_kpa"]),
                ),
                samples=samples,
                authority=str(table.get("authority", document.get("authority", ""))),
                source_branch_description=str(table.get("source_branch_description", "")),
                provenance=_pairs(provenance if isinstance(provenance, dict) else None),
            )
        )

    source = document.get("source", {})
    return TireLateralForceBranchSet(
        branch_set_id=str(document.get("branch_set_id", "")),
        version=str(document.get("version", "")),
        source_tire_id=str(document.get("source_tire_id", "")),
        intended_tire_id=str(document.get("intended_tire_id", "")),
        authority=str(document.get("authority", "")),
        source_path=str(document.get("source_path", source_path)),
        branches=tuple(branches),
        provenance=_pairs(source if isinstance(source, dict) else None),
    )
