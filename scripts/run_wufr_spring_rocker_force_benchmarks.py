#!/usr/bin/env python3
"""Generate BENCH-SUSP-0025 physical spring-rocker force diagnostics."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from pssd_suspension import (
    build_nominal_wheel_reference,
    evaluate_spring_from_actuation,
    load_optimumk_geometry_snapshot,
    load_wufr26_wheel_reference_profile,
    load_wufr27_spring_package,
    solve_actuation_q_L_state,
)
from pssd_suspension.wufr_spring_rocker_force import (
    WufrSpringRockerForceFailureCode,
    physical_spring_force_at_rocker,
    recover_wufr_spring_rocker_force,
)

ROOT = Path(__file__).resolve().parents[1]
GEOMETRY_PATH = ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
WHEEL_PROFILE_PATH = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml"
SPRING_PACKAGE_PATH = ROOT / "data_catalog/wufr27_spring_package_v0.toml"


def _case(geometry, wheel_profile, package, axle: str, side: str) -> dict:
    corner = geometry.corner(axle, side)
    wheel = build_nominal_wheel_reference(wheel_profile, axle, side)
    actuation = solve_actuation_q_L_state(
        corner,
        wheel,
        0.0,
        geometry_id=geometry.geometry_id,
        source_authority=geometry.authority,
    )
    if not actuation.ok:
        raise RuntimeError(f"{axle} {side} actuation failed: {actuation.message}")
    definition = package.front if axle == "front" else package.rear
    spring = evaluate_spring_from_actuation(
        definition,
        package.reference,
        actuation,
        use_local_rho_dw_when_available=False,
    )
    if not spring.ok:
        raise RuntimeError(f"{axle} {side} spring failed: {spring.message}")
    physical = recover_wufr_spring_rocker_force(corner, actuation, spring)
    if not physical.ok:
        raise RuntimeError(f"{axle} {side} physical spring force failed: {physical.message}")
    assert physical.force_on_rocker_N is not None
    assert physical.force_on_chassis_N is not None
    return {
        "axle": axle,
        "side": side,
        "spring_force_magnitude_N": physical.spring_force_magnitude_N,
        "eye_to_eye_length_m": physical.eye_to_eye_length_m,
        "chassis_to_rocker_unit": list(physical.chassis_to_rocker_unit or ()),
        "force_on_rocker_N": list(physical.force_on_rocker_N),
        "force_on_chassis_N": list(physical.force_on_chassis_N),
        "rocker_axis_torque_Nm": physical.rocker_axis_torque_Nm,
        "dL_dtheta_m_per_rad": physical.dL_dtheta_m_per_rad,
        "virtual_work_torque_Nm": physical.generalized_rocker_torque_from_virtual_work_Nm,
        "action_reaction_inf_norm_N": physical.action_reaction_inf_norm_N,
        "rocker_torque_identity_residual_Nm": physical.rocker_torque_identity_residual_Nm,
        "spring_only": physical.spring_only,
        "installed_as_built_authority": physical.installed_as_built_authority,
    }


def build_report() -> dict:
    geometry = load_optimumk_geometry_snapshot(GEOMETRY_PATH)
    wheel_profile = load_wufr26_wheel_reference_profile(WHEEL_PROFILE_PATH)
    package = load_wufr27_spring_package(SPRING_PACKAGE_PATH)
    nominal = {
        f"{axle}_{side}": _case(geometry, wheel_profile, package, axle, side)
        for axle in ("front", "rear")
        for side in ("left", "right")
    }
    synthetic = physical_spring_force_at_rocker(
        chassis_eye_m=(0.13, -0.22, 0.31),
        rocker_eye_m=(0.41, 0.17, 0.55),
        rocker_pivot_m=(0.05, 0.09, 0.12),
        rocker_axis=(0.7, -0.2, 0.5),
        spring_force_magnitude_N=812.3,
        spring_id="synthetic",
        spring_source_id="BENCH-SUSP-0025",
        configuration_id="synthetic-3d",
        assumption_ids=("ASM-SUSP-0007",),
    )
    if not synthetic.ok:
        raise RuntimeError(synthetic.message)
    degenerate = physical_spring_force_at_rocker(
        chassis_eye_m=(1.0, 2.0, 3.0),
        rocker_eye_m=(1.0, 2.0, 3.0),
        rocker_pivot_m=(0.0, 0.0, 0.0),
        rocker_axis=(1.0, 0.0, 0.0),
        spring_force_magnitude_N=100.0,
    )
    max_action_reaction = max(float(case["action_reaction_inf_norm_N"] or 0.0) for case in nominal.values())
    max_torque_residual = max(abs(float(case["rocker_torque_identity_residual_Nm"] or 0.0)) for case in nominal.values())
    nominal_force_errors = [
        abs(float(nominal["front_left"]["spring_force_magnitude_N"]) - package.front_nominal_force_N),
        abs(float(nominal["front_right"]["spring_force_magnitude_N"]) - package.front_nominal_force_N),
        abs(float(nominal["rear_left"]["spring_force_magnitude_N"]) - package.rear_nominal_force_N),
        abs(float(nominal["rear_right"]["spring_force_magnitude_N"]) - package.rear_nominal_force_N),
    ]
    nominal_length_errors = [
        abs(float(nominal["front_left"]["eye_to_eye_length_m"]) - package.front_nominal_coilover_length_m),
        abs(float(nominal["front_right"]["eye_to_eye_length_m"]) - package.front_nominal_coilover_length_m),
        abs(float(nominal["rear_left"]["eye_to_eye_length_m"]) - package.rear_nominal_coilover_length_m),
        abs(float(nominal["rear_right"]["eye_to_eye_length_m"]) - package.rear_nominal_coilover_length_m),
    ]
    passed = (
        max(nominal_force_errors) <= 1.0e-6
        and max(nominal_length_errors) <= 2.0e-6
        and max_action_reaction <= 1.0e-10
        and max_torque_residual <= 1.0e-10
        and abs(float(synthetic.rocker_torque_identity_residual_Nm or 0.0)) <= 1.0e-10
        and degenerate.failure_code is WufrSpringRockerForceFailureCode.DEGENERATE_EYE_LINE
    )
    if not passed:
        raise RuntimeError("BENCH-SUSP-0025 acceptance failed")
    return {
        "model_id": "MOD-SUSP-0004",
        "authorization_id": "AUTH-SUSP-0014",
        "assumption_id": "ASM-SUSP-0007",
        "benchmark_id": "BENCH-SUSP-0025",
        "authority": "spring-only direct-coilover eye-force vector; no non-spring damper force, rocker equilibrium, pivot reaction, stress, or installed/as-built authority",
        "nominal": nominal,
        "maximum_nominal_force_error_N": max(nominal_force_errors),
        "maximum_nominal_length_error_m": max(nominal_length_errors),
        "maximum_action_reaction_residual_N": max_action_reaction,
        "maximum_rocker_torque_identity_residual_Nm": max_torque_residual,
        "synthetic_3d": {
            "spring_force_magnitude_N": synthetic.spring_force_magnitude_N,
            "rocker_axis_torque_Nm": synthetic.rocker_axis_torque_Nm,
            "virtual_work_torque_Nm": synthetic.generalized_rocker_torque_from_virtual_work_Nm,
            "torque_residual_Nm": synthetic.rocker_torque_identity_residual_Nm,
        },
        "degenerate_eye_failure": degenerate.failure_code.value if degenerate.failure_code else None,
        "pass": passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        print(json.dumps({
            "pass": report["pass"],
            "maximum_nominal_force_error_N": report["maximum_nominal_force_error_N"],
            "maximum_nominal_length_error_m": report["maximum_nominal_length_error_m"],
            "maximum_action_reaction_residual_N": report["maximum_action_reaction_residual_N"],
            "maximum_rocker_torque_identity_residual_Nm": report["maximum_rocker_torque_identity_residual_Nm"],
        }, sort_keys=True))
    elif not args.output:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
