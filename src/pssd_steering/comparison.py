"""Traceable curve preparation and comparison for steering cross-tool evidence.

This module prepares SolidWorks-style exported curves for a later Level E
comparison. It deliberately does not infer signal identity, coordinate frames,
static toe, steering-input transmission, or monitor definitions. A comparison is
available only when both series declare the same canonical quantity and unit.

The functions are standard-library only and never extrapolate, silently reorder
samples, fit a global polynomial, or replace the rigid mechanism equations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import csv
import io
import math
from typing import Iterable, Mapping, Sequence


class SeriesError(ValueError):
    """Raised when a source curve or comparison contract is invalid."""


class ComparisonStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SignalSeries:
    """One ordered scalar output curve against one ordered scalar input."""

    source_id: str
    input_quantity_id: str
    output_quantity_id: str
    input_unit: str
    output_unit: str
    inputs: tuple[float, ...]
    outputs: tuple[float, ...]
    processing_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_id:
            raise SeriesError("source_id is required")
        if not self.input_quantity_id or not self.output_quantity_id:
            raise SeriesError("Canonical input and output quantity identities are required")
        if not self.input_unit or not self.output_unit:
            raise SeriesError("Input and output units are required")
        if len(self.inputs) != len(self.outputs) or len(self.inputs) < 2:
            raise SeriesError("A series requires equal input/output lengths of at least two")
        if not all(math.isfinite(value) for value in (*self.inputs, *self.outputs)):
            raise SeriesError("Series values must be finite")
        if not all(b > a for a, b in zip(self.inputs, self.inputs[1:])):
            raise SeriesError("Inputs must be strictly increasing; source order is not silently changed")


@dataclass(frozen=True)
class MonitorNormalization:
    """Explicit transformation from a periodic CAD monitor to a declared signal."""

    output_sign: float = 1.0
    period: float = 360.0
    center_input: float = 0.0
    subtract_center: bool = True
    description: str = ""

    def __post_init__(self) -> None:
        if not math.isfinite(self.output_sign) or self.output_sign == 0.0:
            raise SeriesError("output_sign must be finite and nonzero")
        if not math.isfinite(self.period) or self.period <= 0.0:
            raise SeriesError("period must be finite and positive")
        if not math.isfinite(self.center_input):
            raise SeriesError("center_input must be finite")


@dataclass(frozen=True)
class ComparisonMetrics:
    sample_count: int
    mean_error: float
    rmse: float
    maximum_absolute_error: float
    input_min: float
    input_max: float


@dataclass(frozen=True)
class SeriesComparison:
    status: ComparisonStatus
    metrics: ComparisonMetrics | None = None
    residuals: tuple[float, ...] = ()
    missing_or_conflicting_items: tuple[str, ...] = ()
    message: str = ""

    @property
    def available(self) -> bool:
        return self.status is ComparisonStatus.AVAILABLE


LEVEL_E_REQUIRED_METADATA = (
    "source_file_id_and_version",
    "source_hash",
    "active_solidworks_configuration",
    "motion_study_name_and_settings",
    "input_signal_identity",
    "output_signal_identity",
    "input_sign_and_unit",
    "output_sign_unit_and_monitor_definition",
    "rack_center_or_zero_input_definition",
    "static_toe_and_wheel_plane_reference",
    "evaluated_domain_and_stop_state",
)


def level_e_missing_metadata(metadata: Mapping[str, object]) -> tuple[str, ...]:
    """Return missing Level E declarations without guessing any value."""

    missing: list[str] = []
    for key in LEVEL_E_REQUIRED_METADATA:
        value = metadata.get(key)
        if value is None or value == "" or value == "unresolved":
            missing.append(key)
    return tuple(missing)


def _parse_numeric_row(row: Sequence[str], *, label: str) -> tuple[float, ...]:
    values: list[float] = []
    for index, raw in enumerate(row[1:], start=2):
        text = raw.strip()
        if not text:
            raise SeriesError(f"Blank value in row {label!r}, column {index}")
        try:
            value = float(text)
        except ValueError as exc:
            raise SeriesError(
                f"Non-numeric value {text!r} in row {label!r}, column {index}"
            ) from exc
        if not math.isfinite(value):
            raise SeriesError(f"Nonfinite value in row {label!r}, column {index}")
        values.append(value)
    return tuple(values)


def parse_transposed_csv_text(
    text: str,
    *,
    source_id: str,
    input_row_label: str,
    output_row_label: str,
    input_quantity_id: str,
    output_quantity_id: str,
    input_unit: str,
    output_unit: str,
) -> SignalSeries:
    """Parse the two-row transposed format used by recovered motion-study CSVs.

    The first cell of each row is a signal label and subsequent cells are sample
    values. Exact requested labels are required. Inputs must already be strictly
    increasing; the parser does not sort or deduplicate evidence.
    """

    rows: dict[str, tuple[float, ...]] = {}
    reader = csv.reader(io.StringIO(text))
    for raw_row in reader:
        if not raw_row or not any(cell.strip() for cell in raw_row):
            continue
        label = raw_row[0].strip()
        if not label:
            raise SeriesError("Every nonblank CSV row requires a signal label")
        if label in rows:
            raise SeriesError(f"Duplicate signal row {label!r}")
        rows[label] = _parse_numeric_row(raw_row, label=label)

    missing = [label for label in (input_row_label, output_row_label) if label not in rows]
    if missing:
        raise SeriesError(f"Missing required signal rows: {', '.join(missing)}")

    inputs = rows[input_row_label]
    outputs = rows[output_row_label]
    return SignalSeries(
        source_id=source_id,
        input_quantity_id=input_quantity_id,
        output_quantity_id=output_quantity_id,
        input_unit=input_unit,
        output_unit=output_unit,
        inputs=inputs,
        outputs=outputs,
        processing_notes=("parsed from transposed CSV without reordering",),
    )


def unwrap_periodic(values: Iterable[float], *, period: float) -> tuple[float, ...]:
    """Unwrap a periodic scalar signal by minimizing adjacent jumps.

    This is a representation transformation, not a physical model. The period
    and signal identity must come from the source contract.
    """

    if not math.isfinite(period) or period <= 0.0:
        raise SeriesError("period must be finite and positive")
    source = tuple(float(value) for value in values)
    if not source or not all(math.isfinite(value) for value in source):
        raise SeriesError("unwrap input must contain finite values")

    result = [source[0]]
    half = 0.5 * period
    for value in source[1:]:
        candidate = value
        previous = result[-1]
        while candidate - previous > half:
            candidate -= period
        while candidate - previous <= -half:
            candidate += period
        result.append(candidate)
    return tuple(result)


def interpolate_linear(inputs: Sequence[float], outputs: Sequence[float], query: float) -> float:
    """Linear interpolation inside a strictly increasing source domain only."""

    if len(inputs) != len(outputs) or len(inputs) < 2:
        raise SeriesError("Interpolation arrays must have equal length of at least two")
    if not math.isfinite(query):
        raise SeriesError("Interpolation query must be finite")
    if query < inputs[0] or query > inputs[-1]:
        raise SeriesError("Extrapolation is prohibited")
    for index, value in enumerate(inputs):
        if query == value:
            return float(outputs[index])
    for index in range(len(inputs) - 1):
        lower = inputs[index]
        upper = inputs[index + 1]
        if lower < query < upper:
            fraction = (query - lower) / (upper - lower)
            return outputs[index] + fraction * (outputs[index + 1] - outputs[index])
    raise SeriesError("Could not bracket interpolation query")


def normalize_periodic_monitor(
    series: SignalSeries,
    normalization: MonitorNormalization,
    *,
    normalized_output_quantity_id: str,
    normalized_output_unit: str | None = None,
) -> SignalSeries:
    """Apply declared sign, periodic unwrapping, and optional center subtraction."""

    unwrapped = unwrap_periodic(series.outputs, period=normalization.period)
    signed = tuple(normalization.output_sign * value for value in unwrapped)
    notes = [
        *series.processing_notes,
        f"periodic unwrap with period {normalization.period:g} {series.output_unit}",
        f"declared output sign multiplier {normalization.output_sign:g}",
    ]
    if normalization.subtract_center:
        center = interpolate_linear(series.inputs, signed, normalization.center_input)
        signed = tuple(value - center for value in signed)
        notes.append(
            f"subtracted value {center:.17g} at input {normalization.center_input:.17g}"
        )
    if normalization.description:
        notes.append(normalization.description)
    return SignalSeries(
        source_id=series.source_id,
        input_quantity_id=series.input_quantity_id,
        output_quantity_id=normalized_output_quantity_id,
        input_unit=series.input_unit,
        output_unit=normalized_output_unit or series.output_unit,
        inputs=series.inputs,
        outputs=signed,
        processing_notes=tuple(notes),
    )


def compare_series(reference: SignalSeries, candidate: SignalSeries) -> SeriesComparison:
    """Compare a candidate to a reference on the candidate input grid.

    Quantity identities and units must match exactly. Reference interpolation is
    linear and domain-limited. Residual is candidate minus reference.
    """

    conflicts: list[str] = []
    for field in (
        "input_quantity_id",
        "output_quantity_id",
        "input_unit",
        "output_unit",
    ):
        if getattr(reference, field) != getattr(candidate, field):
            conflicts.append(field)
    if conflicts:
        return SeriesComparison(
            status=ComparisonStatus.UNAVAILABLE,
            missing_or_conflicting_items=tuple(conflicts),
            message="Series identities or units do not match; comparison was not performed",
        )
    if candidate.inputs[0] < reference.inputs[0] or candidate.inputs[-1] > reference.inputs[-1]:
        return SeriesComparison(
            status=ComparisonStatus.UNAVAILABLE,
            missing_or_conflicting_items=("overlapping_domain_without_extrapolation",),
            message="Candidate domain extends beyond the reference domain",
        )

    residuals = tuple(
        candidate_value
        - interpolate_linear(reference.inputs, reference.outputs, candidate_input)
        for candidate_input, candidate_value in zip(candidate.inputs, candidate.outputs)
    )
    mean_error = sum(residuals) / len(residuals)
    rmse = math.sqrt(sum(value * value for value in residuals) / len(residuals))
    maximum = max(abs(value) for value in residuals)
    return SeriesComparison(
        status=ComparisonStatus.AVAILABLE,
        metrics=ComparisonMetrics(
            sample_count=len(residuals),
            mean_error=mean_error,
            rmse=rmse,
            maximum_absolute_error=maximum,
            input_min=candidate.inputs[0],
            input_max=candidate.inputs[-1],
        ),
        residuals=residuals,
        message="Compared on the candidate grid using domain-limited linear interpolation",
    )
