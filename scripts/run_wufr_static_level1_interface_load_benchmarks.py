#!/usr/bin/env python3
"""Generate BENCH-SUSP-0029..0031 synchronized static Level-1 diagnostics."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
from typing import Any, Sequence

from pssd_suspension.wufr_interface_statics import CompleteCarrierWrench, InterfaceStaticsSolverConfig
from pssd_suspension.wufr_static_level1_interface_loads import (
    CORNER_ORDER,
    WUFRStaticLevel1Config,
    WUFRStaticLevel1Error,
    WUFRStaticLevel1FailureCode,
    evaluate_wufr_static_level1_interface_loads,
    load_wufr_static_level1_provider,
)
from pssd_vehicle.wufr_static_carrier_wrench import (
    WUFRStaticCarrierWrenchStatus,
    evaluate_wufr_static_carrier_wrenches,
)

ROOT = Path(__file__).resolve().parents[1]


def provider(*, config: WUFRStaticLevel1Config | None = None):
    return load_wufr_static_level1_provider(
        source_path=ROOT / "data_catalog/wufr27_static_level1_interface_loads_v0.toml",
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
        config=config,
    )


def _v(values: Sequence[float]) -> list[float]:
    return [float(value) for value in values]


def _geometry(g) -> dict[str, Any]:
    return {
        "axle": g.axle,
        "side": g.side,
        "frame_id": g.frame_id,
        "configuration_id": g.configuration_id,
        "geometry_source_id": g.geometry_source_id,
        "carrier_reference_m": _v(g.carrier_reference_m),
        "upper_arm_reference_m": _v(g.upper_arm_reference_m),
        "lower_arm_reference_m": _v(g.lower_arm_reference_m),
        "upper_hinge_point_m": _v(g.upper_hinge_point_m),
        "upper_hinge_axis_unit": _v(g.upper_hinge_axis_unit),
        "lower_hinge_point_m": _v(g.lower_hinge_point_m),
        "lower_hinge_axis_unit": _v(g.lower_hinge_axis_unit),
        "upper_spherical_point_m": _v(g.upper_spherical_point_m),
        "lower_spherical_point_m": _v(g.lower_spherical_point_m),
        "lateral_body_point_m": _v(g.lateral_body_point_m),
        "lateral_remote_point_m": _v(g.lateral_remote_point_m),
        "lateral_source_id": g.lateral_source_id,
        "actuation_body_point_m": _v(g.actuation_body_point_m),
        "actuation_remote_point_m": _v(g.actuation_remote_point_m),
        "actuation_owner": g.actuation_owner,
        "actuation_source_id": g.actuation_source_id,
    }


def _hinge(h) -> dict[str, Any] | None:
    if h is None:
        return None
    return {
        "body_id": h.body_id,
        "point_m": _v(h.point_m),
        "axis_unit": _v(h.axis_unit),
        "force_N": _v(h.force_N),
        "moment_Nm": _v(h.moment_Nm),
        "moment_axis_component_Nm": h.moment_axis_component_Nm,
        "basis_v1": _v(h.basis_v1),
        "basis_v2": _v(h.basis_v2),
        "scalar_moment_v1_Nm": h.scalar_moment_v1_Nm,
        "scalar_moment_v2_Nm": h.scalar_moment_v2_Nm,
    }


def _spherical(s) -> dict[str, Any] | None:
    if s is None:
        return None
    return {
        "interface_id": s.interface_id,
        "point_m": _v(s.point_m),
        "force_on_carrier_N": _v(s.force_on_carrier_N),
        "force_on_arm_N": _v(s.force_on_arm_N),
    }


def _axial(a) -> dict[str, Any] | None:
    if a is None:
        return None
    return {
        "element_id": a.element_id,
        "body_id": a.body_id,
        "body_point_m": _v(a.body_point_m),
        "remote_point_m": _v(a.remote_point_m),
        "unit_axis_body_to_remote": _v(a.unit_axis_body_to_remote),
        "axial_force_N": a.axial_force_N,
        "force_on_body_N": _v(a.force_on_body_N),
        "force_on_remote_N": _v(a.force_on_remote_N),
        "source_id": a.source_id,
    }


def _solve(s) -> dict[str, Any]:
    return {
        "ok": s.ok,
        "status": s.status.value,
        "failure_code": s.failure_code.value if s.failure_code else None,
        "message": s.message,
        "authorization_id": s.authorization_id,
        "assumption_id": s.assumption_id,
        "unknown_order": list(s.unknown_order),
        "solution": _v(s.solution),
        "equilibrium_matrix": [_v(row) for row in s.equilibrium_matrix],
        "rhs": _v(s.rhs),
        "scaled_equilibrium_matrix": [_v(row) for row in s.scaled_equilibrium_matrix],
        "scaled_rhs": _v(s.scaled_rhs),
        "characteristic_lengths_m": _v(s.characteristic_lengths_m),
        "condition_number_inf": s.condition_number_inf,
        "minimum_relative_pivot": s.minimum_relative_pivot,
        "upper_hinge": _hinge(s.upper_hinge),
        "lower_hinge": _hinge(s.lower_hinge),
        "upper_spherical": _spherical(s.upper_spherical),
        "lower_spherical": _spherical(s.lower_spherical),
        "lateral": _axial(s.lateral),
        "actuation": _axial(s.actuation),
        "body_residuals": [
            {
                "body_id": r.body_id,
                "force_residual_N": _v(r.force_residual_N),
                "moment_residual_Nm": _v(r.moment_residual_Nm),
                "force_inf_norm_N": r.force_inf_norm_N,
                "moment_inf_norm_Nm": r.moment_inf_norm_Nm,
            }
            for r in s.body_residuals
        ],
        "translated_carrier_force_N": _v(s.translated_carrier_force_N or ()),
        "translated_carrier_moment_Nm": _v(s.translated_carrier_moment_Nm or ()),
    }


def _corner(c) -> dict[str, Any]:
    return {
        "corner_id": c.corner_id,
        "axle": c.axle,
        "side": c.side,
        "wheel_coordinate_m": c.wheel_coordinate_m,
        "q_L_rad": c.q_L_rad,
        "geometry": _geometry(c.geometry),
        "carrier_wrench": {
            "frame_id": c.carrier_wrench.frame_id,
            "reference_point_m": _v(c.carrier_wrench.reference_point_m),
            "force_N": _v(c.carrier_wrench.force_N),
            "moment_Nm": _v(c.carrier_wrench.moment_Nm),
            "source_id": c.carrier_wrench.source_id,
            "load_case_id": c.carrier_wrench.load_case_id,
            "complete": c.carrier_wrench.complete,
        },
        "steering_source_id": c.steering_source_id,
        "steering_closure_residual_m": c.steering_closure_residual_m,
        "actuation_state": {
            "q_L_rad": c.actuation_state.q_L_rad,
            "q_U_rad": c.actuation_state.q_U_rad,
            "owning_arm": c.actuation_state.owning_arm,
            "arm_attachment_m": _v(c.actuation_state.arm_attachment_m or ()),
            "rocker_theta_rad": c.actuation_state.rocker_theta_rad,
            "rocker_rod_point_m": _v(c.actuation_state.rocker_rod_point_m or ()),
            "configuration_id": c.actuation_state.configuration_id,
            "source_fixture_id": c.actuation_state.source_fixture_id,
        },
        "solve": _solve(c.solve),
    }


def _failed_builder(*args, **kwargs):
    raise WUFRStaticLevel1Error(
        WUFRStaticLevel1FailureCode.FRONT_STEERING_STATE_UNAVAILABLE,
        "injected centered-rack steering failure",
    )


def build_report() -> dict[str, Any]:
    p = provider()
    carrier = evaluate_wufr_static_carrier_wrenches(p.carrier_provider)
    result = evaluate_wufr_static_level1_interface_loads(p, carrier_result=carrier)
    if not result.ok:
        raise RuntimeError(f"Static Level-1 benchmark failed: {result.failure_code} {result.message}")

    reference_error = max(
        max(abs(c.geometry.carrier_reference_m[i] - c.carrier_wrench.reference_point_m[i]) for i in range(3))
        for c in result.corners
    )
    spherical_action_reaction_error = max(
        abs(a + b)
        for c in result.corners
        for s in (c.solve.upper_spherical, c.solve.lower_spherical)
        if s is not None
        for a, b in zip(s.force_on_carrier_N, s.force_on_arm_N)
    )
    axial_action_reaction_error = max(
        abs(a + b)
        for c in result.corners
        for arow in (c.solve.lateral, c.solve.actuation)
        if arow is not None
        for a, b in zip(arow.force_on_body_N, arow.force_on_remote_N)
    )

    reordered = evaluate_wufr_static_level1_interface_loads(
        p,
        carrier_result=replace(carrier, corners=(carrier.corners[1], carrier.corners[0], *carrier.corners[2:])),
    )
    incomplete = evaluate_wufr_static_level1_interface_loads(
        p,
        carrier_result=replace(carrier, status=WUFRStaticCarrierWrenchStatus.FAILURE, message="injected"),
    )
    first = carrier.corners[0]
    assert first.level1_wrench is not None
    bad_frame_corner = replace(first, level1_wrench=replace(first.level1_wrench, frame_id="wrong_frame"))
    bad_frame = evaluate_wufr_static_level1_interface_loads(
        p,
        carrier_result=replace(carrier, corners=(bad_frame_corner, *carrier.corners[1:])),
    )
    shifted = list(first.level1_wrench.reference_point_m)
    shifted[0] += 1.0e-6
    bad_ref_corner = replace(
        first,
        level1_wrench=replace(first.level1_wrench, reference_point_m=tuple(shifted)),
    )
    bad_ref = evaluate_wufr_static_level1_interface_loads(
        p,
        carrier_result=replace(carrier, corners=(bad_ref_corner, *carrier.corners[1:])),
    )
    steering = evaluate_wufr_static_level1_interface_loads(
        p,
        carrier_result=carrier,
        front_steering_builder=_failed_builder,
    )
    condition_provider = provider(
        config=WUFRStaticLevel1Config(
            solver_config=InterfaceStaticsSolverConfig(condition_limit=1.0)
        )
    )
    condition = evaluate_wufr_static_level1_interface_loads(
        condition_provider,
        carrier_result=carrier,
    )
    failure_codes = {
        "reordered_corners": reordered.failure_code.value if reordered.failure_code else None,
        "unsuccessful_carrier": incomplete.failure_code.value if incomplete.failure_code else None,
        "frame_mismatch": bad_frame.failure_code.value if bad_frame.failure_code else None,
        "reference_mismatch": bad_ref.failure_code.value if bad_ref.failure_code else None,
        "front_steering_unavailable": steering.failure_code.value if steering.failure_code else None,
        "forced_condition_failure": condition.failure_code.value if condition.failure_code else None,
    }
    expected_failures = {
        "reordered_corners": "corner_count_or_order_mismatch",
        "unsuccessful_carrier": "upstream_carrier_result_failure",
        "frame_mismatch": "frame_or_reference_mismatch",
        "reference_mismatch": "frame_or_reference_mismatch",
        "front_steering_unavailable": "front_steering_state_unavailable",
        "forced_condition_failure": "corner_solve_failure",
    }

    record = {
        "version": "0.1.0",
        "status": "accepted",
        "result_label": result.result_label,
        "authorization_id": result.authorization_id,
        "model_id": result.model_id,
        "configuration_id": result.configuration_id,
        "static_state_id": result.static_state_id,
        "corner_order": list(CORNER_ORDER),
        "upstream": {
            "carrier_result_label": result.upstream_carrier_result_label,
            "carrier_model_id": result.upstream_carrier_model_id,
            "carrier_authorization_id": result.upstream_carrier_authorization_id,
            "carrier_result_path": "benchmarks/vehicle/wufr_static_carrier_wrench_result_v0.1.0.json",
        },
        "corners": [_corner(c) for c in result.corners],
        "collection": {
            "maximum_force_residual_N": result.maximum_force_residual_N,
            "maximum_moment_residual_Nm": result.maximum_moment_residual_Nm,
            "maximum_hinge_axis_moment_Nm": result.maximum_hinge_axis_moment_Nm,
            "maximum_condition_number_inf": result.maximum_condition_number_inf,
            "minimum_relative_pivot": result.minimum_relative_pivot,
        },
        "boundaries": {
            "complete_for_authorized_static_gravity_case": result.complete_for_authorized_static_gravity_case,
            "complete_physical_vehicle_load_case": result.complete_physical_vehicle_load_case,
            "maneuver_complete": result.maneuver_complete,
            "individual_a_arm_joint_split_authorized": result.individual_a_arm_joint_split_authorized,
            "rocker_result_publication_authorized": result.rocker_result_publication_authorized,
            "installed_as_built_authority": result.installed_as_built_authority,
            "production_authority": result.production_authority,
        },
        "BENCH-SUSP-0029": {
            "pass": reference_error <= 1.0e-12 and all(
                c.steering_source_id is None or c.steering_source_id.startswith("MOD-STEER-0001:")
                for c in result.corners
            ),
            "maximum_carrier_reference_error_m": reference_error,
            "front_steering_source_ids": [c.steering_source_id for c in result.corners[:2]],
            "geometry_source_ids": [c.geometry.geometry_source_id for c in result.corners],
        },
        "BENCH-SUSP-0030": {
            "pass": (
                result.maximum_force_residual_N is not None
                and result.maximum_force_residual_N <= 1.0e-9
                and result.maximum_moment_residual_Nm is not None
                and result.maximum_moment_residual_Nm <= 1.0e-9
                and spherical_action_reaction_error <= 1.0e-12
                and axial_action_reaction_error <= 1.0e-12
            ),
            "lateral_axial_force_N": [c.solve.lateral.axial_force_N for c in result.corners],
            "actuation_axial_force_N": [c.solve.actuation.axial_force_N for c in result.corners],
            "maximum_spherical_action_reaction_error_N": spherical_action_reaction_error,
            "maximum_axial_action_reaction_error_N": axial_action_reaction_error,
        },
        "BENCH-SUSP-0031": {
            "pass": failure_codes == expected_failures,
            "failure_codes": failure_codes,
            "expected_failure_codes": expected_failures,
            "partial_publication_observed": any(bool(x.corners) for x in (reordered, incomplete, bad_frame, bad_ref, steering, condition)),
        },
    }
    if not all(record[key]["pass"] for key in ("BENCH-SUSP-0029", "BENCH-SUSP-0030", "BENCH-SUSP-0031")):
        raise RuntimeError("Static Level-1 benchmark acceptance failed")
    return record


def summary_toml(report: dict[str, Any]) -> str:
    c = report["collection"]
    lateral = report["BENCH-SUSP-0030"]["lateral_axial_force_N"]
    actuation = report["BENCH-SUSP-0030"]["actuation_axial_force_N"]
    lines = [
        'version = "0.1.0"',
        'result_label = "uncorrelated_design_intent_static_level1_interface_loads"',
        'authorization_id = "AUTH-SUSP-0017"',
        'model_id = "MOD-SUSP-0009"',
        'configuration_id = "WUFR27_SUSPENSION_BASELINE_V0"',
        'static_state_id = "WUFR26_DRIVER_NO_FUEL_DESIGN_INTENT_REFERENCE"',
        'status = "accepted"',
        'corner_order = ["front_left", "front_right", "rear_left", "rear_right"]',
        f"maximum_force_residual_N = {c['maximum_force_residual_N']!r}",
        f"maximum_moment_residual_Nm = {c['maximum_moment_residual_Nm']!r}",
        f"maximum_hinge_axis_moment_Nm = {c['maximum_hinge_axis_moment_Nm']!r}",
        f"maximum_condition_number_inf = {c['maximum_condition_number_inf']!r}",
        f"minimum_relative_pivot = {c['minimum_relative_pivot']!r}",
        "lateral_axial_force_N = [" + ", ".join(repr(v) for v in lateral) + "]",
        "actuation_axial_force_N = [" + ", ".join(repr(v) for v in actuation) + "]",
        "complete_for_authorized_static_gravity_case = true",
        "complete_physical_vehicle_load_case = false",
        "maneuver_complete = false",
        "individual_a_arm_joint_split_authorized = false",
        "rocker_result_publication_authorized = false",
        "installed_as_built_authority = false",
        "production_authority = false",
        "bench_susp_0029_pass = true",
        "bench_susp_0030_pass = true",
        "bench_susp_0031_pass = true",
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
            "lateral_axial_force_N": report["BENCH-SUSP-0030"]["lateral_axial_force_N"],
            "actuation_axial_force_N": report["BENCH-SUSP-0030"]["actuation_axial_force_N"],
            "maximum_force_residual_N": report["collection"]["maximum_force_residual_N"],
            "maximum_moment_residual_Nm": report["collection"]["maximum_moment_residual_Nm"],
        }, sort_keys=True))
    elif not args.output and not args.summary_output:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
