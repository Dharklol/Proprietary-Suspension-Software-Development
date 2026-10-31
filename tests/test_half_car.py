from dataclasses import replace
import math
import unittest
from pssd_vehicle.half_car import HalfCar, evaluate, simulate_half_car
from pssd_vehicle.reduced_ride import RoadSample, flat_road, cosine_bump


def symmetric(damping=0.):
    return HalfCar(2.,2.,1.,1.,1.,1.,2.,2.,3.,3.,damping,damping,1.,1.,'manufactured','symmetric')


def asymmetric():
    return HalfCar(3.,2.4,.8,1.2,.7,1.1,2.7,1.8,4.2,3.1,.3,.5,1.,1.,'manufactured','asymmetric')


class HalfCarVerification(unittest.TestCase):
    def run_case(self,s,initial=(0.,)*8,front=flat_road,rear=flat_road,dt=.0025,steps=4000):
        result=simulate_half_car(s,front,rear,road_source_ids=('front-manufactured','rear-manufactured'),dt=dt,steps=steps,initial=initial)
        self.assertTrue(result.ok,result.failure_code)
        return result

    def test_zero(self):
        result=self.run_case(asymmetric(),steps=20)
        self.assertTrue(all(x.state==(0.,)*8 and x.energy_residual==0 for x in result.samples))
        self.assertAlmostEqual(sum(result.samples[0].evaluation.normal_loads),(3.+.7+1.1)*9.80665)

    def test_exact_heave_and_pitch_modes(self):
        for pitch in (False,True):
            for eigenvalue,(body,unsprung) in ((1.,(2.,1.)),(6.,(1.,-2.))):
                displacement=(0.,.01*body,.01*unsprung,-.01*unsprung) if pitch else (.01*body,0.,.01*unsprung,.01*unsprung)
                run=self.run_case(symmetric(),initial=displacement+(0.,)*4)
                omega=math.sqrt(eigenvalue)
                error=0.
                for sample in run.samples:
                    expected=tuple(v*math.cos(omega*sample.time) for v in displacement)+tuple(-v*omega*math.sin(omega*sample.time) for v in displacement)
                    error=max(error,max(abs(a-b) for a,b in zip(sample.state,expected)))
                    self.assertEqual(sample.state[0 if pitch else 1],0.)
                self.assertLess(error,1e-9)
                self.assertLess(max(abs(x.energy_residual) for x in run.samples),1e-10)

    def test_asymmetric_force_moment_and_energy(self):
        s=asymmetric()
        q=(.01,.02,-.01,.005,.03,-.01,.02,-.04)
        front,rear=RoadSample(.003,.01),RoadSample(-.002,-.02)
        result=evaluate(s,q,front,rear)
        # Independently form physical point forces from attachment displacements.
        ff=-2.7*(.01+.8*.02+.01)-.3*(.03+.8*(-.01)-.02)
        fr=-1.8*(.01-1.2*.02-.005)-.5*(.03-1.2*(-.01)+.04)
        self.assertAlmostEqual(result.derivative[4]*3.,ff+fr)
        self.assertAlmostEqual(result.derivative[5]*2.4,.8*ff-1.2*fr)
        self.assertAlmostEqual(result.derivative[6]*.7,4.2*(.003+.01)-ff)
        self.assertAlmostEqual(result.derivative[7]*1.1,3.1*(-.002-.005)-fr)
        def energy(state,rf,rr):
            z,theta,uf,ur,v,w,vf,vr=state
            return (3*v*v+2.4*w*w+.7*vf*vf+1.1*vr*vr+
                2.7*(z+.8*theta-uf)**2+1.8*(z-1.2*theta-ur)**2+
                4.2*(uf-rf)**2+3.1*(ur-rr)**2)/2
        h=1e-6
        energies=[]
        for sign in (-1,1):
            state=tuple(v+sign*h*d for v,d in zip(q,result.derivative))
            energies.append(energy(state,front.displacement+sign*h*front.velocity,rear.displacement+sign*h*rear.velocity))
        rate=(energies[1]-energies[0])/(2*h)
        self.assertLess(abs(rate-result.road_power+result.loss_power),1e-8)

    def test_independent_bumps_refinement(self):
        s=asymmetric()
        front,rear=cosine_bump(.01,.3,.8),cosine_bump(.008,.9,.6)
        coarse=self.run_case(s,front=front,rear=rear,dt=.002,steps=2000)
        fine=self.run_case(s,front=front,rear=rear,dt=.001,steps=4000)
        self.assertLess(max(abs(x.energy_residual) for x in fine.samples),1e-8)
        self.assertLess(max(max(abs(a-b) for a,b in zip(x.state,y.state)) for x,y in zip(coarse.samples,fine.samples[::2])),1e-7)
        self.assertGreater(fine.samples[-1].road_work,0.)
        self.assertGreater(fine.samples[-1].dissipated,0.)
        self.assertTrue(any(abs(x.state[1])>1e-5 for x in fine.samples))

    def test_damped_decay(self):
        run=self.run_case(symmetric(.4),initial=(.02,.01,-.01,.005,0.,0.,0.,0.))
        self.assertTrue(all(b.evaluation.energy<=a.evaluation.energy+1e-13 for a,b in zip(run.samples,run.samples[1:])))
        self.assertLess(run.samples[-1].evaluation.energy,run.samples[0].evaluation.energy)
        self.assertLess(max(abs(x.energy_residual) for x in run.samples),1e-10)

    def test_guards_and_contracts(self):
        for field,value in (('pitch_inertia',0.),('front_distance',-1.),('rear_damping',-1.),('source_id','')):
            with self.assertRaises(ValueError): replace(symmetric(),**{field:value})
        args=dict(road_source_ids=('f','r'),dt=.01,steps=20)
        for override in ({'dt':0.},{'steps':True},{'road_source_ids':('f','')},{'initial':(0.,)}):
            with self.assertRaises(ValueError): simulate_half_car(symmetric(),flat_road,flat_road,**(args|override))
        for initial,code in (((0.,0.,10.,0.,0.,0.,0.,0.),'contact_loss'),((2.,0.,0.,0.,0.,0.,0.,0.),'travel_exceeded')):
            run=simulate_half_car(symmetric(),flat_road,flat_road,initial=initial,**args)
            self.assertEqual(run.failure_code,code)
            self.assertEqual(run.samples,())
        run=simulate_half_car(replace(symmetric(),extension_limit=.001),flat_road,flat_road,initial=(0.,0.,0.,0.,1.,0.,0.,0.),**args)
        self.assertEqual(run.failure_code,'travel_exceeded')
        self.assertEqual(len(run.samples),1)
        self.assertGreater(run.failure_time,0.)
        def bad_road(t): return RoadSample(0. if t<.015 else float('nan'),0.)
        run=simulate_half_car(symmetric(),bad_road,flat_road,**args)
        self.assertEqual(run.failure_code,'nonfinite_evaluation')
        self.assertEqual(len(run.samples),2)


if __name__=='__main__': unittest.main()
