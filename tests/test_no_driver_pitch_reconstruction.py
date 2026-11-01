"""Independent mass-moment references for the offline COM reconstruction."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_no_driver_pitch_study import combine


class PitchReconstructionTests(unittest.TestCase):
    def test_hand_mass_moment_and_translation(self):
        # Two 2 kg lumps at x=±1 m, intrinsic Jy=1 each: total Jy=6.
        parts=[[2.,-1.,0.,0.,1.],[2.,1.,0.,0.,1.]]
        first=combine(parts)
        self.assertEqual(first['mass_kg'],4.)
        self.assertEqual(first['pitch_inertia_kg_m2'],6.)
        moved=combine([[m,x+3.,y-4.,z+2.,j] for m,x,y,z,j in parts])
        self.assertAlmostEqual(moved['pitch_inertia_kg_m2'],6.)
        self.assertEqual(moved['cg_m'],(3.,-4.,2.))

    def test_electrical_at_cg_preserves_inertia(self):
        parts=[[2.,-1.,0.,0.,1.],[2.,1.,0.,0.,1.]]
        added=combine(parts+[[3.,0.,0.,0.,0.]])
        self.assertEqual(added['mass_kg'],7.)
        self.assertEqual(added['pitch_inertia_kg_m2'],6.)

    def test_invalid_mass_and_inertia(self):
        for records in ([],[[0.,0.,0.,0.,0.]],[[-1.,0.,0.,0.,1.]],[[1.,0.,0.,0.,-1.]],[[1.,float('nan'),0.,0.,0.]]):
            with self.assertRaises(ValueError): combine(records)


if __name__=='__main__': unittest.main()
