#!/usr/bin/env python3
"""Generate BENCH-SUSP-0009/0010 spring-force verification diagnostics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pssd_suspension import (
    SpringDefinition,
    SpringFailureCode,
    SpringLawKind,
    SpringReference,
    check_spring_energy_gradient,
    compression_from_coilover_reference,
    evaluate_spring_from_coilover,
    evaluate_spring_law,
    generalized_spring_force,
    load_wufr27_spring_package,
)


ROOT = Path(__file__).resolve().parents[1]


def synthetic_benchmark() -> dict:
    linear = SpringDefinition(
        spring_id="BENCH_SUSP_0009_LINEAR",
        kind=SpringLawKind.LINEAR,
        free_length_m=0.100,
        source_id="BENCH-SUSP-0009",
        configuration_id="SYNTHETIC",
        linear_rate_N_per_m=10000.0,
    )
    linear_state = evaluate_spring_law(linear, 0.020)

    reference = SpringReference(
        reference_id="BENCH_SUSP_0009_REF",
        configuration_id="SYNTHETIC",
        reference_coilover_length_m=0.200,
        preload_compression_m=0.005,
    )
    preload = compression_from_coilover_reference(
        current_coilover_length_m=0.190,
        reference=reference,
        free_length_m=0.100,
    )
    zero_reference = SpringReference(
        reference_id="BENCH_SUSP_0009_ZERO",
        configuration_id="SYNTHETIC",
        reference_coilover_length_m=0.200,
    )
    unseated = compression_from_coilover_reference(
        current_coilover_length_m=0.201,
        reference=zero_reference,
        free_length_m=0.100,
    )
    generalized = generalized_spring_force(
        200.0,
        -0.25,
        coordinate_order=("q_m",),
        coordinate_units=("m",),
    )
    energy_check = check_spring_energy_gradient(
        linear,
        0.020,
        -0.25,
        step_sizes=(1.0e-6, 5.0e-7),
    )

    table = SpringDefinition(
        spring_id="BENCH_SUSP_0009_TABLE",
        kind=SpringLawKind.PIECEWISE_LINEAR_FORCE,
        free_length_m=0.100,
        source_id="BENCH-SUSP-0009",
        configuration_id="SYNTHETIC",
        domain_max_m=0.020,
        force_points=((0.0, 0.0), (0.010, 100.0), (0.020, 240.0)),
    )
    table_state = evaluate_spring_law(table, 0.015)
    table_outside = evaluate_spring_law(table, 0.021)

    if not all((linear_state.ok, preload.ok, generalized.ok, energy_check.ok, table_state.ok)):
        raise RuntimeError("BENCH-SUSP-0009 synthetic spring benchmark could not be evaluated")

    force_error = abs(float(linear_state.force_N) - 200.0)
    energy_error = abs(float(linear_state.stored_energy_J) - 2.0)
    tangent_error = abs(float(linear_state.tangent_stiffness_N_per_m) - 10000.0)
    preload_error = abs(float(preload.x_s_m) - 0.015)
    generalized_error = abs(float(generalized.generalized_force[0]) + 50.0)
    max_energy_gradient_residual = max(energy_check.absolute_residuals)
    table_force_error = abs(float(table_state.force_N) - 170.0)
    table_energy_error = abs(float(table_state.stored_energy_J) - 1.175)
    table_tangent_error = abs(float(table_state.tangent_stiffness_N_per_m) - 14000.0)

    passed = (
        force_error <= 1.0e-12
        and energy_error <= 1.0e-12
        and tangent_error <= 1.0e-12
        and preload_error <= 1.0e-12
        and unseated.failure_code is SpringFailureCode.SPRING_UNSEATED
        and generalized_error <= 1.0e-12
        and max_energy_gradient_residual <= 5.0e-10
        and table_force_error <= 1.0e-12
        and table_energy_error <= 1.0e-12
        and table_tangent_error <= 1.0e-12
        and table_outside.failure_code is SpringFailureCode.CONSTITUTIVE_DOMAIN_EXCEEDED
    )
    return {
        "linear_force_error_N": force_error,
        "linear_energy_error_J": energy_error,
        "linear_tangent_error_N_per_m": tangent_error,
        "preload_compression_error_m": preload_error,
        "unseated_failure_code": unseated.failure_code.value if unseated.failure_code else None,
        "signed_generalized_force": generalized.generalized_force[0],
        "generalized_force_error": generalized_error,
        "energy_check_steps": list(energy_check.step_sizes),
        "energy_check_fd_generalized_force": list(energy_check.finite_difference_generalized_force),
        "max_energy_gradient_residual": max_energy_gradient_residual,
        "table_force_error_N": table_force_error,
        "table_energy_error_J": table_energy_error,
        "table_tangent_error_N_per_m": table_tangent_error,
        "table_outside_failure_code": table_outside.failure_code.value if table_outside.failure_code else None,
        "pass": passed,
    }


def wufr_benchmark() -> dict:
    package = load_wufr27_spring_package(ROOT / "data_catalog/wufr27_spring_package_v0.toml")
    front = evaluate_spring_from_coilover(
        package.front,
        package.reference,
        package.front_nominal_coilover_length_m,
    )
    rear = evaluate_spring_from_coilover(
        package.rear,
        package.reference,
        package.rear_nominal_coilover_length_m,
    )
    rear_outside = evaluate_spring_law(package.rear, 0.0570001)
    if not front.ok or not rear.ok:
        raise RuntimeError("BENCH-SUSP-0010 WUFR nominal spring benchmark could not be evaluated")

    front_x_expected = 0.1857 - package.front_nominal_coilover_length_m
    rear_x_expected = 0.1857 - package.rear_nominal_coilover_length_m
    front_compression_error = abs(float(front.x_s_m) - front_x_expected)
    rear_compression_error = abs(float(rear.x_s_m) - rear_x_expected)
    front_force_error = abs(float(front.force_N) - package.front_nominal_force_N)
    rear_force_error = abs(float(rear.force_N) - package.rear_nominal_force_N)
    rear_tangent_error = abs(float(rear.tangent_stiffness_N_per_m) - package.rear_nominal_tangent_rate_N_per_m)
    instantaneous_rate_product_N = float(rear.tangent_stiffness_N_per_m) * float(rear.x_s_m)
    integrated_force_difference_N = instantaneous_rate_product_N - float(rear.force_N)

    rear_energy_check = check_spring_energy_gradient(
        package.rear,
        float(rear.x_s_m),
        -1.0,
        step_sizes=(1.0e-6, 5.0e-7),
    )
    if not rear_energy_check.ok:
        raise RuntimeError(f"BENCH-SUSP-0010 rear energy check failed: {rear_energy_check.message}")

    passed = (
        package.configuration_id == "WUFR27_SUSPENSION_BASELINE_V0"
        and package.front.assumption_ids == ("ASM-SUSP-0002",)
        and package.rear.assumption_ids == ("ASM-SUSP-0002",)
        and not package.installed_as_built_authority
        and front_compression_error <= 1.0e-14
        and rear_compression_error <= 1.0e-14
        and front_force_error <= 1.0e-9
        and rear_force_error <= 1.0e-9
        and rear_tangent_error <= 1.0e-8
        and integrated_force_difference_N > 20.0
        and rear_outside.failure_code is SpringFailureCode.CONSTITUTIVE_DOMAIN_EXCEEDED
        and max(rear_energy_check.absolute_residuals) <= 5.0e-8
        and package.shockpot_reported_raw == "44m"
    )
    return {
        "configuration_id": package.configuration_id,
        "assumption_ids": list(package.rear.assumption_ids),
        "installed_as_built_authority": package.installed_as_built_authority,
        "front_nominal_coilover_length_m": package.front_nominal_coilover_length_m,
        "rear_nominal_coilover_length_m": package.rear_nominal_coilover_length_m,
        "front_nominal_compression_m": front.x_s_m,
        "rear_nominal_compression_m": rear.x_s_m,
        "front_nominal_force_N": front.force_N,
        "rear_nominal_force_N": rear.force_N,
        "rear_nominal_tangent_stiffness_N_per_m": rear.tangent_stiffness_N_per_m,
        "front_compression_error_m": front_compression_error,
        "rear_compression_error_m": rear_compression_error,
        "front_force_error_N": front_force_error,
        "rear_force_error_N": rear_force_error,
        "rear_tangent_error_N_per_m": rear_tangent_error,
        "rear_instantaneous_tangent_times_compression_N": instantaneous_rate_product_N,
        "rear_integrated_force_difference_N": integrated_force_difference_N,
        "rear_outside_failure_code": rear_outside.failure_code.value if rear_outside.failure_code else None,
        "rear_energy_check_max_residual": max(rear_energy_check.absolute_residuals),
        "shockpot_reported_raw": package.shockpot_reported_raw,
        "pass": passed,
    }


def build_report() -> dict:
    b9 = synthetic_benchmark()
    b10 = wufr_benchmark()
    if not b9["pass"] or not b10["pass"]:
        raise RuntimeError("Suspension spring-force benchmark acceptance failed")
    return {
        "model_id": "MOD-SUSP-0004",
        "authorization_id": "AUTH-SUSP-0004",
        "assumption_ids": ["ASM-SUSP-0002"],
        "authority": "software verification and reviewed design-intent assumption evidence only",
        "BENCH-SUSP-0009": b9,
        "BENCH-SUSP-0010": b10,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("suspension_spring_force_report.json"))
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        b10 = report["BENCH-SUSP-0010"]
        print(
            "MOD-SUSP-0004: "
            f"front_force_N={b10['front_nominal_force_N']:.9g}, "
            f"rear_force_N={b10['rear_nominal_force_N']:.9g}, "
            f"rear_kt_N_per_mm={1e-3*b10['rear_nominal_tangent_stiffness_N_per_m']:.9g}, "
            f"rear_energy_residual={b10['rear_energy_check_max_residual']:.3g}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
