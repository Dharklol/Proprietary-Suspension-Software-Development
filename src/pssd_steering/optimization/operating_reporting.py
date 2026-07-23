"""Machine-readable reports for operating-state steering target studies."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .operating_evaluation import OperatingStateCandidateEvaluation
from .operating_search import OperatingStateSearchResult
from .operating_targets import OperatingStateTargetSet
from .pose_reporting import multi_state_steering_report
from .poses import SuspensionPoseSet


def _target_set_payload(target_set: OperatingStateTargetSet) -> dict[str, Any]:
    return {
        "target_set_id": target_set.target_set_id,
        "version": target_set.version,
        "pose_set_id": target_set.pose_set_id,
        "sampling_target_id": target_set.sampling_target.target_id,
        "aggregation_method": target_set.aggregation_method,
        "unlisted_state_role": target_set.unlisted_state_role.value,
        "authority": target_set.authority,
        "source_path": target_set.source_path,
        "provenance": dict(target_set.provenance),
        "state_targets": [
            {
                "state_id": target.state_id,
                "role": target.role.value,
                "objective_id": target.objective_id,
                "output_quantity_id": target.output_quantity_id,
                "output_unit": target.output_unit,
                "left_outputs": list(target.left_outputs),
                "right_outputs": list(target.right_outputs),
                "sample_weights": list(target.sample_weights),
                "normalization_scale_deg": target.normalization_scale_deg,
                "objective_weight": target.objective_weight,
                "canonical_to_target_output_sign": target.canonical_to_target_output_sign,
                "require_monotonic_response": target.require_monotonic_response,
                "monotonic_tolerance_deg": target.monotonic_tolerance_deg,
                "source_type": target.source_type,
                "authority": target.authority,
                "source_path": target.source_path,
                "provenance": dict(target.provenance),
            }
            for target in target_set.state_targets
        ],
    }


def operating_state_candidate_report(
    evaluation: OperatingStateCandidateEvaluation,
    target_set: OperatingStateTargetSet,
    pose_set: SuspensionPoseSet,
) -> dict[str, Any]:
    """Serialize a complete candidate with per-state objective decomposition."""

    return {
        "candidate_id": evaluation.candidate_id,
        "requirement_set_id": evaluation.requirement_set_id,
        "target_set_id": evaluation.target_set_id,
        "pose_set_id": evaluation.pose_set_id,
        "status": evaluation.status.value,
        "feasible": evaluation.feasible,
        "candidate_values": dict(evaluation.candidate_values),
        "total_objective": evaluation.total_objective,
        "constraints": [asdict(item) for item in evaluation.constraints],
        "objectives": [asdict(item) for item in evaluation.objectives],
        "failure_code": evaluation.failure_code,
        "failure_message": evaluation.failure_message,
        "multistate": (
            multi_state_steering_report(evaluation.multistate, pose_set)
            if evaluation.multistate is not None
            else None
        ),
        "target_set": _target_set_payload(target_set),
        "provenance": dict(evaluation.provenance),
        "authority_boundary": (
            "Operating-state target aggregation and deterministic development search only. "
            "State targets are explicit provider inputs; no tire-optimality, suspension-model, "
            "physical-correlation, hardware-feasibility, robustness, Pareto, global-optimality, "
            "or production-selection authority is implied."
        ),
    }


def operating_state_search_report(
    result: OperatingStateSearchResult,
    target_set: OperatingStateTargetSet,
    pose_set: SuspensionPoseSet,
) -> dict[str, Any]:
    """Serialize the deterministic multi-state candidate archive retained for comparison."""

    return {
        "search_id": result.search_id,
        "requirement_set_id": result.requirement_set_id,
        "target_set_id": result.target_set_id,
        "pose_set_id": result.pose_set_id,
        "method_id": result.method_id,
        "method_references": list(result.method_references),
        "settings": asdict(result.settings),
        "active_variable_ids": list(result.active_variable_ids),
        "evaluated_candidate_count": result.evaluated_candidate_count,
        "feasible_candidate_count": result.feasible_candidate_count,
        "infeasible_candidate_count": result.infeasible_candidate_count,
        "starts": [asdict(item) for item in result.starts],
        "ranked_candidates": [
            {
                "rank": item.rank,
                "ranking_basis": item.ranking_basis,
                "candidate": operating_state_candidate_report(
                    item.evaluation, target_set, pose_set
                ),
            }
            for item in result.ranked_candidates
        ],
        "failure_message": result.failure_message,
        "target_set": _target_set_payload(target_set),
        "provenance": dict(result.provenance),
        "authority_boundary": (
            "Candidate ranking uses only the explicitly listed operating-state objective terms "
            "and hard analyzer/monotonicity constraints. Unlisted states are report-only by "
            "declared policy; unavailable future tire, effort, hardware, tolerance, and physical "
            "providers cannot affect the score."
        ),
    }
