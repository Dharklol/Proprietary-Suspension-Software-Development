#!/usr/bin/env python3
"""Generate steering constraint-screening, sensitivity, and comparison reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pssd_steering import load_geometry
from pssd_steering.optimization import (
    CandidateComparisonSettings,
    SearchSettings,
    SensitivitySettings,
    analyze_local_sensitivity,
    build_candidate_comparison,
    candidate_comparison_report,
    evaluate_candidate,
    load_constraint_set,
    load_historical_fit_target,
    load_requirement_set,
    load_synthetic_recovery_fixture,
    local_sensitivity_report,
    resolve_candidate,
    run_nominal_inverse_design,
    screen_candidate_evaluation,
    screened_candidate_report,
)


def build_report() -> dict:
    root = Path(__file__).resolve().parents[1]
    baseline = load_geometry(
        root / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
    )
    requirement = load_requirement_set(
        root / "configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml"
    )
    constraint_set = load_constraint_set(
        root / "configurations/steering/STEERING_CONSTRAINT_PROVIDER_DEV_V0.toml"
    )
    historical = load_historical_fit_target(
        root / "benchmarks/steering/WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
    )
    synthetic = load_synthetic_recovery_fixture(
        root / "benchmarks/steering/STEERING_SYNTHETIC_RECOVERY_V0.toml",
        baseline,
        requirement,
    )

    reference_candidate = resolve_candidate(
        requirement, candidate_id="CONSTRAINT-SENSITIVITY-REFERENCE"
    )
    reference_evaluation = evaluate_candidate(
        baseline, requirement, reference_candidate, historical
    )
    screened_reference = screen_candidate_evaluation(
        reference_evaluation, constraint_set
    )
    sensitivity = analyze_local_sensitivity(
        baseline,
        requirement,
        reference_candidate,
        historical,
        constraint_set=constraint_set,
        settings=SensitivitySettings(
            relative_step_fraction=0.001,
            minimum_absolute_step=1.0e-7,
            variable_ids=("rack_longitudinal_offset",),
        ),
    )

    search = run_nominal_inverse_design(
        baseline,
        requirement,
        synthetic.target,
        settings=SearchSettings(
            active_variable_ids=synthetic.active_variable_ids,
            start_count=2,
            seed=synthetic.seed,
            maximum_iterations_per_start=12,
            initial_step_fraction=0.25,
            contraction_factor=0.5,
            minimum_step_fraction=0.01,
            start_radius_fraction=0.20,
            retained_candidate_count=30,
        ),
        search_id="STEERING-CONSTRAINT-COMPARISON-V0",
    )
    comparison = build_candidate_comparison(
        search,
        requirement,
        constraint_set,
        settings=CandidateComparisonSettings(
            maximum_candidates=4,
            minimum_normalized_design_distance=0.005,
        ),
    )

    return {
        "result_id": "STEERING-CONSTRAINT-SENSITIVITY-BENCHMARKS-V0",
        "authorization_id": "AUTH-STEER-0002",
        "evaluator_model_id": "MOD-STEER-0001",
        "optimizer_model_id": "MOD-STEER-0002",
        "baseline_geometry_id": baseline.geometry_id,
        "requirement_set_id": requirement.id,
        "constraint_set_id": constraint_set.constraint_set_id,
        "screened_reference": screened_candidate_report(
            screened_reference, requirement
        ),
        "local_sensitivity": local_sensitivity_report(
            sensitivity, requirement
        ),
        "candidate_comparison": candidate_comparison_report(comparison),
        "authority_boundary": (
            "Development constraint screening and local sensitivity only. Unavailable "
            "hardware evidence remains unavailable; no packaging, manufacturing, "
            "robustness, physical, Pareto, or production authority is implied."
        ),
    }


def summary_report(report: dict) -> dict:
    screening = report["screened_reference"]
    sensitivity = report["local_sensitivity"]
    comparison = report["candidate_comparison"]
    supplemental = screening["supplemental_constraints"]
    active = [item for item in supplemental if item["available"]]
    unavailable = [item for item in supplemental if not item["available"]]
    variable = sensitivity["variable_results"][0]
    return {
        "result_id": report["result_id"],
        "baseline_geometry_id": report["baseline_geometry_id"],
        "requirement_set_id": report["requirement_set_id"],
        "constraint_set_id": report["constraint_set_id"],
        "reference_screened_feasible": screening["screened_feasible"],
        "reference_objective": screening["candidate"]["total_objective"],
        "active_constraint_count": len(active),
        "active_constraint_pass_count": sum(1 for item in active if item["passed"]),
        "unavailable_constraint_count": len(unavailable),
        "unavailable_constraint_ids": [item["constraint_id"] for item in unavailable],
        "sensitivity_variable_id": variable["variable_id"],
        "sensitivity_scheme": variable["scheme"],
        "sensitivity_step": variable["step"],
        "objective_derivative_per_unit": variable["objective_derivative_per_unit"],
        "normalized_objective_derivative": variable[
            "normalized_objective_derivative"
        ],
        "comparison_screened_candidate_count": comparison[
            "screened_candidate_count"
        ],
        "comparison_screened_feasible_count": comparison[
            "screened_feasible_count"
        ],
        "comparison_selected_candidate_count": len(
            comparison["selected_candidates"]
        ),
        "comparison_excluded_near_duplicate_count": comparison[
            "excluded_near_duplicate_count"
        ],
        "selected_candidates": [
            {
                "comparison_rank": item["comparison_rank"],
                "candidate_id": item["candidate_id"],
                "total_objective": item["total_objective"],
                "objective_delta_from_best": item[
                    "objective_delta_from_best"
                ],
                "normalized_design_distance_from_best": item[
                    "normalized_design_distance_from_best"
                ],
                "tie_rod_length_m": item["tie_rod_length_m"],
            }
            for item in comparison["selected_candidates"]
        ],
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
