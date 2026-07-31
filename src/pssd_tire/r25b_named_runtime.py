"""AUTH-TIRE-0003 classified R25B runtime and named inverse selection."""

from __future__ import annotations

from dataclasses import replace
from typing import Final

from .r25b_branch_classification import (
    NAMED_BRANCH_IDS,
    R25B_CLASSIFIED_TABLE_ID,
    R25bNamedBranchSelector,
    apply_r25b_branch_classification,
    require_r25b_branch_classification_authorization,
)
from .r25b_runtime import (
    R25B_CANONICAL_SOURCE_CONVENTION_ID,
    load_r25b_steady_state_lateral_table,
)
from .r25b_source_native import EXPECTED_SOURCE_TIRE_ID
from .steady_state_lateral import (
    SteadyStateLateralCurve,
    SteadyStateLateralFailure,
    SteadyStateLateralInverseResult,
    SteadyStateLateralOperatingState,
    SteadyStateLateralResponse,
    SteadyStateLateralTable,
    evaluate_table,
    invert_lateral_force,
)

R25B_NAMED_RUNTIME_TABLE_ID: Final[str] = R25B_CLASSIFIED_TABLE_ID


def load_r25b_classified_lateral_table() -> SteadyStateLateralTable:
    """Load AUTH-TIRE-0002 data and apply the reviewed AUTH-TIRE-0003 policy."""

    return apply_r25b_branch_classification(load_r25b_steady_state_lateral_table())


def evaluate_r25b_classified_lateral(
    operating_state: SteadyStateLateralOperatingState,
    *,
    table: SteadyStateLateralTable | None = None,
) -> SteadyStateLateralResponse:
    """Evaluate the sample-identical classified table without extrapolation."""

    selected_table = table or load_r25b_classified_lateral_table()
    return evaluate_table(selected_table, operating_state)


def _exact_source_state_curve(
    table: SteadyStateLateralTable,
    *,
    normal_load_N: float,
    inclination_rad: float,
    pressure_Pa: float,
) -> SteadyStateLateralCurve:
    matches = [
        curve
        for curve in table.curves
        if abs(curve.normal_load_N - normal_load_N) <= 1.0e-12
        and abs(curve.inclination_rad - inclination_rad) <= 1.0e-12
        and abs(curve.pressure_Pa - pressure_Pa) <= 1.0e-12
    ]
    if len(matches) != 1:
        raise SteadyStateLateralFailure(
            "inverse_named_branch_requires_exact_source_state",
            "AUTH-TIRE-0003 permits named selection only at one exact R25B source state",
        )
    return matches[0]


def invert_r25b_classified_lateral_force(
    *,
    normal_load_N: float,
    inclination_rad: float,
    pressure_Pa: float,
    requested_lateral_force_N: float,
    state_id: str = "r25b_classified_inverse_query",
    branch_selector: R25bNamedBranchSelector | None = None,
    table: SteadyStateLateralTable | None = None,
) -> SteadyStateLateralInverseResult:
    """Return all roots or select one reviewed exact-state signed branch.

    The all-root path remains available at exact and bounded interpolated states.
    Named selection is exact-state only because branch boundaries need not align
    across curves in a complete interpolation cell.
    """

    selected_table = table or load_r25b_classified_lateral_table()
    result = invert_lateral_force(
        selected_table,
        normal_load_N=normal_load_N,
        inclination_rad=inclination_rad,
        pressure_Pa=pressure_Pa,
        requested_lateral_force_N=requested_lateral_force_N,
        source_id=EXPECTED_SOURCE_TIRE_ID,
        source_convention_id=R25B_CANONICAL_SOURCE_CONVENTION_ID,
        state_id=state_id,
        branch_selector=None,
    )
    if branch_selector is None:
        return result

    require_r25b_branch_classification_authorization()
    if branch_selector not in NAMED_BRANCH_IDS:
        raise SteadyStateLateralFailure(
            "inverse_branch_ambiguous",
            f"unrecognized R25B named branch selector: {branch_selector}",
        )
    _exact_source_state_curve(
        selected_table,
        normal_load_N=normal_load_N,
        inclination_rad=inclination_rad,
        pressure_Pa=pressure_Pa,
    )
    matches = [
        candidate
        for candidate in result.candidates
        if branch_selector in candidate.contributing_branch_ids
    ]
    if not matches:
        raise SteadyStateLateralFailure(
            "inverse_branch_unavailable",
            "the requested named branch has no root at this exact source state and force",
        )
    if len(matches) != 1:
        raise SteadyStateLateralFailure(
            "inverse_branch_ambiguous",
            "the requested named branch identifies multiple roots; no candidate was selected",
        )
    return replace(
        result,
        status="named_branch_selected",
        message=f"exact-state R25B branch selected: {branch_selector}",
        branch_selection_applied=True,
        selected_candidate=matches[0],
    )
