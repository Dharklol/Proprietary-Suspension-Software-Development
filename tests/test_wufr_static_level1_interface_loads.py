from __future__ import annotations

import unittest

from scripts.run_wufr_static_level1_interface_load_benchmarks import provider
from pssd_suspension.wufr_static_level1_interface_loads import (
    CORNER_ORDER,
    RESULT_LABEL,
    evaluate_wufr_static_level1_interface_loads,
)


class WufrStaticLevel1InterfaceLoadsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = evaluate_wufr_static_level1_interface_loads(provider())

    def test_four_corner_static_level1_composition_succeeds_atomically(self) -> None:
        result = self.result
        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.result_label, RESULT_LABEL)
        self.assertEqual(tuple(c.corner_id for c in result.corners), CORNER_ORDER)
        self.assertTrue(result.complete_for_authorized_static_gravity_case)
        self.assertFalse(result.complete_physical_vehicle_load_case)
        self.assertFalse(result.maneuver_complete)
        self.assertFalse(result.rocker_result_publication_authorized)
        self.assertFalse(result.installed_as_built_authority)

    def test_frozen_signed_lateral_and_actuation_forces(self) -> None:
        expected_lateral = (
            14.593622421729782,
            14.38492391983325,
            -1.7576884629764493,
            -1.6908855705296213,
        )
        expected_actuation = (
            2620.7597222455165,
            2579.8086149239616,
            -1125.2623993423208,
            -1092.2991277987778,
        )
        for corner, lateral, actuation in zip(self.result.corners, expected_lateral, expected_actuation):
            self.assertIsNotNone(corner.solve.lateral)
            self.assertIsNotNone(corner.solve.actuation)
            assert corner.solve.lateral and corner.solve.actuation
            self.assertAlmostEqual(corner.solve.lateral.axial_force_N, lateral, delta=1.0e-9)
            self.assertAlmostEqual(corner.solve.actuation.axial_force_N, actuation, delta=1.0e-8)

    def test_exact_current_reference_and_steering_ownership_are_preserved(self) -> None:
        for corner in self.result.corners:
            self.assertEqual(corner.geometry.frame_id, corner.carrier_wrench.frame_id)
            self.assertEqual(corner.geometry.carrier_reference_m, corner.carrier_wrench.reference_point_m)
            self.assertEqual(corner.geometry.configuration_id, self.result.configuration_id)
            self.assertEqual(corner.geometry.geometry_source_id, "WUFR27_LEVEL1_LINKAGE_TOPOLOGY_V0")
        for corner in self.result.corners[:2]:
            self.assertIsNotNone(corner.steering_source_id)
            self.assertTrue(corner.steering_source_id.startswith("MOD-STEER-0001:"))
        for corner in self.result.corners[2:]:
            self.assertIsNone(corner.steering_source_id)
            self.assertEqual(corner.geometry.lateral_source_id, "MOD-SUSP-0001:rear_toe_link_current")

    def test_action_reaction_and_physical_residuals_close(self) -> None:
        for corner in self.result.corners:
            for spherical in (corner.solve.upper_spherical, corner.solve.lower_spherical):
                self.assertIsNotNone(spherical)
                assert spherical
                for a, b in zip(spherical.force_on_carrier_N, spherical.force_on_arm_N):
                    self.assertAlmostEqual(a + b, 0.0, delta=1.0e-12)
            for axial in (corner.solve.lateral, corner.solve.actuation):
                self.assertIsNotNone(axial)
                assert axial
                for a, b in zip(axial.force_on_body_N, axial.force_on_remote_N):
                    self.assertAlmostEqual(a + b, 0.0, delta=1.0e-12)
            for residual in corner.solve.body_residuals:
                self.assertLessEqual(residual.force_inf_norm_N, 1.0e-9)
                self.assertLessEqual(residual.moment_inf_norm_Nm, 1.0e-9)


if __name__ == "__main__":
    unittest.main()
