"""Machine-readable reports for suspension-pose steering evaluation."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .multistate import MultiStateSteeringEvaluation
from .poses import RigidTransform, SuspensionPoseSet


def _transform_payload(transform: RigidTransform) -> dict[str, Any]:
    return {
        "rotation": [list(row) for row in transform.rotation],
        "translation_m": list(transform.translation_m),
        "source_role": transform.source_role,
    }


def _position_payload(state) -> dict[str, Any]:
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


def multi_state_steering_report(
    result: MultiStateSteeringEvaluation,
    pose_set: SuspensionPoseSet,
) -> dict[str, Any]:
    """Serialize one provider-neutral multi-state steering study."""

    pose_map = pose_set.state_map
    states = []
    for evaluation in result.states:
        pose = pose_map[evaluation.state_id]
        states.append(
            {
                "state_id": evaluation.state_id,
                "feasible": evaluation.feasible,
                "coordinates": [asdict(item) for item in pose.coordinates],
                "left_transform": _transform_payload(pose.left_transform),
                "right_transform": _transform_payload(pose.right_transform),
                "source_type": pose.source_type,
                "source_path": pose.source_path,
                "authority": pose.authority,
                "steering_dof_rule": pose.steering_dof_rule,
                "center_left_total_heading_deg": evaluation.center_left_total_heading_deg,
                "center_right_total_heading_deg": evaluation.center_right_total_heading_deg,
                "center_left_global_heading_change_deg": evaluation.center_left_global_heading_change_deg,
                "center_right_global_heading_change_deg": evaluation.center_right_global_heading_change_deg,
                "center_left_side_local_toe_out_change_deg": evaluation.center_left_side_local_toe_out_change_deg,
                "center_right_side_local_toe_out_change_deg": evaluation.center_right_side_local_toe_out_change_deg,
                "minimum_singularity_ratio": evaluation.minimum_singularity_ratio,
                "left_total_heading_deg": list(evaluation.left_total_heading_deg),
                "right_total_heading_deg": list(evaluation.right_total_heading_deg),
                "left_incremental_from_pose_deg": list(evaluation.left_incremental_from_pose_deg),
                "right_incremental_from_pose_deg": list(evaluation.right_incremental_from_pose_deg),
                "failure_code": evaluation.failure_code,
                "failure_message": evaluation.failure_message,
                "analyzer_results": {
                    side: [_position_payload(item) for item in values]
                    for side, values in evaluation.analyzer_results
                },
                "provenance": dict(evaluation.provenance),
            }
        )
    return {
        "candidate_id": result.candidate_id,
        "requirement_set_id": result.requirement_set_id,
        "pose_set_id": result.pose_set_id,
        "nominal_state_id": result.nominal_state_id,
        "target_id_for_rack_domain_and_alignment": result.target_id,
        "feasible": result.feasible,
        "states": states,
        "provenance": dict(result.provenance),
        "authority_boundary": (
            "Provider-interface and steering-response development only. Synthetic pose states are "
            "software verification, not WUFR suspension-motion evidence. No suspension solver, "
            "physical correlation, packaging, robustness, or production authority is implied."
        ),
    }
