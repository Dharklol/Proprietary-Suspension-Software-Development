#!/usr/bin/env python3
"""Generate suspension-pose provider and multi-state steering benchmark reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pssd_steering import load_geometry
from pssd_steering.optimization import (
    evaluate_candidate_over_pose_set,
    load_historical_fit_target,
    load_pose_set,
    load_requirement_set,
    resolve_candidate,
)
from pssd_steering.optimization.pose_reporting import multi_state_steering_report


def build_report() -> dict:
    root = Path(__file__).resolve().parents[1]
    baseline = load_geometry(root / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml")
    requirement = load_requirement_set(root / "configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml")
    target = load_historical_fit_target(root / "benchmarks/steering/WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml")
    pose_set = load_pose_set(root / "benchmarks/steering/STEERING_SYNTHETIC_POSE_SET_V0.toml")
    candidate = resolve_candidate(requirement, candidate_id="POSE-PROVIDER-REFERENCE")
    evaluation = evaluate_candidate_over_pose_set(
        baseline,
        requirement,
        candidate,
        target,
        pose_set,
    )
    report = multi_state_steering_report(evaluation, pose_set)
    report.update(
        {
            "result_id": "STEERING-POSE-PROVIDER-BENCHMARKS-V0",
            "authorization_id": "AUTH-STEER-0002",
            "evaluator_model_id": "MOD-STEER-0001",
            "optimizer_model_id": "MOD-STEER-0002",
            "baseline_geometry_id": baseline.geometry_id,
        }
    )
    return report


def summary_report(report: dict) -> dict:
    states = {item["state_id"]: item for item in report["states"]}
    nominal = states["nominal"]
    bump = states["symmetric_bump_5mm"]
    opposed = states["opposed_travel_5mm"]
    return {
        "result_id": report["result_id"],
        "baseline_geometry_id": report["baseline_geometry_id"],
        "pose_set_id": report["pose_set_id"],
        "state_count": len(report["states"]),
        "all_states_feasible": report["feasible"],
        "nominal_left_dynamic_toe_deg": nominal["center_left_side_local_toe_out_change_deg"],
        "nominal_right_dynamic_toe_deg": nominal["center_right_side_local_toe_out_change_deg"],
        "symmetric_bump_left_dynamic_toe_deg": bump["center_left_side_local_toe_out_change_deg"],
        "symmetric_bump_right_dynamic_toe_deg": bump["center_right_side_local_toe_out_change_deg"],
        "symmetric_bump_minimum_singularity_ratio": bump["minimum_singularity_ratio"],
        "opposed_travel_left_dynamic_toe_deg": opposed["center_left_side_local_toe_out_change_deg"],
        "opposed_travel_right_dynamic_toe_deg": opposed["center_right_side_local_toe_out_change_deg"],
        "opposed_travel_minimum_singularity_ratio": opposed["minimum_singularity_ratio"],
        "rack_sample_count_per_side": len(nominal["left_total_heading_deg"]),
        "authority_boundary": report["authority_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = build_report()
    payload = summary_report(report) if arguments.summary else report
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
