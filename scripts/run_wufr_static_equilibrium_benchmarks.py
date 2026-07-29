#!/usr/bin/env python3
"""Generate BENCH-VEH-0011..0014 WUFR static-equilibrium diagnostics."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Sequence

from pssd_vehicle import wufr_static_equilibrium_core as core
from pssd_vehicle import wufr_static_equilibrium_runtime as runtime
from pssd_vehicle.quasi_static import (
    QuasiStaticStatus,
    SuspensionGeneralizedForceState,
    recover_active_contact_normal_reactions,
)
from pssd_vehicle.wufr_static_equilibrium import (
    RESULT_LABEL,
    load_wufr_static_equilibrium_provider,
    solve_wufr_static_equilibrium,
)


ROOT = Path(__file__).resolve().parents[1]
CONTINUATION_Q_TOLERANCE = 1.0e-8
CONTINUATION_REACTION_TOLERANCE_N = 1.0e-5
GRAVITY_ORACLE_TOLERANCE = 1.0e-5
GRAVITY_ORACLE_STEPS = (1.0e-5, 5.0e-6)
OLD_EQ_VEH_0016_PROBE_Q = (
    -0.0026807702741682574,
    -0.00008013635009263544,
    0.0026941883103072345,
)


def _provider():
    return load_wufr_static_equilibrium_provider(
        source_path=ROOT / "data_catalog/wufr27_static_equilibrium_composition_v1.toml",
        road_contact_source_path=ROOT / "data_catalog/wufr26_road_contact_reference_v0.toml",
        suspension_geometry_path=ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml",
        wheel_profile_path=ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml",
        steering_geometry_path=ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml",
        whole_vehicle_path=ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml",
        gravity_path=ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml",
        spring_package_path=ROOT / "data_catalog/wufr27_spring_package_v0.toml",
        zbar_fixture_path=ROOT / "benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml",
    )


def _vector(values: Sequence[float]) -> list[float]:
    return [float(value) for value in values]


def _gravity_reduction_record(result) -> dict:
    return {
        "ok": result.ok,
        "status": result.status.value,
        "body_direct_generalized_force": _vector(result.body_direct_generalized_force),
        "wheel_generalized_force": _vector(result.wheel_generalized_force),
        "body_mapped_generalized_force": _vector(result.body_mapped_generalized_force),
        "body_reduced_generalized_force": _vector(result.body_reduced_generalized_force),
        "sprung_generalized_force": _vector(result.sprung_generalized_force),
        "total_body_external_generalized_force": _vector(
            result.total_body_external_generalized_force
        ),
        "sprung_potential_energy_J": result.sprung_potential_energy_J,
        "unsprung_potential_energy_J": result.unsprung_potential_energy_J,
        "total_gravity_potential_energy_J": result.total_gravity_potential_energy_J,
        "corner_direct_contributions": [
            _vector(values) for values in result.corner_direct_contributions
        ],
        "source_id": result.source_id,
        "configuration_id": result.configuration_id,
        "failure_code": result.failure_code.value if result.failure_code else None,
        "message": result.message,
    }


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
            "failure_code": (
                result.solve.failure_code.value if result.solve.failure_code else None
            ),
            "message": result.solve.message,
        }
    if result.suspension is not None:
        record["suspension"] = {
            "wheel_coordinates_m": _vector(result.suspension.wheel_coordinates_m),
            "generalized_spring_force_N": _vector(
                result.suspension.generalized_spring_force_N
            ),
            "generalized_arb_force_N": _vector(
                result.suspension.generalized_arb_force_N
            ),
            "generalized_suspension_force_N": _vector(
                result.suspension.generalized_suspension_force_N
            ),
            "spring_energy_J": result.suspension.spring_energy_J,
            "arb_energy_J": result.suspension.arb_energy_J,
            "stored_energy_J": result.suspension.stored_energy_J,
            "spring_actuation_derivative_method": [
                item.derivative_method
                for item in result.suspension.spring_actuation_states
            ],
            "spring_actuation_rho_dw": [
                item.rho_dw for item in result.suspension.spring_actuation_states
            ],
        }
    if result.gravity_reduction is not None:
        record["gravity_reduction"] = _gravity_reduction_record(
            result.gravity_reduction
        )
    if result.contact_recovery is not None:
        record["contact"] = {
            "normal_reaction_N": _vector(result.contact_recovery.normal_reaction_N),
            "wheel_external_generalized_force_N": _vector(
                result.contact_recovery.wheel_external_generalized_force
            ),
            "contact_coefficients": _vector(
                result.contact_recovery.contact_coefficients
            ),
            "wheel_equilibrium_residual_N": _vector(
                result.contact_recovery.wheel_equilibrium_residual
            ),
            "failure_code": (
                result.contact_recovery.failure_code.value
                if result.contact_recovery.failure_code
                else None
            ),
            "message": result.contact_recovery.message,
        }
    if result.energy_gradient is not None:
        record["energy_gradient"] = {
            "expected_generalized_force": _vector(
                result.energy_gradient.expected_generalized_force
            ),
            "finite_difference_generalized_force": [
                _vector(values)
                for values in result.energy_gradient.finite_difference_generalized_force
            ],
            "relative_step_multipliers": _vector(
                result.energy_gradient.relative_step_multipliers
            ),
            "maximum_absolute_residual": (
                result.energy_gradient.maximum_absolute_residual
            ),
            "failure_code": (
                result.energy_gradient.failure_code.value
                if result.energy_gradient.failure_code
                else None
            ),
            "message": result.energy_gradient.message,
        }
    if result.physical_closure is not None:
        closure = result.physical_closure
        record["physical_closure"] = {
            "ok": closure.ok,
            "maximum_force_residual_N": closure.maximum_force_residual_N,
            "maximum_moment_residual_Nm": closure.maximum_moment_residual_Nm,
            "failure_code": (
                closure.failure_code.value if closure.failure_code else None
            ),
            "message": closure.message,
        }
        if closure.resultant is not None:
            record["physical_closure"]["resultant_force_N"] = _vector(
                closure.resultant.resultant_force_N
            )
            record["physical_closure"]["resultant_moment_Nm"] = _vector(
                closure.resultant.resultant_moment_Nm
            )
    if result.road_contact is not None and result.road_contact.compatibility.roots:
        record["physical_points"] = {
            root.corner_id: {
                "contact_point_m": (
                    _vector(root.state.contact_road.position_m) if root.state else None
                ),
                "wheel_center_m": (
                    _vector(root.state.wheel_center_road.position_m)
                    if root.state
                    else None
                ),
            }
            for root in result.road_contact.compatibility.roots
        }
    return record


def _max_difference(left: Sequence[float], right: Sequence[float]) -> float:
    return max(abs(float(a) - float(b)) for a, b in zip(left, right))


def _compatible_unsprung_potential(provider, cache, q_body: Sequence[float]) -> float:
    evaluation = cache.evaluation(q_body)
    if not evaluation.ok:
        raise RuntimeError(evaluation.message)
    masses = {item.corner_id: item for item in provider.gravity.unsprung}
    total = 0.0
    for root in evaluation.compatibility.roots:
        if root.state is None or root.corner_id not in masses:
            raise RuntimeError("Compatible unsprung potential requires four current wheel centers")
        mass = masses[root.corner_id]
        total += (
            mass.mass_kg
            * provider.gravity.g_mps2
            * root.state.wheel_center_road.position_m[2]
        )
    return total


def _gravity_oracle(provider, q_body: Sequence[float]) -> dict:
    q = tuple(float(value) for value in q_body)
    cache = runtime._CompatibilityCache(provider)
    compatibility = cache.state(q)
    evaluation = cache.evaluation(q)
    pose = core._pose_from_q(provider, q)
    wheel_force = tuple(
        float(item.value) for item in evaluation.unsprung_gravity_forces
    )
    reduction = core.evaluate_wufr_unsprung_gravity_reduction(
        provider,
        pose,
        evaluation.compatibility,
        compatibility.J_wb,
        wheel_force,
    )
    finite_difference_sets: list[list[float]] = []
    for step in GRAVITY_ORACLE_STEPS:
        force: list[float] = []
        for axis in range(3):
            q_minus = list(q)
            q_plus = list(q)
            q_minus[axis] -= step
            q_plus[axis] += step
            force.append(
                -(
                    _compatible_unsprung_potential(provider, cache, q_plus)
                    - _compatible_unsprung_potential(provider, cache, q_minus)
                )
                / (2.0 * step)
            )
        finite_difference_sets.append(force)
    maximum_residual = max(
        abs(force[axis] - reduction.body_reduced_generalized_force[axis])
        for force in finite_difference_sets
        for axis in range(3)
    )
    convergence_difference = _max_difference(
        finite_difference_sets[0], finite_difference_sets[1]
    )
    return {
        "q_body": _vector(q),
        "gravity_reduction": _gravity_reduction_record(reduction),
        "finite_difference_steps": _vector(GRAVITY_ORACLE_STEPS),
        "finite_difference_generalized_force": finite_difference_sets,
        "maximum_absolute_residual": maximum_residual,
        "two_step_maximum_difference": convergence_difference,
        "tolerance": GRAVITY_ORACLE_TOLERANCE,
        "pass": maximum_residual <= GRAVITY_ORACLE_TOLERANCE,
    }


def _old_equation_negative_evidence(provider) -> dict:
    q = OLD_EQ_VEH_0016_PROBE_Q
    cache = runtime._CompatibilityCache(provider)
    compatibility = cache.state(q)
    evaluation = cache.evaluation(q)
    pose = core._pose_from_q(provider, q)
    wheel_gravity = tuple(
        float(item.value) for item in evaluation.unsprung_gravity_forces
    )
    reduction = core.evaluate_wufr_unsprung_gravity_reduction(
        provider,
        pose,
        evaluation.compatibility,
        compatibility.J_wb,
        wheel_gravity,
    )
    suspension = core.evaluate_wufr_suspension_composition(
        provider,
        evaluation.compatibility.wheel_coordinates_m,
        front_arb_setting=1,
        rear_arb_setting=1,
    )
    mapped_suspension = tuple(
        sum(
            compatibility.J_wb[corner][axis]
            * suspension.generalized_suspension_force_N[corner]
            for corner in range(4)
        )
        for axis in range(3)
    )
    old_residual = tuple(
        reduction.sprung_generalized_force[axis] + mapped_suspension[axis]
        for axis in range(3)
    )
    corrected_residual = tuple(
        reduction.total_body_external_generalized_force[axis]
        + mapped_suspension[axis]
        for axis in range(3)
    )
    suspension_state = SuspensionGeneralizedForceState(
        QuasiStaticStatus.SUCCESS,
        generalized_wheel_force=suspension.generalized_suspension_force_N,
        stored_energy_J=suspension.stored_energy_J,
        coordinate_order=core.CORNER_ORDER,
        coordinate_units=core.WHEEL_UNITS,
        source_id=provider.source.record_id,
        configuration_id=provider.source.configuration_id,
    )
    contact = recover_active_contact_normal_reactions(
        suspension_state,
        wheel_external_generalized_force=wheel_gravity,
        contact_coefficients=tuple(
            float(item.value) for item in evaluation.contact_coefficients
        ),
    )
    closure = core.evaluate_wufr_physical_closure(
        provider,
        pose,
        evaluation,
        contact,
    )
    if closure.resultant is None:
        raise RuntimeError(closure.message)
    physical_residual = (
        closure.resultant.resultant_force_N[2],
        closure.resultant.resultant_moment_Nm[0],
        closure.resultant.resultant_moment_Nm[1],
    )
    old_physical_mismatch = tuple(
        old_residual[axis] - physical_residual[axis] for axis in range(3)
    )
    corrected_physical_mismatch = tuple(
        corrected_residual[axis] - physical_residual[axis] for axis in range(3)
    )
    return {
        "q_body": _vector(q),
        "old_EQ_VEH_0016_residual": _vector(old_residual),
        "omitted_EQ_VEH_0018_reduction": _vector(
            reduction.body_reduced_generalized_force
        ),
        "corrected_EQ_VEH_0019_residual": _vector(corrected_residual),
        "independent_physical_residual": _vector(physical_residual),
        "old_equation_physical_mismatch": _vector(old_physical_mismatch),
        "corrected_equation_physical_mismatch": _vector(
            corrected_physical_mismatch
        ),
        "old_mismatch_inf_norm": max(abs(value) for value in old_physical_mismatch),
        "corrected_mismatch_inf_norm": max(
            abs(value) for value in corrected_physical_mismatch
        ),
        "physical_force_tolerance_N": provider.config.physical_force_residual_tolerance_N,
        "physical_moment_tolerance_Nm": (
            provider.config.physical_moment_residual_tolerance_Nm
        ),
        "old_equation_fails_physical_closure": (
            abs(old_physical_mismatch[0])
            > provider.config.physical_force_residual_tolerance_N
            or max(abs(value) for value in old_physical_mismatch[1:])
            > provider.config.physical_moment_residual_tolerance_Nm
        ),
        "corrected_equation_matches_physical_wrench": (
            abs(corrected_physical_mismatch[0])
            <= provider.config.physical_force_residual_tolerance_N
            and max(abs(value) for value in corrected_physical_mismatch[1:])
            <= provider.config.physical_moment_residual_tolerance_Nm
        ),
        "balancing_wrench_used": False,
    }


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
    gravity_oracles = {
        "nominal": _gravity_oracle(provider, (0.0, 0.0, 0.0)),
        "bounded_nonzero": _gravity_oracle(provider, OLD_EQ_VEH_0016_PROBE_Q),
    }
    negative_evidence = _old_equation_negative_evidence(provider)
    same_solution = (
        q_difference <= CONTINUATION_Q_TOLERANCE
        and reaction_difference <= CONTINUATION_REACTION_TOLERANCE_N
    )
    report = {
        "version": "0.2.0",
        "status": "pass",
        "model_id": "MOD-VEH-0007",
        "authorization_id": "AUTH-VEH-0010",
        "equation_ids": [
            "EQ-VEH-0015",
            "EQ-VEH-0017",
            "EQ-VEH-0018",
            "EQ-VEH-0019",
        ],
        "benchmark_ids": [
            "BENCH-VEH-0011",
            "BENCH-VEH-0012",
            "BENCH-VEH-0013",
            "BENCH-VEH-0014",
        ],
        "assumption_ids": [
            "ASM-VEH-0002",
            "ASM-VEH-0003",
            "ASM-VEH-0005",
            "ASM-SUSP-0002",
            "ASM-SUSP-0003",
        ],
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
            "coordinate_scales": _vector(
                provider.quasi_static_config.coordinate_scales
            ),
            "residual_scales": _vector(provider.quasi_static_config.residual_scales),
            "lower_bounds": list(provider.quasi_static_config.lower_bounds),
            "upper_bounds": list(provider.quasi_static_config.upper_bounds),
            "residual_absolute_tolerance": (
                provider.quasi_static_config.residual_absolute_tolerance
            ),
            "residual_relative_tolerance": (
                provider.quasi_static_config.residual_relative_tolerance
            ),
            "max_iterations": provider.quasi_static_config.max_iterations,
            "finite_difference_relative_step": (
                provider.quasi_static_config.finite_difference_relative_step
            ),
            "finite_difference_min_step": (
                provider.quasi_static_config.finite_difference_min_step
            ),
            "line_search_reduction": (
                provider.quasi_static_config.line_search_reduction
            ),
            "line_search_max_trials": (
                provider.quasi_static_config.line_search_max_trials
            ),
            "energy_gradient_step_multipliers": _vector(
                provider.config.energy_gradient_step_multipliers
            ),
            "energy_gradient_absolute_tolerance": (
                provider.config.energy_gradient_absolute_tolerance
            ),
            "physical_force_residual_tolerance_N": (
                provider.config.physical_force_residual_tolerance_N
            ),
            "physical_moment_residual_tolerance_Nm": (
                provider.config.physical_moment_residual_tolerance_Nm
            ),
            "wheel_equilibrium_residual_tolerance_N": (
                provider.config.wheel_equilibrium_residual_tolerance_N
            ),
        },
        "numerical_derivative_contract": {
            "road_compatibility": "implicit exact-root differentiation with shared g_z",
            "rocker_over_wheel": provider.rocker_derivative.coordinate_mode,
            "road_gap_tolerance_m": provider.road_contact.config.road_gap_tolerance_m,
            "wheel_coordinate_tolerance_m": (
                provider.road_contact.config.wheel_coordinate_tolerance_m
            ),
            "physical_q_L_tolerance_rad": (
                provider.road_contact.config.physical_q_L_tolerance_rad
            ),
            "physical_displacement_tolerance_m": (
                provider.road_contact.config.physical_displacement_tolerance_m
            ),
            "kinematics_root_angle_tolerance_rad": (
                provider.road_contact.config.kinematics_root_angle_tolerance_rad
            ),
            "kinematics_length_residual_tolerance_m": (
                provider.road_contact.config.kinematics_length_residual_tolerance_m
            ),
        },
        "primary": _result_record(primary),
        "alternate_initial_guess": _result_record(alternate),
        "continuation_comparison": {
            "maximum_q_body_difference": q_difference,
            "q_body_tolerance": CONTINUATION_Q_TOLERANCE,
            "maximum_normal_reaction_difference_N": reaction_difference,
            "normal_reaction_tolerance_N": CONTINUATION_REACTION_TOLERANCE_N,
            "same_continuation_solution": same_solution,
        },
        "gravity_reduction_oracles": gravity_oracles,
        "old_equation_negative_evidence": negative_evidence,
        "invalid_setting_failure": _result_record(invalid),
        "boundaries": {
            "historical_scale_fit": False,
            "installed_as_built_authority": False,
            "physical_correlation_authority": False,
            "arb_setup_selection_authority": False,
            "carrier_wrench_authority": False,
            "structural_load_case_authority": False,
            "maneuver_qss_authority": False,
            "balancing_wrench_used": False,
            "old_equation_fallback": False,
        },
    }
    checks = (
        primary.ok,
        alternate.ok,
        same_solution,
        not invalid.ok and invalid.failure_code is not None,
        all(item["pass"] for item in gravity_oracles.values()),
        negative_evidence["old_equation_fails_physical_closure"],
        negative_evidence["corrected_equation_matches_physical_wrench"],
    )
    if not all(checks):
        report["status"] = "fail"
    return report


def validate_report(report: dict) -> None:
    if report["status"] != "pass":
        raise RuntimeError(json.dumps(report, indent=2, sort_keys=True))


def build_summary(report: dict) -> dict:
    primary = report["primary"]
    return {
        "status": report["status"],
        "ok": primary["ok"],
        "result_label": primary["result_label"],
        "q_body": primary.get("solve", {}).get("q_body"),
        "normal_reaction_N": primary.get("contact", {}).get("normal_reaction_N"),
        "scaled_residual_norm": primary.get("solve", {}).get(
            "scaled_residual_norm"
        ),
        "energy_gradient_max_residual": primary.get("energy_gradient", {}).get(
            "maximum_absolute_residual"
        ),
        "physical_force_residual_N": primary.get("physical_closure", {}).get(
            "maximum_force_residual_N"
        ),
        "physical_moment_residual_Nm": primary.get("physical_closure", {}).get(
            "maximum_moment_residual_Nm"
        ),
        "maximum_q_body_restart_difference": report["continuation_comparison"][
            "maximum_q_body_difference"
        ],
        "maximum_reaction_restart_difference_N": report["continuation_comparison"][
            "maximum_normal_reaction_difference_N"
        ],
        "gravity_oracle_max_residual": max(
            item["maximum_absolute_residual"]
            for item in report["gravity_reduction_oracles"].values()
        ),
        "old_equation_physical_mismatch": report["old_equation_negative_evidence"][
            "old_mismatch_inf_norm"
        ],
        "corrected_equation_physical_mismatch": report[
            "old_equation_negative_evidence"
        ]["corrected_mismatch_inf_norm"],
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
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.summary:
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif not args.output and not args.summary_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    validate_report(report)


if __name__ == "__main__":
    main()
