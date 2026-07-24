#!/usr/bin/env python3
"""Generate force-demand tire-slip steering target and regime diagnostics."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from pssd_steering import load_geometry
from pssd_steering.derived import assign_inside_outside
from pssd_steering.optimization import (
    evaluate_operating_state_candidate,
    load_historical_fit_target,
    load_pose_set,
    load_requirement_set,
    resolve_candidate,
)
from pssd_steering.optimization.force_demand_targets import (
    ForceDemandStateDefinition,
    build_force_demand_operating_target_set,
    classify_heading_pair,
    differential_heading_reference,
)
from pssd_steering.optimization.tire_targets import peak_grip_slip_angle_differential
from pssd_tire import (
    TireOperatingPoint,
    load_lateral_force_branch_set,
    load_lateral_summary_grid,
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


def _heading_record(reference) -> dict:
    return {
        "inside_heading_magnitude_deg": reference.inside_heading_magnitude_deg,
        "ackermann_outside_heading_magnitude_deg": (
            reference.ackermann_outside_heading_magnitude_deg
        ),
        "slip_differential_deg": reference.slip_differential_deg,
        "corrected_outside_heading_magnitude_deg": (
            reference.corrected_outside_heading_magnitude_deg
        ),
        "ackermann_inside_minus_outside_gap_deg": (
            reference.ackermann_inside_minus_outside_gap_deg
        ),
        "corrected_inside_minus_outside_gap_deg": (
            reference.corrected_inside_minus_outside_gap_deg
        ),
        "regime": reference.regime.value,
    }


def build_report() -> dict:
    root = Path(__file__).resolve().parents[1]
    geometry = load_geometry(
        root / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
    )
    if geometry.wheelbase is None or geometry.steering_axis_track is None:
        raise RuntimeError("Force-demand Ackermann adapter requires wheelbase and track")
    requirement = load_requirement_set(
        root / "configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml"
    )
    sampling = load_historical_fit_target(
        root / "benchmarks/steering/WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
    )
    pose_set = load_pose_set(
        root / "benchmarks/steering/STEERING_SYNTHETIC_POSE_SET_V0.toml"
    )
    r25b_grid = load_lateral_summary_grid(
        root / "benchmarks/tires/WUFR26_H43105_R25B_LATERAL_SUMMARY_V0.toml"
    )
    synthetic_branches = load_lateral_force_branch_set(
        root / "benchmarks/tires/SYNTHETIC_FORCE_DEMAND_BRANCHES_V0.toml"
    )

    inside_point = TireOperatingPoint(222.0, 0.0, 83.0)
    outside_point = TireOperatingPoint(1112.0, 2.0, 83.0)

    # Diagnose the already-merged PR28 target using its actual R25B peak-slip pair.
    peak = peak_grip_slip_angle_differential(
        r25b_grid, inside_point, outside_point
    )
    peak_differential = peak.outside_minus_inside_peak_slip_deg
    maximum_input = max(abs(value) for value in sampling.inputs)

    endpoint_index = sampling.inputs.index(maximum_input)
    endpoint_assignment = assign_inside_outside(
        math.radians(
            sampling.canonical_to_target_output_sign
            * sampling.left_outputs[endpoint_index]
        ),
        math.radians(
            sampling.canonical_to_target_output_sign
            * sampling.right_outputs[endpoint_index]
        ),
    )
    endpoint_reference = differential_heading_reference(
        math.degrees(endpoint_assignment.inside_incremental_magnitude),
        wheelbase_m=geometry.wheelbase,
        steering_axis_track_m=geometry.steering_axis_track,
        slip_differential_deg=peak_differential,
    )

    near_center_index = sampling.inputs.index(15.0)
    near_center_assignment = assign_inside_outside(
        math.radians(
            sampling.canonical_to_target_output_sign
            * sampling.left_outputs[near_center_index]
        ),
        math.radians(
            sampling.canonical_to_target_output_sign
            * sampling.right_outputs[near_center_index]
        ),
    )
    near_center_utilization = abs(sampling.inputs[near_center_index]) / maximum_input
    near_center_reference = differential_heading_reference(
        math.degrees(near_center_assignment.inside_incremental_magnitude),
        wheelbase_m=geometry.wheelbase,
        steering_axis_track_m=geometry.steering_axis_track,
        slip_differential_deg=peak_differential * near_center_utilization,
    )

    # Software-only force-demand schedule.  It intentionally exercises a mixed regime:
    # the force-derived slip differential can exceed the small geometric Ackermann gap
    # at modest steer but remain below the much larger gap at the endpoint.
    utilization = tuple(abs(value) / maximum_input for value in sampling.inputs)
    inside_force = tuple(300.0 * value for value in utilization)
    outside_force = tuple(2500.0 * value for value in utilization)
    definition = ForceDemandStateDefinition(
        state_id="nominal",
        inside_operating_point=inside_point,
        outside_operating_point=outside_point,
        inside_lateral_force_magnitude_by_sample=inside_force,
        outside_lateral_force_magnitude_by_sample=outside_force,
        authority="synthetic force-demand schedule for software verification only",
        provenance=(("physical_authority", "none"),),
    )
    target_set = build_force_demand_operating_target_set(
        sampling,
        pose_set,
        synthetic_branches,
        (definition,),
        target_set_id="SYNTHETIC_FORCE_DEMAND_STEERING_TARGET_V0",
        version="0.1.0",
        wheelbase_m=geometry.wheelbase,
        steering_axis_track_m=geometry.steering_axis_track,
        authority="BENCH-STEER-0021 software verification only",
        source_path="scripts/run_steering_force_demand_benchmarks.py",
    )
    target = target_set.state_map["nominal"]

    regimes = []
    for index, input_deg in enumerate(sampling.inputs):
        if input_deg == 0.0:
            regimes.append(
                {
                    "input_deg": input_deg,
                    "regime": "parallel",
                    "inside_heading_magnitude_deg": 0.0,
                    "outside_heading_magnitude_deg": 0.0,
                }
            )
            continue
        assignment = assign_inside_outside(
            math.radians(
                sampling.canonical_to_target_output_sign * target.left_outputs[index]
            ),
            math.radians(
                sampling.canonical_to_target_output_sign * target.right_outputs[index]
            ),
        )
        inside_heading = math.degrees(assignment.inside_incremental_magnitude)
        outside_heading = math.degrees(assignment.outside_incremental_magnitude)
        regimes.append(
            {
                "input_deg": input_deg,
                "regime": classify_heading_pair(inside_heading, outside_heading).value,
                "inside_heading_magnitude_deg": inside_heading,
                "outside_heading_magnitude_deg": outside_heading,
                "inside_force_demand_magnitude_n": inside_force[index],
                "outside_force_demand_magnitude_n": outside_force[index],
            }
        )

    candidate = resolve_candidate(
        requirement,
        candidate_id="FORCE-DEMAND-REFERENCE-CANDIDATE",
    )
    evaluation = evaluate_operating_state_candidate(
        geometry,
        requirement,
        candidate,
        target_set,
        pose_set,
    )

    return {
        "result_id": "STEERING-FORCE-DEMAND-TARGET-BENCHMARKS-V0",
        "benchmark_id": "BENCH-STEER-0021",
        "authorization_ids": ["AUTH-STEER-0002", "AUTH-VEH-0001"],
        "evaluator_model_id": "MOD-STEER-0001",
        "optimizer_model_id": "MOD-STEER-0002",
        "vehicle_state_model_id": "MOD-VEH-0001",
        "pr28_r25b_diagnostic": {
            "tire_grid_id": r25b_grid.grid_id,
            "source_tire_id": r25b_grid.source_tire_id,
            "intended_tire_id": r25b_grid.intended_tire_id,
            "inside_peak_slip_deg": peak.inside.peak_slip_angle_magnitude_deg,
            "outside_peak_slip_deg": peak.outside.peak_slip_angle_magnitude_deg,
            "outside_minus_inside_peak_slip_deg": peak_differential,
            "endpoint": _heading_record(endpoint_reference),
            "near_center_15deg_input": _heading_record(near_center_reference),
            "interpretation": (
                "The positive R25B peak-slip differential moves the outside wheel toward "
                "parallel/anti-Ackermann. At the endpoint it is much smaller than the geometric "
                "Ackermann split, so the endpoint remains pro-Ackermann; near center the geometric "
                "split is small enough that the utilization-scaled correction crosses slightly anti."
            ),
        },
        "synthetic_force_branch_verification": {
            "branch_set_id": synthetic_branches.branch_set_id,
            "authority": synthetic_branches.authority,
            "physical_tire_claim": False,
            "inside_operating_point": {
                "normal_load_n": inside_point.normal_load_n,
                "inclination_deg": inside_point.inclination_deg,
                "pressure_kpa": inside_point.pressure_kpa,
            },
            "outside_operating_point": {
                "normal_load_n": outside_point.normal_load_n,
                "inclination_deg": outside_point.inclination_deg,
                "pressure_kpa": outside_point.pressure_kpa,
            },
            "inside_force_schedule_n": list(inside_force),
            "outside_force_schedule_n": list(outside_force),
            "regimes": regimes,
            "target_left_outputs_deg": list(target.left_outputs),
            "target_right_outputs_deg": list(target.right_outputs),
        },
        "reference_candidate": {
            "candidate_id": evaluation.candidate_id,
            "feasible": evaluation.feasible,
            "total_objective": evaluation.total_objective,
            "failure_code": evaluation.failure_code,
            "failure_message": evaluation.failure_message,
            "objectives": [_objective_record(item) for item in evaluation.objectives],
        },
        "source_gap": {
            "status": "real_force_branch_export_not_yet_frozen",
            "reason": (
                "The team R25B package contains raw Round 6 cornering data, a Cornering Trojan "
                "spline dataset, and fitted TIR models, but the repository does not yet contain a "
                "reviewed source-derived pre-peak Fy(alpha) branch export. Tire Selection Notes "
                "provide stiffness/peak/camber-thrust summaries but not enough points to reconstruct "
                "an arbitrary pre-peak branch without introducing a surrogate."
            ),
            "next_source_step": (
                "Export bounded monotonic pre-peak branches from the reviewed TTC/TIR/MATLAB source "
                "at representative operating points, preserving source signs and without applying the "
                "historical 2/3 track-scale factor unless separately authorized."
            ),
        },
        "authority_boundary": (
            "BENCH-STEER-0021 proves software composition and explains why pro/anti regime can change "
            "with steer angle. Only the PR28 peak-slip diagnostic uses R25B source-derived values. "
            "The force-demand branch values are synthetic and must not be used for WUFR design ranking."
        ),
    }


def summary_report(report: dict) -> dict:
    diagnostic = report["pr28_r25b_diagnostic"]
    synthetic = report["synthetic_force_branch_verification"]
    regime_counts: dict[str, int] = {}
    for item in synthetic["regimes"]:
        regime_counts[item["regime"]] = regime_counts.get(item["regime"], 0) + 1
    return {
        "result_id": report["result_id"],
        "benchmark_id": report["benchmark_id"],
        "r25b_peak_slip_differential_deg": diagnostic[
            "outside_minus_inside_peak_slip_deg"
        ],
        "r25b_endpoint_regime": diagnostic["endpoint"]["regime"],
        "r25b_endpoint_ackermann_gap_deg": diagnostic["endpoint"][
            "ackermann_inside_minus_outside_gap_deg"
        ],
        "r25b_endpoint_corrected_gap_deg": diagnostic["endpoint"][
            "corrected_inside_minus_outside_gap_deg"
        ],
        "r25b_15deg_input_regime": diagnostic["near_center_15deg_input"]["regime"],
        "synthetic_force_target_regime_counts": regime_counts,
        "reference_candidate_feasible": report["reference_candidate"]["feasible"],
        "reference_candidate_total_objective": report["reference_candidate"][
            "total_objective"
        ],
        "real_force_branch_status": report["source_gap"]["status"],
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
