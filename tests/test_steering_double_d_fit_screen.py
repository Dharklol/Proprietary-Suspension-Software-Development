"""Double-D fit screen exact geometry regression and boundary checks."""
import math
import unittest
from pssd_steering.double_d_fit_screen import IdealDoubleDFit


class DoubleDContactScreens(unittest.TestCase):
    def setUp(self):
        self.d=IdealDoubleDFit()

    def test_nominal_dims(self):
        self.assertAlmostEqual(self.d.half_chord_in,.177,places=12)
        self.assertAlmostEqual(self.d.flat_depth_in,.059,places=12)

    def test_exact_coaxial_geometric_play(self):
        expected=((.0005,.162005),(.001,.324317),(.0015,.486938),
                  (.002,.649870),(.005,1.634115),(.010,3.300891))
        for c,play in expected:
            with self.subTest(clearance=c):
                self.assertAlmostEqual(self.d.bidirectional_ideal_play_deg(c),
                                       play,delta=.00001)
                self.assertAlmostEqual(
                    2*self.d.one_sided_ideal_rotation_deg(c),play,delta=.00001)
        self.assertEqual(self.d.bidirectional_ideal_play_deg(0),0.0)

    def test_inverse_clearance_budget(self):
        for budget in (.15,.25,.5,1,2):
            c=self.d.max_clearance_for_bidirectional_play_in(budget)
            self.assertAlmostEqual(self.d.bidirectional_ideal_play_deg(c),
                                   budget,delta=1e-10)
        self.assertAlmostEqual(
            self.d.max_clearance_for_bidirectional_play_in(.5),.001540118,delta=1e-8)

    def test_machine_tolerance_mismatch_and_fit_budget(self):
        self.assertEqual(self.d.nominal_clearance_range_in(.472,.005,.005),
                         (-.01,.01))
        # Female precision alone does not cure independently loose male fit
        cmin,cmax=self.d.nominal_clearance_range_in(.478,.005,.0005)
        self.assertAlmostEqual(cmin,.0005)
        self.assertAlmostEqual(cmax,.0115)
        self.assertGreater(self.d.bidirectional_ideal_play_deg(cmax),3.5)

    def test_contact_force_is_lower_bound_and_patch_dependent(self):
        self.assertAlmostEqual(self.d.lower_bound_flank_reaction_n(35.54700928),
                               3953.3575,delta=.01)
        p1=self.d.illustrative_mean_contact_pressure_mpa(35.54700928,1)
        p5=self.d.illustrative_mean_contact_pressure_mpa(35.54700928,5)
        self.assertAlmostEqual(p1,415.05066,delta=.01)
        self.assertAlmostEqual(p5,p1/5)
        self.assertEqual(self.d.lower_bound_flank_reaction_n(0),0)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            IdealDoubleDFit(.2,.5)
        for c in (-.01,float('nan'),.2):
            with self.assertRaises(ValueError):
                self.d.one_sided_ideal_rotation_deg(c)
        with self.assertRaises(ValueError):
            self.d.max_clearance_for_bidirectional_play_in(0)
        with self.assertRaises(ValueError):
            self.d.illustrative_mean_contact_pressure_mpa(1,0)


if __name__=="__main__":
    unittest.main()
