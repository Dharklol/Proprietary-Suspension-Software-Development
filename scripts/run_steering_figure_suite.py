#!/usr/bin/env python3
"""Generate canonical steering R&D figures from reviewed machine-readable results."""

from __future__ import annotations

import argparse
from pathlib import Path

from pssd_steering import load_geometry
from pssd_steering.optimization import (
    evaluate_candidate,
    load_historical_fit_target,
    load_requirement_set,
    resolve_candidate,
)
from pssd_tire import load_lateral_force_branch_set
from pssd_viz import artifact_record, write_figure_manifest, write_report_manifest
from pssd_viz.matplotlib_renderer import render_engineering_figure
from pssd_viz.steering_figures import (
    motion_state_comparison_spec,
    steering_residual_spec,
    steering_response_comparison_spec,
    target_comparison_spec,
    target_correction_spec,
    tire_force_branch_spec,
    unavailable_figure_spec,
)

# These existing benchmark reporters remain the source of the higher-level target and
# motion diagnostics.  This script only translates their returned machine-readable
# values into visualization contracts.
from run_motion_aware_force_demand_benchmarks import build_report as build_motion_report
from run_steering_force_demand_benchmarks import build_report as build_force_demand_report
from run_steering_tire_target_benchmarks import build_report as build_tire_target_report


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
REQUIREMENT_PATH = ROOT / "configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml"
HISTORICAL_TARGET_PATH = (
    ROOT / "benchmarks/steering/WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
)
SYNTHETIC_BRANCH_PATH = ROOT / "benchmarks/tires/SYNTHETIC_FORCE_DEMAND_BRANCHES_V0.toml"
R25B_EXPORT_PROFILE_PATH = (
    ROOT / "benchmarks/tires/WUFR26_H43105_R25B_CORNERING_TROJAN_EXPORT_PROFILE_V0.toml"
)


def _render(spec, output_dir: Path) -> Path:
    outputs = render_engineering_figure(
        spec,
        output_dir / spec.metadata.figure_id,
        formats=("svg", "png"),
    )
    records = tuple(artifact_record(path, root=output_dir) for path in outputs)
    return write_figure_manifest(
        spec,
        records,
        output_dir / f"{spec.metadata.figure_id}.manifest.json",
    )


def build_specs():
    baseline = load_geometry(BASELINE_PATH)
    requirement = load_requirement_set(REQUIREMENT_PATH)
    historical = load_historical_fit_target(HISTORICAL_TARGET_PATH)
    reference = resolve_candidate(requirement, candidate_id="FIGURE-SUITE-REFERENCE")
    evaluation = evaluate_candidate(baseline, requirement, reference, historical)
    if not evaluation.feasible:
        raise RuntimeError(
            "Historical response figure source candidate is infeasible: "
            f"{evaluation.failure_code}: {evaluation.failure_message}"
        )

    common_sources = (
        str(HISTORICAL_TARGET_PATH.relative_to(ROOT)),
        str(BASELINE_PATH.relative_to(ROOT)),
    )
    response = steering_response_comparison_spec(
        figure_id="FIG-STEER-RND-001",
        title="WUFR Steering Baseline Response vs Historical Design-Source Target",
        inputs_deg=historical.inputs,
        left_target_deg=historical.left_outputs,
        right_target_deg=historical.right_outputs,
        left_response_deg=evaluation.left_outputs,
        right_response_deg=evaluation.right_outputs,
        configuration_id=baseline.geometry_id,
        authority="historical design-source regression comparison; not installed-state validation",
        source_ids=common_sources,
        notes=(
            "Target is the frozen WUFR-26/27 historical fit; evaluated curves come from MOD-STEER-0001.",
            "This comparison does not include backlash, compliance, fabrication error, or physical stops.",
        ),
    )
    residual = steering_residual_spec(
        figure_id="FIG-STEER-RND-002",
        title="WUFR Steering Baseline Residual vs Historical Design-Source Target",
        inputs_deg=historical.inputs,
        left_target_deg=historical.left_outputs,
        right_target_deg=historical.right_outputs,
        left_response_deg=evaluation.left_outputs,
        right_response_deg=evaluation.right_outputs,
        configuration_id=baseline.geometry_id,
        authority="historical design-source regression residual; not installed-state validation",
        source_ids=common_sources,
        notes=("Residual = MOD-STEER-0001 evaluated heading minus historical target heading.",),
    )

    tire_report = build_tire_target_report()
    tire_target = tire_report["target"]
    tire_sources = (
        "benchmarks/tires/WUFR26_H43105_R25B_LATERAL_SUMMARY_V0.toml",
        str(HISTORICAL_TARGET_PATH.relative_to(ROOT)),
    )
    tire_notes = (
        f"Source tire: {tire_report['source_tire_id']}; intended tire: {tire_report['intended_tire_id']}.",
        "Reference Fz/camber/pressure and slip-utilization schedule are development inputs, not a WUFR production operating state.",
    )
    tire_compare = target_comparison_spec(
        figure_id="FIG-STEER-RND-003",
        title="Historical Steering Target vs R25B Peak-Slip-Informed Development Target",
        inputs_deg=tire_target["inputs_deg"],
        baseline_left_deg=historical.left_outputs,
        baseline_right_deg=historical.right_outputs,
        alternate_left_deg=tire_target["left_outputs_deg"],
        alternate_right_deg=tire_target["right_outputs_deg"],
        configuration_id=tire_report["target"]["target_set_id"],
        authority=tire_report["engineering_proxy_authority"],
        source_ids=tire_sources,
        notes=tire_notes,
    )
    tire_correction = target_correction_spec(
        figure_id="FIG-STEER-RND-005",
        title="R25B Peak-Slip-Informed Target Correction Relative to Historical Target",
        inputs_deg=tire_target["inputs_deg"],
        baseline_left_deg=historical.left_outputs,
        baseline_right_deg=historical.right_outputs,
        alternate_left_deg=tire_target["left_outputs_deg"],
        alternate_right_deg=tire_target["right_outputs_deg"],
        configuration_id=tire_report["target"]["target_set_id"],
        authority=tire_report["engineering_proxy_authority"],
        source_ids=tire_sources,
        notes=tire_notes
        + (
            "This difference plot makes the tire-target correction visible where the absolute target curves overlap closely.",
        ),
    )

    branches = load_lateral_force_branch_set(SYNTHETIC_BRANCH_PATH)
    branch_curves = []
    for branch in branches.branches:
        point = branch.operating_point
        label = (
            f"{branch.branch_id}: Fz={point.normal_load_n:g} N, "
            f"IA={point.inclination_deg:g} deg, P={point.pressure_kpa:g} kPa"
        )
        branch_curves.append(
            (
                label,
                tuple(sample.slip_angle_magnitude_deg for sample in branch.samples),
                tuple(sample.lateral_force_magnitude_n for sample in branch.samples),
            )
        )
    synthetic_force = tire_force_branch_spec(
        figure_id="FIG-TIRE-RND-001",
        title="Synthetic Pre-Peak Tire Branches Used to Verify Force-Demand Inversion",
        curves=branch_curves,
        configuration_id=branches.branch_set_id,
        authority=branches.authority,
        source_ids=(str(SYNTHETIC_BRANCH_PATH.relative_to(ROOT)),),
        notes=(
            "Artificial values verify bounded interpolation/inversion only.",
            "Do not interpret these curves as Hoosier R25B or R20 tire behavior.",
        ),
    )

    force_report = build_force_demand_report()
    real_force_unavailable = unavailable_figure_spec(
        figure_id="FIG-TIRE-RND-002",
        title="R25B Source-Derived Pre-Peak Fy(alpha) Branches",
        x_quantity="Slip-angle magnitude",
        x_unit="deg",
        y_quantity="Lateral-force magnitude",
        y_unit="N",
        model_id="TIRE-LATERAL-FORCE-BRANCH",
        configuration_id="WUFR26_H43105_R25B_SOURCE_EXPORT_PENDING",
        authority="source-gated; no repository-authoritative branch values available yet",
        reason=force_report["source_gap"]["reason"],
        source_ids=(str(R25B_EXPORT_PROFILE_PATH.relative_to(ROOT)),),
        notes=(force_report["source_gap"]["next_source_step"],),
    )

    motion_report = build_motion_report()
    comparison = motion_report["same_tire_demands_velocity_center_comparison"]
    rear = comparison["rear_axle_velocity_center"]
    front = comparison["front_axle_velocity_center"]
    motion_compare = motion_state_comparison_spec(
        figure_id="FIG-STEER-RND-004",
        title="Same Tire Slip Demands, Different Vehicle Velocity-Center States",
        velocity_center_s_m=(rear["S_m"], front["S_m"]),
        left_heading_deg=(rear["left_heading_deg"], front["left_heading_deg"]),
        right_heading_deg=(rear["right_heading_deg"], front["right_heading_deg"]),
        configuration_id="SYNTHETIC_MOTION_AWARE_FORCE_DEMAND_V0",
        authority=motion_report["authority"],
        source_ids=(
            "benchmarks/tires/SYNTHETIC_FORCE_DEMAND_BRANCHES_V0.toml",
            "scripts/run_motion_aware_force_demand_benchmarks.py",
        ),
        state_ids=("rear_axle_velocity_center", "front_axle_velocity_center"),
        notes=(
            f"Required slips are held fixed at {comparison['inside_required_slip_deg']:.6g} deg inside and {comparison['outside_required_slip_deg']:.6g} deg outside.",
            f"Rear-axle velocity-center result: {rear['regime']}; front-state result: {front['regime']}.",
            "Synthetic software evidence only; this demonstrates state dependence, not a WUFR handling prediction.",
        ),
    )

    return (
        response,
        residual,
        tire_compare,
        tire_correction,
        synthetic_force,
        real_force_unavailable,
        motion_compare,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("steering_rnd_figure_suite"),
    )
    arguments = parser.parse_args()
    arguments.output_dir.mkdir(parents=True, exist_ok=True)

    manifests = tuple(_render(spec, arguments.output_dir) for spec in build_specs())
    report = write_report_manifest(
        report_id="STEERING_RND_FIGURE_SUITE_V0.1.0",
        figure_manifests=manifests,
        output_path=arguments.output_dir / "report.manifest.json",
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
