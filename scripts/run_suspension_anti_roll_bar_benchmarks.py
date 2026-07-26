#!/usr/bin/env python3
"""Generate BENCH-SUSP-0011/0012 anti-roll-bar verification diagnostics."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from pssd_suspension import (
    AntiRollBarDefinition,
    AntiRollBarFailureCode,
    AntiRollBarReference,
    AntiRollBarStatus,
    check_anti_roll_bar_energy_gradient,
    evaluate_anti_roll_bar,
    evaluate_anti_roll_bar_law,
    load_wufr27_anti_roll_bar_package,
    symmetric_differential_angle,
)


ROOT = Path(__file__).resolve().parents[1]


def synthetic_benchmark() -> dict:
    definition = AntiRollBarDefinition(
        arb_id="BENCH_SUSP_0011_ARB",
        axle="synthetic",
        stiffness_Nm_per_rad=10000.0,
        source_id="BENCH-SUSP-0011",
        configuration_id="SYNTHETIC",
        max_abs_deformation_rad=0.050,
    )
    zero_reference = AntiRollBarReference(
        reference_id="BENCH_SUSP_0011_ZERO",
        configuration_id="SYNTHETIC",
    )
    common_map = symmetric_differential_angle(0.010, 0.010, 1.0)
    differential_map = symmetric_differential_angle(0.010, -0.010, 1.0)
    if not common_map.ok or not differential_map.ok:
        raise RuntimeError("BENCH-SUSP-0011 bilateral mapping could not be evaluated")

    common = evaluate_anti_roll_bar(definition, zero_reference, float(common_map.angle_rad))
    differential = evaluate_anti_roll_bar(
        definition,
        zero_reference,
        float(differential_map.angle_rad),
        dphi_dq=(float(differential_map.dphi_dz_left), float(differential_map.dphi_dz_right)),
        coordinate_order=("z_left_m", "z_right_m"),
        coordinate_units=("m", "m"),
    )
    energy_check = check_anti_roll_bar_energy_gradient(
        definition,
        zero_reference,
        float(differential_map.angle_rad),
        float(differential_map.dphi_dz_left),
        step_sizes=(1.0e-6, 5.0e-7),
    )

    preload_reference = AntiRollBarReference(
        reference_id="BENCH_SUSP_0011_SHIFTED",
        configuration_id="SYNTHETIC",
        zero_energy_angle_rad=0.003,
    )
    shifted = evaluate_anti_roll_bar(definition, preload_reference, 0.020)
    no_bar = evaluate_anti_roll_bar(
        None,
        zero_reference,
        0.020,
        enabled=False,
        coordinate_order=("z_left_m", "z_right_m"),
        coordinate_units=("m", "m"),
        disabled_arb_id="BENCH_SUSP_0011_NO_BAR",
        disabled_axle="synthetic",
        disabled_source_id="BENCH-SUSP-0011",
    )
    missing = evaluate_anti_roll_bar(None, zero_reference, 0.020)
    outside = evaluate_anti_roll_bar_law(definition, 0.0501)

    if not all((common.ok, differential.ok, energy_check.ok, shifted.ok, no_bar.ok)):
        raise RuntimeError("BENCH-SUSP-0011 synthetic ARB benchmark could not be evaluated")

    common_energy_error = abs(float(common.stored_energy_J))
    common_action_error = abs(float(common.restoring_moment_Nm))
    differential_angle_error = abs(float(differential.deformation_rad) - 0.020)
    differential_action_error = abs(float(differential.restoring_moment_Nm) - 200.0)
    differential_energy_error = abs(float(differential.stored_energy_J) - 2.0)
    generalized_error = max(
        abs(differential.generalized_force[0] + 200.0),
        abs(differential.generalized_force[1] - 200.0),
    )
    shifted_error = abs(float(shifted.deformation_rad) - 0.017)
    max_energy_gradient_residual = max(energy_check.absolute_residuals)

    passed = (
        common_energy_error <= 1.0e-14
        and common_action_error <= 1.0e-14
        and differential_angle_error <= 1.0e-14
        and differential_action_error <= 1.0e-12
        and differential_energy_error <= 1.0e-12
        and generalized_error <= 1.0e-12
        and abs(sum(differential.generalized_force)) <= 1.0e-12
        and shifted_error <= 1.0e-14
        and no_bar.status is AntiRollBarStatus.NO_BAR
        and no_bar.stored_energy_J == 0.0
        and no_bar.restoring_moment_Nm == 0.0
        and missing.failure_code is AntiRollBarFailureCode.MISSING_STIFFNESS_AUTHORITY
        and outside.failure_code is AntiRollBarFailureCode.CONSTITUTIVE_DOMAIN_EXCEEDED
        and max_energy_gradient_residual <= 1.0e-8
    )
    return {
        "common_mode_angle_rad": common.deformation_rad,
        "common_mode_energy_J": common.stored_energy_J,
        "common_mode_action_Nm": common.restoring_moment_Nm,
        "differential_angle_rad": differential.deformation_rad,
        "differential_action_Nm": differential.restoring_moment_Nm,
        "differential_energy_J": differential.stored_energy_J,
        "differential_generalized_force": list(differential.generalized_force),
        "generalized_force_error": generalized_error,
        "shifted_reference_deformation_rad": shifted.deformation_rad,
        "no_bar_status": no_bar.status.value,
        "missing_stiffness_failure_code": missing.failure_code.value if missing.failure_code else None,
        "outside_domain_failure_code": outside.failure_code.value if outside.failure_code else None,
        "energy_check_steps": list(energy_check.step_sizes),
        "energy_check_fd_generalized_force": list(energy_check.finite_difference_generalized_force),
        "max_energy_gradient_residual": max_energy_gradient_residual,
        "pass": passed,
    }


def wufr_benchmark() -> dict:
    package = load_wufr27_anti_roll_bar_package(
        ROOT / "data_catalog/wufr27_anti_roll_bar_package_v0.toml"
    )
    phi = math.radians(1.0)
    front = evaluate_anti_roll_bar(
        package.front,
        package.reference,
        phi,
        dphi_dq=1.0,
        coordinate_order=("phi_arb_rad",),
        coordinate_units=("rad",),
    )
    rear = evaluate_anti_roll_bar(package.rear, package.reference, phi)
    zero_front = evaluate_anti_roll_bar(package.front, package.reference, 0.0)
    if not front.ok or not rear.ok or not zero_front.ok:
        raise RuntimeError("BENCH-SUSP-0012 WUFR reduced ARB benchmark could not be evaluated")

    front_si_expected = package.source_front_stiffness_Nm_per_deg * 180.0 / math.pi
    rear_si_expected = package.source_rear_stiffness_Nm_per_deg * 180.0 / math.pi
    front_stiffness_error = abs(package.front.stiffness_Nm_per_rad - front_si_expected)
    rear_stiffness_error = abs(package.rear.stiffness_Nm_per_rad - rear_si_expected)
    front_action_error = abs(float(front.restoring_moment_Nm) - 2560.0)
    rear_action_error = abs(float(rear.restoring_moment_Nm) - 2270.0)
    front_energy_expected = 0.5 * front_si_expected * phi * phi
    rear_energy_expected = 0.5 * rear_si_expected * phi * phi
    front_energy_error = abs(float(front.stored_energy_J) - front_energy_expected)
    rear_energy_error = abs(float(rear.stored_energy_J) - rear_energy_expected)

    front_check = check_anti_roll_bar_energy_gradient(
        package.front,
        package.reference,
        phi,
        1.0,
        step_sizes=(1.0e-6, 5.0e-7),
    )
    if not front_check.ok:
        raise RuntimeError(f"BENCH-SUSP-0012 energy check failed: {front_check.message}")

    passed = (
        package.configuration_id == "WUFR27_SUSPENSION_BASELINE_V0"
        and package.front.assumption_ids == ("ASM-SUSP-0003",)
        and package.rear.assumption_ids == ("ASM-SUSP-0003",)
        and not package.installed_as_built_authority
        and package.front.reduced_axle_level
        and package.rear.reduced_axle_level
        and package.source_front_stiffness_Nm_per_deg == 2560.0
        and package.source_rear_stiffness_Nm_per_deg == 2270.0
        and package.instron_status == "qualitative_corroboration_only"
        and front_stiffness_error <= 1.0e-10
        and rear_stiffness_error <= 1.0e-10
        and front_action_error <= 1.0e-10
        and rear_action_error <= 1.0e-10
        and front_energy_error <= 1.0e-12
        and rear_energy_error <= 1.0e-12
        and abs(float(zero_front.stored_energy_J)) <= 1.0e-14
        and abs(float(zero_front.restoring_moment_Nm)) <= 1.0e-14
        and math.isclose(front.generalized_force[0], -2560.0, rel_tol=1.0e-14, abs_tol=1.0e-12)
        and max(front_check.absolute_residuals) <= 1.0e-6
    )
    return {
        "configuration_id": package.configuration_id,
        "assumption_ids": list(package.front.assumption_ids),
        "installed_as_built_authority": package.installed_as_built_authority,
        "reduced_axle_level": package.front.reduced_axle_level and package.rear.reduced_axle_level,
        "source_front_stiffness_Nm_per_deg": package.source_front_stiffness_Nm_per_deg,
        "source_rear_stiffness_Nm_per_deg": package.source_rear_stiffness_Nm_per_deg,
        "front_stiffness_Nm_per_rad": package.front.stiffness_Nm_per_rad,
        "rear_stiffness_Nm_per_rad": package.rear.stiffness_Nm_per_rad,
        "front_one_degree_action_Nm": front.restoring_moment_Nm,
        "rear_one_degree_action_Nm": rear.restoring_moment_Nm,
        "front_one_degree_energy_J": front.stored_energy_J,
        "rear_one_degree_energy_J": rear.stored_energy_J,
        "front_one_degree_generalized_force": front.generalized_force[0],
        "zero_front_energy_J": zero_front.stored_energy_J,
        "zero_front_action_Nm": zero_front.restoring_moment_Nm,
        "front_stiffness_conversion_error": front_stiffness_error,
        "rear_stiffness_conversion_error": rear_stiffness_error,
        "front_action_error_Nm": front_action_error,
        "rear_action_error_Nm": rear_action_error,
        "front_energy_error_J": front_energy_error,
        "rear_energy_error_J": rear_energy_error,
        "front_energy_check_max_residual": max(front_check.absolute_residuals),
        "instron_status": package.instron_status,
        "pass": passed,
    }


def build_report() -> dict:
    b11 = synthetic_benchmark()
    b12 = wufr_benchmark()
    if not b11["pass"] or not b12["pass"]:
        raise RuntimeError("Suspension anti-roll-bar benchmark acceptance failed")
    return {
        "model_id": "MOD-SUSP-0005",
        "authorization_id": "AUTH-SUSP-0005",
        "assumption_ids": ["ASM-SUSP-0003"],
        "authority": "software verification and reviewer-selected reduced design-intent ARB stiffness only; not blade/component or installed authority",
        "BENCH-SUSP-0011": b11,
        "BENCH-SUSP-0012": b12,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("suspension_anti_roll_bar_report.json"))
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        b12 = report["BENCH-SUSP-0012"]
        print(
            "MOD-SUSP-0005: "
            f"front_K_Nm_per_deg={b12['source_front_stiffness_Nm_per_deg']:.9g}, "
            f"rear_K_Nm_per_deg={b12['source_rear_stiffness_Nm_per_deg']:.9g}, "
            f"front_1deg_M_Nm={b12['front_one_degree_action_Nm']:.9g}, "
            f"front_energy_residual={b12['front_energy_check_max_residual']:.3g}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
