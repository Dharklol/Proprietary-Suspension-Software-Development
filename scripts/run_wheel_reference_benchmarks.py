#!/usr/bin/env python3
"""Generate BENCH-SUSP-0004 through BENCH-SUSP-0006 diagnostics."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import tomllib

from pssd_suspension import (
    Axle,
    PhysicalStateSolverConfig,
    Side,
    build_nominal_wheel_reference,
    load_optimumk_geometry_snapshot,
    load_wufr26_wheel_reference_profile,
    minimum_twist_upright_transform,
    reconstruct_source_steering_twist,
    remove_source_steering_from_point,
    solve_body_vertical_displacement,
    solve_wheel_reference_state,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _max_component_error(a: tuple[float, float, float], b: list[float]) -> float:
    return max(abs(x - y) for x, y in zip(a, b))


def build_report() -> dict:
    profile_fixture = _load("benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml")
    profile = load_wufr26_wheel_reference_profile(
        ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml"
    )

    expected_rows = {
        (row["axle"], row["side"]): row for row in profile_fixture["nominal_expected"]
    }
    nominal_rows = []
    max_center_error = 0.0
    max_plane_error = 0.0
    for axle in Axle:
        for side in Side:
            reference = build_nominal_wheel_reference(profile, axle, side)
            expected = expected_rows[(axle.value, side.value)]
            center_error = _max_component_error(reference.center_m, expected["wheel_center_m"])
            normal_error = _max_component_error(reference.plane_normal, expected["plane_normal"])
            forward_error = _max_component_error(
                reference.forward_reference, expected["forward_reference"]
            )
            plane_error = max(normal_error, forward_error)
            max_center_error = max(max_center_error, center_error)
            max_plane_error = max(max_plane_error, plane_error)
            nominal_rows.append(
                {
                    "axle": axle.value,
                    "side": side.value,
                    "center_m": reference.center_m,
                    "max_center_component_error_m": center_error,
                    "max_plane_component_error": plane_error,
                }
            )

    source_3d = _load(
        "benchmarks/suspension/WUFR26_OPTIMUMK_HEAVE_FRONT_LEFT_WHEEL_REFERENCE_SOURCE_V0.toml"
    )
    nominal = source_3d["nominal"]
    source_rows = []
    max_twist_error = 0.0
    max_unsteer_error = 0.0
    min_reference_lever = math.inf
    min_source_lever = math.inf
    max_scalar_vs_twist_difference_deg = 0.0
    for state in source_3d["states"]:
        transform = minimum_twist_upright_transform(
            tuple(nominal["lower_m"]),
            tuple(nominal["upper_m"]),
            tuple(state["lower_m"]),
            tuple(state["upper_m"]),
        )
        recovered = reconstruct_source_steering_twist(
            transform,
            tuple(nominal["tie_m"]),
            tuple(state["lower_m"]),
            tuple(state["upper_m"]),
            tuple(state["tie_m"]),
        )
        if not recovered.ok or recovered.twist_rad is None:
            raise RuntimeError(
                f"BENCH-SUSP-0005 failed at heave={state['heave_mm']} mm: {recovered.message}"
            )
        unsteered = remove_source_steering_from_point(
            tuple(state["wheel_center_m"]),
            tuple(state["lower_m"]),
            tuple(state["upper_m"]),
            recovered.twist_rad,
        )
        expected_unsteered = transform.apply_point(tuple(nominal["wheel_center_m"]))
        point_error = _distance(unsteered, expected_unsteered)
        twist_error = abs(
            recovered.twist_rad - math.radians(float(state["expected_twist_deg"]))
        )
        scalar_difference = abs(
            float(state["scalar_steer_angle_deg"])
            - math.degrees(recovered.twist_rad)
        )
        max_unsteer_error = max(max_unsteer_error, point_error)
        max_twist_error = max(max_twist_error, twist_error)
        max_scalar_vs_twist_difference_deg = max(
            max_scalar_vs_twist_difference_deg, scalar_difference
        )
        min_reference_lever = min(
            min_reference_lever, float(recovered.reference_lever_arm_m or math.inf)
        )
        min_source_lever = min(
            min_source_lever, float(recovered.source_lever_arm_m or math.inf)
        )
        source_rows.append(
            {
                "heave_mm": state["heave_mm"],
                "recovered_twist_deg": math.degrees(recovered.twist_rad),
                "scalar_steer_angle_deg": state["scalar_steer_angle_deg"],
                "twist_error_rad": twist_error,
                "unsteered_wheel_center_error_m": point_error,
            }
        )

    geometry = load_optimumk_geometry_snapshot(
        ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
    )
    front_right = geometry.corner(Axle.FRONT, Side.RIGHT)
    nominal_right = build_nominal_wheel_reference(profile, Axle.FRONT, Side.RIGHT)
    kinematics_fixture = _load(
        "benchmarks/suspension/WUFR26_OPTIMUMK_HEAVE_FRONT_KINEMATICS_V0.toml"
    )
    q_values = [math.radians(float(row["q_L_deg"])) for row in kinematics_fixture["states"]]
    state_solver = PhysicalStateSolverConfig(
        q_L_min_rad=min(q_values) - math.radians(0.15),
        q_L_max_rad=max(q_values) + math.radians(0.15),
        scan_intervals_per_side=30,
        q_L_tolerance_rad=2.0e-9,
        displacement_tolerance_m=2.0e-9,
    )
    selected_indices = (0, 2, 5, 8, 10)
    inversion_rows = []
    max_q_error = 0.0
    max_residual = 0.0
    max_iterations = 0
    for index in selected_indices:
        source_state = kinematics_fixture["states"][index]
        expected_q = math.radians(float(source_state["q_L_deg"]))
        forward = solve_wheel_reference_state(
            front_right,
            nominal_right,
            expected_q,
            geometry_id=geometry.geometry_id,
            configuration_id="WUFR27_SUSPENSION_BASELINE_V0",
            source_authority=geometry.authority,
        )
        if not forward.ok or forward.delta_z_wc_body_m is None:
            raise RuntimeError(
                f"BENCH-SUSP-0006 forward state failed at heave={source_state['heave_mm']}: {forward.message}"
            )
        inverse = solve_body_vertical_displacement(
            front_right,
            nominal_right,
            forward.delta_z_wc_body_m,
            state_solver,
            geometry_id=geometry.geometry_id,
            configuration_id="WUFR27_SUSPENSION_BASELINE_V0",
            source_authority=geometry.authority,
        )
        if not inverse.ok or inverse.q_L_rad is None:
            raise RuntimeError(
                f"BENCH-SUSP-0006 inverse state failed at heave={source_state['heave_mm']}: {inverse.message}"
            )
        q_error = abs(inverse.q_L_rad - expected_q)
        residual = abs(float(inverse.residual_m or 0.0))
        max_q_error = max(max_q_error, q_error)
        max_residual = max(max_residual, residual)
        max_iterations = max(max_iterations, inverse.iterations)
        inversion_rows.append(
            {
                "heave_mm": source_state["heave_mm"],
                "source_derived_q_L_deg": source_state["q_L_deg"],
                "requested_delta_z_wc_body_m": forward.delta_z_wc_body_m,
                "recovered_q_L_deg": math.degrees(inverse.q_L_rad),
                "q_L_error_rad": q_error,
                "residual_m": residual,
                "iterations": inverse.iterations,
                "reachable_delta_z_range_m": inverse.reachable_delta_z_range_m,
            }
        )

    outside = solve_body_vertical_displacement(
        front_right,
        nominal_right,
        0.2,
        state_solver,
        geometry_id=geometry.geometry_id,
        configuration_id="WUFR27_SUSPENSION_BASELINE_V0",
        source_authority=geometry.authority,
    )

    return {
        "model_id": "MOD-SUSP-0002",
        "authorization_id": "AUTH-SUSP-0002",
        "authority": "software verification and historical external kinematics evidence only",
        "BENCH-SUSP-0004": {
            "max_nominal_wheel_center_component_error_m": max_center_error,
            "max_nominal_wheel_plane_component_error": max_plane_error,
            "tolerances": profile_fixture["tolerances"],
            "states": nominal_rows,
        },
        "BENCH-SUSP-0005": {
            "source_sha256": source_3d["source_sha256"],
            "source_export_version": source_3d["source_export_version"],
            "max_reconstructed_twist_error_rad": max_twist_error,
            "max_unsteered_wheel_center_error_m": max_unsteer_error,
            "minimum_reference_tie_lever_arm_m": min_reference_lever,
            "minimum_source_tie_lever_arm_m": min_source_lever,
            "max_scalar_steer_vs_3d_twist_difference_deg": max_scalar_vs_twist_difference_deg,
            "scalar_steer_angle_used_as_rotation": False,
            "tolerances": source_3d["tolerances"],
            "states": source_rows,
        },
        "BENCH-SUSP-0006": {
            "reviewed_q_L_domain_rad": [state_solver.q_L_min_rad, state_solver.q_L_max_rad],
            "max_q_L_recovery_error_rad": max_q_error,
            "max_displacement_residual_m": max_residual,
            "max_iterations": max_iterations,
            "outside_domain_failure_code": (
                outside.failure_code.value if outside.failure_code is not None else None
            ),
            "states": inversion_rows,
        },
        "scope_exclusions": [
            "nonzero OptimumK wheel-offset semantics",
            "front tie-rod steering closure inside suspension",
            "generic contact-patch or tire-deflection geometry",
            "actuation/motion-ratio kinematics",
            "whole-vehicle source-origin translation",
            "loads/compliance/vehicle equilibrium",
            "installed/as-built authority",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("wheel_reference_report.json"))
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        b4 = report["BENCH-SUSP-0004"]
        b5 = report["BENCH-SUSP-0005"]
        b6 = report["BENCH-SUSP-0006"]
        print(
            "MOD-SUSP-0002: "
            f"nominal_center_error_nm={1e9*b4['max_nominal_wheel_center_component_error_m']:.6g}, "
            f"source_unsteer_error_nm={1e9*b5['max_unsteered_wheel_center_error_m']:.6g}, "
            f"twist_error_nrad={1e9*b5['max_reconstructed_twist_error_rad']:.6g}, "
            f"qL_recovery_urad={1e6*b6['max_q_L_recovery_error_rad']:.6g}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
