#!/usr/bin/env python3
"""Generate BENCH-VEH-0011..0013 WUFR static-equilibrium diagnostics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pssd_vehicle.wufr_static_equilibrium import (
    RESULT_LABEL,
    load_wufr_static_equilibrium_provider,
    solve_wufr_static_equilibrium,
)


ROOT = Path(__file__).resolve().parents[1]


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
    report = {
        "model_id": "MOD-VEH-0007",
        "authorization_id": "AUTH-VEH-0009",
        "result_label": RESULT_LABEL,
        "configuration_id": provider.source.configuration_id,
        "static_state_id": provider.source.static_state_id,
        "benchmark_fixture": {"front_arb_setting": 1, "rear_arb_setting": 1},
        "primary": _result_record(primary),
        "alternate_initial_guess": _result_record(alternate),
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
    if not primary.ok:
        raise RuntimeError(json.dumps(report, indent=2, sort_keys=True))
    if not alternate.ok:
        raise RuntimeError(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if args.summary:
        primary = report["primary"]
        summary = {
            "ok": primary["ok"],
            "result_label": primary["result_label"],
            "q_body": primary.get("solve", {}).get("q_body"),
            "normal_reaction_N": primary.get("contact", {}).get("normal_reaction_N"),
            "energy_gradient_max_residual": primary.get("energy_gradient", {}).get("maximum_absolute_residual"),
            "physical_force_residual_N": primary.get("physical_closure", {}).get("maximum_force_residual_N"),
            "physical_moment_residual_Nm": primary.get("physical_closure", {}).get("maximum_moment_residual_Nm"),
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif not args.output:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
