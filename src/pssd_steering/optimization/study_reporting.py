"""Machine-readable reports for constraint screening, sensitivity, and comparison."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .candidate_comparison import CandidateComparisonResult
from .constraints import ScreenedCandidateEvaluation
from .reporting import candidate_evaluation_report
from .roles import RequirementSet
from .sensitivity import LocalSensitivityResult


def screened_candidate_report(
    screened: ScreenedCandidateEvaluation,
    requirement_set: RequirementSet,
) -> dict[str, Any]:
    return {
        "candidate": candidate_evaluation_report(
            screened.base_evaluation, requirement_set
        ),
        "constraint_set_id": screened.constraint_set_id,
        "screened_feasible": screened.feasible,
        "screening_failure_code": screened.failure_code,
        "screening_failure_message": screened.failure_message,
        "supplemental_constraints": [
            {
                **asdict(item),
                "disposition": item.disposition.value,
                "passed": item.passed,
                "available": item.available,
            }
            for item in screened.supplemental_constraints
        ],
        "unavailable_constraint_ids": list(screened.unavailable_constraint_ids),
    }


def local_sensitivity_report(
    result: LocalSensitivityResult,
    requirement_set: RequirementSet,
) -> dict[str, Any]:
    return {
        "candidate_id": result.candidate_id,
        "requirement_set_id": result.requirement_set_id,
        "target_id": result.target_id,
        "constraint_set_id": result.constraint_set_id,
        "status": result.status,
        "message": result.message,
        "base_evaluation": (
            screened_candidate_report(result.base_evaluation, requirement_set)
            if result.base_evaluation is not None
            else None
        ),
        "variable_results": [asdict(item) for item in result.variable_results],
        "provenance": dict(result.provenance),
        "authority_boundary": (
            "Local finite-difference development sensitivity only. It is not a "
            "manufacturing tolerance, uncertainty propagation, robustness, or physical "
            "correlation result."
        ),
    }


def candidate_comparison_report(
    result: CandidateComparisonResult,
) -> dict[str, Any]:
    return {
        "search_id": result.search_id,
        "requirement_set_id": result.requirement_set_id,
        "target_id": result.target_id,
        "constraint_set_id": result.constraint_set_id,
        "screened_candidate_count": result.screened_candidate_count,
        "screened_feasible_count": result.screened_feasible_count,
        "screened_infeasible_count": result.screened_infeasible_count,
        "excluded_near_duplicate_count": result.excluded_near_duplicate_count,
        "selected_candidates": [asdict(item) for item in result.selected_candidates],
        "authority_boundary": result.authority_boundary,
        "provenance": dict(result.provenance),
    }
