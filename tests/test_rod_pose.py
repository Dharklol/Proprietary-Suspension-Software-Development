import math
import unittest
from pssd_suspension.rod_pose import transport_rod_offset


class RodPoseTests(unittest.TestCase):
    def test_exact_rotation_and_derivative(self):
        t=.4;o=(.2,-.3,.1);u=(math.cos(t),math.sin(t),0.);up=(-math.sin(t),math.cos(t),0.)
        r,d=transport_rod_offset((1.,0.,0.),u,up,o)
        expected=(o[0]*math.cos(t)-o[1]*math.sin(t),o[0]*math.sin(t)+o[1]*math.cos(t),o[2])
        for x,y in zip(r,expected): self.assertAlmostEqual(x,y,places=14)
        for x,y in zip(d,(-r[1],r[0],0.)): self.assertAlmostEqual(x,y,places=14)

    def test_general_direction_finite_difference(self):
        u0=(0.,0.,1.);offset=(.1,.2,-.1);t=.3;h=1e-6
        def direction(x): return (math.sin(x)/math.sqrt(2),math.sin(x)/math.sqrt(2),math.cos(x))
        up=(math.cos(t)/math.sqrt(2),math.cos(t)/math.sqrt(2),-math.sin(t))
        r,d=transport_rod_offset(u0,direction(t),up,offset)
        minus=transport_rod_offset(u0,direction(t-h),(0.,)*3,offset)[0]
        plus=transport_rod_offset(u0,direction(t+h),(0.,)*3,offset)[0]
        for x,a,b in zip(d,plus,minus): self.assertAlmostEqual(x,(a-b)/(2*h),places=9)
        self.assertAlmostEqual(sum(x*x for x in r),sum(x*x for x in offset),places=14)

    def test_nominal_identity(self):
        o=(.1,.2,.3)
        r,d=transport_rod_offset((1.,0.,0.),(1.,0.,0.),(0.,)*3,o)
        self.assertEqual(r,o);self.assertEqual(d,(0.,)*3)

    def test_rejections(self):
        for u,up in (((-1.,0.,0.),(0.,)*3),((2.,0.,0.),(0.,)*3),((1.,0.,0.),(1.,0.,0.)),((math.nan,0.,0.),(0.,)*3)):
            with self.assertRaises(ValueError): transport_rod_offset((1.,0.,0.),u,up,(0.,)*3)


if __name__=='__main__': unittest.main()
