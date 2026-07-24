#!/usr/bin/env python3
"""Generate bounded tire-informed differential steering target reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tomllib

from pssd_steering import load_geometry
from pssd_steering.optimization import (
    evaluate_operating_state_candidate,
    load_historical_fit_target,
    load_pose_set,
    load_requirement_set,
    resolve_candidate,
)
from pssd_steering.optimization.tire_targets import (
    TireDifferentialStateDefinition,
    build_tire_informed_operating_target_set,
    peak_grip_slip_angle_differential,
)
from pssd_tire import TireOperatingPoint, load_lateral_summary_grid


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


def build_report() -> dict:
    root = Path(__file__).resolve().parents[1]
    geometry = load_geometry(
        root / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
    )
    if geometry.wheelbase is None or geometry.steering_axis_track is None:
        raise RuntimeError(
            "Tire-informed Ackermann adapter requires wheelbase and steering-axis track"
        )
    requirement = load_requirement_set(
        root / "configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml"
    )
    sampling = load_historical_fit_target(
        root / "benchmarks/steering/WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
    )
    pose_set = load_pose_set(
        root / "benchmarks/steering/STEERING_SYNTHETIC_POSE_SET_V0.toml"
    )
    tire_grid = load_lateral_summary_grid(
        root / "benchmarks/tires/WUFR26_H43105_R25B_LATERAL_SUMMARY_V0.toml"
    )
    with (
        root / "benchmarks/tires/WUFR26_H43105_R25B_MATLAB_REFERENCE_V0.toml"
    ).open("rb") as stream:
        matlab_reference = tomllib.load(stream)

    inside = TireOperatingPoint(
        normal_load_n=222.0,
        inclination_deg=0.0,
        pressure_kpa=83.0,
    )
    outside = TireOperatingPoint(
        normal_load_n=1112.0,
        inclination_deg=2.0,
        pressure_kpa=83.0,
    )
    differential = peak_grip_slip_angle_differential(tire_grid, inside, outside)
    maximum_input = max(abs(item) for item in sampling.inputs)
    utilization = tuple(abs(value) / maximum_input for value in sampling.inputs)
    definition = TireDifferentialStateDefinition(
        state_id="nominal",
        inside_operating_point=inside,
        outside_operating_point=outside,
        slip_utilization_by_sample=utilization,
        objective_weight=1.0,
        normalization_scale_deg=1.0,
        authority=(
            "TTC-envelope steering-development reference pair only; explicit load/camber/pressure "
            "inputs are not a WUFR-27 production operating-state claim"
        ),
        provenance=(
            ("utilization_schedule", "abs(input_deg)/102; development benchmark only"),
        ),
    )
    target_set = build_tire_informed_operating_target_set(
        sampling,
        pose_set,
        tire_grid,
        (definition,),
        target_set_id="WUFR27_TIRE_INFORMED_STEERING_DEV_V0",
        version="0.1.0",
        wheelbase_m=geometry.wheelbase,
        steering_axis_track_m=geometry.steering_axis_track,
        authority="AUTH-STEER-0002 bounded tire-informed target-provider development",
        source_path="scripts/run_steering_tire_target_benchmarks.py",
    )
    target = target_set.state_map["nominal"]

    candidate = resolve_candidate(
        requirement,
        candidate_id="TIRE-TARGET-REFERENCE-CANDIDATE",
    )
    evaluation = evaluate_operating_state_candidate(
        geometry,
        requirement,
        candidate,
        target_set,
        pose_set,
    )

    source_ref = matlab_reference["balanced_lateral_acceleration_reference"]
    return {
        "result_id": "STEERING-TIRE-INFORMED-TARGET-BENCHMARKS-V0",
        "benchmark_id": "BENCH-STEER-0020",
        "authorization_id": "AUTH-STEER-0002",
        "evaluator_model_id": "MOD-STEER-0001",
        "optimizer_model_id": "MOD-STEER-0002",
        "tire_grid_id": tire_grid.grid_id,
        "source_tire_id": tire_grid.source_tire_id,
        "intended_tire_id": tire_grid.intended_tire_id,
        "engineering_proxy_authority": tire_grid.authority,
        "reference_state": {
            "state_id": "nominal",
            "inside_operating_point": {
                "normal_load_n": inside.normal_load_n,
                "inclination_deg": inside.inclination_deg,
                "pressure_kpa": inside.pressure_kpa,
            },
            "outside_operating_point": {
                "normal_load_n": outside.normal_load_n,
                "inclination_deg": outside.inclination_deg,
                "pressure_kpa": outside.pressure_kpa,
            },
            "inside_peak_slip_deg": differential.inside.peak_slip_angle_magnitude_deg,
            "outside_peak_slip_deg": differential.outside.peak_slip_angle_magnitude_deg,
            "outside_minus_inside_peak_slip_deg": (
                differential.outside_minus_inside_peak_slip_deg
            ),
            "utilization_schedule": list(utilization),
        },
        "target": {
            "target_set_id": target_set.target_set_id,
            "inputs_deg": list(sampling.inputs),
            "rack_displacements_m": list(sampling.rack_displacements),
            "left_outputs_deg": list(target.left_outputs),
            "right_outputs_deg": list(target.right_outputs),
            "source_type": target.source_type,
            "authority": target.authority,
            "provenance": dict(target.provenance),
        },
        "reference_candidate": {
            "candidate_id": evaluation.candidate_id,
            "feasible": evaluation.feasible,
            "total_objective": evaluation.total_objective,
            "failure_code": evaluation.failure_code,
            "failure_message": evaluation.failure_message,
            "objectives": [_objective_record(item) for item in evaluation.objectives],
        },
        "matlab_integration_reference": {
            "reference_id": matlab_reference["reference_id"],
            "source_type": matlab_reference["source_type"],
            "authority": matlab_reference["authority"],
            "historical_force_and_moment_scale": (
                matlab_reference["model_chain"]["historical_force_and_moment_scale"]
            ),
            "historical_scale_promoted_to_tire_provider": False,
            "balanced_lateral_acceleration_reference": source_ref,
        },
        "authority_boundary": (
            "The Python tire layer is a bounded TTC-derived lateral summary and target adapter, not "
            "a Magic Formula rewrite or a vehicle equilibrium solver. The 43105 R25B data are an "
            "explicit engineering proxy for the intended 43104 R20 tire. Peak-slip values censored "
            "at the 12 deg source sweep boundary are rejected. The explicit utilization schedule and "
            "reference wheel loads/cambers are development inputs, so this benchmark does not "
            "establish production tire-optimal Ackermann, track scaling, or installed-state authority."
        ),
    }


def summary_report(report: dict) -> dict:
    target = report["target"]
    reference = report["reference_state"]
    matlab = report["matlab_integration_reference"]
    return {
        "result_id": report["result_id"],
        "benchmark_id": report["benchmark_id"],
        "tire_grid_id": report["tire_grid_id"],
        "source_tire_id": report["source_tire_id"],
        "intended_tire_id": report["intended_tire_id"],
        "inside_peak_slip_deg": reference["inside_peak_slip_deg"],
        "outside_peak_slip_deg": reference["outside_peak_slip_deg"],
        "outside_minus_inside_peak_slip_deg": (
            reference["outside_minus_inside_peak_slip_deg"]
        ),
        "left_endpoint_targets_deg": [
            target["left_outputs_deg"][0],
            target["left_outputs_deg"][-1],
        ],
        "right_endpoint_targets_deg": [
            target["right_outputs_deg"][0],
            target["right_outputs_deg"][-1],
        ],
        "reference_candidate_feasible": report["reference_candidate"]["feasible"],
        "reference_candidate_total_objective": report["reference_candidate"][
            "total_objective"
        ],
        "matlab_reference_pressures_psi": [
            item["pressure_psi"]
            for item in matlab["balanced_lateral_acceleration_reference"]
        ],
        "historical_scale_promoted_to_tire_provider": matlab[
            "historical_scale_promoted_to_tire_provider"
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
