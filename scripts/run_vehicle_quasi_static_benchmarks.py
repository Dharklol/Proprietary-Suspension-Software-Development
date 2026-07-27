#!/usr/bin/env python3
"""Generate BENCH-VEH-0005/0006 quasi-static equilibrium diagnostics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pssd_vehicle.quasi_static import (
    BodyExternalGeneralizedForceState,
    CompatibilityState,
    QuasiStaticFailureCode,
    QuasiStaticSolverConfig,
    QuasiStaticStatus,
    SuspensionGeneralizedForceState,
    check_total_potential_gradient,
    recover_active_contact_normal_reactions,
    solve_quasi_static_equilibrium,
)


BODY_ORDER = ("z_s_m", "phi_rad", "theta_rad")
BODY_UNITS = ("m", "rad", "rad")
WHEEL_ORDER = ("front_left", "front_right", "rear_left", "rear_right")
WHEEL_UNITS = ("m", "m", "m", "m")
POSITIONS = (
    (0.75, 0.50),
    (0.75, -0.50),
    (-0.75, 0.50),
    (-0.75, -0.50),
)
K = 10000.0
G = 9.81
SPRUNG_MASS = 100.0


def compatibility(q: tuple[float, ...]) -> CompatibilityState:
    z_s, phi, theta = q
    rows = tuple((-1.0, -y, x) for x, y in POSITIONS)
    z = tuple(-z_s - y * phi + x * theta for x, y in POSITIONS)
    return CompatibilityState(
        QuasiStaticStatus.SUCCESS,
        wheel_coordinates=z,
        J_wb=rows,
        wheel_coordinate_order=WHEEL_ORDER,
        wheel_coordinate_units=WHEEL_UNITS,
        source_id="BENCH-VEH-0005-compatibility",
        configuration_id="SYNTHETIC",
    )


def suspension(z: tuple[float, ...]) -> SuspensionGeneralizedForceState:
    return SuspensionGeneralizedForceState(
        QuasiStaticStatus.SUCCESS,
        generalized_wheel_force=tuple(-K * value for value in z),
        stored_energy_J=0.5 * K * sum(value * value for value in z),
        coordinate_order=WHEEL_ORDER,
        coordinate_units=WHEEL_UNITS,
        source_id="BENCH-VEH-0005-springs",
        configuration_id="SYNTHETIC",
    )


def body_external(q: tuple[float, ...]) -> BodyExternalGeneralizedForceState:
    return BodyExternalGeneralizedForceState(
        QuasiStaticStatus.SUCCESS,
        generalized_force=(-SPRUNG_MASS * G, 0.0, 0.0),
        potential_energy_J=SPRUNG_MASS * G * q[0],
        coordinate_order=BODY_ORDER,
        coordinate_units=BODY_UNITS,
        source_id="BENCH-VEH-0005-gravity",
        configuration_id="SYNTHETIC",
    )


def solver_config(**overrides: object) -> QuasiStaticSolverConfig:
    values: dict[str, object] = {
        "coordinate_scales": (0.05, 0.1, 0.1),
        "residual_scales": (1000.0, 500.0, 500.0),
        "residual_absolute_tolerance": 1.0e-10,
        "residual_relative_tolerance": 1.0e-10,
        "max_iterations": 20,
    }
    values.update(overrides)
    return QuasiStaticSolverConfig(**values)  # type: ignore[arg-type]


def bench_0005() -> dict:
    solve = solve_quasi_static_equilibrium(
        (0.0, 0.0, 0.0),
        body_coordinate_order=BODY_ORDER,
        body_coordinate_units=BODY_UNITS,
        compatibility_provider=compatibility,
        suspension_provider=suspension,
        body_external_provider=body_external,
        config=solver_config(),
    )
    if not solve.ok:
        raise RuntimeError(f"BENCH-VEH-0005 equilibrium failed: {solve.failure_code}: {solve.message}")
    wheel = compatibility(solve.q_body)
    spring = suspension(wheel.wheel_coordinates)
    contact = recover_active_contact_normal_reactions(
        spring,
        wheel_external_generalized_force=(-49.05, -49.05, -49.05, -49.05),
        contact_coefficients=(1.0, 1.0, 1.0, 1.0),
    )
    if not contact.ok:
        raise RuntimeError(f"BENCH-VEH-0005 contact recovery failed: {contact.failure_code}: {contact.message}")
    gradient = check_total_potential_gradient(
        (-0.012, 0.006, -0.004),
        body_coordinate_order=BODY_ORDER,
        body_coordinate_units=BODY_UNITS,
        compatibility_provider=compatibility,
        suspension_provider=suspension,
        body_external_provider=body_external,
        config=solver_config(),
        relative_step_multipliers=(1.0e-5, 5.0e-6),
        absolute_tolerance=1.0e-6,
    )
    if not gradient.ok:
        raise RuntimeError(f"BENCH-VEH-0005 energy check failed: {gradient.failure_code}: {gradient.message}")

    analytical_q = (-0.024525, 0.0, 0.0)
    max_q_error = max(abs(a - b) for a, b in zip(solve.q_body, analytical_q))
    max_wheel_error = max(abs(value - 0.024525) for value in wheel.wheel_coordinates)
    max_spring_force_error = max(abs(value + 245.25) for value in spring.generalized_wheel_force)
    max_reaction_error = max(abs(value - 294.30) for value in contact.normal_reaction_N)
    total_reaction_error = abs(sum(contact.normal_reaction_N) - 1177.20)
    passed = (
        max_q_error <= 1.0e-9
        and max_wheel_error <= 1.0e-9
        and max_spring_force_error <= 1.0e-7
        and max_reaction_error <= 1.0e-7
        and total_reaction_error <= 1.0e-7
        and (solve.scaled_residual_norm or 1.0) <= 1.0e-8
        and (gradient.maximum_absolute_residual or 1.0) <= 1.0e-6
    )
    return {
        "synthetic_only": True,
        "sprung_mass_kg": SPRUNG_MASS,
        "synthetic_wheel_side_mass_kg_per_corner": 5.0,
        "gravity_m_per_s2": G,
        "support_stiffness_N_per_m": K,
        "body_solution": list(solve.q_body),
        "analytical_body_solution": list(analytical_q),
        "max_body_coordinate_error": max_q_error,
        "wheel_coordinates_m": list(wheel.wheel_coordinates),
        "max_wheel_coordinate_error_m": max_wheel_error,
        "suspension_generalized_force_N": list(spring.generalized_wheel_force),
        "max_suspension_force_error_N": max_spring_force_error,
        "normal_reaction_N": list(contact.normal_reaction_N),
        "normal_reaction_sum_N": sum(contact.normal_reaction_N),
        "max_reaction_error_N": max_reaction_error,
        "total_reaction_error_N": total_reaction_error,
        "iterations": solve.iterations,
        "scaled_residual_norm": solve.scaled_residual_norm,
        "reciprocal_pivot_ratio": solve.reciprocal_pivot_ratio,
        "energy_gradient_max_residual": gradient.maximum_absolute_residual,
        "energy_gradient_steps": list(gradient.relative_step_multipliers),
        "pass": passed,
    }


def bench_0006() -> dict:
    first = solve_quasi_static_equilibrium(
        (0.0, 0.0, 0.0),
        body_coordinate_order=BODY_ORDER,
        body_coordinate_units=BODY_UNITS,
        compatibility_provider=compatibility,
        suspension_provider=suspension,
        body_external_provider=body_external,
        config=solver_config(),
    )
    second = solve_quasi_static_equilibrium(
        (-0.015, 0.004, -0.003),
        body_coordinate_order=BODY_ORDER,
        body_coordinate_units=BODY_UNITS,
        compatibility_provider=compatibility,
        suspension_provider=suspension,
        body_external_provider=body_external,
        config=solver_config(),
    )

    def singular_compatibility(q: tuple[float, ...]) -> CompatibilityState:
        return CompatibilityState(
            QuasiStaticStatus.SUCCESS,
            wheel_coordinates=(-q[0],) * 4,
            J_wb=((-1.0, 0.0, 0.0),) * 4,
            wheel_coordinate_order=WHEEL_ORDER,
            wheel_coordinate_units=WHEEL_UNITS,
            source_id="BENCH-VEH-0006-singular",
            configuration_id="SYNTHETIC",
        )

    singular = solve_quasi_static_equilibrium(
        (0.0, 0.0, 0.0),
        body_coordinate_order=BODY_ORDER,
        body_coordinate_units=BODY_UNITS,
        compatibility_provider=singular_compatibility,
        suspension_provider=suspension,
        body_external_provider=body_external,
        config=solver_config(),
    )
    bounded = solve_quasi_static_equilibrium(
        (0.0, 0.0, 0.0),
        body_coordinate_order=BODY_ORDER,
        body_coordinate_units=BODY_UNITS,
        compatibility_provider=compatibility,
        suspension_provider=suspension,
        body_external_provider=body_external,
        config=solver_config(
            lower_bounds=(-0.010, -0.05, -0.05),
            upper_bounds=(0.010, 0.05, 0.05),
        ),
    )
    missing_external = recover_active_contact_normal_reactions(
        suspension((0.01, 0.01, 0.01, 0.01)),
        wheel_external_generalized_force=None,
        contact_coefficients=(1.0, 1.0, 1.0, 1.0),
    )
    negative_state = SuspensionGeneralizedForceState(
        QuasiStaticStatus.SUCCESS,
        generalized_wheel_force=(10.0, -10.0, -10.0, -10.0),
        stored_energy_J=0.0,
        coordinate_order=WHEEL_ORDER,
        coordinate_units=WHEEL_UNITS,
        source_id="BENCH-VEH-0006-negative-reaction",
        configuration_id="SYNTHETIC",
    )
    negative = recover_active_contact_normal_reactions(
        negative_state,
        wheel_external_generalized_force=(0.0, 0.0, 0.0, 0.0),
        contact_coefficients=(1.0, 1.0, 1.0, 1.0),
    )

    repeatability = max(abs(a - b) for a, b in zip(first.q_body, second.q_body))
    passed = (
        first.ok
        and second.ok
        and repeatability <= 1.0e-9
        and singular.failure_code is QuasiStaticFailureCode.SINGULAR_OR_ILL_CONDITIONED_TANGENT
        and not bounded.ok
        and missing_external.failure_code is QuasiStaticFailureCode.MISSING_WHEEL_EXTERNAL_FORCE_AUTHORITY
        and negative.failure_code is QuasiStaticFailureCode.NEGATIVE_NORMAL_REACTION
        and negative.normal_reaction_N[0] == -10.0
    )
    return {
        "repeatability_max_coordinate_difference": repeatability,
        "singular_failure": singular.failure_code.value if singular.failure_code else None,
        "bounded_failure": bounded.failure_code.value if bounded.failure_code else None,
        "bounded_final_q": list(bounded.q_body),
        "missing_wheel_external_force_failure": (
            missing_external.failure_code.value if missing_external.failure_code else None
        ),
        "negative_reaction_failure": negative.failure_code.value if negative.failure_code else None,
        "negative_reaction_preserved_N": list(negative.normal_reaction_N),
        "hidden_wufr_mass_default_used": False,
        "pass": passed,
    }


def build_report() -> dict:
    b5 = bench_0005()
    b6 = bench_0006()
    if not b5["pass"] or not b6["pass"]:
        raise RuntimeError("Vehicle quasi-static benchmark acceptance failed")
    return {
        "model_id": "MOD-VEH-0004",
        "authorization_id": "AUTH-VEH-0004",
        "authority": (
            "provider-neutral synthetic software verification only; no WUFR mass/gravity or "
            "road-reaction authority"
        ),
        "BENCH-VEH-0005": b5,
        "BENCH-VEH-0006": b6,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("vehicle_quasi_static_report.json"),
    )
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        b5 = report["BENCH-VEH-0005"]
        b6 = report["BENCH-VEH-0006"]
        print(
            "MOD-VEH-0004: "
            f"z_s={b5['body_solution'][0]:.9g} m, "
            f"reaction={b5['normal_reaction_N'][0]:.9g} N/corner, "
            f"energy_error={b5['energy_gradient_max_residual']:.3g}, "
            f"singular={b6['singular_failure']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
