import unittest

from scripts.run_native_numerical_recovery import COORDINATE_ORDER, common_perturbed_seed
from scripts.run_native_envelope_bound_control import widen_sideslip_bound
from tests.wufr_cornering_fixture import solver_config


class NativeNumericalRecoveryTests(unittest.TestCase):
    def test_same_nonzero_seed_is_valid_for_every_control_variant(self):
        anchor=(-.001,.001,.001,.0805,-.01,60.,650.,1000.,400.,950.)
        offset=(.0001,.00005,-.00005,.001,.0001,0.,0.,0.,0.,0.)
        configs=[widen_sideslip_bound(solver_config(),bound) for bound in (.1,.12)]
        point=common_perturbed_seed(anchor,COORDINATE_ORDER,offset,configs)
        self.assertNotEqual(point,anchor)
        self.assertAlmostEqual(point[3],.0815)
        self.assertAlmostEqual(point[0],-.0009)
        self.assertEqual(point[6:],anchor[6:])

    def test_no_zero_nonfinite_wrong_order_or_clipped_seed(self):
        anchor=(-.001,.001,.001,.0805,-.01,60.,650.,1000.,400.,950.)
        configs=[widen_sideslip_bound(solver_config(),.1)]
        for order,offset in ((COORDINATE_ORDER,(0.,)*10),
            (tuple(reversed(COORDINATE_ORDER)),(.001,)*10),
            (COORDINATE_ORDER,(float('nan'),)*10),
            (COORDINATE_ORDER,(1.,)*10)):
            with self.assertRaises(ValueError):common_perturbed_seed(anchor,order,offset,configs)


if __name__=='__main__':unittest.main()
