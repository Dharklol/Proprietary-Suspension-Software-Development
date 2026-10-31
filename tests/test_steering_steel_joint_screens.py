"""Sensitivity and unit regression tests for non-released steering steel screens."""
import math
import unittest

from pssd_steering.steel_joint_screens import (
    ClevisPinBendingScreen, LugScreen, WeldRingScreen,
    required_shear_endurance_mpa,
)


class SteelJointScreenTests(unittest.TestCase):
    def test_tube_and_weld_mean_radius(self):
        w = WeldRingScreen()
        self.assertAlmostEqual(w.wall_thickness_m / .0254, .0625)
        self.assertAlmostEqual(w.mean_radius_m / .0254, .34375)
        self.assertAlmostEqual(w.shear_flow_n_per_mm(35.54700928), 74.21135, places=3)
        self.assertAlmostEqual(w.full_wall_line_shear_mpa(35.54700928),
                               46.7473, places=3)
        self.assertAlmostEqual(w.required_throat_mm(35.54700928, 40),
                               1.85528, places=3)
        self.assertAlmostEqual(w.required_throat_mm(35.54700928, 75),
                               .98948, places=3)
        self.assertAlmostEqual(w.shear_flow_n_per_mm(-14.44408009),
                               w.shear_flow_n_per_mm(14.44408009))
        self.assertAlmostEqual(w.shear_mpa(10, 2),
                               w.shear_mpa(10, 1)/2)

    def test_pin_bending_is_span_sensitive_and_below_simple_shear(self):
        pin = ClevisPinBendingScreen()
        self.assertAlmostEqual(pin.point_load_capacity_n(.25), 122.68, delta=.1)
        self.assertAlmostEqual(pin.point_load_capacity_n(.5), 61.34, delta=.1)
        self.assertAlmostEqual(pin.point_load_capacity_n(.25),
                               2 * pin.point_load_capacity_n(.5))
        self.assertAlmostEqual(pin.uniform_center_load_capacity_n(.472, .094),
                               pin.point_load_capacity_n(.330), places=7)

    def test_lug_capacity_only_if_true_steel_ligament(self):
        lug = LugScreen()
        self.assertAlmostEqual(lug.net_section_allowable_n(), 725, delta=2)
        self.assertAlmostEqual(lug.shear_out_allowable_n(.367), 1457, delta=3)
        self.assertAlmostEqual(lug.shear_out_allowable_n(.687), 2988, delta=3)
        self.assertLess(lug.shear_out_allowable_n(.125),
                        lug.shear_out_allowable_n(.367))

    def test_required_fatigue_property_not_claimed_available(self):
        self.assertAlmostEqual(
            required_shear_endurance_mpa(33.1,
               fatigue_notch_factor=2,
               required_fatigue_safety_factor=2), 132.4
        )
        self.assertAlmostEqual(
            required_shear_endurance_mpa(54.3,
               fatigue_notch_factor=1.5,
               required_fatigue_safety_factor=2), 162.9
        )

    def test_input_validation(self):
        with self.assertRaises(ValueError):
            WeldRingScreen(.5, .5)
        with self.assertRaises(ValueError):
            WeldRingScreen().shear_flow_n_per_mm(math.nan)
        with self.assertRaises(ValueError):
            WeldRingScreen().required_throat_mm(35, 0)
        with self.assertRaises(ValueError):
            ClevisPinBendingScreen().point_load_capacity_n(0)
        with self.assertRaises(ValueError):
            LugScreen().shear_out_allowable_n(.05)
        with self.assertRaises(ValueError):
            required_shear_endurance_mpa(5, fatigue_notch_factor=0,
                                           required_fatigue_safety_factor=2)


if __name__ == "__main__":
    unittest.main()
