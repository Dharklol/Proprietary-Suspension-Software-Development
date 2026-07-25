#!/usr/bin/env python3
"""Generate BENCH-SUSP-0007/0008 actuation verification diagnostics."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import tomllib

from pssd_suspension import (
    ActuationAttachment,
    ActuationGeometry,
    ActuationSolverConfig,
    PhysicalStateSolverConfig,
    SuspensionPoint,
    build_nominal_wheel_reference,
    evaluate_local_derivative,
    load_optimumk_geometry_snapshot,
    load_wufr26_wheel_reference_profile,
    solve_actuation_q_L_state,
    solve_body_vertical_actuation_state,
    solve_rocker_closure,
)

ROOT = Path(__file__).resolve().parents[1]


def load_toml(path: str) -> dict:
    with (ROOT / path).open("rb") as stream:
        return tomllib.load(stream)


def point(name: str, xyz: tuple[float, float, float]) -> SuspensionPoint:
    return SuspensionPoint(name, tuple(1000.0 * x for x in xyz), xyz)


def synthetic_benchmark() -> dict:
    geom = ActuationGeometry(
        point("arm", (2.0, 0.0, 0.0)),
        point("damper", (0.0, 2.0, 0.0)),
        point("axis", (0.0, 0.0, 1.0)),
        point("pivot", (0.0, 0.0, 0.0)),
        point("rod", (1.0, 0.0, 0.0)),
        point("coil", (0.0, 1.0, 0.0)),
        ActuationAttachment.UPPER_ARM,
    )
    theta = 0.4
    rod = (math.cos(theta), math.sin(theta), 0.0)
    solved = solve_rocker_closure(geom, (rod[0] + 1.0, rod[1], 0.0), predecessor_theta_R_rad=0.35)
    unreachable = solve_rocker_closure(geom, (5.0, 0.0, 0.0))
    ambiguous = solve_rocker_closure(geom, (1.0, 1.0, 0.0), predecessor_theta_R_rad=math.pi / 4.0)
    derivative = evaluate_local_derivative(
        z_center_m=0.0, delta_l_center_m=0.0,
        z_minus_m=-0.1, delta_l_minus_m=0.02,
        z_plus_m=0.1, delta_l_plus_m=-0.02,
    )
    if not solved.ok or solved.theta_R_rad is None or not derivative.ok or derivative.rho_dw is None:
        raise RuntimeError("BENCH-SUSP-0007 analytical fixture failed")
    return {
        "theta_error_rad": abs(solved.theta_R_rad - theta),
        "rod_length_residual_m": abs(float(solved.rod_length_residual_m or 0.0)),
        "unreachable_failure_code": unreachable.failure_code.value if unreachable.failure_code else None,
        "ambiguous_failure_code": ambiguous.failure_code.value if ambiguous.failure_code else None,
        "rho_dw": derivative.rho_dw,
        "rho_dw_error": abs(derivative.rho_dw + 0.2),
        "pass": (
            abs(solved.theta_R_rad - theta) <= 1e-10
            and abs(float(solved.rod_length_residual_m or 0.0)) <= 1e-10
            and unreachable.failure_code is not None
            and unreachable.failure_code.value == "no_rocker_root"
            and ambiguous.failure_code is not None
            and ambiguous.failure_code.value == "rocker_branch_ambiguity"
            and abs(derivative.rho_dw + 0.2) <= 1e-12
        ),
    }


def source_benchmark() -> dict:
    fixture = load_toml("benchmarks/suspension/WUFR26_OPTIMUMK_ACTUATION_V0.toml")
    geometry = load_optimumk_geometry_snapshot(ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml")
    profile = load_wufr26_wheel_reference_profile(ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml")
    rows = []
    for axle in ("front", "rear"):
        for side in ("left", "right"):
            corner = geometry.corner(axle, side)
            nominal = build_nominal_wheel_reference(profile, axle, side)
            q_key = f"{axle}_{side}_q_L_deg"
            for indices in ([5, 4, 3, 2, 1, 0], [5, 6, 7, 8, 9, 10]):
                predecessor = None
                for index in indices:
                    source = fixture["states"][index]
                    state = solve_actuation_q_L_state(
                        corner, nominal, math.radians(float(source[q_key])),
                        predecessor=predecessor,
                        geometry_id=geometry.geometry_id,
                        source_authority=geometry.authority,
                    )
                    if not state.ok or state.current_coilover_length_m is None or state.delta_L_d_m is None:
                        raise RuntimeError(f"BENCH-SUSP-0008 failed at {axle}/{side}/{source['heave_mm']}: {state.message}")
                    if index != 5 or not any(r["axle"] == axle and r["side"] == side and r["heave_mm"] == 0.0 for r in rows):
                        rows.append({
                            "axle": axle, "side": side, "heave_mm": source["heave_mm"],
                            "length_error_m": abs(state.current_coilover_length_m - 0.001 * source[f"{axle}_coilover_length_mm"]),
                            "displacement_error_m": abs(state.delta_L_d_m - 0.001 * source[f"{axle}_coilover_displacement_mm"]),
                            "rod_residual_m": abs(float(state.rod_length_residual_m or 0.0)),
                        })
                    predecessor = state
    max_length = max(row["length_error_m"] for row in rows)
    max_disp = max(row["displacement_error_m"] for row in rows)
    max_rod = max(row["rod_residual_m"] for row in rows)

    front_left = geometry.corner("front", "left")
    nominal = build_nominal_wheel_reference(profile, "front", "left")
    physical = PhysicalStateSolverConfig(
        q_L_min_rad=math.radians(-4.0), q_L_max_rad=math.radians(4.0),
        scan_intervals_per_side=30, q_L_tolerance_rad=2e-9, displacement_tolerance_m=2e-9,
    )
    derivative = solve_body_vertical_actuation_state(
        front_left, nominal, 0.0, physical,
        actuation_config=ActuationSolverConfig(derivative_step_m=1e-4),
        geometry_id=geometry.geometry_id, source_authority=geometry.authority,
    )
    if not derivative.ok or derivative.rho_dw is None:
        raise RuntimeError(f"BENCH-SUSP-0008 derivative failed: {derivative.message}")
    length_tol = float(fixture["tolerances"]["implementation_length_match_m"])
    disp_tol = float(fixture["tolerances"]["implementation_displacement_match_m"])
    rod_tol = float(fixture["tolerances"]["rod_length_residual_m"])
    return {
        "corner_count": 4,
        "state_count": len(rows),
        "max_coilover_length_error_m": max_length,
        "max_coilover_displacement_error_m": max_disp,
        "max_rod_length_residual_m": max_rod,
        "nominal_front_left_rho_dw": derivative.rho_dw,
        "nominal_front_left_rho_wd": derivative.rho_wd,
        "historical_nominal_front_motion_ratio_heave": fixture["states"][5]["front_source_motion_ratio_heave"],
        "historical_ratio_used_as_canonical_input": False,
        "pass": max_length <= length_tol and max_disp <= disp_tol and max_rod <= rod_tol and derivative.rho_dw < 0.0,
    }


def build_report() -> dict:
    b7 = synthetic_benchmark()
    b8 = source_benchmark()
    if not b7["pass"] or not b8["pass"]:
        raise RuntimeError("Suspension actuation benchmark acceptance failed")
    return {
        "model_id": "MOD-SUSP-0003",
        "authorization_id": "AUTH-SUSP-0003",
        "authority": "software verification and historical external kinematics evidence only",
        "BENCH-SUSP-0007": b7,
        "BENCH-SUSP-0008": b8,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("suspension_actuation_report.json"))
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        b8 = report["BENCH-SUSP-0008"]
        print(
            "MOD-SUSP-0003: "
            f"length_error_um={1e6*b8['max_coilover_length_error_m']:.6g}, "
            f"displacement_error_um={1e6*b8['max_coilover_displacement_error_m']:.6g}, "
            f"rod_residual_nm={1e9*b8['max_rod_length_residual_m']:.6g}, "
            f"rho_dw_nominal={b8['nominal_front_left_rho_dw']:.9g}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
