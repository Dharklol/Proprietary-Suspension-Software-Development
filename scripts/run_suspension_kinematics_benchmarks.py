#!/usr/bin/env python3
"""Generate BENCH-SUSP-0001 through BENCH-SUSP-0003 diagnostics."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import tomllib

from pssd_suspension import (
    ActuationAttachment,
    ActuationGeometry,
    Axle,
    DoubleWishboneGeometry,
    KinematicsSolverConfig,
    Side,
    SuspensionCornerGeometry,
    SuspensionPoint,
    ToeLinkGeometry,
    ToeLinkRole,
    UprightReferenceTransform,
    WheelSetup,
    load_optimumk_geometry_snapshot,
    solve_corner_state,
    solve_rear_toe_twist,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


def _point(name: str, xyz: tuple[float, float, float]) -> SuspensionPoint:
    return SuspensionPoint(source_name=name, source_position_mm=xyz, position_m=xyz)


def _dummy_actuation() -> ActuationGeometry:
    p = _point("dummy", (0.0, 0.0, 0.0))
    return ActuationGeometry(p, p, p, p, p, p, ActuationAttachment.LOWER_ARM)


def _wheel_setup() -> WheelSetup:
    return WheelSetup(0.6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.254, 0.46, 0.19)


def _parallel_corner() -> SuspensionCornerGeometry:
    return SuspensionCornerGeometry(
        axle=Axle.FRONT,
        side=Side.LEFT,
        wishbone=DoubleWishboneGeometry(
            _point("lf", (0.0, 0.0, 0.0)),
            _point("la", (1.0, 0.0, 0.0)),
            _point("uf", (0.0, 0.0, 0.2)),
            _point("ua", (1.0, 0.0, 0.2)),
            _point("lj", (0.0, 0.4, 0.0)),
            _point("uj", (0.0, 0.4, 0.2)),
        ),
        toe_link=ToeLinkGeometry(
            _point("ti", (0.0, 0.0, 0.1)),
            _point("to", (0.0, 0.4, 0.1)),
            ToeLinkRole.STEERING_TIE_ROD,
        ),
        actuation=_dummy_actuation(),
        wheel_setup=_wheel_setup(),
    )


def _rear_toe_corner() -> SuspensionCornerGeometry:
    return SuspensionCornerGeometry(
        axle=Axle.REAR,
        side=Side.LEFT,
        wishbone=DoubleWishboneGeometry(
            _point("lf", (0.0, -0.2, 0.0)),
            _point("la", (1.0, -0.2, 0.0)),
            _point("uf", (0.0, -0.2, 0.2)),
            _point("ua", (1.0, -0.2, 0.2)),
            _point("lj", (0.0, 0.0, 0.0)),
            _point("uj", (0.0, 0.0, 0.2)),
        ),
        toe_link=ToeLinkGeometry(
            _point("ti", (0.4, 0.0, 0.1)),
            _point("to", (0.1, 0.0, 0.1)),
            ToeLinkRole.CHASSIS_LOCATING_TOE_LINK,
        ),
        actuation=_dummy_actuation(),
        wheel_setup=_wheel_setup(),
    )


def _max_point_error(actual: tuple[float, float, float], expected: list[float]) -> float:
    return max(abs(a - b) for a, b in zip(actual, expected))


def build_report() -> dict:
    benchmark_solver = KinematicsSolverConfig(
        root_angle_tolerance_rad=1.0e-14,
        length_residual_tolerance_m=1.0e-13,
    )

    basic = _load("benchmarks/suspension/GEO-SUSP-BASIC-001.toml")
    parallel = _parallel_corner()
    basic_rows = []
    basic_max_position_error = 0.0
    basic_max_angle_error = 0.0
    basic_max_residual = 0.0
    for state in basic["states"]:
        result = solve_corner_state(
            parallel,
            math.radians(state["q_L_deg"]),
            config=benchmark_solver,
        )
        if not result.ok or result.q_U_rad is None or result.lower_upright_m is None or result.upper_upright_m is None:
            raise RuntimeError(f"BENCH-SUSP-0001 failed at q_L={state['q_L_deg']}: {result.message}")
        position_error = max(
            _max_point_error(result.lower_upright_m, state["expected_lower_upright_m"]),
            _max_point_error(result.upper_upright_m, state["expected_upper_upright_m"]),
        )
        angle_error = abs(result.q_U_rad - math.radians(state["expected_q_U_deg"]))
        residual = abs(result.upright_separation_residual_m or 0.0)
        basic_max_position_error = max(basic_max_position_error, position_error)
        basic_max_angle_error = max(basic_max_angle_error, angle_error)
        basic_max_residual = max(basic_max_residual, residual)
        basic_rows.append({
            "q_L_deg": state["q_L_deg"],
            "q_U_deg": math.degrees(result.q_U_rad),
            "max_point_error_m": position_error,
            "upright_separation_residual_m": residual,
        })

    geometry = load_optimumk_geometry_snapshot(
        ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
    )
    wufr = _load("benchmarks/suspension/WUFR26_OPTIMUMK_HEAVE_FRONT_KINEMATICS_V0.toml")
    front_right = geometry.corner(Axle.FRONT, Side.RIGHT)
    wufr_rows = []
    wufr_max_position_error = 0.0
    wufr_max_upper_angle_error = 0.0
    wufr_max_residual = 0.0
    for state in wufr["states"]:
        result = solve_corner_state(
            front_right,
            math.radians(state["q_L_deg"]),
            config=benchmark_solver,
            geometry_id=geometry.geometry_id,
            configuration_id="WUFR27_SUSPENSION_BASELINE_V0",
            source_authority=geometry.authority,
        )
        if not result.ok or result.q_U_rad is None or result.lower_upright_m is None or result.upper_upright_m is None:
            raise RuntimeError(f"BENCH-SUSP-0002 failed at heave={state['heave_mm']} mm: {result.message}")
        position_error = max(
            _max_point_error(result.lower_upright_m, state["expected_lower_upright_m"]),
            _max_point_error(result.upper_upright_m, state["expected_upper_upright_m"]),
        )
        angle_error = abs(result.q_U_rad - math.radians(state["expected_q_U_deg"]))
        residual = abs(result.upright_separation_residual_m or 0.0)
        wufr_max_position_error = max(wufr_max_position_error, position_error)
        wufr_max_upper_angle_error = max(wufr_max_upper_angle_error, angle_error)
        wufr_max_residual = max(wufr_max_residual, residual)
        wufr_rows.append({
            "heave_mm": state["heave_mm"],
            "q_L_deg": state["q_L_deg"],
            "q_U_deg": math.degrees(result.q_U_rad),
            "max_point_error_m": position_error,
            "upright_separation_residual_m": residual,
        })

    rear_fixture = _load("benchmarks/suspension/GEO-SUSP-REAR-TOE-001.toml")
    seed_angle = math.radians(-rear_fixture["expected"]["twist_deg"])
    minimum_twist = UprightReferenceTransform(
        rotation=(
            (math.cos(seed_angle), -math.sin(seed_angle), 0.0),
            (math.sin(seed_angle), math.cos(seed_angle), 0.0),
            (0.0, 0.0, 1.0),
        ),
        translation_m=(0.0, 0.0, 0.0),
    )
    rear_root, rear_residual, rear_derivative, rear_transform = solve_rear_toe_twist(
        _rear_toe_corner(),
        minimum_twist,
        current_lower_m=(0.0, 0.0, 0.0),
        current_upper_m=(0.0, 0.0, 0.2),
        config=KinematicsSolverConfig(
            initial_bracket_step_rad=math.radians(rear_fixture["expected"]["twist_deg"]),
            root_angle_tolerance_rad=1.0e-14,
            length_residual_tolerance_m=1.0e-13,
        ),
    )
    if not rear_root.ok or rear_root.root_rad is None or rear_transform is None:
        raise RuntimeError(f"BENCH-SUSP-0003 failed: {rear_root.message}")
    rear_point = rear_transform.apply_point((0.1, 0.0, 0.1))
    rear_angle_error = abs(rear_root.root_rad - math.radians(rear_fixture["expected"]["twist_deg"]))
    rear_point_error = _max_point_error(rear_point, rear_fixture["expected"]["toe_outboard_m"])

    return {
        "model_id": "MOD-SUSP-0001",
        "authorization_id": "AUTH-SUSP-0001",
        "authority": "software verification and historical external kinematics cross-tool evidence only",
        "wheelbase_confirmation": {
            "value_m": 1.5624,
            "source": "team/reviewer confirmation on PR39",
            "usage_in_this_report": "metadata only; no rear source-frame translation is performed",
        },
        "BENCH-SUSP-0001": {
            "max_point_error_m": basic_max_position_error,
            "max_q_U_error_rad": basic_max_angle_error,
            "max_upright_separation_residual_m": basic_max_residual,
            "tolerances": basic["tolerances"],
            "states": basic_rows,
        },
        "BENCH-SUSP-0002": {
            "source_sha256": wufr["source_sha256"],
            "source_export_version": wufr["source_export_version"],
            "max_point_error_m": wufr_max_position_error,
            "max_q_U_error_rad": wufr_max_upper_angle_error,
            "max_upright_separation_residual_m": wufr_max_residual,
            "tolerances": wufr["tolerances"],
            "states": wufr_rows,
        },
        "BENCH-SUSP-0003": {
            "solved_twist_deg": math.degrees(rear_root.root_rad),
            "twist_error_rad": rear_angle_error,
            "max_toe_point_error_m": rear_point_error,
            "toe_link_residual_m": abs(rear_residual or 0.0),
            "closure_derivative_m2_per_rad": rear_derivative,
            "tolerances": rear_fixture["tolerances"],
            "note": "The frozen fixture is tangent at closure; the current benchmark samples the exact 10 deg solution and records the near-zero closure derivative as singular-limit evidence.",
        },
        "scope_exclusions": [
            "front tie-rod steering closure",
            "wheel center and wheel plane construction",
            "motion ratio and actuation kinematics",
            "loads/compliance/vehicle equilibrium",
            "installed/as-built authority",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("suspension_kinematics_report.json"))
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        b1 = report["BENCH-SUSP-0001"]
        b2 = report["BENCH-SUSP-0002"]
        b3 = report["BENCH-SUSP-0003"]
        print(
            "MOD-SUSP-0001: "
            f"synthetic_point_error_um={1e6*b1['max_point_error_m']:.6g}, "
            f"wufr_point_error_um={1e6*b2['max_point_error_m']:.6g}, "
            f"wufr_qU_error_urad={1e6*b2['max_q_U_error_rad']:.6g}, "
            f"rear_twist_error_urad={1e6*b3['twist_error_rad']:.6g}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
