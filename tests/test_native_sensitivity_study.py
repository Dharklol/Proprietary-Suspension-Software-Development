from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import unittest

from scripts.run_native_sensitivity_study import (
    StudyControls, finite_step_response, numerical_variants, pressure_case, verify_sources,
)
from tests.steady_cornering_fixture import case
from tests.wufr_cornering_fixture import solver_config


def controls():
    return StudyControls(.1,.125,(1000.,2000.),.1,.12,.5,2,2,1e-5)


class NativeSensitivityStudyTests(unittest.TestCase):
    def test_pressure_cases_change_only_explicit_pressure_and_identity(self):
        base=case(pressures_pa=(68900.,)*4)
        for delta in (-2000.,-1000.,1000.,2000.):
            changed=pressure_case(base,delta,'pressure_test')
            for field in base.__dataclass_fields__:
                if field not in ('state_id','pressures_pa'):
                    self.assertEqual(getattr(base,field),getattr(changed,field))
            self.assertEqual(changed.pressures_pa,(68900.+delta,)*4)
        for delta in (0.,float('nan'),-80000.):
            with self.assertRaises(ValueError):pressure_case(base,delta,'bad')

    def test_numerical_variants_preserve_equilibrium_and_acceptance_controls(self):
        base=solver_config(); variants=numerical_variants(base,controls())
        self.assertEqual(variants['anchor'].upper_bounds[3],.1)
        self.assertEqual(variants['wider_sideslip_box'].upper_bounds[3],.12)
        self.assertEqual(variants['half_fd_steps'].fd_steps,tuple(x*.5 for x in base.fd_steps))
        for variant in variants.values():
            for key,value in asdict(base).items():
                if key not in ('lower_bounds','upper_bounds','fd_steps'):
                    self.assertEqual(value,getattr(variant,key))
            for i in range(10):
                if i!=3:
                    self.assertEqual(base.lower_bounds[i],variant.lower_bounds[i])
                    self.assertEqual(base.upper_bounds[i],variant.upper_bounds[i])
        self.assertEqual(base.upper_bounds[3],.08)

    def test_left_and_right_finite_step_responses_are_not_centrally_averaged(self):
        # Manufactured response Q(P0+d)=10+3d+2d^2: unequal one-sided slopes.
        base={'q':10.}
        expected={1.:5.,2.:7.,-1.:1.,-2.:-1.}
        for step,slope in expected.items():
            changed={'q':10.+3*step+2*step**2}
            response=finite_step_response(base,changed,step)
            self.assertEqual(response['q']['finite_step_slope_per_pa'],slope)
            self.assertEqual(response['q']['absolute_change'],changed['q']-10.)
        self.assertIsNone(finite_step_response(base,None,1.))
        with self.assertRaises(ValueError):finite_step_response(base,base,0.)

    def test_source_changes_are_rejected_before_seed_use(self):
        with TemporaryDirectory() as temporary:
            root=Path(temporary); (root/'source').write_text('original')
            hashes={'source':hashlib.sha256((root/'source').read_bytes()).hexdigest()}
            verify_sources(hashes,root)
            (root/'source').write_text('changed')
            with self.assertRaises(ValueError):verify_sources(hashes,root)

    def test_invalid_or_non_discrete_controls_fail(self):
        for changes in ({'pressure_steps_pa':(2000.,1000.)},{'fd_step_multiplier':1.},
                        {'front_arb_target':2.5},{'wider_sideslip_bound_rad':.1},
                        {'numerical_coordinate_difference_limit':float('nan')}):
            with self.assertRaises(ValueError):replace(controls(),**changes)


if __name__=='__main__':unittest.main()
