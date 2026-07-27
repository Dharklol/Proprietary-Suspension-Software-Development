from __future__ import annotations

import math
import unittest

from pssd_vehicle.quasi_static import (
    BodyExternalGeneralizedForceState,
    CompatibilityState,
    QuasiStaticFailureCode,
    QuasiStaticSolverConfig,
    QuasiStaticStatus,
    SuspensionGeneralizedForceState,
    check_total_potential_gradient,
    evaluate_quasi_static_residual,
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


def config(**overrides: object) -> QuasiStaticSolverConfig:
    values: dict[str, object] = {
        "coordinate_scales": (0.05, 0.1, 0.1),
        "residual_scales": (1000.0, 500.0, 500.0),
        "residual_absolute_tolerance": 1.0e-10,
        "residual_relative_tolerance": 1.0e-10,
        "max_iterations": 20,
    }
    values.update(overrides)
    return QuasiStaticSolverConfig(**values)  # type: ignore[arg-type]


class VehicleQuasiStaticTests(unittest.TestCase):
    def test_symmetric_analytical_equilibrium_and_contact_recovery(self) -> None:
        result = solve_quasi_static_equilibrium(
            (0.0, 0.0, 0.0),
            body_coordinate_order=BODY_ORDER,
            body_coordinate_units=BODY_UNITS,
            compatibility_provider=compatibility,
            suspension_provider=suspension,
            body_external_provider=body_external,
            config=config(),
        )
        self.assertTrue(result.ok, result.message)
        self.assertAlmostEqual(result.q_body[0], -0.024525, places=10)
        self.assertAlmostEqual(result.q_body[1], 0.0, places=10)
        self.assertAlmostEqual(result.q_body[2], 0.0, places=10)
        self.assertLess(result.scaled_residual_norm or 1.0, 1.0e-9)
        self.assertGreater(result.reciprocal_pivot_ratio or 0.0, 1.0e-8)

        z = compatibility(result.q_body)
        spring = suspension(z.wheel_coordinates)
        for value in z.wheel_coordinates:
            self.assertAlmostEqual(value, 0.024525, places=10)
        for value in spring.generalized_wheel_force:
            self.assertAlmostEqual(value, -245.25, places=8)

        contact = recover_active_contact_normal_reactions(
            spring,
            wheel_external_generalized_force=(-49.05, -49.05, -49.05, -49.05),
            contact_coefficients=(1.0, 1.0, 1.0, 1.0),
        )
        self.assertTrue(contact.ok, contact.message)
        for reaction in contact.normal_reaction_N:
            self.assertAlmostEqual(reaction, 294.30, places=8)
        self.assertAlmostEqual(sum(contact.normal_reaction_N), 1177.20, places=8)
        self.assertTrue(all(abs(value) <= 1.0e-12 for value in contact.wheel_equilibrium_residual))

    def test_solution_is_repeatable_from_two_bounded_guesses(self) -> None:
        guesses = ((0.0, 0.0, 0.0), (-0.015, 0.004, -0.003))
        solutions = []
        for guess in guesses:
            result = solve_quasi_static_equilibrium(
                guess,
                body_coordinate_order=BODY_ORDER,
                body_coordinate_units=BODY_UNITS,
                compatibility_provider=compatibility,
                suspension_provider=suspension,
                body_external_provider=body_external,
                config=config(),
            )
            self.assertTrue(result.ok, result.message)
            solutions.append(result.q_body)
        for a, b in zip(solutions[0], solutions[1]):
            self.assertAlmostEqual(a, b, places=9)

    def test_total_potential_gradient_matches_assembled_generalized_force(self) -> None:
        q = (-0.012, 0.006, -0.004)
        check = check_total_potential_gradient(
            q,
            body_coordinate_order=BODY_ORDER,
            body_coordinate_units=BODY_UNITS,
            compatibility_provider=compatibility,
            suspension_provider=suspension,
            body_external_provider=body_external,
            config=config(),
            relative_step_multipliers=(1.0e-5, 5.0e-6),
            absolute_tolerance=1.0e-6,
        )
        self.assertTrue(check.ok, check.message)
        self.assertEqual(len(check.finite_difference_generalized_force), 2)
        self.assertLess(check.maximum_absolute_residual or 1.0, 1.0e-6)

    def test_missing_wheel_external_force_never_defaults_to_zero(self) -> None:
        spring = suspension((0.01, 0.01, 0.01, 0.01))
        contact = recover_active_contact_normal_reactions(
            spring,
            wheel_external_generalized_force=None,
            contact_coefficients=(1.0, 1.0, 1.0, 1.0),
        )
        self.assertFalse(contact.ok)
        self.assertEqual(
            contact.failure_code,
            QuasiStaticFailureCode.MISSING_WHEEL_EXTERNAL_FORCE_AUTHORITY,
        )
        self.assertEqual(contact.normal_reaction_N, ())

    def test_negative_reaction_is_preserved_and_flagged(self) -> None:
        state = SuspensionGeneralizedForceState(
            QuasiStaticStatus.SUCCESS,
            generalized_wheel_force=(10.0, -10.0, -10.0, -10.0),
            stored_energy_J=0.0,
            coordinate_order=WHEEL_ORDER,
            coordinate_units=WHEEL_UNITS,
            source_id="synthetic-negative-reaction",
        )
        contact = recover_active_contact_normal_reactions(
            state,
            wheel_external_generalized_force=(0.0, 0.0, 0.0, 0.0),
            contact_coefficients=(1.0, 1.0, 1.0, 1.0),
        )
        self.assertFalse(contact.ok)
        self.assertEqual(contact.failure_code, QuasiStaticFailureCode.NEGATIVE_NORMAL_REACTION)
        self.assertEqual(contact.normal_reaction_N[0], -10.0)
        self.assertEqual(contact.normal_reaction_N[1:], (10.0, 10.0, 10.0))

    def test_singular_compatibility_returns_explicit_tangent_failure(self) -> None:
        def singular_compatibility(q: tuple[float, ...]) -> CompatibilityState:
            z = (-q[0],) * 4
            return CompatibilityState(
                QuasiStaticStatus.SUCCESS,
                wheel_coordinates=z,
                J_wb=((-1.0, 0.0, 0.0),) * 4,
                wheel_coordinate_order=WHEEL_ORDER,
                wheel_coordinate_units=WHEEL_UNITS,
                source_id="singular-synthetic",
            )

        result = solve_quasi_static_equilibrium(
            (0.0, 0.0, 0.0),
            body_coordinate_order=BODY_ORDER,
            body_coordinate_units=BODY_UNITS,
            compatibility_provider=singular_compatibility,
            suspension_provider=suspension,
            body_external_provider=body_external,
            config=config(),
        )
        self.assertFalse(result.ok)
        self.assertEqual(
            result.failure_code,
            QuasiStaticFailureCode.SINGULAR_OR_ILL_CONDITIONED_TANGENT,
        )

    def test_unreachable_equilibrium_does_not_clip_to_coordinate_bound(self) -> None:
        bounded = config(
            lower_bounds=(-0.010, -0.05, -0.05),
            upper_bounds=(0.010, 0.05, 0.05),
        )
        result = solve_quasi_static_equilibrium(
            (0.0, 0.0, 0.0),
            body_coordinate_order=BODY_ORDER,
            body_coordinate_units=BODY_UNITS,
            compatibility_provider=compatibility,
            suspension_provider=suspension,
            body_external_provider=body_external,
            config=bounded,
        )
        self.assertFalse(result.ok)
        self.assertIn(
            result.failure_code,
            {
                QuasiStaticFailureCode.LINE_SEARCH_FAILURE,
                QuasiStaticFailureCode.COORDINATE_BOUND_EXCEEDED,
                QuasiStaticFailureCode.NONCONVERGENCE,
            },
        )
        self.assertGreaterEqual(result.q_body[0], -0.010)
        self.assertLessEqual(result.q_body[0], 0.010)

    def test_coordinate_order_mismatch_is_rejected(self) -> None:
        def wrong_suspension(z: tuple[float, ...]) -> SuspensionGeneralizedForceState:
            return SuspensionGeneralizedForceState(
                QuasiStaticStatus.SUCCESS,
                generalized_wheel_force=tuple(-K * value for value in z),
                stored_energy_J=0.5 * K * sum(value * value for value in z),
                coordinate_order=("wrong",) * 4,
                coordinate_units=WHEEL_UNITS,
                source_id="wrong-order",
            )

        evaluation = evaluate_quasi_static_residual(
            (0.0, 0.0, 0.0),
            body_coordinate_order=BODY_ORDER,
            body_coordinate_units=BODY_UNITS,
            compatibility_provider=compatibility,
            suspension_provider=wrong_suspension,
            body_external_provider=body_external,
            residual_scales=config().residual_scales,
        )
        self.assertFalse(evaluation.ok)
        self.assertEqual(
            evaluation.failure_code,
            QuasiStaticFailureCode.COORDINATE_CONTRACT_MISMATCH,
        )

    def test_result_contains_no_wufr_mass_default_path(self) -> None:
        result = solve_quasi_static_equilibrium(
            (0.0, 0.0, 0.0),
            body_coordinate_order=BODY_ORDER,
            body_coordinate_units=BODY_UNITS,
            compatibility_provider=compatibility,
            suspension_provider=suspension,
            body_external_provider=body_external,
            config=config(),
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.compatibility_source_id, "BENCH-VEH-0005-compatibility")
        self.assertEqual(result.suspension_source_id, "BENCH-VEH-0005-springs")
        self.assertEqual(result.body_external_source_id, "BENCH-VEH-0005-gravity")
        self.assertTrue(math.isfinite(result.suspension_stored_energy_J or 0.0))


if __name__ == "__main__":
    unittest.main()
