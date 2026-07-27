#!/usr/bin/env python3
"""Generate AUTH-SUSP-0013 physical Z-bar linkage-force diagnostics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pssd_suspension.wufr_zbar import evaluate_two_arm_force, load_wufr_zbar_fixture
from pssd_suspension.wufr_zbar_link_force import (
    ZBarLinkForceConfig,
    ZBarLinkForceFailureCode,
    recover_single_link_force,
    recover_wufr_zbar_physical_link_forces,
)
from pssd_suspension.wufr_zbar_nominal import solve_nominal_zbar_mechanism


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml"
ROCKER_TORQUE_ORACLE_TOLERANCE_NM = 1.0e-6
AUTH_CONFIG = ZBarLinkForceConfig(
    rocker_torque_agreement_tolerance_Nm=ROCKER_TORQUE_ORACLE_TOLERANCE_NM
)


def _side_record(side) -> dict:
    return {
        "projection_u_dot_n": side.projection_u_dot_n,
        "elastic_transverse_force_N": side.elastic_transverse_force_N,
        "axial_force_N": side.axial_force_N,
        "force_on_rocker_N": list(side.force_on_rocker_N),
        "force_on_blade_N": list(side.force_on_blade_N),
        "physical_rocker_torque_Nm": side.physical_rocker_torque_Nm,
        "expected_generalized_rocker_torque_Nm": side.expected_generalized_rocker_torque_Nm,
        "force_projection_residual_N": side.force_projection_residual_N,
        "rocker_torque_residual_Nm": side.rocker_torque_residual_Nm,
        "link_closure_residual_m": side.link_closure_residual_m,
    }


def _case(axle: str, ql: float, qr: float, setting: int, stiffness: float) -> dict:
    fixture = load_wufr_zbar_fixture(FIXTURE_PATH, axle)
    state = solve_nominal_zbar_mechanism(fixture, ql, qr)
    if not state.ok:
        raise RuntimeError(f"{axle} mechanism failed: {state.message}")
    force = evaluate_two_arm_force(state, setting=setting, stiffness_N_per_m=stiffness)
    if not force.ok:
        raise RuntimeError(f"{axle} elastic force failed: {force.message}")
    physical = recover_wufr_zbar_physical_link_forces(
        fixture,
        state,
        force,
        config=AUTH_CONFIG,
    )
    if not physical.ok or physical.left is None or physical.right is None:
        raise RuntimeError(f"{axle} physical linkage force failed: {physical.message}")
    max_torque_residual = max(
        abs(physical.left.rocker_torque_residual_Nm or 0.0),
        abs(physical.right.rocker_torque_residual_Nm or 0.0),
    )
    max_projection_residual = max(
        abs(physical.left.force_projection_residual_N),
        abs(physical.right.force_projection_residual_N),
    )
    return {
        "axle": axle,
        "rocker_angles_rad": [ql, qr],
        "setting": setting,
        "stiffness_N_per_m": stiffness,
        "left": _side_record(physical.left),
        "right": _side_record(physical.right),
        "maximum_rocker_torque_residual_Nm": max_torque_residual,
        "maximum_force_projection_residual_N": max_projection_residual,
        "rocker_torque_oracle_tolerance_Nm": ROCKER_TORQUE_ORACLE_TOLERANCE_NM,
        "pass": (
            max_torque_residual <= ROCKER_TORQUE_ORACLE_TOLERANCE_NM
            and max_projection_residual <= 1.0e-8
        ),
    }


def build_report() -> dict:
    nominal_front = _case("front", 0.0, 0.0, 1, 280000.0)
    nominal_rear = _case("rear", 0.0, 0.0, 1, 280000.0)
    # Use equal signed front rocker-coordinate perturbations because the opposite-
    # signed pair is a zero-deflection free-housing mode for this fixture. Do not
    # assign wheel roll/heave semantics here; this benchmark is in rocker coordinates.
    front = _case("front", 0.01, 0.01, 3, 400000.0)
    rear = _case("rear", 0.008, -0.006, 2, 300000.0)
    degenerate = recover_single_link_force(
        side="synthetic",
        blade_tip_m=(0.0, 0.0, 0.0),
        rocker_pickup_m=(1.0, 0.0, 0.0),
        blade_transverse_unit=(0.0, 1.0, 0.0),
        elastic_transverse_force_N=100.0,
        rocker_pivot_m=(0.0, 0.0, 0.0),
        rocker_axis_unit=(0.0, 0.0, 1.0),
        nominal_link_length_m=1.0,
        expected_generalized_rocker_torque_Nm=None,
        config=AUTH_CONFIG,
    )
    zero_pass = all(
        abs(case[side]["axial_force_N"]) <= 1.0e-8
        and abs(case[side]["physical_rocker_torque_Nm"]) <= 1.0e-9
        for case in (nominal_front, nominal_rear)
        for side in ("left", "right")
    )
    front_nontrivial = (
        abs(front["left"]["axial_force_N"]) + abs(front["right"]["axial_force_N"])
        > 1.0e-8
    )
    failure_pass = degenerate.failure_code is ZBarLinkForceFailureCode.DEGENERATE_LINK_PROJECTION
    overall = zero_pass and front_nontrivial and front["pass"] and rear["pass"] and failure_pass
    if not overall:
        raise RuntimeError("BENCH-SUSP-0024 acceptance failed")
    return {
        "model_id": "MOD-SUSP-0005",
        "authorization_id": "AUTH-SUSP-0013",
        "benchmark_id": "BENCH-SUSP-0024",
        "authority": "Physical ideal axial ARB linkage force only; no rocker equilibrium, load transfer, stress, or installed/as-built authority",
        "nominal_front": nominal_front,
        "nominal_rear": nominal_rear,
        "front_coupled_rocker_state": front,
        "rear_asymmetric": rear,
        "degenerate_projection_failure": (
            degenerate.failure_code.value if degenerate.failure_code else None
        ),
        "pass": overall,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    if args.output:
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.summary:
        print(
            json.dumps(
                {
                    "pass": report["pass"],
                    "front_left_axial_force_N": report["front_coupled_rocker_state"]["left"]["axial_force_N"],
                    "front_right_axial_force_N": report["front_coupled_rocker_state"]["right"]["axial_force_N"],
                    "rear_left_axial_force_N": report["rear_asymmetric"]["left"]["axial_force_N"],
                    "rear_right_axial_force_N": report["rear_asymmetric"]["right"]["axial_force_N"],
                    "front_max_torque_residual_Nm": report["front_coupled_rocker_state"]["maximum_rocker_torque_residual_Nm"],
                    "rear_max_torque_residual_Nm": report["rear_asymmetric"]["maximum_rocker_torque_residual_Nm"],
                    "rocker_torque_oracle_tolerance_Nm": ROCKER_TORQUE_ORACLE_TOLERANCE_NM,
                },
                sort_keys=True,
            )
        )
    elif not args.output:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
