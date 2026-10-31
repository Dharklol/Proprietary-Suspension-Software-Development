from dataclasses import asdict
import unittest

from scripts.run_native_envelope_bound_control import widen_sideslip_bound
from tests.wufr_cornering_fixture import solver_config


class NativeEnvelopeBoundControlTests(unittest.TestCase):
    def test_only_sideslip_bounds_change_and_acceptance_limits_are_preserved(self):
        original=solver_config()
        changed=widen_sideslip_bound(original,.1)
        for key,value in asdict(original).items():
            if key not in ('lower_bounds','upper_bounds'):
                self.assertEqual(value,getattr(changed,key))
        for i in range(10):
            if i!=3:
                self.assertEqual(original.lower_bounds[i],changed.lower_bounds[i])
                self.assertEqual(original.upper_bounds[i],changed.upper_bounds[i])
        self.assertEqual(changed.lower_bounds[3],-.1)
        self.assertEqual(changed.upper_bounds[3],.1)
        self.assertEqual(original.upper_bounds[3],.08)

    def test_no_silent_shrinking_equal_or_nonfinite_bound(self):
        for bound in (.08,.04,-.1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):widen_sideslip_bound(solver_config(),bound)


if __name__=='__main__':unittest.main()
