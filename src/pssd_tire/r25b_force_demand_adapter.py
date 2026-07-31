"""Source-backed exact-state R25B branches for steering force-demand inversion.

The adapter projects the explicitly classified negative-slip pre-peak source
branches into the existing magnitude-only steering exchange contract.  The
selected source side is recorded and no zero-force anchor, smoothing, repair,
track scaling, operating-state interpolation, or force extrapolation is added.
"""

from __future__ import annotations

from math import degrees, radians
from typing import Final

from .force_demand import (
    LateralForceBranch,
    LateralForceCurveSample,
    TireLateralForceBranchSet,
)
from .lateral import TireOperatingPoint
from .r25b_branch_classification import NEGATIVE_PRE_PEAK
from .r25b_named_runtime import load_r25b_classified_lateral_table
from .steady_state_lateral import (
    SteadyStateLateralCurve,
    SteadyStateLateralFailure,
    SteadyStateLateralTable,
)

R25B_FORCE_DEMAND_BRANCH_SET_ID: Final[str] = (
    "WUFR26_R25B_EXACT_NEGATIVE_PREPEAK_FORCE_DEMAND_V1"
)
R25B_FORCE_DEMAND_ADAPTER_AUTHORITY: Final[str] = (
    "AUTH-STEER-0003 with AUTH-TIRE-0002 and AUTH-TIRE-0003"
)
INSIDE_REFERENCE_POINT: Final[TireOperatingPoint] = TireOperatingPoint(
    222.0, 0.0, 82.7
)
OUTSIDE_REFERENCE_POINT: Final[TireOperatingPoint] = TireOperatingPoint(
    1112.0, 2.0, 82.7
)


def _curve_for(
    table: SteadyStateLateralTable,
    operating_point: TireOperatingPoint,
) -> SteadyStateLateralCurve:
    inclination_rad = radians(operating_point.inclination_deg)
    pressure_pa = 1000.0 * operating_point.pressure_kpa
    matches = [
        curve
        for curve in table.curves
        if abs(curve.normal_load_N - operating_point.normal_load_n) <= 1.0e-12
        and abs(curve.inclination_rad - inclination_rad) <= 1.0e-12
        and abs(curve.pressure_Pa - pressure_pa) <= 1.0e-9
    ]
    if len(matches) != 1:
        raise SteadyStateLateralFailure(
            "source_curve_unavailable",
            "R25B force-demand adapter requires one exact classified source state",
        )
    return matches[0]


def _negative_prepeak_magnitude_branch(
    curve: SteadyStateLateralCurve,
    operating_point: TireOperatingPoint,
    *,
    branch_id: str,
    expected_sample_count: int,
    role: str,
) -> LateralForceBranch:
    segment_indices = tuple(
        index
        for index, source_branch_id in enumerate(curve.segment_branch_ids)
        if source_branch_id == NEGATIVE_PRE_PEAK
    )
    if not segment_indices:
        raise SteadyStateLateralFailure(
            "source_curve_unavailable",
            f"{curve.curve_id} has no authorized negative-slip pre-peak branch",
        )
    if segment_indices != tuple(
        range(segment_indices[0], segment_indices[-1] + 1)
    ):
        raise SteadyStateLateralFailure(
            "source_curve_invalid",
            f"{curve.curve_id} negative-slip pre-peak branch is not contiguous",
        )

    knot_indices = tuple(range(segment_indices[0], segment_indices[-1] + 2))
    pairs = []
    for index in knot_indices:
        alpha = curve.slip_angle_rad[index]
        force = curve.lateral_force_N[index]
        if alpha >= 0.0 or force >= 0.0:
            raise SteadyStateLateralFailure(
                "source_adapter_mismatch",
                "selected R25B negative-slip pre-peak knots must retain negative canonical alpha and Fy",
            )
        pairs.append((abs(degrees(alpha)), -force))
    pairs.sort(key=lambda pair: pair[0])
    samples = tuple(
        LateralForceCurveSample(
            slip_angle_magnitude_deg=slip,
            lateral_force_magnitude_n=force,
        )
        for slip, force in pairs
    )
    if len(samples) != expected_sample_count:
        raise SteadyStateLateralFailure(
            "source_curve_invalid",
            f"{curve.curve_id} expected {expected_sample_count} exact pre-peak samples, found {len(samples)}",
        )
    return LateralForceBranch(
        branch_id=branch_id,
        operating_point=operating_point,
        samples=samples,
        authority=R25B_FORCE_DEMAND_ADAPTER_AUTHORITY,
        source_branch_description=(
            "Exact AUTH-TIRE-0003 negative_slip_pre_peak source knots projected to "
            f"|alpha|/|Fy| for the declared {role} reference role; no zero anchor or repair."
        ),
        provenance=(
            ("source_curve_id", curve.curve_id),
            ("source_branch_id", NEGATIVE_PRE_PEAK),
            ("source_side", "negative_slip"),
            ("canonical_force_sign", "negative"),
            ("canonical_slip_sign", "negative"),
            ("magnitude_projection", "abs(alpha), -Fy"),
            ("zero_anchor_inserted", "false"),
            ("track_scale_applied", "false"),
        ),
    )


def load_r25b_reference_force_demand_branch_set(
    table: SteadyStateLateralTable | None = None,
) -> TireLateralForceBranchSet:
    """Build the reviewed two-state steering branch exchange from exact source knots."""

    selected = table or load_r25b_classified_lateral_table()
    inside_curve = _curve_for(selected, INSIDE_REFERENCE_POINT)
    outside_curve = _curve_for(selected, OUTSIDE_REFERENCE_POINT)
    inside = _negative_prepeak_magnitude_branch(
        inside_curve,
        INSIDE_REFERENCE_POINT,
        branch_id="r25b_inside_222n_0deg_82p7kpa_negative_prepeak",
        expected_sample_count=64,
        role="inside-low-load",
    )
    outside = _negative_prepeak_magnitude_branch(
        outside_curve,
        OUTSIDE_REFERENCE_POINT,
        branch_id="r25b_outside_1112n_2deg_82p7kpa_negative_prepeak",
        expected_sample_count=86,
        role="outside-high-load",
    )
    return TireLateralForceBranchSet(
        branch_set_id=R25B_FORCE_DEMAND_BRANCH_SET_ID,
        version="0.1.0",
        source_tire_id=inside_curve.source_tire_id,
        intended_tire_id=inside_curve.intended_tire_id,
        authority=R25B_FORCE_DEMAND_ADAPTER_AUTHORITY,
        source_path=inside_curve.source_path,
        branches=(inside, outside),
        provenance=(
            ("adapter", "exact_negative_slip_prepeak_to_magnitude_v1"),
            ("upstream_tire_authorization", "AUTH-TIRE-0003"),
            ("steering_authorization", "AUTH-STEER-0003"),
            ("operating_state_interpolation", "false"),
            ("zero_anchor_inserted", "false"),
            ("track_scale_applied", "false"),
        ),
    )
