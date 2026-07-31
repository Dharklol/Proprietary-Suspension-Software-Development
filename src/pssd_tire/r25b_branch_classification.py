"""Reviewed no-repair named-branch policy for the canonical R25B runtime table.

AUTH-TIRE-0003 selects a strict monotonic-prefix definition for each signed
pre-peak branch.  The policy preserves every source sample and publishes one
branch ID per existing source segment; it does not insert a zero-slip knot,
smooth a reversal, delete a point, or construct a monotonic envelope.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import tomllib
from typing import Final, Literal

from .steady_state_lateral import (
    SteadyStateLateralCurve,
    SteadyStateLateralFailure,
    SteadyStateLateralTable,
)

R25B_BRANCH_CLASSIFICATION_AUTHORIZED: Final[bool] = True
R25B_BRANCH_AUTHORIZATION_ID: Final[str] = "AUTH-TIRE-0003"
R25B_BRANCH_POLICY_ID: Final[str] = "R25B_STRICT_MONOTONIC_PREFIX_SIGNED_V1"
R25B_CLASSIFIED_TABLE_ID: Final[str] = "R25B_CANONICAL_CLASSIFIED_RUNTIME_V2"

POSITIVE_PRE_PEAK: Final[str] = "positive_slip_pre_peak"
NEGATIVE_PRE_PEAK: Final[str] = "negative_slip_pre_peak"
POSITIVE_POST_PEAK: Final[str] = "positive_slip_post_peak"
NEGATIVE_POST_PEAK: Final[str] = "negative_slip_post_peak"
CENTRAL_TRANSITION: Final[str] = "central_transition"
POSITIVE_INDETERMINATE_APPROACH: Final[str] = (
    "positive_slip_indeterminate_peak_approach"
)
NEGATIVE_INDETERMINATE_APPROACH: Final[str] = (
    "negative_slip_indeterminate_peak_approach"
)

R25bNamedBranchSelector = Literal[
    "positive_slip_pre_peak",
    "negative_slip_pre_peak",
    "positive_slip_post_peak",
    "negative_slip_post_peak",
]

NAMED_BRANCH_IDS: Final[tuple[str, ...]] = (
    POSITIVE_PRE_PEAK,
    NEGATIVE_PRE_PEAK,
    POSITIVE_POST_PEAK,
    NEGATIVE_POST_PEAK,
)
ALL_CLASSIFICATION_IDS: Final[tuple[str, ...]] = (
    *NAMED_BRANCH_IDS,
    CENTRAL_TRANSITION,
    POSITIVE_INDETERMINATE_APPROACH,
    NEGATIVE_INDETERMINATE_APPROACH,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_R25B_BRANCH_AUTHORIZATION: Final[Path] = (
    _REPOSITORY_ROOT / "authorizations/tire/AUTH-TIRE-0003.toml"
)


@dataclass(frozen=True, slots=True)
class R25bCurveBranchClassification:
    """Exact segment labels and side availability for one source curve."""

    curve_id: str
    segment_branch_ids: tuple[str, ...]
    positive_peak_at_source_boundary: bool
    negative_peak_at_source_boundary: bool
    positive_reversal_before_peak: bool
    negative_reversal_before_peak: bool


@dataclass(frozen=True, slots=True)
class _SideClassification:
    labels_by_source_segment: tuple[tuple[int, str], ...]
    peak_at_source_boundary: bool
    reversal_before_peak: bool


def _load_branch_authorization(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SteadyStateLateralFailure(
            "source_specific_activation_blocked",
            f"R25B branch authorization is unavailable: {path}",
        )
    with path.open("rb") as stream:
        record = tomllib.load(stream)

    required_top_level = {
        "authorization_id": R25B_BRANCH_AUTHORIZATION_ID,
        "status": "reviewed",
        "implementation_authorized": True,
        "upstream_authorization_id": "AUTH-TIRE-0002",
    }
    for key, expected in required_top_level.items():
        if record.get(key) != expected:
            raise SteadyStateLateralFailure(
                "source_specific_activation_blocked",
                f"R25B branch authorization field {key!r} does not match",
            )

    scope = record.get("scope")
    policy = record.get("branch_policy")
    branch_ids = record.get("branch_ids")
    no_repair = record.get("no_repair_contract")
    if not all(isinstance(value, dict) for value in (scope, policy, branch_ids, no_repair)):
        raise SteadyStateLateralFailure(
            "source_specific_activation_blocked",
            "R25B branch authorization is structurally incomplete",
        )
    assert isinstance(scope, dict)
    assert isinstance(policy, dict)
    assert isinstance(branch_ids, dict)
    assert isinstance(no_repair, dict)

    required_scope = {
        "named_branch_selection_authorized": True,
        "exact_source_state_named_selection_authorized": True,
        "interpolated_state_named_selection_authorized": False,
        "generic_all_root_inverse_remains_authorized": True,
    }
    for key, expected in required_scope.items():
        if scope.get(key) != expected:
            raise SteadyStateLateralFailure(
                "source_specific_activation_blocked",
                f"R25B branch scope field {key!r} does not match",
            )

    required_policy = {
        "policy_id": R25B_BRANCH_POLICY_ID,
        "pre_peak_semantics": "strict_monotonic_prefix",
        "center_crossing_role": CENTRAL_TRANSITION,
        "boundary_peak_post_peak_role": "post_peak_unavailable",
        "multiple_named_roots_behavior": "fail_closed_without_selected_candidate",
        "post_peak_semantics": "segments_outward_of_first_global_side_extremum",
    }
    for key, expected in required_policy.items():
        if policy.get(key) != expected:
            raise SteadyStateLateralFailure(
                "source_adapter_mismatch",
                f"R25B branch policy field {key!r} does not match",
            )

    expected_branch_ids = {
        "positive_pre_peak": POSITIVE_PRE_PEAK,
        "negative_pre_peak": NEGATIVE_PRE_PEAK,
        "positive_post_peak": POSITIVE_POST_PEAK,
        "negative_post_peak": NEGATIVE_POST_PEAK,
        "central_transition": CENTRAL_TRANSITION,
        "positive_indeterminate_peak_approach": POSITIVE_INDETERMINATE_APPROACH,
        "negative_indeterminate_peak_approach": NEGATIVE_INDETERMINATE_APPROACH,
    }
    for key, expected in expected_branch_ids.items():
        if branch_ids.get(key) != expected:
            raise SteadyStateLateralFailure(
                "source_adapter_mismatch",
                f"R25B branch ID field {key!r} does not match",
            )

    for key in (
        "source_samples_unchanged",
        "zero_slip_knot_insertion_prohibited",
        "smoothing_prohibited",
        "monotonic_envelope_prohibited",
        "isotonic_repair_prohibited",
        "point_deletion_prohibited",
        "tolerance_repair_prohibited",
    ):
        if no_repair.get(key) is not True:
            raise SteadyStateLateralFailure(
                "source_adapter_mismatch",
                f"R25B no-repair field {key!r} is not enforced",
            )
    return record


def require_r25b_branch_classification_authorization(
    authorization_path: Path = DEFAULT_R25B_BRANCH_AUTHORIZATION,
) -> None:
    """Validate AUTH-TIRE-0003 and return normally when it is exact."""

    if not R25B_BRANCH_CLASSIFICATION_AUTHORIZED:
        raise SteadyStateLateralFailure(
            "source_specific_activation_blocked",
            "R25B named-branch classification constant is disabled",
        )
    _load_branch_authorization(authorization_path)


def _classify_side(
    curve: SteadyStateLateralCurve,
    *,
    positive: bool,
) -> _SideClassification:
    if positive:
        sample_indices = tuple(
            index for index, alpha in enumerate(curve.slip_angle_rad) if alpha > 0.0
        )
        response = tuple(curve.lateral_force_N[index] for index in sample_indices)
        pre_peak_id = POSITIVE_PRE_PEAK
        post_peak_id = POSITIVE_POST_PEAK
        indeterminate_id = POSITIVE_INDETERMINATE_APPROACH
    else:
        sample_indices = tuple(
            reversed(
                tuple(
                    index
                    for index, alpha in enumerate(curve.slip_angle_rad)
                    if alpha < 0.0
                )
            )
        )
        response = tuple(-curve.lateral_force_N[index] for index in sample_indices)
        pre_peak_id = NEGATIVE_PRE_PEAK
        post_peak_id = NEGATIVE_POST_PEAK
        indeterminate_id = NEGATIVE_INDETERMINATE_APPROACH

    if len(sample_indices) < 2:
        side_name = "positive" if positive else "negative"
        raise SteadyStateLateralFailure(
            "source_curve_invalid",
            f"{curve.curve_id} has insufficient {side_name}-slip samples",
        )

    peak_index = max(range(len(response)), key=response.__getitem__)
    first_reversal = next(
        (
            index
            for index, (left, right) in enumerate(
                zip(response[: peak_index + 1], response[1 : peak_index + 1])
            )
            if right < left
        ),
        None,
    )
    strict_endpoint = peak_index if first_reversal is None else first_reversal

    labels: list[tuple[int, str]] = []
    for outward_segment_index in range(len(sample_indices) - 1):
        left_sample = sample_indices[outward_segment_index]
        right_sample = sample_indices[outward_segment_index + 1]
        source_segment_index = min(left_sample, right_sample)
        if outward_segment_index < strict_endpoint:
            branch_id = pre_peak_id
        elif outward_segment_index < peak_index:
            branch_id = indeterminate_id
        else:
            branch_id = post_peak_id
        labels.append((source_segment_index, branch_id))

    return _SideClassification(
        labels_by_source_segment=tuple(labels),
        peak_at_source_boundary=peak_index == len(sample_indices) - 1,
        reversal_before_peak=first_reversal is not None,
    )


def classify_r25b_curve_segments(
    curve: SteadyStateLateralCurve,
) -> R25bCurveBranchClassification:
    """Classify every existing segment under the reviewed strict-prefix rule."""

    crossing_segments = tuple(
        index
        for index, (left, right) in enumerate(
            zip(curve.slip_angle_rad, curve.slip_angle_rad[1:])
        )
        if left < 0.0 < right
    )
    if len(crossing_segments) != 1:
        raise SteadyStateLateralFailure(
            "source_curve_invalid",
            "AUTH-TIRE-0003 requires exactly one existing segment crossing alpha=0 and no inserted zero-slip knot",
        )

    labels: list[str | None] = [None] * (len(curve.slip_angle_rad) - 1)
    labels[crossing_segments[0]] = CENTRAL_TRANSITION
    positive = _classify_side(curve, positive=True)
    negative = _classify_side(curve, positive=False)

    for segment_index, branch_id in (
        positive.labels_by_source_segment + negative.labels_by_source_segment
    ):
        if labels[segment_index] is not None:
            raise SteadyStateLateralFailure(
                "source_curve_invalid",
                f"R25B segment {segment_index} received conflicting branch roles",
            )
        labels[segment_index] = branch_id

    if any(branch_id is None for branch_id in labels):
        raise SteadyStateLateralFailure(
            "source_curve_invalid",
            "R25B branch policy did not classify every existing source segment",
        )
    frozen_labels = tuple(str(branch_id) for branch_id in labels)
    if any(branch_id not in ALL_CLASSIFICATION_IDS for branch_id in frozen_labels):
        raise SteadyStateLateralFailure(
            "source_curve_invalid", "R25B branch policy emitted an unknown branch ID"
        )
    return R25bCurveBranchClassification(
        curve_id=curve.curve_id,
        segment_branch_ids=frozen_labels,
        positive_peak_at_source_boundary=positive.peak_at_source_boundary,
        negative_peak_at_source_boundary=negative.peak_at_source_boundary,
        positive_reversal_before_peak=positive.reversal_before_peak,
        negative_reversal_before_peak=negative.reversal_before_peak,
    )


def apply_r25b_branch_classification(
    table: SteadyStateLateralTable,
    authorization_path: Path = DEFAULT_R25B_BRANCH_AUTHORIZATION,
) -> SteadyStateLateralTable:
    """Return a sample-identical table with reviewed source-segment branch IDs."""

    require_r25b_branch_classification_authorization(authorization_path)
    classified_curves: list[SteadyStateLateralCurve] = []
    for curve in table.curves:
        classification = classify_r25b_curve_segments(curve)
        availability = (
            "positive_post_peak_unavailable_at_source_boundary"
            if classification.positive_peak_at_source_boundary
            else "positive_post_peak_demonstrated_inside_source_domain"
        )
        negative_availability = (
            "negative_post_peak_unavailable_at_source_boundary"
            if classification.negative_peak_at_source_boundary
            else "negative_post_peak_demonstrated_inside_source_domain"
        )
        classified_curves.append(
            replace(
                curve,
                source_branch_role="complete_signed_r25b_curve_with_reviewed_named_segments",
                segment_branch_ids=classification.segment_branch_ids,
                domain_and_censor_metadata=curve.domain_and_censor_metadata
                + (
                    f"branch_policy={R25B_BRANCH_POLICY_ID}",
                    "central_transition_is_not_named_pre_peak_or_post_peak",
                    availability,
                    negative_availability,
                    "named_branch_selection_exact_source_states_only",
                    "multiple_named_roots_fail_closed",
                ),
            )
        )
    return SteadyStateLateralTable(
        table_id=R25B_CLASSIFIED_TABLE_ID,
        curves=tuple(classified_curves),
    )
