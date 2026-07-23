#!/usr/bin/env python3
"""Generate operating-state steering target aggregation and recovery reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pssd_steering import load_geometry
from pssd_steering.optimization import (
    SearchSettings,
    evaluate_operating_state_candidate,
    load_historical_fit_target,
    load_pose_set,
    load_requirement_set,
    load_synthetic_operating_target_fixture,
    operating_state_candidate_report,
    operating_state_search_report,
    resolve_candidate,
    run_operating_state_inverse_design,
)


def build_report() -> dict:
    root = Path(__file__).resolve().parents[1]
    baseline = load_geometry(
        root / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
    )
    requirement = load_requirement_set(
        root / "configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml"
    )
    sampling_target = load_historical_fit_target(
        root / "benchmarks/steering/WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
    )
    pose_set = load_pose_set(
        root / "benchmarks/steering/STEERING_SYNTHETIC_POSE_SET_V0.toml"
    )
    fixture = load_synthetic_operating_target_fixture(
        root / "benchmarks/steering/STEERING_SYNTHETIC_OPERATING_TARGETS_V0.toml",
        baseline,
        requirement,
        sampling_target,
        pose_set,
    )

    source = resolve_candidate(
        requirement,
        dict(fixture.source_candidate_values),
        candidate_id="OPERATING-BENCHMARK-SOURCE",
    )
    source_evaluation = evaluate_operating_state_candidate(
        baseline, requirement, source, fixture.target_set, pose_set
    )
    reference = resolve_candidate(requirement, candidate_id="OPERATING-BENCHMARK-REFERENCE")
    reference_evaluation = evaluate_operating_state_candidate(
        baseline, requirement, reference, fixture.target_set, pose_set
    )
    search = run_operating_state_inverse_design(
        baseline,
        requirement,
        fixture.target_set,
        pose_set,
        settings=SearchSettings(
            active_variable_ids=fixture.active_variable_ids,
            start_count=2,
            seed=fixture.seed,
            maximum_iterations_per_start=16,
            initial_step_fraction=0.25,
            contraction_factor=0.5,
            minimum_step_fraction=0.001,
            start_radius_fraction=0.20,
            retained_candidate_count=8,
        ),
        search_id="STEERING-SYNTHETIC-OPERATING-RECOVERY-V0",
    )

    return {
        "result_id": "STEERING-OPERATING-STATE-BENCHMARKS-V0",
        "authorization_id": "AUTH-STEER-0002",
        "evaluator_model_id": "MOD-STEER-0001",
        "optimizer_model_id": "MOD-STEER-0002",
        "baseline_geometry_id": baseline.geometry_id,
        "requirement_set_id": requirement.id,
        "pose_set_id": pose_set.pose_set_id,
        "target_set_id": fixture.target_set.target_set_id,
        "source_candidate_values": dict(fixture.source_candidate_values),
        "recovery_tolerance": fixture.recovery_tolerance,
        "objective_tolerance": fixture.objective_tolerance,
        "source_candidate": operating_state_candidate_report(
            source_evaluation, fixture.target_set, pose_set
        ),
        "reference_candidate": operating_state_candidate_report(
            reference_evaluation, fixture.target_set, pose_set
        ),
        "search": operating_state_search_report(search, fixture.target_set, pose_set),
        "authority_boundary": (
            "Synthetic multi-state software verification only. The pose set and state targets are "
            "not WUFR suspension or tire-design evidence. No physical, tire-optimal, hardware, "
            "robustness, Pareto, global-optimality, or production authority is implied."
        ),
    }


def summary_report(report: dict) -> dict:
    search = report["search"]
    ranked = search["ranked_candidates"]
    best = ranked[0]["candidate"] if ranked else None
    source_x = report["source_candidate_values"]["rack_longitudinal_offset"]
    recovered_x = (
        best["candidate_values"]["rack_longitudinal_offset"] if best is not None else None
    )
    return {
        "result_id": report["result_id"],
        "baseline_geometry_id": report["baseline_geometry_id"],
        "requirement_set_id": report["requirement_set_id"],
        "pose_set_id": report["pose_set_id"],
        "target_set_id": report["target_set_id"],
        "objective_states": [
            {
                "state_id": item["state_id"],
                "role": item["role"],
                "objective_weight": item["objective_weight"],
                "normalization_scale_deg": item["normalization_scale_deg"],
            }
            for item in report["source_candidate"]["target_set"]["state_targets"]
        ],
        "source_total_objective": report["source_candidate"]["total_objective"],
        "reference_total_objective": report["reference_candidate"]["total_objective"],
        "source_rack_longitudinal_offset_m": source_x,
        "recovered_rack_longitudinal_offset_m": recovered_x,
        "recovery_absolute_error_m": (
            abs(recovered_x - source_x) if recovered_x is not None else None
        ),
        "best_total_objective": best["total_objective"] if best is not None else None,
        "best_objective_contributions": (
            [
                {
                    "objective_id": item["objective_id"],
                    "raw_value": item["raw_value"],
                    "normalized_value": item["normalized_value"],
                    "weight": item["weight"],
                    "weighted_contribution": item["weighted_contribution"],
                }
                for item in best["objectives"]
            ]
            if best is not None
            else []
        ),
        "evaluated_candidate_count": search["evaluated_candidate_count"],
        "feasible_candidate_count": search["feasible_candidate_count"],
        "infeasible_candidate_count": search["infeasible_candidate_count"],
        "retained_candidate_count": len(ranked),
        "method_id": search["method_id"],
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
