"""Deterministic audit of candidate named-branch policies for the R25B table.

This module is diagnostic only. It does not assign segment branch IDs, alter
source samples, or authorize named inverse selection. The audit compares two
non-repair policies against the exact canonical R25B source curves:

* ``strict_monotonic_prefix`` stops before the first outward force reversal;
* ``global_extremum_positional`` retains every sample through the first global
  side extremum and reports all force intervals with multiple side-local roots.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import degrees
from typing import Final, Literal

from .r25b_runtime import load_r25b_steady_state_lateral_table
from .steady_state_lateral import SteadyStateLateralCurve, SteadyStateLateralTable

BranchSide = Literal["positive_slip", "negative_slip"]
BRANCH_CLASSIFICATION_AUDIT_ID: Final[str] = "R25B_BRANCH_CLASSIFICATION_AUDIT_V1"


@dataclass(frozen=True, slots=True)
class AmbiguousForceInterval:
    lower_response_N: float
    upper_response_N: float
    maximum_root_count: int

    @property
    def span_N(self) -> float:
        return self.upper_response_N - self.lower_response_N


@dataclass(frozen=True, slots=True)
class R25bSideBranchAudit:
    curve_id: str
    side: BranchSide
    side_sample_count: int
    peak_sample_index_from_center: int
    peak_at_source_domain_boundary: bool
    peak_abs_slip_deg: float
    peak_outward_response_N: float
    reversal_segment_count: int
    maximum_local_reversal_N: float
    strict_prefix_endpoint_index_from_center: int
    strict_prefix_endpoint_abs_slip_deg: float
    strict_prefix_endpoint_response_N: float
    strict_prefix_force_shortfall_N: float
    strict_prefix_relative_force_shortfall: float
    strict_prefix_slip_truncation_deg: float
    ambiguous_force_intervals: tuple[AmbiguousForceInterval, ...]

    @property
    def has_prepeak_reversal(self) -> bool:
        return self.reversal_segment_count > 0

    @property
    def ambiguous_force_span_N(self) -> float:
        return sum(interval.span_N for interval in self.ambiguous_force_intervals)


@dataclass(frozen=True, slots=True)
class R25bBranchClassificationAudit:
    audit_id: str
    curve_count: int
    sample_count: int
    exact_zero_slip_knot_curve_count: int
    side_audits: tuple[R25bSideBranchAudit, ...]

    @property
    def affected_side_count(self) -> int:
        return sum(side.has_prepeak_reversal for side in self.side_audits)

    @property
    def affected_curve_count(self) -> int:
        return len({side.curve_id for side in self.side_audits if side.has_prepeak_reversal})


def _side_samples(
    curve: SteadyStateLateralCurve,
    side: BranchSide,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if side == "positive_slip":
        pairs = [
            (alpha, force)
            for alpha, force in zip(curve.slip_angle_rad, curve.lateral_force_N)
            if alpha > 0.0
        ]
    else:
        pairs = [
            (-alpha, -force)
            for alpha, force in reversed(
                tuple(zip(curve.slip_angle_rad, curve.lateral_force_N))
            )
            if alpha < 0.0
        ]
    return tuple(pair[0] for pair in pairs), tuple(pair[1] for pair in pairs)


def _ambiguous_force_intervals(
    outward_response_N: tuple[float, ...],
) -> tuple[AmbiguousForceInterval, ...]:
    levels = sorted(set(outward_response_N))
    elementary: list[AmbiguousForceInterval] = []
    for lower, upper in zip(levels, levels[1:]):
        if upper <= lower:
            continue
        query = 0.5 * (lower + upper)
        root_count = sum(
            min(left, right) < query < max(left, right)
            for left, right in zip(outward_response_N, outward_response_N[1:])
        )
        if root_count > 1:
            elementary.append(
                AmbiguousForceInterval(
                    lower_response_N=lower,
                    upper_response_N=upper,
                    maximum_root_count=root_count,
                )
            )

    merged: list[AmbiguousForceInterval] = []
    for interval in elementary:
        if merged and abs(interval.lower_response_N - merged[-1].upper_response_N) <= 1.0e-12:
            previous = merged[-1]
            merged[-1] = AmbiguousForceInterval(
                lower_response_N=previous.lower_response_N,
                upper_response_N=interval.upper_response_N,
                maximum_root_count=max(
                    previous.maximum_root_count, interval.maximum_root_count
                ),
            )
        else:
            merged.append(interval)
    return tuple(merged)


def audit_curve_side(
    curve: SteadyStateLateralCurve,
    side: BranchSide,
) -> R25bSideBranchAudit:
    abs_slip_rad, outward_response_N = _side_samples(curve, side)
    if len(abs_slip_rad) < 2:
        raise ValueError(f"{curve.curve_id} has insufficient {side} samples")

    peak_index = max(range(len(outward_response_N)), key=outward_response_N.__getitem__)
    approach_slip = abs_slip_rad[: peak_index + 1]
    approach_response = outward_response_N[: peak_index + 1]
    reversals = tuple(
        left - right
        for left, right in zip(approach_response, approach_response[1:])
        if right < left
    )
    if reversals:
        strict_index = next(
            index
            for index, (left, right) in enumerate(
                zip(approach_response, approach_response[1:])
            )
            if right < left
        )
    else:
        strict_index = peak_index

    peak_response = approach_response[-1]
    strict_response = approach_response[strict_index]
    shortfall = peak_response - strict_response
    return R25bSideBranchAudit(
        curve_id=curve.curve_id,
        side=side,
        side_sample_count=len(abs_slip_rad),
        peak_sample_index_from_center=peak_index,
        peak_at_source_domain_boundary=peak_index == len(abs_slip_rad) - 1,
        peak_abs_slip_deg=degrees(approach_slip[-1]),
        peak_outward_response_N=peak_response,
        reversal_segment_count=len(reversals),
        maximum_local_reversal_N=max(reversals, default=0.0),
        strict_prefix_endpoint_index_from_center=strict_index,
        strict_prefix_endpoint_abs_slip_deg=degrees(approach_slip[strict_index]),
        strict_prefix_endpoint_response_N=strict_response,
        strict_prefix_force_shortfall_N=shortfall,
        strict_prefix_relative_force_shortfall=(
            shortfall / abs(peak_response) if peak_response != 0.0 else 0.0
        ),
        strict_prefix_slip_truncation_deg=degrees(
            approach_slip[-1] - approach_slip[strict_index]
        ),
        ambiguous_force_intervals=_ambiguous_force_intervals(approach_response),
    )


def audit_r25b_branch_classification(
    table: SteadyStateLateralTable | None = None,
) -> R25bBranchClassificationAudit:
    selected = table or load_r25b_steady_state_lateral_table()
    side_audits = tuple(
        audit_curve_side(curve, side)
        for curve in selected.curves
        for side in ("positive_slip", "negative_slip")
    )
    return R25bBranchClassificationAudit(
        audit_id=BRANCH_CLASSIFICATION_AUDIT_ID,
        curve_count=len(selected.curves),
        sample_count=sum(len(curve.slip_angle_rad) for curve in selected.curves),
        exact_zero_slip_knot_curve_count=sum(
            any(alpha == 0.0 for alpha in curve.slip_angle_rad)
            for curve in selected.curves
        ),
        side_audits=side_audits,
    )


def build_r25b_branch_classification_result(
    table: SteadyStateLateralTable | None = None,
) -> dict[str, object]:
    audit = audit_r25b_branch_classification(table)
    affected = tuple(side for side in audit.side_audits if side.has_prepeak_reversal)
    positive = tuple(side for side in audit.side_audits if side.side == "positive_slip")
    negative = tuple(side for side in audit.side_audits if side.side == "negative_slip")

    def maximum(attribute: str) -> float:
        return max(float(getattr(side, attribute)) for side in audit.side_audits)

    return {
        "audit_id": audit.audit_id,
        "authorization_id": "AUTH-TIRE-0002",
        "status": "review_required_no_branch_ids_assigned",
        "curve_count": audit.curve_count,
        "sample_count": audit.sample_count,
        "side_count": len(audit.side_audits),
        "exact_zero_slip_knot_curve_count": audit.exact_zero_slip_knot_curve_count,
        "positive_side": {
            "reversal_affected_curve_count": sum(side.has_prepeak_reversal for side in positive),
            "reversal_segment_count": sum(side.reversal_segment_count for side in positive),
            "peak_at_source_boundary_count": sum(
                side.peak_at_source_domain_boundary for side in positive
            ),
        },
        "negative_side": {
            "reversal_affected_curve_count": sum(side.has_prepeak_reversal for side in negative),
            "reversal_segment_count": sum(side.reversal_segment_count for side in negative),
            "peak_at_source_boundary_count": sum(
                side.peak_at_source_domain_boundary for side in negative
            ),
        },
        "combined": {
            "reversal_affected_side_count": audit.affected_side_count,
            "reversal_affected_curve_count": audit.affected_curve_count,
            "maximum_local_reversal_N": maximum("maximum_local_reversal_N"),
            "maximum_strict_prefix_force_shortfall_N": maximum(
                "strict_prefix_force_shortfall_N"
            ),
            "maximum_strict_prefix_relative_force_shortfall": maximum(
                "strict_prefix_relative_force_shortfall"
            ),
            "maximum_strict_prefix_slip_truncation_deg": maximum(
                "strict_prefix_slip_truncation_deg"
            ),
            "maximum_global_extremum_ambiguous_force_span_N": maximum(
                "ambiguous_force_span_N"
            ),
            "maximum_side_local_root_count": max(
                (
                    interval.maximum_root_count
                    for side in audit.side_audits
                    for interval in side.ambiguous_force_intervals
                ),
                default=1,
            ),
        },
        "affected_sides": [
            {
                "curve_id": side.curve_id,
                "side": side.side,
                "reversal_segment_count": side.reversal_segment_count,
                "maximum_local_reversal_N": side.maximum_local_reversal_N,
                "strict_prefix_force_shortfall_N": side.strict_prefix_force_shortfall_N,
                "strict_prefix_relative_force_shortfall": side.strict_prefix_relative_force_shortfall,
                "strict_prefix_slip_truncation_deg": side.strict_prefix_slip_truncation_deg,
                "peak_at_source_domain_boundary": side.peak_at_source_domain_boundary,
                "ambiguous_force_intervals": [
                    {
                        "lower_response_N": interval.lower_response_N,
                        "upper_response_N": interval.upper_response_N,
                        "maximum_root_count": interval.maximum_root_count,
                    }
                    for interval in side.ambiguous_force_intervals
                ],
            }
            for side in affected
        ],
        "policy_candidates": {
            "strict_monotonic_prefix": {
                "source_sample_values_modified": False,
                "unique_monotonic_side_inverse": True,
                "force_reach_reduced_on_affected_sides": True,
                "remainder_before_global_peak_role": "indeterminate_peak_approach",
            },
            "global_extremum_positional": {
                "source_sample_values_modified": False,
                "full_global_peak_reach_retained": True,
                "multiple_named_prepeak_roots_possible": True,
                "required_ambiguity_behavior": "fail_closed_without_selected_candidate",
            },
            "tolerance_or_isotonic_repair": {
                "source_sample_values_modified": True,
                "compatible_with_current_no_repair_authorization": False,
            },
        },
        "unresolved_decisions": [
            "Choose strict monotonic-prefix or global-extremum positional pre-peak semantics.",
            "Define the branch role of each segment that crosses alpha=0 because no source curve contains an exact zero-slip knot.",
            "Define post-peak availability when a side extremum occurs at the +/-12 deg source boundary.",
            "Define fail-closed behavior for multiple roots within a named branch.",
        ],
    }
