#!/usr/bin/env python3
"""Generate BENCH-SUSP-0011/0012 anti-roll-bar verification diagnostics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pssd_suspension import (
    AntiRollBarDefinition,
    AntiRollBarFailureCode,
    AntiRollBarReference,
    AntiRollBarStatus,
    check_anti_roll_bar_energy_gradient,
    evaluate_anti_roll_bar,
    evaluate_anti_roll_bar_law,
    symmetric_differential_coordinate,
)
from pssd_suspension.wufr_anti_roll_bar import load_wufr27_blade_anti_roll_bar_package


ROOT = Path(__file__).resolve().parents[1]


def synthetic_benchmark() -> dict:
    definition = AntiRollBarDefinition(
        arb_id="BENCH_SUSP_0011_ARB",
        axle="synthetic",
        stiffness_action_per_coordinate=10000.0,
        elastic_coordinate_unit="m",
        elastic_action_unit="N",
        source_id="BENCH-SUSP-0011",
        configuration_id="SYNTHETIC",
        max_abs_deformation=0.050,
    )
    zero_reference = AntiRollBarReference(
        reference_id="BENCH_SUSP_0011_ZERO",
        configuration_id="SYNTHETIC",
        elastic_coordinate_unit="m",
    )
    common_map = symmetric_differential_coordinate(0.010, 0.010)
    differential_map = symmetric_differential_coordinate(0.010, -0.010)
    if not common_map.ok or not differential_map.ok:
        raise RuntimeError("BENCH-SUSP-0011 bilateral mapping could not be evaluated")

    common = evaluate_anti_roll_bar(definition, zero_reference, float(common_map.deformation_m))
    differential = evaluate_anti_roll_bar(
        definition,
        zero_reference,
        float(differential_map.deformation_m),
        ds_dq=(float(differential_map.ds_dz_left), float(differential_map.ds_dz_right)),
        coordinate_order=("z_left_m", "z_right_m"),
        coordinate_units=("m", "m"),
    )
    energy_check = check_anti_roll_bar_energy_gradient(
        definition, zero_reference, float(differential_map.deformation_m), 1.0,
        step_sizes=(1.0e-6, 5.0e-7),
    )
    shifted_reference = AntiRollBarReference(
        reference_id="BENCH_SUSP_0011_SHIFTED",
        configuration_id="SYNTHETIC",
        elastic_coordinate_unit="m",
        zero_energy_coordinate=0.003,
    )
    shifted = evaluate_anti_roll_bar(definition, shifted_reference, 0.020)
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

    max_residual = max(energy_check.absolute_residuals)
    passed = (
        common.ok and differential.ok and energy_check.ok and shifted.ok and no_bar.ok
        and abs(float(common.stored_energy_J)) <= 1.0e-14
        and abs(float(common.elastic_action)) <= 1.0e-14
        and abs(float(differential.deformation) - 0.020) <= 1.0e-14
        and abs(float(differential.elastic_action) - 200.0) <= 1.0e-12
        and abs(float(differential.stored_energy_J) - 2.0) <= 1.0e-12
        and differential.generalized_force == (-200.0, 200.0)
        and abs(float(shifted.deformation) - 0.017) <= 1.0e-14
        and no_bar.status is AntiRollBarStatus.NO_BAR
        and missing.failure_code is AntiRollBarFailureCode.MISSING_STIFFNESS_AUTHORITY
        and outside.failure_code is AntiRollBarFailureCode.CONSTITUTIVE_DOMAIN_EXCEEDED
        and max_residual <= 1.0e-8
    )
    return {
        "common_mode_deformation_m": common.deformation,
        "common_mode_energy_J": common.stored_energy_J,
        "common_mode_action_N": common.elastic_action,
        "differential_deformation_m": differential.deformation,
        "differential_action_N": differential.elastic_action,
        "differential_energy_J": differential.stored_energy_J,
        "differential_generalized_force_N": list(differential.generalized_force),
        "shifted_reference_deformation_m": shifted.deformation,
        "no_bar_status": no_bar.status.value,
        "missing_stiffness_failure_code": missing.failure_code.value if missing.failure_code else None,
        "outside_domain_failure_code": outside.failure_code.value if outside.failure_code else None,
        "energy_check_steps_m": list(energy_check.step_sizes),
        "energy_check_fd_generalized_force_N": list(energy_check.finite_difference_generalized_force),
        "max_energy_gradient_residual_N": max_residual,
        "pass": passed,
    }


def wufr_benchmark() -> dict:
    package = load_wufr27_blade_anti_roll_bar_package(
        ROOT / "data_catalog/wufr27_anti_roll_bar_package_v0.toml"
    )
    expected_forces = (280.0, 300.0, 400.0, 700.0, 2300.0)
    expected_energies = (0.140, 0.150, 0.200, 0.350, 1.150)
    one_mm = 0.001
    settings: list[dict] = []

    for index, (expected_force, expected_energy) in enumerate(zip(expected_forces, expected_energies), start=1):
        definition = package.definition_for_setting(index)
        state = evaluate_anti_roll_bar(definition, package.reference, one_mm)
        if not state.ok:
            raise RuntimeError(f"BENCH-SUSP-0012 setting {index} could not be evaluated: {state.message}")
        settings.append({
            "setting": index,
            "stiffness_N_per_mm": definition.stiffness_action_per_coordinate / 1000.0,
            "stiffness_N_per_m": definition.stiffness_action_per_coordinate,
            "deflection_mm": 1.0,
            "force_N": state.elastic_action,
            "energy_J": state.stored_energy_J,
            "generalized_force_available": state.generalized_force_available,
            "force_error_N": abs(float(state.elastic_action) - expected_force),
            "energy_error_J": abs(float(state.stored_energy_J) - expected_energy),
        })

    energy_check = check_anti_roll_bar_energy_gradient(
        package.definition_for_setting(3), package.reference, one_mm, 1.0,
        step_sizes=(1.0e-7, 5.0e-8),
    )
    if not energy_check.ok:
        raise RuntimeError(f"BENCH-SUSP-0012 blade-coordinate energy check failed: {energy_check.message}")

    passed = (
        package.configuration_id == "WUFR27_SUSPENSION_BASELINE_V0"
        and package.solidworks_fea_stiffness_N_per_mm == expected_forces
        and package.simulink_comparison_N_per_mm == (285.0, 309.0, 400.0, 724.0, 2628.0)
        and package.instron_comparison_N_per_mm == (900.0, 980.0, 1320.0, 1970.0, 2630.0)
        and package.matlab_reduced_axle_comparison_Nm_per_deg == (2560.0, 2270.0)
        and not package.interpolation_authorized
        and not package.geometry_map_authorized
        and not package.installed_as_built_authority
        and all(item["force_error_N"] <= 1.0e-12 for item in settings)
        and all(item["energy_error_J"] <= 1.0e-12 for item in settings)
        and all(not item["generalized_force_available"] for item in settings)
        and max(energy_check.absolute_residuals) <= 1.0e-7
    )
    return {
        "configuration_id": package.configuration_id,
        "source_url": package.source_url,
        "source_sheet": package.source_sheet,
        "governing_quantity": "SolidWorks FEA linear blade-tip stiffness",
        "governing_unit": "N/mm (stored in SI as N/m)",
        "settings": settings,
        "simulink_comparison_N_per_mm": list(package.simulink_comparison_N_per_mm),
        "instron_comparison_N_per_mm": list(package.instron_comparison_N_per_mm),
        "matlab_reduced_axle_comparison_Nm_per_deg": list(package.matlab_reduced_axle_comparison_Nm_per_deg),
        "interpolation_authorized": package.interpolation_authorized,
        "z_bar_geometry_map_authorized": package.geometry_map_authorized,
        "installed_as_built_authority": package.installed_as_built_authority,
        "setting3_blade_coordinate_energy_check_max_residual_N": max(energy_check.absolute_residuals),
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
        "authority": "generic conservative ARB mechanics plus reviewer-selected discrete SolidWorks FEA blade-tip stiffness; WUFR Z-bar geometry map remains unavailable",
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
            f"blade_k_N_per_mm={[item['stiffness_N_per_mm'] for item in b12['settings']]}, "
            f"one_mm_force_N={[item['force_N'] for item in b12['settings']]}, "
            f"zbar_map_authorized={b12['z_bar_geometry_map_authorized']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
