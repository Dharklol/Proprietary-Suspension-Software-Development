import math
import unittest
from pssd_vehicle.static_balance import reaction_family


class StaticBalanceTests(unittest.TestCase):
    def test_symmetric_hand_solution_remains_family(self):
        r=reaction_family(100.,(-1.,0.,.3),0.,-2.,.5,.5,g=10.)
        self.assertEqual(r['front_axle_N'],500.)
        self.assertEqual(r['rear_axle_N'],500.)
        self.assertEqual(r['front_left_parameter_interval_N'],(0.,500.))
        self.assertEqual(r['endpoint_loads_N'],((0.,500.,500.,0.),(500.,0.,0.,500.)))
        self.assertFalse(r['corner_loads_unique'])

    def test_offset_cg_closes_all_three_wrenches(self):
        mass=120.;cg=(-.8,.1,.4);g=9.81
        r=reaction_family(mass,cg,.1,-1.7,.6,.5,g=g)
        for loads in r['endpoint_loads_N']:
            self.assertGreaterEqual(min(loads),-1e-10)
            self.assertAlmostEqual(sum(loads),mass*g)
            self.assertAlmostEqual(.1*(loads[0]+loads[1])-1.7*(loads[2]+loads[3]),mass*g*cg[0])
            self.assertAlmostEqual(.6*(loads[0]-loads[1])+.5*(loads[2]-loads[3]),mass*g*cg[1])

    def test_reject_invalid_and_unsupported_cg(self):
        for mass,cg in ((-1.,(-1.,0.,0.)),(100.,(-1.,2.,0.)),(100.,(1.,0.,0.)),(100.,(-1.,math.nan,0.))):
            with self.assertRaises(ValueError): reaction_family(mass,cg,0.,-2.,.5,.5)

    def test_support_vertex_is_unique(self):
        r=reaction_family(100.,(0.,.5,.3),0.,-2.,.5,.5,g=10.)
        self.assertTrue(r['corner_loads_unique'])
        self.assertEqual(r['endpoint_loads_N'][0],(1000.,0.,0.,0.))


if __name__=='__main__': unittest.main()
