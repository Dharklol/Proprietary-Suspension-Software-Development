"""Machine-readable reports for steering candidate comparison.

The report keeps raw engineering values, role-selected parameter deltas, objective
terms, hard-constraint dispositions, analyzer states, and method provenance
visible. It does not promote a ranked development candidate to design authority.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .evaluation import CandidateEvaluation
from .roles import RequirementSet
from .search import SteeringSearchResult


def _position_state(state) -> dict[str, Any]:
    return {
        "side": state.side,
        "rack_displacement_m": state.rack_displacement,
        "status": state.status.value,
        "failure_code": state.failure_code.value if state.failure_code is not None else None,
        "message": state.message,
        "upright_rotation_rad": state.upright_rotation,
        "closure_length_residual_m": state.closure_length_residual,
        "closure_rotation_derivative": state.closure_rotation_derivative,
        "local_upright_gain_rad_per_m": state.local_upright_gain_rad_per_m,
        "branch_signature": state.branch_signature,
        "singularity_ratio_to_reference": state.singularity_ratio_to_reference,
        "geometric_branch_margin_m": state.geometric_branch_margin,
        "warnings": [item.value for item in state.warnings],
        "source_role": state.source_role,
    }


def candidate_evaluation_report(
    evaluation: CandidateEvaluation,
    requirement_set: RequirementSet,
) -> dict[str, Any]:
    """Serialize one evaluation without discarding analyzer diagnostics."""

    definitions = requirement_set.variable_map
    variables = []
    for variable_id, value in evaluation.candidate_values:
        definition = definitions[variable_id]
        variables.append(
            {
                "id": variable_id,
                "role": definition.role.value,
                "unit": definition.unit,
                "value": value,
                "reference": definition.reference,
                "delta_from_reference": value - definition.reference,
                "minimum": definition.minimum,
                "maximum": definition.maximum,
            }
        )
    geometry = None
    if evaluation.generated is not None:
        generated = evaluation.generated
        model = generated.geometry
        geometry = {
            "geometry_id": model.geometry_id,
            "version": model.version,
            "baseline_geometry_id": generated.baseline_geometry_id,
            "rack_axis_origin_m": list(model.rack.axis.point),
            "rack_axis_direction": list(model.rack.axis.direction),
            "left_inner_joint_m": list(model.left.rack_inner_joint_at_center),
            "right_inner_joint_m": list(model.right.rack_inner_joint_at_center),
            "left_outer_joint_m": list(model.left.outer_tie_rod_joint_at_center),
            "right_outer_joint_m": list(model.right.outer_tie_rod_joint_at_center),
            "left_tie_rod_length_m": generated.left_tie_rod_length,
            "right_tie_rod_length_m": generated.right_tie_rod_length,
            "metadata": dict(model.metadata),
        }
    analyzer = {
        side: [_position_state(state) for state in states]
        for side, states in evaluation.analyzer_results
    }
    return {
        "candidate_id": evaluation.candidate_id,
        "requirement_set_id": evaluation.requirement_set_id,
        "target_id": evaluation.target_id,
        "status": evaluation.status.value,
        "failure_code": evaluation.failure_code,
        "failure_message": evaluation.failure_message,
        "total_objective": evaluation.total_objective,
        "variables": variables,
        "geometry": geometry,
        "target_inputs": list(evaluation.target_inputs),
        "left_outputs_deg": list(evaluation.left_outputs),
        "right_outputs_deg": list(evaluation.right_outputs),
        "objectives": [asdict(item) for item in evaluation.objectives],
        "constraints": [asdict(item) for item in evaluation.constraints],
        "analyzer_results": analyzer,
        "provenance": dict(evaluation.provenance),
    }


def steering_search_report(
    result: SteeringSearchResult,
    requirement_set: RequirementSet,
) -> dict[str, Any]:
    """Serialize a complete search and every retained comparison candidate."""

    return {
        "search_id": result.search_id,
        "requirement_set_id": result.requirement_set_id,
        "target_id": result.target_id,
        "method_id": result.method_id,
        "method_references": list(result.method_references),
        "settings": asdict(result.settings),
        "active_variable_ids": list(result.active_variable_ids),
        "evaluated_candidate_count": result.evaluated_candidate_count,
        "feasible_candidate_count": result.feasible_candidate_count,
        "infeasible_candidate_count": result.infeasible_candidate_count,
        "failure_message": result.failure_message,
        "starts": [asdict(item) for item in result.starts],
        "ranked_candidates": [
            {
                "rank": item.rank,
                "ranking_basis": item.ranking_basis,
                "candidate": candidate_evaluation_report(item.evaluation, requirement_set),
            }
            for item in result.ranked_candidates
        ],
        "provenance": dict(result.provenance),
        "authority_boundary": (
            "Development inverse-design comparison only. Ranking does not establish "
            "packaging, manufacturing, effort, robustness, tire optimality, physical "
            "validation, or production geometry authority."
        ),
    }


def write_json_report(payload: dict[str, Any], path: str | Path) -> None:
    """Write a deterministic UTF-8 JSON report."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
