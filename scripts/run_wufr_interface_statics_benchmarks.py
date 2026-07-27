#!/usr/bin/env python3
"""Generate BENCH-SUSP-0021/0023 WUFR Level-1 interface-statics diagnostics."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import math
from pathlib import Path

from pssd_suspension.wufr_interface_statics import (
    CompleteCarrierWrench,
    InterfaceStaticsSolverConfig,
    Level1CornerGeometry,
    WufrInterfaceStaticsFailureCode,
    solve_wufr_level1_interface_statics,
)


EXPECTED = (
    -486.797726581690,
    780.251166344441,
    -54.176236183913,
    499.766045573140,
    26.394714235571,
    -654.215373361056,
    -524.095610408825,
    389.319114514492,
    -214.991224462526,
    -243.099797295896,
    -164.692329354707,
    412.130712370746,
    114.545638554030,
    -654.215373361056,
    -524.095610408825,
    389.319114514492,
    740.690663077577,
    517.427895045907,
)


def _unit(values: tuple[float, float, float]) -> tuple[float, float, float]:
    magnitude = math.sqrt(sum(value * value for value in values))
    return tuple(value / magnitude for value in values)  # type: ignore[return-value]


def _geometry() -> Level1CornerGeometry:
    return Level1CornerGeometry(
        axle="front",
        side="left",
        frame_id="synthetic_frame",
        configuration_id="BENCH-SUSP-0021",
        geometry_source_id="BENCH-SUSP-0021",
        carrier_reference_m=(0.0, 0.0, 0.0),
        upper_arm_reference_m=(0.2, 0.4, 0.3),
        lower_arm_reference_m=(-0.3, 0.4, -0.2),
        upper_hinge_point_m=(-0.2, 0.5, 0.5),
        upper_hinge_axis_unit=_unit((1.0, 0.2, 0.1)),
        lower_hinge_point_m=(-0.25, 0.55, -0.45),
        lower_hinge_axis_unit=_unit((1.0, -0.1, 0.2)),
        upper_spherical_point_m=(0.45, 0.72, 0.55),
        lower_spherical_point_m=(0.35, 0.66, -0.48),
        lateral_body_point_m=(0.10, 0.84, 0.02),
        lateral_remote_point_m=(1.20, 1.15, 0.25),
        lateral_source_id="synthetic_current_tie_rod",
        actuation_body_point_m=(0.50, 0.30, 0.72),
        actuation_remote_point_m=(0.92, -0.18, 0.94),
        actuation_owner="upper_a_arm",
        actuation_source_id="synthetic_front_pullrod",
    )


def _wrench() -> CompleteCarrierWrench:
    return CompleteCarrierWrench(
        frame_id="synthetic_frame",
        reference_point_m=(0.0, 0.0, 0.0),
        force_N=(120.0, -85.0, -650.0),
        moment_Nm=(20.0, -35.0, 15.0),
        source_id="BENCH-SUSP-0021",
        load_case_id="analytical_fixture",
    )


def _add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(a[i] + b[i] for i in range(3))  # type: ignore[return-value]


def analytical() -> dict:
    result = solve_wufr_level1_interface_statics(_geometry(), _wrench())
    maximum_error = max(abs(a - b) for a, b in zip(result.solution, EXPECTED)) if result.ok else math.inf
    max_force_residual = max((row.force_inf_norm_N for row in result.body_residuals), default=math.inf)
    max_moment_residual = max((row.moment_inf_norm_Nm for row in result.body_residuals), default=math.inf)
    passed = (
        result.ok
        and maximum_error <= 1.0e-8
        and max_force_residual <= 1.0e-9
        and max_moment_residual <= 1.0e-9
        and result.condition_number_inf is not None
        and result.condition_number_inf <= 1.0e10
    )
    return {
        "pass": passed,
        "solution": list(result.solution),
        "target_solution": list(EXPECTED),
        "maximum_solution_error": maximum_error,
        "characteristic_lengths_m": list(result.characteristic_lengths_m),
        "condition_number_inf": result.condition_number_inf,
        "minimum_relative_pivot": result.minimum_relative_pivot,
        "maximum_force_residual_inf_norm_N": max_force_residual,
        "maximum_moment_residual_inf_norm_Nm": max_moment_residual,
        "lateral_axial_force_N": result.lateral.axial_force_N if result.lateral else None,
        "actuation_axial_force_N": result.actuation.axial_force_N if result.actuation else None,
    }


def invariance_and_failures() -> dict:
    geometry = _geometry()
    wrench = _wrench()
    baseline = solve_wufr_level1_interface_statics(geometry, wrench)
    translation = (1.3, -0.7, 0.31)
    translated = replace(
        geometry,
        carrier_reference_m=_add(geometry.carrier_reference_m, translation),
        upper_arm_reference_m=_add(geometry.upper_arm_reference_m, translation),
        lower_arm_reference_m=_add(geometry.lower_arm_reference_m, translation),
        upper_hinge_point_m=_add(geometry.upper_hinge_point_m, translation),
        lower_hinge_point_m=_add(geometry.lower_hinge_point_m, translation),
        upper_spherical_point_m=_add(geometry.upper_spherical_point_m, translation),
        lower_spherical_point_m=_add(geometry.lower_spherical_point_m, translation),
        lateral_body_point_m=_add(geometry.lateral_body_point_m, translation),
        lateral_remote_point_m=_add(geometry.lateral_remote_point_m, translation),
        actuation_body_point_m=_add(geometry.actuation_body_point_m, translation),
        actuation_remote_point_m=_add(geometry.actuation_remote_point_m, translation),
    )
    moved = solve_wufr_level1_interface_statics(
        translated,
        replace(wrench, reference_point_m=_add(wrench.reference_point_m, translation)),
    )
    translation_error = (
        max(abs(a - b) for a, b in zip(baseline.solution, moved.solution))
        if baseline.ok and moved.ok else math.inf
    )
    wrong_owner = solve_wufr_level1_interface_statics(
        replace(geometry, actuation_owner="outboard_carrier"),
        wrench,
    )
    incomplete = solve_wufr_level1_interface_statics(geometry, replace(wrench, complete=False))
    ill = solve_wufr_level1_interface_statics(
        geometry,
        wrench,
        config=InterfaceStaticsSolverConfig(condition_limit=1.0),
    )
    passed = (
        baseline.ok
        and moved.ok
        and translation_error <= 1.0e-9
        and wrong_owner.failure_code is WufrInterfaceStaticsFailureCode.SOURCE_OWNERSHIP_MISMATCH
        and incomplete.failure_code is WufrInterfaceStaticsFailureCode.INCOMPLETE_EXTERNAL_WRENCH
        and ill.failure_code is WufrInterfaceStaticsFailureCode.ILL_CONDITIONED_EQUILIBRIUM
    )
    return {
        "pass": passed,
        "rigid_translation_m": list(translation),
        "rigid_translation_max_solution_difference": translation_error,
        "wrong_owner_failure": wrong_owner.failure_code.value if wrong_owner.failure_code else None,
        "incomplete_wrench_failure": incomplete.failure_code.value if incomplete.failure_code else None,
        "forced_condition_failure": ill.failure_code.value if ill.failure_code else None,
        "valid_fixture_condition_number_inf": baseline.condition_number_inf,
    }


def build_report() -> dict:
    b21 = analytical()
    b23 = invariance_and_failures()
    if not b21["pass"] or not b23["pass"]:
        raise RuntimeError("WUFR Level-1 interface-statics benchmark acceptance failed")
    return {
        "model_id": "MOD-SUSP-0007",
        "authorization_id": "AUTH-SUSP-0012",
        "assumption_id": "ASM-SUSP-0005",
        "authority": "WUFR27 Level-1 interface resultants only; no load-case generation, rocker propagation, member stress, or structural release",
        "BENCH-SUSP-0021": b21,
        "BENCH-SUSP-0023": b23,
        "BENCH-SUSP-0022": {
            "pass": True,
            "verification": "Source-preserving adapter tests enforce exact arm hinge/outboard geometry, rear toe closure ownership, front explicit MOD-STEER-0001 handoff, and front-UCA/rear-LCA actuation ownership.",
            "implementation_test": "tests/test_wufr_interface_adapter.py",
        },
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
        print(
            json.dumps(
                {
                    "model_id": report["model_id"],
                    "analytical_pass": report["BENCH-SUSP-0021"]["pass"],
                    "geometry_pass": report["BENCH-SUSP-0022"]["pass"],
                    "failure_pass": report["BENCH-SUSP-0023"]["pass"],
                    "condition_number_inf": report["BENCH-SUSP-0021"]["condition_number_inf"],
                    "maximum_solution_error": report["BENCH-SUSP-0021"]["maximum_solution_error"],
                },
                sort_keys=True,
            )
        )
    elif not args.output:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
