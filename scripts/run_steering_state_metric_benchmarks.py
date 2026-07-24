#!/usr/bin/env python3
"""Generate dynamic-toe and state-dependent rack-gain objective benchmark reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pssd_steering import load_geometry
from pssd_steering.optimization import (
    SearchSettings,
    StateMetricId,
    build_analyzer_state_metric_target_set,
    evaluate_state_metric_candidate,
    load_historical_fit_target,
    load_pose_set,
    load_requirement_set,
    resolve_candidate,
    run_state_metric_inverse_design,
    state_metric_pair,
)


def _objective_record(item) -> dict:
    return {
        "objective_id": item.objective_id,
        "raw_value": item.raw_value,
        "raw_unit": item.raw_unit,
        "normalization_scale": item.normalization_scale,
        "normalized_value": item.normalized_value,
        "weight": item.weight,
        "weighted_contribution": item.weighted_contribution,
        "domain": item.domain,
        "message": item.message,
    }


def _candidate_record(evaluation) -> dict:
    return {
        "candidate_id": evaluation.candidate_id,
        "feasible": evaluation.feasible,
        "candidate_values": dict(evaluation.candidate_values),
        "total_objective": evaluation.total_objective,
        "failure_code": evaluation.failure_code,
        "failure_message": evaluation.failure_message,
        "objectives": [_objective_record(item) for item in evaluation.objectives],
        "constraints": [
            {
                "constraint_id": item.constraint_id,
                "passed": item.passed,
                "state": item.state,
                "authority": item.authority,
                "message": item.message,
            }
            for item in evaluation.constraints
        ],
    }


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

    source_values = {"rack_longitudinal_offset": 0.01875}
    target_set = build_analyzer_state_metric_target_set(
        baseline,
        requirement,
        source_values,
        sampling_target,
        pose_set,
        target_set_id="STEERING-SYNTHETIC-STATE-METRICS-V0",
        version="0.1.0",
        state_metric_weights={
            ("symmetric_bump_5mm", StateMetricId.CENTER_DYNAMIC_TOE_OUT_CHANGE): 1.0,
            ("opposed_travel_5mm", StateMetricId.CENTER_DYNAMIC_TOE_OUT_CHANGE): 0.8,
            ("nominal", StateMetricId.CENTER_RACK_TO_WHEEL_GAIN): 0.6,
            ("symmetric_bump_5mm", StateMetricId.CENTER_RACK_TO_WHEEL_GAIN): 0.6,
        },
        authority="software_verification_only",
        source_path="scripts/run_steering_state_metric_benchmarks.py",
    )

    source = resolve_candidate(
        requirement,
        source_values,
        candidate_id="STATE-METRIC-BENCHMARK-SOURCE",
    )
    source_evaluation = evaluate_state_metric_candidate(
        baseline, requirement, source, target_set, pose_set
    )
    reference = resolve_candidate(requirement, candidate_id="STATE-METRIC-BENCHMARK-REFERENCE")
    reference_evaluation = evaluate_state_metric_candidate(
        baseline, requirement, reference, target_set, pose_set
    )

    source_metric_pairs: dict[str, dict[str, list[float]]] = {}
    assert source_evaluation.multistate is not None
    for state_id in ("nominal", "symmetric_bump_5mm", "opposed_travel_5mm"):
        state = source_evaluation.multistate.state_map[state_id]
        source_metric_pairs[state_id] = {
            StateMetricId.CENTER_DYNAMIC_TOE_OUT_CHANGE.value: list(
                state_metric_pair(
                    state,
                    sampling_target.rack_displacements,
                    StateMetricId.CENTER_DYNAMIC_TOE_OUT_CHANGE,
                )
            ),
            StateMetricId.CENTER_RACK_TO_WHEEL_GAIN.value: list(
                state_metric_pair(
                    state,
                    sampling_target.rack_displacements,
                    StateMetricId.CENTER_RACK_TO_WHEEL_GAIN,
                )
            ),
        }

    settings = SearchSettings(
        active_variable_ids=("rack_longitudinal_offset",),
        start_count=2,
        seed=2701,
        maximum_iterations_per_start=16,
        initial_step_fraction=0.25,
        contraction_factor=0.5,
        minimum_step_fraction=0.001,
        start_radius_fraction=0.20,
        retained_candidate_count=8,
    )
    search = run_state_metric_inverse_design(
        baseline,
        requirement,
        target_set,
        pose_set,
        settings=settings,
        search_id="STEERING-SYNTHETIC-STATE-METRIC-RECOVERY-V0",
    )

    return {
        "result_id": "STEERING-STATE-METRIC-BENCHMARKS-V0",
        "authorization_id": "AUTH-STEER-0002",
        "evaluator_model_id": "MOD-STEER-0001",
        "optimizer_model_id": "MOD-STEER-0002",
        "baseline_geometry_id": baseline.geometry_id,
        "requirement_set_id": requirement.id,
        "pose_set_id": pose_set.pose_set_id,
        "target_set_id": target_set.target_set_id,
        "source_candidate_values": source_values,
        "target_terms": [
            {
                "state_id": item.state_id,
                "metric_id": item.metric_id.value,
                "left_target": item.left_target,
                "right_target": item.right_target,
                "output_unit": item.output_unit,
                "normalization_scale": item.normalization_scale,
                "objective_weight": item.objective_weight,
                "authority": item.authority,
            }
            for item in target_set.targets
        ],
        "source_metric_pairs": source_metric_pairs,
        "source_candidate": _candidate_record(source_evaluation),
        "reference_candidate": _candidate_record(reference_evaluation),
        "search": {
            "search_id": search.search_id,
            "method_id": search.method_id,
            "active_variable_ids": list(search.active_variable_ids),
            "evaluated_candidate_count": search.evaluated_candidate_count,
            "feasible_candidate_count": search.feasible_candidate_count,
            "infeasible_candidate_count": search.infeasible_candidate_count,
            "starts": [
                {
                    "start_index": item.start_index,
                    "start_normalized": list(item.start_normalized),
                    "terminal_candidate_id": item.terminal_candidate_id,
                    "terminal_objective": item.terminal_objective,
                    "iterations": item.iterations,
                    "termination_reason": item.termination_reason,
                }
                for item in search.starts
            ],
            "ranked_candidates": [
                {
                    "rank": item.rank,
                    "ranking_basis": item.ranking_basis,
                    "candidate": _candidate_record(item.evaluation),
                }
                for item in search.ranked_candidates
            ],
            "failure_message": search.failure_message,
            "provenance": dict(search.provenance),
        },
        "authority_boundary": (
            "Synthetic state-metric software verification only. Dynamic-toe and rack-gain targets "
            "are analyzer-generated and do not establish WUFR suspension, tire-optimal, hardware, "
            "robustness, transmission, global-optimality, or production authority. The OptimumK "
            "dimensionless Steering Toe Angle Gain channel is not used as the deg/mm rack-gain target."
        ),
    }


def summary_report(report: dict) -> dict:
    ranked = report["search"]["ranked_candidates"]
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
        "source_total_objective": report["source_candidate"]["total_objective"],
        "reference_total_objective": report["reference_candidate"]["total_objective"],
        "source_rack_longitudinal_offset_m": source_x,
        "recovered_rack_longitudinal_offset_m": recovered_x,
        "recovery_absolute_error_m": (
            abs(recovered_x - source_x) if recovered_x is not None else None
        ),
        "best_total_objective": best["total_objective"] if best is not None else None,
        "best_objective_contributions": best["objectives"] if best is not None else [],
        "source_metric_pairs": report["source_metric_pairs"],
        "evaluated_candidate_count": report["search"]["evaluated_candidate_count"],
        "feasible_candidate_count": report["search"]["feasible_candidate_count"],
        "infeasible_candidate_count": report["search"]["infeasible_candidate_count"],
        "retained_candidate_count": len(ranked),
        "method_id": report["search"]["method_id"],
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
