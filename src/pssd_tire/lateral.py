"""Dependency-free lateral tire summary interpolation.

This module intentionally implements a small, source-preserving response-surface
contract rather than a second Magic Formula implementation. The first use case is
steering target generation from reviewed TTC-derived lateral summaries. Richer tire
models may be added behind the same operating-point contract later.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import tomllib
from typing import Iterable


class TireDataError(ValueError):
    """Raised when tire source data are incomplete, inconsistent, or out of domain."""


@dataclass(frozen=True)
class TireOperatingPoint:
    """Steady lateral tire operating point used to query a response surface."""

    normal_load_n: float
    inclination_deg: float
    pressure_kpa: float

    def __post_init__(self) -> None:
        values = (self.normal_load_n, self.inclination_deg, self.pressure_kpa)
        if not all(math.isfinite(value) for value in values):
            raise TireDataError("Tire operating-point values must be finite")
        if self.normal_load_n <= 0.0:
            raise TireDataError("normal_load_n must be positive")
        if self.pressure_kpa <= 0.0:
            raise TireDataError("pressure_kpa must be positive")


@dataclass(frozen=True)
class LateralSummarySample:
    """One source-grid sample with no hidden convention conversion."""

    normal_load_n: float
    inclination_deg: float
    pressure_kpa: float
    cornering_stiffness_n_per_deg: float
    peak_lateral_force_n: float
    source_peak_slip_angle_deg: float
    peak_slip_angle_censored: bool = False

    @property
    def peak_slip_angle_magnitude_deg(self) -> float:
        return abs(self.source_peak_slip_angle_deg)


@dataclass(frozen=True)
class LateralSummaryEstimate:
    """Interpolated lateral summary at one operating point."""

    operating_point: TireOperatingPoint
    cornering_stiffness_n_per_deg: float
    peak_lateral_force_n: float
    source_peak_slip_angle_deg: float
    peak_slip_angle_censored: bool
    source_sample_count: int

    @property
    def peak_slip_angle_magnitude_deg(self) -> float:
        return abs(self.source_peak_slip_angle_deg)


@dataclass(frozen=True)
class TireLateralSummaryGrid:
    """Reviewed steady-state lateral summary with bounded trilinear interpolation."""

    grid_id: str
    version: str
    source_tire_id: str
    intended_tire_id: str
    authority: str
    source_path: str
    samples: tuple[LateralSummarySample, ...]
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.grid_id or not self.source_tire_id or not self.intended_tire_id:
            raise TireDataError("Tire grid identity fields are required")
        if not self.samples:
            raise TireDataError("Tire grid requires at least one sample")
        keys = [
            (sample.pressure_kpa, sample.inclination_deg, sample.normal_load_n)
            for sample in self.samples
        ]
        if len(keys) != len(set(keys)):
            raise TireDataError("Tire grid contains duplicate operating points")

    @property
    def pressures_kpa(self) -> tuple[float, ...]:
        return tuple(sorted({sample.pressure_kpa for sample in self.samples}))

    @property
    def inclinations_deg(self) -> tuple[float, ...]:
        return tuple(sorted({sample.inclination_deg for sample in self.samples}))

    @property
    def normal_loads_n(self) -> tuple[float, ...]:
        return tuple(sorted({sample.normal_load_n for sample in self.samples}))

    @property
    def sample_map(self) -> dict[tuple[float, float, float], LateralSummarySample]:
        return {
            (sample.pressure_kpa, sample.inclination_deg, sample.normal_load_n): sample
            for sample in self.samples
        }

    def estimate(
        self,
        operating_point: TireOperatingPoint,
        *,
        require_uncensored_peak: bool = True,
    ) -> LateralSummaryEstimate:
        """Interpolate without extrapolation and propagate source peak censoring."""

        pressure = _axis_weights(
            operating_point.pressure_kpa, self.pressures_kpa, name="pressure_kpa"
        )
        inclination = _axis_weights(
            operating_point.inclination_deg, self.inclinations_deg, name="inclination_deg"
        )
        normal_load = _axis_weights(
            operating_point.normal_load_n, self.normal_loads_n, name="normal_load_n"
        )

        weighted: list[tuple[LateralSummarySample, float]] = []
        mapping = self.sample_map
        for p_value, p_weight in pressure:
            for ia_value, ia_weight in inclination:
                for fz_value, fz_weight in normal_load:
                    weight = p_weight * ia_weight * fz_weight
                    if weight <= 0.0:
                        continue
                    key = (p_value, ia_value, fz_value)
                    try:
                        sample = mapping[key]
                    except KeyError as exc:
                        raise TireDataError(
                            "Tire grid is missing an interpolation corner at "
                            f"P={p_value:g} kPa, IA={ia_value:g} deg, Fz={fz_value:g} N"
                        ) from exc
                    weighted.append((sample, weight))

        censored = any(
            sample.peak_slip_angle_censored
            for sample, weight in weighted
            if weight > 0.0
        )
        if require_uncensored_peak and censored:
            raise TireDataError(
                "Peak-slip interpolation touches a source value censored by the slip-angle sweep boundary"
            )

        return LateralSummaryEstimate(
            operating_point=operating_point,
            cornering_stiffness_n_per_deg=_weighted_value(
                weighted, "cornering_stiffness_n_per_deg"
            ),
            peak_lateral_force_n=_weighted_value(weighted, "peak_lateral_force_n"),
            source_peak_slip_angle_deg=_weighted_value(
                weighted, "source_peak_slip_angle_deg"
            ),
            peak_slip_angle_censored=censored,
            source_sample_count=len(weighted),
        )


def _weighted_value(
    weighted: Iterable[tuple[LateralSummarySample, float]], attribute: str
) -> float:
    return sum(getattr(sample, attribute) * weight for sample, weight in weighted)


def _axis_weights(
    value: float,
    axis: tuple[float, ...],
    *,
    name: str,
    tolerance: float = 1.0e-12,
) -> tuple[tuple[float, float], ...]:
    if not axis:
        raise TireDataError(f"{name} axis is empty")
    for point in axis:
        if math.isclose(value, point, rel_tol=0.0, abs_tol=tolerance):
            return ((point, 1.0),)
    if value < axis[0] or value > axis[-1]:
        raise TireDataError(
            f"{name}={value:g} is outside reviewed interpolation domain [{axis[0]:g}, {axis[-1]:g}]"
        )
    for lower, upper in zip(axis, axis[1:]):
        if lower < value < upper:
            fraction = (value - lower) / (upper - lower)
            return ((lower, 1.0 - fraction), (upper, fraction))
    raise TireDataError(f"Could not bracket {name}={value:g}")


def load_lateral_summary_grid(path: str | Path) -> TireLateralSummaryGrid:
    """Load a provider-neutral lateral summary grid from TOML."""

    source_path = Path(path)
    with source_path.open("rb") as stream:
        document = tomllib.load(stream)
    if str(document.get("source_type", "")) != "tabulated_lateral_summary":
        raise TireDataError("Tire source_type is not tabulated_lateral_summary")

    samples: list[LateralSummarySample] = []
    for item in document.get("samples", []):
        sample = LateralSummarySample(
            normal_load_n=float(item["normal_load_n"]),
            inclination_deg=float(item["inclination_deg"]),
            pressure_kpa=float(item["pressure_kpa"]),
            cornering_stiffness_n_per_deg=float(item["cornering_stiffness_n_per_deg"]),
            peak_lateral_force_n=float(item["peak_lateral_force_n"]),
            source_peak_slip_angle_deg=float(item["source_peak_slip_angle_deg"]),
            peak_slip_angle_censored=bool(
                item.get("peak_slip_angle_censored", False)
            ),
        )
        values = (
            sample.normal_load_n,
            sample.inclination_deg,
            sample.pressure_kpa,
            sample.cornering_stiffness_n_per_deg,
            sample.peak_lateral_force_n,
            sample.source_peak_slip_angle_deg,
        )
        if not all(math.isfinite(value) for value in values):
            raise TireDataError("Tire sample contains a nonfinite numeric value")
        if (
            sample.cornering_stiffness_n_per_deg <= 0.0
            or sample.peak_lateral_force_n <= 0.0
        ):
            raise TireDataError(
                "Tire summary stiffness and peak force must be positive magnitudes"
            )
        samples.append(sample)

    source = document.get("source", {})
    equivalence = document.get("engineering_equivalence", {})
    provenance = tuple(
        sorted(
            (str(key), str(value))
            for key, value in {
                "source_provider": source.get("provider", ""),
                "source_folder_id": source.get("folder_id", ""),
                "cornering_runs": source.get("cornering_runs", ""),
                "intended_tire_equivalence_basis": equivalence.get("basis", ""),
            }.items()
        )
    )
    return TireLateralSummaryGrid(
        grid_id=str(document.get("grid_id", "")),
        version=str(document.get("version", "0")),
        source_tire_id=str(document.get("source_tire_id", "")),
        intended_tire_id=str(document.get("intended_tire_id", "")),
        authority=str(document.get("authority", "")),
        source_path=str(source_path),
        samples=tuple(samples),
        provenance=provenance,
    )
