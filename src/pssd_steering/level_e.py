"""WUFR-26 canonical wheel-heading comparison against recovered Desmos fits.

This module keeps the historical convention adapter explicit.  The rigid model
is evaluated in the canonical body frame, projected through the wheel plane,
and then adapted into the historical fit convention before residuals are
computed.  Static values are retained from each evidence source instead of
being silently forced to agree.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from .comparison import SeriesComparison, SignalSeries, compare_series
from .core import GeometryError, SteeringGeometry, solve_sweep
from .legacy_fits import WheelAnglePolynomialFit
from .projection import projected_wheel_heading, reference_from_static_alignment

INPUT_QUANTITY_ID = "steering_or_pinion_input_angle_design_study"
TOTAL_OUTPUT_QUANTITY_ID = "toe_inclusive_projected_road_wheel_heading"
INCREMENTAL_OUTPUT_QUANTITY_ID = "centered_projected_road_wheel_heading"


@dataclass(frozen=True)
class HistoricalConventionAdapter:
    """Explicit mapping from canonical projected heading to a historical fit.

    ``input_sign`` maps historical input to canonical input. ``output_sign``
    maps canonical incremental heading to the historical angular orientation.
    Total-angle comparison preserves each source's own static datum; therefore
    the candidate total curve is the historical static fit value plus the
    adapted canonical incremental response.
    """

    input_sign: float = 1.0
    output_sign: float = -1.0
    side_mapping: str = "same_side"
    description: str = (
        "historical input maps directly to the reviewed Design Study input; "
        "historical response orientation is the negative of canonical signed heading; "
        "left/right identities are retained"
    )

    def __post_init__(self) -> None:
        if self.input_sign not in {-1.0, 1.0}:
            raise ValueError("input_sign must be +1 or -1")
        if self.output_sign not in {-1.0, 1.0}:
            raise ValueError("output_sign must be +1 or -1")
        if self.side_mapping != "same_side":
            raise ValueError("Only the reviewed same-side mapping is implemented")


@dataclass(frozen=True)
class SideComparison:
    side: str
    total: SeriesComparison
    incremental: SeriesComparison
    canonical_static_deg: float
    historical_static_deg: float


@dataclass(frozen=True)
class WUFR26LevelEComparison:
    adapter: HistoricalConventionAdapter
    left: SideComparison
    right: SideComparison


def _reference_series(
    fit: WheelAnglePolynomialFit,
    side: str,
    historical_inputs_deg: tuple[float, ...],
    *,
    incremental: bool,
) -> SignalSeries:
    if side == "left":
        evaluator = fit.left_incremental_deg if incremental else fit.left_total_deg
    elif side == "right":
        evaluator = fit.right_incremental_deg if incremental else fit.right_total_deg
    else:
        raise ValueError("side must be 'left' or 'right'")
    return SignalSeries(
        source_id=f"WUFR26-DESMOS-{fit.fit_id}-{side}",
        input_quantity_id=INPUT_QUANTITY_ID,
        output_quantity_id=(
            INCREMENTAL_OUTPUT_QUANTITY_ID if incremental else TOTAL_OUTPUT_QUANTITY_ID
        ),
        input_unit="deg",
        output_unit="deg",
        inputs=historical_inputs_deg,
        outputs=tuple(evaluator(value) for value in historical_inputs_deg),
        processing_notes=("direct evaluation of frozen historical polynomial fit",),
    )


def compare_wufr26_projected_heading(
    geometry: SteeringGeometry,
    fit: WheelAnglePolynomialFit,
    historical_inputs_deg: tuple[float, ...],
    *,
    rack_metres_per_input_degree: float,
    static_toe_out_deg: float = -1.0,
    static_camber_deg: float = -2.25,
    adapter: HistoricalConventionAdapter | None = None,
) -> WUFR26LevelEComparison:
    """Compare projected left/right wheel heading to the selected historical fit."""

    adapter = adapter or HistoricalConventionAdapter()
    if len(historical_inputs_deg) < 2 or not all(
        upper > lower for lower, upper in zip(historical_inputs_deg, historical_inputs_deg[1:])
    ):
        raise ValueError("historical_inputs_deg must be strictly increasing")
    if not math.isfinite(rack_metres_per_input_degree) or rack_metres_per_input_degree <= 0.0:
        raise ValueError("rack_metres_per_input_degree must be finite and positive")

    canonical_inputs = tuple(adapter.input_sign * value for value in historical_inputs_deg)
    displacements = tuple(value * rack_metres_per_input_degree for value in canonical_inputs)
    solved = solve_sweep(geometry, displacements)

    side_results: dict[str, SideComparison] = {}
    for side in ("left", "right"):
        corner = geometry.left if side == "left" else geometry.right
        reference = reference_from_static_alignment(
            side,
            toe_out=math.radians(static_toe_out_deg),
            camber=math.radians(static_camber_deg),
            source_role="WUFR26 OptimumK nominal alignment",
        )
        canonical_total_deg: list[float] = []
        canonical_incremental_deg: list[float] = []
        for state in solved[side]:
            if not state.ok or state.upright_rotation is None:
                raise GeometryError(
                    f"{side} steering solution unavailable at rack displacement "
                    f"{state.rack_displacement:.17g} m: {state.message}"
                )
            total, incremental = projected_wheel_heading(
                corner, reference, state.upright_rotation
            )
            canonical_total_deg.append(math.degrees(total))
            canonical_incremental_deg.append(math.degrees(incremental))

        historical_static = (
            fit.left_static_deg if side == "left" else fit.right_static_deg
        )
        adapted_incremental = tuple(
            adapter.output_sign * value for value in canonical_incremental_deg
        )
        adapted_total = tuple(historical_static + value for value in adapted_incremental)

        candidate_total = SignalSeries(
            source_id=f"{geometry.geometry_id}-projected-{side}-adapted-total",
            input_quantity_id=INPUT_QUANTITY_ID,
            output_quantity_id=TOTAL_OUTPUT_QUANTITY_ID,
            input_unit="deg",
            output_unit="deg",
            inputs=historical_inputs_deg,
            outputs=adapted_total,
            processing_notes=(adapter.description, "historical static datum retained"),
        )
        candidate_incremental = SignalSeries(
            source_id=f"{geometry.geometry_id}-projected-{side}-adapted-incremental",
            input_quantity_id=INPUT_QUANTITY_ID,
            output_quantity_id=INCREMENTAL_OUTPUT_QUANTITY_ID,
            input_unit="deg",
            output_unit="deg",
            inputs=historical_inputs_deg,
            outputs=adapted_incremental,
            processing_notes=(adapter.description,),
        )
        reference_total = _reference_series(fit, side, historical_inputs_deg, incremental=False)
        reference_incremental = _reference_series(
            fit, side, historical_inputs_deg, incremental=True
        )
        side_results[side] = SideComparison(
            side=side,
            total=compare_series(reference_total, candidate_total),
            incremental=compare_series(reference_incremental, candidate_incremental),
            canonical_static_deg=canonical_total_deg[historical_inputs_deg.index(0.0)],
            historical_static_deg=historical_static,
        )

    return WUFR26LevelEComparison(
        adapter=adapter,
        left=side_results["left"],
        right=side_results["right"],
    )
