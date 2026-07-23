#!/usr/bin/env python3
"""Generate historical-reference and synthetic-recovery optimizer reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pssd_steering import load_geometry
from pssd_steering.optimization import (
    SearchSettings,
    candidate_evaluation_report,
    evaluate_candidate,
    load_historical_fit_target,
    load_requirement_set,
    load_synthetic_recovery_fixture,
    resolve_candidate,
    run_nominal_inverse_design,
    steering_search_report,
    write_json_report,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "configurations" / "steering" / "WUFR27_STEERING_BASELINE_V0.toml"
REQUIREMENT_PATH = (
    ROOT / "configurations" / "steering" / "STEERING_INVERSE_DESIGN_DEV_V0.toml"
)
HISTORICAL_TARGET_PATH = (
    ROOT / "benchmarks" / "steering" / "WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
)
SYNTHETIC_TARGET_PATH = (
    ROOT / "benchmarks" / "steering" / "STEERING_SYNTHETIC_RECOVERY_V0.toml"
)


def build_report() -> dict:
    baseline = load_geometry(BASELINE_PATH)
    requirement = load_requirement_set(REQUIREMENT_PATH)
    historical_target = load_historical_fit_target(HISTORICAL_TARGET_PATH)
    reference = resolve_candidate(requirement, candidate_id="HISTORICAL-REFERENCE")
    historical_evaluation = evaluate_candidate(
        baseline,
        requirement,
        reference,
        historical_target,
    )
    if not historical_evaluation.feasible:
        raise RuntimeError(
            "Historical baseline evaluation failed: "
            f"{historical_evaluation.failure_code}: {historical_evaluation.failure_message}"
        )

    synthetic = load_synthetic_recovery_fixture(
        SYNTHETIC_TARGET_PATH,
        baseline,
        requirement,
    )
    settings = SearchSettings(
        active_variable_ids=synthetic.active_variable_ids,
        start_count=3,
        seed=synthetic.seed,
        maximum_iterations_per_start=28,
        initial_step_fraction=0.25,
        contraction_factor=0.5,
        minimum_step_fraction=0.0001,
        start_radius_fraction=0.20,
        retained_candidate_count=8,
    )
    recovery = run_nominal_inverse_design(
        baseline,
        requirement,
        synthetic.target,
        settings=settings,
        search_id="STEERING-SYNTHETIC-RECOVERY-V0",
    )
    best = recovery.best
    if best is None:
        raise RuntimeError("Synthetic recovery search returned no feasible candidate")
    source_values = dict(synthetic.source_candidate_values)
    recovered_values = dict(best.candidate_values)
    parameter_error = abs(
        recovered_values["rack_longitudinal_offset"]
        - source_values["rack_longitudinal_offset"]
    )
    objective = best.objectives[0].raw_value
    if parameter_error > synthetic.recovery_tolerance:
        raise RuntimeError(
            f"Synthetic parameter recovery error {parameter_error} m exceeds "
            f"{synthetic.recovery_tolerance} m"
        )
    if objective > synthetic.objective_tolerance_deg_rms:
        raise RuntimeError(
            f"Synthetic target residual {objective} deg RMS exceeds "
            f"{synthetic.objective_tolerance_deg_rms} deg RMS"
        )

    return {
        "report_id": "STEERING-NOMINAL-OPTIMIZER-BENCHMARKS-V0",
        "authorization_id": "AUTH-STEER-0002",
        "evaluator_model_id": "MOD-STEER-0001",
        "optimizer_model_id": "MOD-STEER-0002",
        "baseline_geometry_id": baseline.geometry_id,
        "requirement_set_id": requirement.id,
        "historical_reference_evaluation": candidate_evaluation_report(
            historical_evaluation,
            requirement,
        ),
        "synthetic_recovery": {
            "fixture_path": str(SYNTHETIC_TARGET_PATH),
            "source_candidate_values": source_values,
            "recovered_candidate_values": recovered_values,
            "rack_longitudinal_recovery_error_m": parameter_error,
            "target_residual_deg_rms": objective,
            "recovery_tolerance_m": synthetic.recovery_tolerance,
            "objective_tolerance_deg_rms": synthetic.objective_tolerance_deg_rms,
            "search": steering_search_report(recovery, requirement),
        },
        "authority_boundary": (
            "Historical results are nominal fit-based regression evidence and synthetic "
            "results are software verification. Neither authorizes production geometry."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary", action="store_true")
    arguments = parser.parse_args()
    report = build_report()
    payload = report
    if arguments.summary:
        historical = report["historical_reference_evaluation"]
        recovery = report["synthetic_recovery"]
        search = recovery["search"]
        payload = {
            "report_id": report["report_id"],
            "baseline_geometry_id": report["baseline_geometry_id"],
            "requirement_set_id": report["requirement_set_id"],
            "historical_reference_total_objective": historical["total_objective"],
            "historical_reference_objectives": historical["objectives"],
            "synthetic_recovery_error_m": recovery[
                "rack_longitudinal_recovery_error_m"
            ],
            "synthetic_target_residual_deg_rms": recovery["target_residual_deg_rms"],
            "synthetic_evaluated_candidate_count": search[
                "evaluated_candidate_count"
            ],
            "synthetic_feasible_candidate_count": search["feasible_candidate_count"],
            "synthetic_infeasible_candidate_count": search[
                "infeasible_candidate_count"
            ],
            "synthetic_ranked_candidate_count": len(search["ranked_candidates"]),
            "method_id": search["method_id"],
            "authority_boundary": report["authority_boundary"],
        }
    if arguments.output is not None:
        write_json_report(payload, arguments.output)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
