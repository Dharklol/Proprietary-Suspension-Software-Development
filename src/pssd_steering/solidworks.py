"""Explicit adapters for SolidWorks Design Study steering evidence.

These helpers parse the native scenario-column CSV layout and apply only
reviewed linear input mappings. They do not infer monitor geometry, wheel
heading, static toe, or physical stop authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import csv
import io
import math

from .comparison import SeriesError, SignalSeries


@dataclass(frozen=True)
class LinearInputMap:
    """Reviewed positive-slope mapping between two named scalar inputs.

    A positive scale preserves source sample order. Negative-scale transforms
    are rejected rather than silently reversing evidence rows.
    """

    source_quantity_id: str
    source_unit: str
    target_quantity_id: str
    target_unit: str
    scale: float
    offset: float = 0.0
    description: str = ""

    def __post_init__(self) -> None:
        if not all(
            (
                self.source_quantity_id,
                self.source_unit,
                self.target_quantity_id,
                self.target_unit,
            )
        ):
            raise SeriesError("Linear input mapping requires quantity IDs and units")
        if not math.isfinite(self.scale) or self.scale <= 0.0:
            raise SeriesError("Linear input-map scale must be finite and positive")
        if not math.isfinite(self.offset):
            raise SeriesError("Linear input-map offset must be finite")


def parse_solidworks_design_study_csv_text(
    text: str,
    *,
    source_id: str,
    input_row_label: str,
    output_row_label: str,
    input_quantity_id: str,
    output_quantity_id: str,
    input_unit_override: str | None = None,
    output_unit_override: str | None = None,
) -> SignalSeries:
    """Parse the native SolidWorks Design Study scenario-column CSV layout.

    Expected evidence contains a ``Parameter Constraint or Goal`` header,
    an ``Initial Value`` column, and one or more ``Scenario N`` columns. Only
    scenario values are returned; the initial-value column is preserved in a
    processing note but is not inserted into or used to reorder the sweep.
    Exact signal-row labels are required.
    """

    rows = [row for row in csv.reader(io.StringIO(text)) if any(cell.strip() for cell in row)]
    if not rows:
        raise SeriesError("SolidWorks Design Study export is empty")

    study_name = rows[0][0].strip()
    if not study_name:
        raise SeriesError("SolidWorks Design Study export has no study name")

    declared_scenarios: int | None = None
    for row in rows:
        if row[0].strip() == "Scenarios/Iterations:":
            if len(row) < 2:
                raise SeriesError("Scenarios/Iterations row has no count")
            try:
                declared_scenarios = int(row[1].strip())
            except ValueError as exc:
                raise SeriesError("Scenarios/Iterations count is not an integer") from exc
            break

    header_index: int | None = None
    for index, row in enumerate(rows):
        if row[0].strip() == "Parameter Constraint or Goal":
            header_index = index
            break
    if header_index is None:
        raise SeriesError("Missing SolidWorks Design Study parameter header")

    header = rows[header_index]
    scenario_columns = [
        index for index, value in enumerate(header) if value.strip().startswith("Scenario ")
    ]
    if not scenario_columns:
        raise SeriesError("SolidWorks Design Study export contains no scenario columns")
    if declared_scenarios is not None and declared_scenarios != len(scenario_columns):
        raise SeriesError(
            "Declared scenario count does not match the number of scenario columns"
        )

    labeled_rows: dict[str, list[str]] = {}
    for row in rows[header_index + 1 :]:
        label = row[0].strip() if row else ""
        if not label:
            continue
        if label in labeled_rows:
            raise SeriesError(f"Duplicate SolidWorks signal row {label!r}")
        labeled_rows[label] = row

    missing = [
        label for label in (input_row_label, output_row_label) if label not in labeled_rows
    ]
    if missing:
        raise SeriesError(f"Missing required SolidWorks signal rows: {', '.join(missing)}")

    def scenario_values(label: str) -> tuple[float, ...]:
        row = labeled_rows[label]
        values: list[float] = []
        for column in scenario_columns:
            if column >= len(row) or not row[column].strip():
                raise SeriesError(f"Blank scenario value in SolidWorks row {label!r}")
            try:
                value = float(row[column])
            except ValueError as exc:
                raise SeriesError(
                    f"Nonnumeric scenario value in SolidWorks row {label!r}"
                ) from exc
            if not math.isfinite(value):
                raise SeriesError(f"Nonfinite scenario value in SolidWorks row {label!r}")
            values.append(value)
        return tuple(values)

    input_row = labeled_rows[input_row_label]
    output_row = labeled_rows[output_row_label]
    input_unit = input_unit_override or (input_row[2].strip() if len(input_row) > 2 else "")
    output_unit = output_unit_override or (
        output_row[2].strip() if len(output_row) > 2 else ""
    )
    if not input_unit or not output_unit:
        raise SeriesError(
            "SolidWorks signal units must be present in the export or supplied explicitly"
        )

    initial_input = input_row[3].strip() if len(input_row) > 3 else "unavailable"
    initial_output = output_row[3].strip() if len(output_row) > 3 else "unavailable"
    output_format = output_row[1].strip() if len(output_row) > 1 else ""

    return SignalSeries(
        source_id=source_id,
        input_quantity_id=input_quantity_id,
        output_quantity_id=output_quantity_id,
        input_unit=input_unit,
        output_unit=output_unit,
        inputs=scenario_values(input_row_label),
        outputs=scenario_values(output_row_label),
        processing_notes=(
            f"parsed native SolidWorks Design Study export {study_name!r}",
            f"preserved {len(scenario_columns)} scenario columns without reordering",
            f"excluded Initial Value pair ({initial_input}, {initial_output}) from sweep",
            f"output row format {output_format or 'not declared'}",
        ),
    )


def transform_linear_input(series: SignalSeries, mapping: LinearInputMap) -> SignalSeries:
    """Apply a reviewed positive-slope linear input transform.

    The output samples are unchanged. Quantity identity, units, scale, offset,
    and provenance remain explicit in the returned processing notes.
    """

    if series.input_quantity_id != mapping.source_quantity_id:
        raise SeriesError("Source input quantity does not match the reviewed linear map")
    if series.input_unit != mapping.source_unit:
        raise SeriesError("Source input unit does not match the reviewed linear map")

    transformed = tuple(mapping.scale * value + mapping.offset for value in series.inputs)
    notes = [
        *series.processing_notes,
        (
            f"input transform {mapping.target_quantity_id} = "
            f"{mapping.scale:.17g} * {mapping.source_quantity_id} + "
            f"{mapping.offset:.17g}"
        ),
    ]
    if mapping.description:
        notes.append(mapping.description)

    return SignalSeries(
        source_id=series.source_id,
        input_quantity_id=mapping.target_quantity_id,
        output_quantity_id=series.output_quantity_id,
        input_unit=mapping.target_unit,
        output_unit=series.output_unit,
        inputs=transformed,
        outputs=series.outputs,
        processing_notes=tuple(notes),
    )
