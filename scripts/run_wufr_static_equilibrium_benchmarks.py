#!/usr/bin/env python3
"""Generate BENCH-VEH-0011..0013 WUFR static-equilibrium diagnostics."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from pssd_vehicle.wufr_static_equilibrium import (
    RESULT_LABEL,
    load_wufr_static_equilibrium_provider,
    solve_wufr_static_equilibrium,
)


ROOT = Path(__file__).resolve().parents[1]
CONTINUATION_Q_TOLERANCE = 1.0e-8
CONTINUATION_REACTION_TOLERANCE_N = 1.0e-5


def _provider():
    return load_wufr_static_equilibrium_provider(
        source_path=ROOT / "data_catalog/wufr27_static_equilibrium_composition_v0.toml",
        road_contact_source_path=ROOT / "data_catalog/wufr26_road_contact_reference_v0.toml",
        suspension_geometry_path=ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml",
        wheel_profile_path=ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml",
        steering_geometry_path=ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml",
        whole_vehicle_path=ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml",
        gravity_path=ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml",
        spring_package_path=ROOT / "data_catalog/wufr27_spring_package_v0.toml",
        zbar_fixture_path=ROOT / "benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml",
    )


def _vector(values) -> list[float]:
    return [float(value) for value in values]


def _result_record(result) -> dict:
    record: dict = {
        "ok": result.ok,
        "status": result.status.value,
        "failure_code": result.failure_code.value if result.failure_code else None,
        "message": result.message,
        "result_label": result.result_label,
        "front_arb_setting": result.front_arb_setting,
        "rear_arb_setting": result.rear_arb_setting,
        "complete_static_road_reaction": result.complete_static_road_reaction,
        "installed_as_built_authority": result.installed_as_built_authority,
        "historical_scale_reconstruction_used": result.historical_scale_reconstruction_used,
    }
    if result.solve is not None:
        record["solve"] = {
            "q_body": _vector(result.solve.q_body),
            "wheel_coordinates_m": _vector(result.solve.wheel_coordinates),
            "body_coordinate_order": list(result.solve.body_coordinate_order),
            "wheel_coordinate_order": list(result.solve.wheel_coordinate_order),
            "residual": _vector(result.solve.residual),
            "scaled_residual": _vector(result.solve.scaled_residual),
            "scaled_residual_norm": result.solve.scaled_residual_norm,
            "iterations": result.solve.iterations,
            "initial_scaled_residual_norm": result.solve.initial_scaled_residual_norm,
            "convergence_threshold": result.solve.convergence_threshold,
            "tangent_methods": list(result.solve.tangent_methods),
            "tangent_steps": _vector(result.solve.tangent_steps),
            "reciprocal_pivot_ratio": result.solve.reciprocal_pivot_ratio,
            "line_search_scale": result.solve.line_search_scale,
            "suspension_stored_energy_J": result.solve.suspension_stored_energy_J,
            "total_potential_energy_J": result.solve.total_potential_energy_J,
            "compatibility_source_id": result.solve.compatibility_source_id,
            "suspension_source_id": result.solve.suspension_source_id,
            "body_external_source_id": result.solve.body_external_source_id,
            "failure_code": result.solve.failure_code.value if result.solve.failure_code else None,
            "message": result.solve.message,
        }
    if result.suspension is not None:
        record["suspension"] = {
            "wheel_coordinates_m": _vector(result.suspension.wheel_coordinates_m),
            "generalized_spring_force_N": _vector(result.suspension.generalized_spring_force_N),
            "generalized_arb_force_N": _vector(result.suspension.generalized_arb_force_N),
            "generalized_suspension_force_N": _vector(result.suspension.generalized_suspension_force_N),
            "spring_energy_J": result.suspension.spring_energy_J,
            "arb_energy_J": result.suspension.arb_energy_J,
            "stored_energy_J": result.suspension.stored_energy_J,
            "spring_actuation_derivative_method": [
                item.derivative_method for item in result.suspension.spring_actuation_states
            ],
            "spring_actuation_rho_dw": [
                item.rho_dw for item in result.suspension.spring_actuation_states
            ],
        }
    if result.contact_recovery is not None:
        record["contact"] = {
            "normal_reaction_N": _vector(result.contact_recovery.normal_reaction_N),
            "wheel_external_generalized_force_N": _vector(result.contact_recovery.wheel_external_generalized_force),
            "contact_coefficients": _vector(result.contact_recovery.contact_coefficients),
            "wheel_equilibrium_residual_N": _vector(result.contact_recovery.wheel_equilibrium_residual),
            "failure_code": result.contact_recovery.failure_code.value if result.contact_recovery.failure_code else None,
            "message": result.contact_recovery.message,
        }
    if result.energy_gradient is not None:
        record["energy_gradient"] = {
            "expected_generalized_force": _vector(result.energy_gradient.expected_generalized_force),
            "finite_difference_generalized_force": [
                _vector(values) for values in result.energy_gradient.finite_difference_generalized_force
            ],
            "relative_step_multipliers": _vector(result.energy_gradient.relative_step_multipliers),
            "maximum_absolute_residual": result.energy_gradient.maximum_absolute_residual,
            "failure_code": result.energy_gradient.failure_code.value if result.energy_gradient.failure_code else None,
            "message": result.energy_gradient.message,
        }
    if result.physical_closure is not None:
        closure = result.physical_closure
        record["physical_closure"] = {
            "ok": closure.ok,
            "maximum_force_residual_N": closure.maximum_force_residual_N,
            "maximum_moment_residual_Nm": closure.maximum_moment_residual_Nm,
            "failure_code": closure.failure_code.value if closure.failure_code else None,
            "message": closure.message,
        }
        if closure.resultant is not None:
            record["physical_closure"]["resultant_force_N"] = _vector(closure.resultant.resultant_force_N)
            record["physical_closure"]["resultant_moment_Nm"] = _vector(closure.resultant.resultant_moment_Nm)
    if result.road_contact is not None and result.road_contact.compatibility.roots:
        record["physical_points"] = {
            root.corner_id: {
                "contact_point_m": _vector(root.state.contact_road.position_m) if root.state else None,
                "wheel_center_m": _vector(root.state.wheel_center_road.position_m) if root.state else None,
            }
            for root in result.road_contact.compatibility.roots
        }
    return record


def _max_difference(left, right) -> float:
    return max(abs(float(a) - float(b)) for a, b in zip(left, right))


def build_report() -> dict:
    provider = _provider()
    primary = solve_wufr_static_equilibrium(
        provider,
        front_arb_setting=1,
        rear_arb_setting=1,
        initial_q_body=(0.0, 0.0, 0.0),
    )
    alternate = solve_wufr_static_equilibrium(
        provider,
        front_arb_setting=1,
        rear_arb_setting=1,
        initial_q_body=(-0.003, 0.001, -0.001),
    )
    invalid = solve_wufr_static_equilibrium(
        provider,
        front_arb_setting=0,
        rear_arb_setting=1,
    )
    q_difference = math.inf
    reaction_difference = math.inf
    if primary.solve is not None and alternate.solve is not None:
        q_difference = _max_difference(primary.solve.q_body, alternate.solve.q_body)
    if primary.contact_recovery is not None and alternate.contact_recovery is not None:
        reaction_difference = _max_difference(
            primary.contact_recovery.normal_reaction_N,
            alternate.contact_recovery.normal_reaction_N,
        )
    report = {
        "version": "0.1.0",
        "model_id": "MOD-VEH-0007",
        "authorization_id": "AUTH-VEH-0009",
        "equation_ids": ["EQ-VEH-0015", "EQ-VEH-0016", "EQ-VEH-0017"],
        "benchmark_ids": ["BENCH-VEH-0011", "BENCH-VEH-0012", "BENCH-VEH-0013"],
        "assumption_ids": ["ASM-VEH-0002", "ASM-VEH-0003", "ASM-VEH-0005", "ASM-SUSP-0002", "ASM-SUSP-0003"],
        "result_label": RESULT_LABEL,
        "configuration_id": provider.source.configuration_id,
        "static_state_id": provider.source.static_state_id,
        "benchmark_fixture": {
            "front_arb_setting": 1,
            "rear_arb_setting": 1,
            "setting_role": "verification_fixture_only_not_setup_authority",
            "primary_initial_q_body": [0.0, 0.0, 0.0],
            "alternate_initial_q_body": [-0.003, 0.001, -0.001],
        },
        "solver_configuration": {
            "coordinate_scales": _vector(provider.quasi_static_config.coordinate_scales),
            "residual_scales": _vector(provider.quasi_static_config.residual_scales),
            "lower_bounds": list(provider.quasi_static_config.lower_bounds),
            "upper_bounds": list(provider.quasi_static_config.upper_bounds),
            "residual_absolute_tolerance": provider.quasi_static_config.residual_absolute_tolerance,
            "residual_relative_tolerance": provider.quasi_static_config.residual_relative_tolerance,
            "max_iterations": provider.quasi_static_config.max_iterations,
            "finite_difference_relative_step": provider.quasi_static_config.finite_difference_relative_step,
            "finite_difference_min_step": provider.quasi_static_config.finite_difference_min_step,
            "line_search_reduction": provider.quasi_static_config.line_search_reduction,
            "line_search_max_trials": provider.quasi_static_config.line_search_max_trials,
            "energy_gradient_step_multipliers": _vector(provider.config.energy_gradient_step_multipliers),
            "energy_gradient_absolute_tolerance": provider.config.energy_gradient_absolute_tolerance,
            "physical_force_residual_tolerance_N": provider.config.physical_force_residual_tolerance_N,
            "physical_moment_residual_tolerance_Nm": provider.config.physical_moment_residual_tolerance_Nm,
            "wheel_equilibrium_residual_tolerance_N": provider.config.wheel_equilibrium_residual_tolerance_N,
        },
        "primary": _result_record(primary),
        "alternate_initial_guess": _result_record(alternate),
        "continuation_comparison": {
            "maximum_q_body_difference": q_difference,
            "q_body_tolerance": CONTINUATION_Q_TOLERANCE,
            "maximum_normal_reaction_difference_N": reaction_difference,
            "normal_reaction_tolerance_N": CONTINUATION_REACTION_TOLERANCE_N,
            "same_continuation_solution": (
                q_difference <= CONTINUATION_Q_TOLERANCE
                and reaction_difference <= CONTINUATION_REACTION_TOLERANCE_N
            ),
        },
        "invalid_setting_failure": _result_record(invalid),
        "boundaries": {
            "historical_scale_fit": False,
            "installed_as_built_authority": False,
            "physical_correlation_authority": False,
            "arb_setup_selection_authority": False,
            "carrier_wrench_authority": False,
            "structural_load_case_authority": False,
            "maneuver_qss_authority": False,
        },
    }
    if not primary.ok or not alternate.ok:
        raise RuntimeError(json.dumps(report, indent=2, sort_keys=True))
    if not report["continuation_comparison"]["same_continuation_solution"]:
        raise RuntimeError(json.dumps(report, indent=2, sort_keys=True))
    if invalid.ok or invalid.failure_code is None:
        raise RuntimeError("BENCH-VEH-0013 invalid-setting fixture did not fail structurally")
    return report


def build_summary(report: dict) -> dict:
    primary = report["primary"]
    return {
        "ok": primary["ok"],
        "result_label": primary["result_label"],
        "q_body": primary.get("solve", {}).get("q_body"),
        "normal_reaction_N": primary.get("contact", {}).get("normal_reaction_N"),
        "scaled_residual_norm": primary.get("solve", {}).get("scaled_residual_norm"),
        "energy_gradient_max_residual": primary.get("energy_gradient", {}).get("maximum_absolute_residual"),
        "physical_force_residual_N": primary.get("physical_closure", {}).get("maximum_force_residual_N"),
        "physical_moment_residual_Nm": primary.get("physical_closure", {}).get("maximum_moment_residual_Nm"),
        "maximum_q_body_restart_difference": report["continuation_comparison"]["maximum_q_body_difference"],
        "maximum_reaction_restart_difference_N": report["continuation_comparison"]["maximum_normal_reaction_difference_N"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    summary = build_summary(report)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if args.summary_output:
        args.summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    if args.summary:
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif not args.output and not args.summary_output:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
