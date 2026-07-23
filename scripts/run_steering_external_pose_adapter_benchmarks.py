#!/usr/bin/env python3
"""Generate external suspension-pose exchange adapter benchmark reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pssd_steering import load_geometry
from pssd_steering.optimization import (
    evaluate_candidate_over_pose_set,
    load_external_pose_table,
    load_historical_fit_target,
    load_pose_set,
    load_requirement_set,
    resolve_candidate,
)


def _max_abs(values: list[float]) -> float:
    return max((abs(value) for value in values), default=0.0)


def build_report() -> dict:
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "benchmarks/steering/STEERING_EXTERNAL_POSE_TABLE_FIXTURE_V0.toml"
    reference_path = root / "benchmarks/steering/STEERING_SYNTHETIC_POSE_SET_V0.toml"
    imported = load_external_pose_table(manifest_path)
    reference = load_pose_set(reference_path)

    transform_differences: list[float] = []
    coordinate_differences: list[float] = []
    for expected, actual in zip(reference.states, imported.pose_set.states):
        for expected_transform, actual_transform in (
            (expected.left_transform, actual.left_transform),
            (expected.right_transform, actual.right_transform),
        ):
            transform_differences.extend(
                a - b
                for expected_row, actual_row in zip(expected_transform.rotation, actual_transform.rotation)
                for a, b in zip(expected_row, actual_row)
            )
            transform_differences.extend(
                a - b
                for a, b in zip(expected_transform.translation_m, actual_transform.translation_m)
            )
        for expected_coordinate, actual_coordinate in zip(expected.coordinates, actual.coordinates):
            coordinate_differences.append(expected_coordinate.value - actual_coordinate.value)

    baseline = load_geometry(root / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml")
    requirement = load_requirement_set(root / "configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml")
    target = load_historical_fit_target(root / "benchmarks/steering/WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml")
    candidate = resolve_candidate(requirement, candidate_id="EXTERNAL-POSE-ADAPTER-BENCHMARK")
    expected_eval = evaluate_candidate_over_pose_set(baseline, requirement, candidate, target, reference)
    actual_eval = evaluate_candidate_over_pose_set(
        baseline, requirement, candidate, target, imported.pose_set
    )

    heading_differences: list[float] = []
    dynamic_toe_differences: list[float] = []
    for expected_state, actual_state in zip(expected_eval.states, actual_eval.states):
        heading_differences.extend(
            a - b
            for a, b in zip(expected_state.left_total_heading_deg, actual_state.left_total_heading_deg)
        )
        heading_differences.extend(
            a - b
            for a, b in zip(expected_state.right_total_heading_deg, actual_state.right_total_heading_deg)
        )
        for expected_value, actual_value in (
            (
                expected_state.center_left_side_local_toe_out_change_deg,
                actual_state.center_left_side_local_toe_out_change_deg,
            ),
            (
                expected_state.center_right_side_local_toe_out_change_deg,
                actual_state.center_right_side_local_toe_out_change_deg,
            ),
        ):
            if expected_value is not None and actual_value is not None:
                dynamic_toe_differences.append(expected_value - actual_value)

    return {
        "result_id": "STEERING-EXTERNAL-POSE-ADAPTER-BENCHMARKS-V0",
        "authorization_id": "AUTH-STEER-0002",
        "evaluator_model_id": "MOD-STEER-0001",
        "optimizer_model_id": "MOD-STEER-0002",
        "adapter_id": imported.adapter_id,
        "adapter_version": imported.adapter_version,
        "manifest_path": imported.manifest_path,
        "data_path": imported.data_path,
        "source_type": imported.source_type,
        "source_path": imported.source_path,
        "source_revision": imported.source_revision,
        "authority": imported.authority,
        "frame_id": imported.frame_id,
        "frame_definition": imported.frame_definition,
        "rotation_convention": imported.rotation_convention,
        "pose_set_id": imported.pose_set.pose_set_id,
        "state_count": len(imported.pose_set.states),
        "reference_pose_set_id": reference.pose_set_id,
        "max_abs_transform_component_difference": _max_abs(transform_differences),
        "max_abs_coordinate_difference": _max_abs(coordinate_differences),
        "max_abs_heading_difference_deg": _max_abs(heading_differences),
        "max_abs_dynamic_toe_difference_deg": _max_abs(dynamic_toe_differences),
        "all_imported_states_feasible": actual_eval.feasible,
        "source_discovery": {
            "status": "no_reviewed_machine_readable_wufr_zero_steer_upright_transform_series_identified",
            "descriptive_sources": [
                {
                    "title": "2026 Suspension Design Binder",
                    "drive_id": "1QjUfQWjII9rNlr8_E_wqP9NjUsBDuH-M5wquw4ZnZec",
                    "role": "descriptive evidence that SolidWorks motion studies were used in suspension/steering geometry development",
                },
                {
                    "title": "Kinematics Validation TRR",
                    "drive_id": "1V4eWwE49s16vMrV9NQ1U9VaELbgXJu_7j2kY4zDxBas",
                    "role": "descriptive evidence that simulated kinematics were intended for comparison with measured toe/camber",
                },
            ],
        },
        "authority_boundary": (
            "This benchmark proves exchange-format ingestion and analyzer parity only. The CSV/TOML fixture "
            "duplicates the existing synthetic pose fixture. It is not WUFR suspension-motion evidence and "
            "does not authorize design ranking until a reviewed external zero-steer upright pose source is supplied."
        ),
    }


def summary_report(report: dict) -> dict:
    return {
        "result_id": report["result_id"],
        "adapter_id": report["adapter_id"],
        "pose_set_id": report["pose_set_id"],
        "state_count": report["state_count"],
        "max_abs_transform_component_difference": report["max_abs_transform_component_difference"],
        "max_abs_coordinate_difference": report["max_abs_coordinate_difference"],
        "max_abs_heading_difference_deg": report["max_abs_heading_difference_deg"],
        "max_abs_dynamic_toe_difference_deg": report["max_abs_dynamic_toe_difference_deg"],
        "all_imported_states_feasible": report["all_imported_states_feasible"],
        "source_discovery_status": report["source_discovery"]["status"],
        "authority_boundary": report["authority_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report()
    payload = summary_report(report) if args.summary else report
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
