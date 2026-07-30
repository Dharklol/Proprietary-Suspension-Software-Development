#!/usr/bin/env python3
"""Generate BENCH-SUSP-0032..0034 synchronized static rocker diagnostics."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
from typing import Any, Sequence

from pssd_suspension.wufr_static_level1_interface_loads import (
    WUFRStaticLevel1Status,
    evaluate_wufr_static_level1_interface_loads,
)
from pssd_suspension.wufr_static_rocker_included_loads import (
    CORNER_ORDER,
    WUFRStaticRockerFailureCode,
    evaluate_wufr_static_rocker_included_loads,
    load_wufr_static_rocker_provider,
)

ROOT = Path(__file__).resolve().parents[1]


def provider():
    return load_wufr_static_rocker_provider(
        source_path=ROOT / "data_catalog/wufr27_static_rocker_included_loads_v0.toml",
        static_level1_source_path=ROOT / "data_catalog/wufr27_static_level1_interface_loads_v0.toml",
        carrier_source_path=ROOT / "data_catalog/wufr27_static_carrier_wrench_v0.toml",
        static_equilibrium_result_path=ROOT / "benchmarks/vehicle/wufr_static_equilibrium_result_v0.2.0.json",
        static_equilibrium_source_path=ROOT / "data_catalog/wufr27_static_equilibrium_composition_v1.toml",
        road_contact_source_path=ROOT / "data_catalog/wufr26_road_contact_reference_v0.toml",
        suspension_geometry_path=ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml",
        wheel_profile_path=ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml",
        steering_geometry_path=ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml",
        whole_vehicle_path=ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml",
        gravity_path=ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml",
        spring_package_path=ROOT / "data_catalog/wufr27_spring_package_v0.toml",
        zbar_fixture_path=ROOT / "benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml",
    )


def _v(values: Sequence[float] | None) -> list[float] | None:
    return None if values is None else [float(value) for value in values]


def _point_load(load) -> dict[str, Any]:
    return {
        "load_id": load.load_id,
        "application_point_m": _v(load.application_point_m),
        "force_N": _v(load.force_N),
        "source_id": load.source_id,
        "frame_id": load.frame_id,
        "configuration_id": load.configuration_id,
        "load_case_id": load.load_case_id,
    }


def _corner(corner) -> dict[str, Any]:
    included = corner.included_result
    assert included is not None
    influence = corner.damper_unit_influence
    return {
        "corner_id": corner.corner_id,
        "axle": corner.axle,
        "side": corner.side,
        "load_case_id": corner.load_case_id,
        "level1_actuation": {
            "axial_force_N": corner.interface_result.solve.actuation.axial_force_N,
            "force_on_remote_N": _v(corner.interface_result.solve.actuation.force_on_remote_N),
            "remote_point_m": _v(corner.interface_result.solve.actuation.remote_point_m),
            "source_id": corner.interface_result.solve.actuation.source_id,
        },
        "spring": {
            "spring_force_magnitude_N": corner.spring_result.spring_force_magnitude_N,
            "force_on_rocker_N": _v(corner.spring_result.force_on_rocker_N),
            "rocker_eye_m": _v(corner.spring_result.rocker_eye_m),
            "rocker_pivot_m": _v(corner.spring_result.rocker_pivot_m),
            "rocker_axis_unit": _v(corner.spring_result.rocker_axis_unit),
            "chassis_eye_m": _v(corner.spring_result.chassis_eye_m),
        },
        "arb": {
            "fixture_id": corner.arb_fixture.fixture_id,
            "setting": corner.arb_link_result.setting,
            "stiffness_N_per_m": corner.arb_link_result.stiffness_N_per_m,
            "physical_link_force_N": (
                corner.arb_link_result.left.axial_force_N
                if corner.side == "left"
                else corner.arb_link_result.right.axial_force_N
            ),
            "rocker_pickup_m": _v(
                corner.arb_mechanism_result.rocker_pickup_left_m
                if corner.side == "left"
                else corner.arb_mechanism_result.rocker_pickup_right_m
            ),
        },
        "included": {
            "included_load_ids": list(included.included_load_ids),
            "missing_load_ids": list(included.missing_load_ids),
            "point_loads": [_point_load(load) for load in included.included_loads],
            "included_resultant_force_N": _v(included.included_resultant_force_N),
            "included_resultant_moment_Nm": _v(included.included_resultant_moment_Nm),
            "pivot_force_contribution_N": _v(included.pivot_force_contribution_N),
            "pivot_moment_contribution_Nm": _v(included.pivot_moment_contribution_Nm),
            "free_axis_moment_residual_Nm": included.free_axis_moment_residual_Nm,
            "final_force_residual_N": _v(included.final_force_residual_N),
            "final_moment_residual_Nm": _v(included.final_moment_residual_Nm),
            "perpendicular_moment_residual_Nm": _v(included.perpendicular_moment_residual_Nm),
            "support_axis_moment_component_Nm": included.support_axis_moment_component_Nm,
            "force_residual_inf_norm_N": included.force_residual_inf_norm_N,
            "perpendicular_moment_residual_inf_norm_Nm": included.perpendicular_moment_residual_inf_norm_Nm,
            "complete_hardware_reaction": included.complete_hardware_reaction,
        },
        "damper_unit_influence": {
            "unit_force_N": influence.unit_force_N,
            "positive_direction_chassis_to_rocker": _v(influence.positive_direction_chassis_to_rocker),
            "application_point_m": _v(influence.application_point_m),
            "rocker_pivot_m": _v(influence.rocker_pivot_m),
            "rocker_axis_unit": _v(influence.rocker_axis_unit),
            "d_pivot_force_d_damper_force": _v(influence.d_pivot_force_d_damper_force),
            "d_pivot_moment_d_damper_force_m": _v(influence.d_pivot_moment_d_damper_force_m),
            "d_free_axis_moment_d_damper_force_m": influence.d_free_axis_moment_d_damper_force_m,
            "actual_force_magnitude_assumed": influence.actual_force_magnitude_assumed,
            "actual_force_authorized": influence.actual_force_authorized,
        },
    }


def build_report() -> dict[str, Any]:
    p = provider()
    level1 = evaluate_wufr_static_level1_interface_loads(p.level1_provider)
    if not level1.ok:
        raise RuntimeError(f"Level-1 prerequisite failed: {level1.failure_code} {level1.message}")
    result = evaluate_wufr_static_rocker_included_loads(p, level1_result=level1)
    if not result.ok:
        raise RuntimeError(f"Static rocker benchmark failed: {result.failure_code} {result.message}")

    handoff_error = max(
        max(abs(a - b) for a, b in zip(
            corner.included_result.included_loads[0].force_N,
            corner.interface_result.solve.actuation.force_on_remote_N,
        ))
        for corner in result.corners
    )
    handoff_point_error = max(
        max(abs(a - b) for a, b in zip(
            corner.included_result.included_loads[0].application_point_m,
            corner.interface_result.solve.actuation.remote_point_m,
        ))
        for corner in result.corners
    )
    influence_force_identity_error = max(
        max(abs(a + b) for a, b in zip(
            corner.damper_unit_influence.d_pivot_force_d_damper_force,
            corner.damper_unit_influence.positive_direction_chassis_to_rocker,
        ))
        for corner in result.corners
    )
    influence_axis_support_error = max(
        abs(sum(a * b for a, b in zip(
            corner.damper_unit_influence.rocker_axis_unit,
            corner.damper_unit_influence.d_pivot_moment_d_damper_force_m,
        )))
        for corner in result.corners
    )

    reordered = evaluate_wufr_static_rocker_included_loads(
        p,
        level1_result=replace(level1, corners=(level1.corners[1], level1.corners[0], *level1.corners[2:])),
    )
    upstream_failure = evaluate_wufr_static_rocker_included_loads(
        p,
        level1_result=replace(level1, status=WUFRStaticLevel1Status.FAILURE, message="injected"),
    )
    config_failure = evaluate_wufr_static_rocker_included_loads(
        p,
        level1_result=replace(level1, configuration_id="wrong_configuration"),
    )
    first = level1.corners[0]
    shifted = tuple(value + (1.0e-4 if index == 0 else 0.0) for index, value in enumerate(first.solve.actuation.remote_point_m))
    changed_actuation = replace(first.solve.actuation, remote_point_m=shifted)
    changed_solve = replace(first.solve, actuation=changed_actuation)
    changed_corner = replace(first, solve=changed_solve)
    moved_point = evaluate_wufr_static_rocker_included_loads(
        p,
        level1_result=replace(level1, corners=(changed_corner, *level1.corners[1:])),
    )
    failure_codes = {
        "reordered_corners": reordered.failure_code.value if reordered.failure_code else None,
        "upstream_failure": upstream_failure.failure_code.value if upstream_failure.failure_code else None,
        "configuration_mismatch": config_failure.failure_code.value if config_failure.failure_code else None,
        "moved_push_pull_point": moved_point.failure_code.value if moved_point.failure_code else None,
    }
    expected_failures = {
        "reordered_corners": WUFRStaticRockerFailureCode.CORNER_COUNT_OR_ORDER_MISMATCH.value,
        "upstream_failure": WUFRStaticRockerFailureCode.UPSTREAM_LEVEL1_RESULT_FAILURE.value,
        "configuration_mismatch": WUFRStaticRockerFailureCode.CONFIGURATION_MISMATCH.value,
        "moved_push_pull_point": WUFRStaticRockerFailureCode.STATE_IDENTITY_MISMATCH.value,
    }

    report = {
        "version": "0.1.0",
        "status": "accepted",
        "result_label": result.result_label,
        "authorization_id": result.authorization_id,
        "model_id": result.model_id,
        "configuration_id": result.configuration_id,
        "static_state_id": result.static_state_id,
        "corner_order": list(CORNER_ORDER),
        "upstream": {
            "result_label": result.upstream_level1_result_label,
            "authorization_id": result.upstream_level1_authorization_id,
            "model_id": result.upstream_level1_model_id,
        },
        "corners": [_corner(corner) for corner in result.corners],
        "collection": {
            "maximum_force_residual_N": result.maximum_force_residual_N,
            "maximum_perpendicular_moment_residual_Nm": result.maximum_perpendicular_moment_residual_Nm,
            "maximum_support_axis_moment_component_Nm": result.maximum_support_axis_moment_component_Nm,
            "maximum_absolute_free_axis_moment_residual_Nm": result.maximum_absolute_free_axis_moment_residual_Nm,
        },
        "boundaries": {
            "complete_for_named_included_load_set": result.complete_for_named_included_load_set,
            "complete_hardware_reaction": result.complete_hardware_reaction,
            "complete_rocker_equilibrium": result.complete_rocker_equilibrium,
            "actual_damper_force_applied": result.actual_damper_force_applied,
            "structural_release_authority": result.structural_release_authority,
            "installed_as_built_authority": result.installed_as_built_authority,
            "production_authority": result.production_authority,
        },
        "BENCH-SUSP-0032": {
            "pass": handoff_error == 0.0 and handoff_point_error == 0.0,
            "maximum_push_pull_force_handoff_error_N": handoff_error,
            "maximum_push_pull_point_handoff_error_m": handoff_point_error,
        },
        "BENCH-SUSP-0033": {
            "pass": (
                result.maximum_force_residual_N is not None
                and result.maximum_force_residual_N <= 1.0e-10
                and result.maximum_perpendicular_moment_residual_Nm is not None
                and result.maximum_perpendicular_moment_residual_Nm <= 1.0e-10
                and result.maximum_support_axis_moment_component_Nm is not None
                and result.maximum_support_axis_moment_component_Nm <= 1.0e-10
                and all(not corner.included_result.complete_hardware_reaction for corner in result.corners)
            ),
            "included_load_ids": [list(corner.included_result.included_load_ids) for corner in result.corners],
            "missing_load_ids": [list(corner.included_result.missing_load_ids) for corner in result.corners],
            "free_axis_moment_residual_Nm": [corner.included_result.free_axis_moment_residual_Nm for corner in result.corners],
            "pivot_force_contribution_N": [_v(corner.included_result.pivot_force_contribution_N) for corner in result.corners],
            "pivot_moment_contribution_Nm": [_v(corner.included_result.pivot_moment_contribution_Nm) for corner in result.corners],
        },
        "BENCH-SUSP-0034": {
            "pass": (
                influence_force_identity_error <= 1.0e-15
                and influence_axis_support_error <= 1.0e-12
                and failure_codes == expected_failures
                and not any(bool(item.corners) for item in (reordered, upstream_failure, config_failure, moved_point))
            ),
            "maximum_unit_force_identity_error": influence_force_identity_error,
            "maximum_unit_support_axis_component_m": influence_axis_support_error,
            "failure_codes": failure_codes,
            "expected_failure_codes": expected_failures,
            "partial_publication_observed": any(bool(item.corners) for item in (reordered, upstream_failure, config_failure, moved_point)),
        },
    }
    if not all(report[key]["pass"] for key in ("BENCH-SUSP-0032", "BENCH-SUSP-0033", "BENCH-SUSP-0034")):
        raise RuntimeError("Static rocker included-load benchmark acceptance failed")
    return report


def summary_toml(report: dict[str, Any]) -> str:
    collection = report["collection"]
    free_axis = report["BENCH-SUSP-0033"]["free_axis_moment_residual_Nm"]
    lines = [
        'version = "0.1.0"',
        'result_label = "uncorrelated_design_intent_static_rocker_included_loads"',
        'authorization_id = "AUTH-SUSP-0018"',
        'model_id = "MOD-SUSP-0010"',
        'configuration_id = "WUFR27_SUSPENSION_BASELINE_V0"',
        'static_state_id = "WUFR26_DRIVER_NO_FUEL_DESIGN_INTENT_REFERENCE"',
        'status = "accepted"',
        'corner_order = ["front_left", "front_right", "rear_left", "rear_right"]',
        f"maximum_force_residual_N = {collection['maximum_force_residual_N']!r}",
        f"maximum_perpendicular_moment_residual_Nm = {collection['maximum_perpendicular_moment_residual_Nm']!r}",
        f"maximum_support_axis_moment_component_Nm = {collection['maximum_support_axis_moment_component_Nm']!r}",
        f"maximum_absolute_free_axis_moment_residual_Nm = {collection['maximum_absolute_free_axis_moment_residual_Nm']!r}",
        "free_axis_moment_residual_Nm = [" + ", ".join(repr(value) for value in free_axis) + "]",
        "complete_for_named_included_load_set = true",
        "complete_hardware_reaction = false",
        "complete_rocker_equilibrium = false",
        "actual_damper_force_applied = false",
        "structural_release_authority = false",
        "installed_as_built_authority = false",
        "production_authority = false",
        "bench_susp_0032_pass = true",
        "bench_susp_0033_pass = true",
        "bench_susp_0034_pass = true",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary_output:
        args.summary_output.write_text(summary_toml(report), encoding="utf-8")
    if args.summary:
        print(json.dumps({
            "model_id": report["model_id"],
            "free_axis_moment_residual_Nm": report["BENCH-SUSP-0033"]["free_axis_moment_residual_Nm"],
            "maximum_force_residual_N": report["collection"]["maximum_force_residual_N"],
            "maximum_perpendicular_moment_residual_Nm": report["collection"]["maximum_perpendicular_moment_residual_Nm"],
        }, sort_keys=True))
    elif not args.output and not args.summary_output:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
