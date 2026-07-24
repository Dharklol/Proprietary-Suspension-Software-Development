"""Downstream figure-spec builders for steering R&D reports.

These helpers only package already-computed arrays and simple report residuals for
:mod:`pssd_viz`.  They do not solve steering geometry, tire response, suspension
motion, or vehicle dynamics.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from .contracts import (
    EngineeringFigureSpec,
    FigureAvailability,
    FigureMetadata,
    SeriesSpec,
)


def _series(label: str, x: Sequence[float], y: Sequence[float]) -> SeriesSpec:
    return SeriesSpec.from_iterables(label=label, x=x, y=y)


def _difference(
    minuend: Sequence[float],
    subtrahend: Sequence[float],
    inputs: Sequence[float],
) -> tuple[float, ...]:
    values = tuple(float(a) - float(b) for a, b in zip(minuend, subtrahend))
    if len(values) != len(inputs):
        raise ValueError("difference inputs and data arrays must have equal lengths")
    return values


def steering_response_comparison_spec(
    *,
    figure_id: str,
    title: str,
    inputs_deg: Sequence[float],
    left_target_deg: Sequence[float],
    right_target_deg: Sequence[float],
    left_response_deg: Sequence[float],
    right_response_deg: Sequence[float],
    configuration_id: str,
    authority: str,
    source_ids: Sequence[str],
    notes: Sequence[str] = (),
) -> EngineeringFigureSpec:
    """Build a target-versus-evaluated steering response figure."""

    return EngineeringFigureSpec(
        metadata=FigureMetadata(
            figure_id=figure_id,
            title=title,
            x_quantity="Steering input",
            x_unit="deg",
            y_quantity="Centered projected road-wheel heading",
            y_unit="deg",
            model_id="MOD-STEER-0001",
            configuration_id=configuration_id,
            authority=authority,
            source_ids=tuple(source_ids),
            notes=tuple(notes),
        ),
        series=(
            _series("left target", inputs_deg, left_target_deg),
            _series("right target", inputs_deg, right_target_deg),
            _series("left evaluated", inputs_deg, left_response_deg),
            _series("right evaluated", inputs_deg, right_response_deg),
        ),
    )


def steering_residual_spec(
    *,
    figure_id: str,
    title: str,
    inputs_deg: Sequence[float],
    left_target_deg: Sequence[float],
    right_target_deg: Sequence[float],
    left_response_deg: Sequence[float],
    right_response_deg: Sequence[float],
    configuration_id: str,
    authority: str,
    source_ids: Sequence[str],
    notes: Sequence[str] = (),
) -> EngineeringFigureSpec:
    """Build evaluated-minus-target residual curves.

    Subtraction is a report transformation only; all physical quantities must already
    have been produced by the upstream evaluator/target providers.
    """

    left = _difference(left_response_deg, left_target_deg, inputs_deg)
    right = _difference(right_response_deg, right_target_deg, inputs_deg)
    return EngineeringFigureSpec(
        metadata=FigureMetadata(
            figure_id=figure_id,
            title=title,
            x_quantity="Steering input",
            x_unit="deg",
            y_quantity="Evaluated minus target wheel heading",
            y_unit="deg",
            model_id="MOD-STEER-0001",
            configuration_id=configuration_id,
            authority=authority,
            source_ids=tuple(source_ids),
            notes=tuple(notes),
        ),
        series=(
            _series("left residual", inputs_deg, left),
            _series("right residual", inputs_deg, right),
        ),
    )


def target_comparison_spec(
    *,
    figure_id: str,
    title: str,
    inputs_deg: Sequence[float],
    baseline_left_deg: Sequence[float],
    baseline_right_deg: Sequence[float],
    alternate_left_deg: Sequence[float],
    alternate_right_deg: Sequence[float],
    configuration_id: str,
    authority: str,
    source_ids: Sequence[str],
    notes: Sequence[str] = (),
) -> EngineeringFigureSpec:
    """Compare two already-computed left/right steering target sets."""

    return EngineeringFigureSpec(
        metadata=FigureMetadata(
            figure_id=figure_id,
            title=title,
            x_quantity="Steering input",
            x_unit="deg",
            y_quantity="Target road-wheel heading",
            y_unit="deg",
            model_id="MOD-STEER-0002",
            configuration_id=configuration_id,
            authority=authority,
            source_ids=tuple(source_ids),
            notes=tuple(notes),
        ),
        series=(
            _series("baseline left", inputs_deg, baseline_left_deg),
            _series("baseline right", inputs_deg, baseline_right_deg),
            _series("alternate left", inputs_deg, alternate_left_deg),
            _series("alternate right", inputs_deg, alternate_right_deg),
        ),
    )


def target_correction_spec(
    *,
    figure_id: str,
    title: str,
    inputs_deg: Sequence[float],
    baseline_left_deg: Sequence[float],
    baseline_right_deg: Sequence[float],
    alternate_left_deg: Sequence[float],
    alternate_right_deg: Sequence[float],
    configuration_id: str,
    authority: str,
    source_ids: Sequence[str],
    notes: Sequence[str] = (),
) -> EngineeringFigureSpec:
    """Show alternate-minus-baseline target correction directly."""

    left = _difference(alternate_left_deg, baseline_left_deg, inputs_deg)
    right = _difference(alternate_right_deg, baseline_right_deg, inputs_deg)
    return EngineeringFigureSpec(
        metadata=FigureMetadata(
            figure_id=figure_id,
            title=title,
            x_quantity="Steering input",
            x_unit="deg",
            y_quantity="Alternate minus baseline target heading",
            y_unit="deg",
            model_id="MOD-STEER-0002",
            configuration_id=configuration_id,
            authority=authority,
            source_ids=tuple(source_ids),
            notes=tuple(notes),
        ),
        series=(
            _series("left target correction", inputs_deg, left),
            _series("right target correction", inputs_deg, right),
        ),
    )


def tire_force_branch_spec(
    *,
    figure_id: str,
    title: str,
    curves: Iterable[tuple[str, Sequence[float], Sequence[float]]],
    configuration_id: str,
    authority: str,
    source_ids: Sequence[str],
    notes: Sequence[str] = (),
) -> EngineeringFigureSpec:
    """Package explicit pre-peak ``|Fy|`` versus ``|alpha|`` branch samples."""

    series = tuple(_series(label, slip, force) for label, slip, force in curves)
    return EngineeringFigureSpec(
        metadata=FigureMetadata(
            figure_id=figure_id,
            title=title,
            x_quantity="Slip-angle magnitude",
            x_unit="deg",
            y_quantity="Lateral-force magnitude",
            y_unit="N",
            model_id="TIRE-LATERAL-FORCE-BRANCH",
            configuration_id=configuration_id,
            authority=authority,
            source_ids=tuple(source_ids),
            notes=tuple(notes),
        ),
        series=series,
    )


def motion_state_comparison_spec(
    *,
    figure_id: str,
    title: str,
    velocity_center_s_m: Sequence[float],
    left_heading_deg: Sequence[float],
    right_heading_deg: Sequence[float],
    configuration_id: str,
    authority: str,
    source_ids: Sequence[str],
    state_ids: Sequence[str],
    notes: Sequence[str] = (),
) -> EngineeringFigureSpec:
    """Compare required headings across already-computed planar-motion states."""

    return EngineeringFigureSpec(
        metadata=FigureMetadata(
            figure_id=figure_id,
            title=title,
            x_quantity="Velocity-center longitudinal position S",
            x_unit="m",
            y_quantity="Required incremental wheel heading",
            y_unit="deg",
            model_id="MOD-VEH-0002",
            configuration_id=configuration_id,
            authority=authority,
            source_ids=tuple(source_ids),
            state_ids=tuple(state_ids),
            notes=tuple(notes),
        ),
        series=(
            _series("left required heading", velocity_center_s_m, left_heading_deg),
            _series("right required heading", velocity_center_s_m, right_heading_deg),
        ),
    )


def unavailable_figure_spec(
    *,
    figure_id: str,
    title: str,
    x_quantity: str,
    x_unit: str,
    y_quantity: str,
    y_unit: str,
    model_id: str,
    configuration_id: str,
    authority: str,
    reason: str,
    source_ids: Sequence[str] = (),
    notes: Sequence[str] = (),
) -> EngineeringFigureSpec:
    """Build an explicit diagnostic artifact for a source-gated requested figure."""

    return EngineeringFigureSpec(
        metadata=FigureMetadata(
            figure_id=figure_id,
            title=title,
            x_quantity=x_quantity,
            x_unit=x_unit,
            y_quantity=y_quantity,
            y_unit=y_unit,
            model_id=model_id,
            configuration_id=configuration_id,
            authority=authority,
            source_ids=tuple(source_ids),
            notes=tuple(notes),
        ),
        availability=FigureAvailability.UNAVAILABLE,
        unavailable_reason=reason,
    )
