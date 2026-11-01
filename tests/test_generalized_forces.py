import math
import unittest
from pssd_suspension.generalized_forces import DeformationPort, evaluate_ports


class GeneralizedForcesTests(unittest.TestCase):
    def test_nonlinear_potential_gradient(self):
        q=.3;h=1e-6;k=17.
        p=DeformationPort('spring',.2*math.sin(q),(.2*math.cos(q),),0.,k,0.)
        force=evaluate_ports((p,),(0.,)).generalized_force[0]
        energy=lambda x:.5*k*(.2*math.sin(x))**2
        self.assertAlmostEqual(force,-(energy(q+h)-energy(q-h))/(2*h),places=9)

    def test_moving_support_power(self):
        p=DeformationPort('road',.02,(-1.,.3),.04,100.,5.,True)
        rates=(.01,-.02);r=evaluate_ports((p,),rates)
        edot=sum(g*v for g,v in zip(p.gradient,rates))+p.explicit_rate_m_s
        Vdot=p.stiffness_N_m*p.deformation_m*edot
        self.assertAlmostEqual(sum(f*v for f,v in zip(r.generalized_force,rates))+Vdot,
                               r.support_power_W-r.dissipation_W,places=14)
        self.assertGreaterEqual(r.dissipation_W,0.)

    def test_contact_loss_stops_without_clipping(self):
        for e,rate in ((0.,0.),(-.01,0.),(.01,-3.)):
            with self.assertRaisesRegex(ValueError,'Contact-valid'):
                evaluate_ports((DeformationPort('contact',e,(1.,),0.,100.,1.,True),),(rate,))

    def test_invalid_contracts(self):
        p=DeformationPort('x',.1,(1.,),0.,1.,1.)
        for ports,rates in (((p,p),(0.,)),((p,),(math.nan,)),((DeformationPort('x',.1,(1.,),0.,-1.,0.),),(0.,)),((p,),(0.,0.))):
            with self.assertRaises(ValueError): evaluate_ports(ports,rates)

    def test_additivity_and_empty_ports(self):
        a=DeformationPort('a',.1,(1.,0.),0.,10.,2.)
        b=DeformationPort('b',-.2,(0.,1.),0.,20.,3.)
        rates=(.2,-.1);r=evaluate_ports((a,b),rates)
        ra=evaluate_ports((a,),rates);rb=evaluate_ports((b,),rates)
        self.assertEqual(r.generalized_force,tuple(x+y for x,y in zip(ra.generalized_force,rb.generalized_force)))
        self.assertEqual(evaluate_ports((),rates).potential_J,0.)


if __name__=='__main__': unittest.main()
