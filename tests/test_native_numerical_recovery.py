import unittest

from scripts.run_native_numerical_recovery import (
    COORDINATE_ORDER, common_perturbed_seed, refined_contact_geometry,
)
from scripts.run_native_envelope_bound_control import widen_sideslip_bound
from tests.wufr_cornering_fixture import solver_config, providers


class NativeNumericalRecoveryTests(unittest.TestCase):
    def test_contact_precision_change_preserves_physical_sources_and_baseline(self):
        from dataclasses import asdict
        original,_=providers()
        refined=refined_contact_geometry(original,1e-14)
        finer=refined_contact_geometry(original,5e-15)
        self.assertEqual(original.geometry_revision,refined.geometry_revision)
        self.assertEqual(original.geometry_revision,finer.geometry_revision)
        self.assertNotEqual(original.setup_revision,refined.setup_revision)
        self.assertNotEqual(refined.setup_revision,finer.setup_revision)
        for name in original.components.__dataclass_fields__:
            if name!='road_contact':
                self.assertIs(getattr(original.components,name),getattr(refined.components,name))
        for key,value in asdict(original.road.config).items():
            if key!='road_gap_tolerance_m':
                self.assertEqual(value,getattr(refined.road.config,key))
        self.assertEqual(original.road.config.road_gap_tolerance_m,1e-13)
        self.assertEqual(refined.road.config.road_gap_tolerance_m,1e-14)
        for bad in (1e-13,0.,float('nan')):
            with self.assertRaises(ValueError):refined_contact_geometry(original,bad)

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
