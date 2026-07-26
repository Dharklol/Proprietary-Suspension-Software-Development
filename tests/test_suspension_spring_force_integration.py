from __future__ import annotations

import math
from pathlib import Path
import unittest

from pssd_suspension import (
    ActuationSolverConfig,
    PhysicalStateSolverConfig,
    build_nominal_wheel_reference,
    evaluate_spring_from_actuation,
    load_optimumk_geometry_snapshot,
    load_wufr26_wheel_reference_profile,
    load_wufr27_spring_package,
    solve_actuation_q_L_state,
    solve_body_vertical_actuation_state,
)


ROOT = Path(__file__).resolve().parents[1]


class SuspensionSpringForceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.geometry = load_optimumk_geometry_snapshot(
            ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
        )
        cls.wheel_profile = load_wufr26_wheel_reference_profile(
            ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml"
        )
        cls.spring_package = load_wufr27_spring_package(
            ROOT / "data_catalog/wufr27_spring_package_v0.toml"
        )

    def test_nominal_actuation_lengths_feed_spring_provider_without_scalar_motion_ratio(self) -> None:
        for axle, expected_length_m, expected_force_N in (
            ("front", 0.164600, 759.6000000000003),
            ("rear", 0.164611, 656.0776800526314),
        ):
            corner = self.geometry.corner(axle, "left")
            nominal = build_nominal_wheel_reference(self.wheel_profile, axle, "left")
            actuation = solve_actuation_q_L_state(
                corner,
                nominal,
                0.0,
                geometry_id=self.geometry.geometry_id,
                source_authority=self.geometry.authority,
            )
            self.assertTrue(actuation.ok, actuation.message)
            self.assertAlmostEqual(actuation.current_coilover_length_m, expected_length_m, places=6)

            spring = self.spring_package.front if axle == "front" else self.spring_package.rear
            result = evaluate_spring_from_actuation(
                spring,
                self.spring_package.reference,
                actuation,
                use_local_rho_dw_when_available=False,
            )
            self.assertTrue(result.ok, result.message)
            self.assertAlmostEqual(result.force_N, expected_force_N, places=6)
            self.assertFalse(result.generalized_force_available)
            self.assertFalse(result.installed_as_built_authority)
            self.assertIn("ASM-SUSP-0002", result.assumption_ids)

    def test_physical_wheel_coordinate_composes_signed_rho_into_spring_force(self) -> None:
        corner = self.geometry.corner("front", "left")
        nominal = build_nominal_wheel_reference(self.wheel_profile, "front", "left")
        physical = PhysicalStateSolverConfig(
            q_L_min_rad=math.radians(-4.0),
            q_L_max_rad=math.radians(4.0),
            scan_intervals_per_side=30,
            q_L_tolerance_rad=2.0e-9,
            displacement_tolerance_m=2.0e-9,
        )
        actuation = solve_body_vertical_actuation_state(
            corner,
            nominal,
            0.0,
            physical,
            actuation_config=ActuationSolverConfig(derivative_step_m=1.0e-4),
            geometry_id=self.geometry.geometry_id,
            source_authority=self.geometry.authority,
        )
        self.assertTrue(actuation.ok, actuation.message)
        self.assertIsNotNone(actuation.rho_dw)
        self.assertLess(float(actuation.rho_dw), 0.0)

        result = evaluate_spring_from_actuation(
            self.spring_package.front,
            self.spring_package.reference,
            actuation,
        )
        self.assertTrue(result.ok, result.message)
        self.assertTrue(result.generalized_force_available)
        self.assertEqual(result.coordinate_order, ("delta_z_wc_body_m",))
        self.assertEqual(result.coordinate_units, ("m",))
        self.assertAlmostEqual(
            result.generalized_force[0],
            float(result.force_N) * float(actuation.rho_dw),
            places=9,
        )
        self.assertLess(result.generalized_force[0], 0.0)


if __name__ == "__main__":
    unittest.main()
