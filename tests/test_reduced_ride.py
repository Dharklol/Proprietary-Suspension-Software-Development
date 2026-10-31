"""Manufactured references independent of the RK4 and modal implementations."""
import cmath
from dataclasses import replace
import math
import unittest

from pssd_vehicle.reduced_ride import RideSystem, simulate, undamped_modes, flat_road, sine_road, cosine_bump
from pssd_suspension.spring_force import SpringDefinition, SpringLawKind, evaluate_spring_law
from pssd_suspension.local_stiffness import CompressionMap, local_stiffness


def system(damping=0.):
    return RideSystem(1.,1.,2.,3.,damping,1.,1.,"manufactured-unit-masses","toy-2-3")


def harmonic_reference(s, amplitude, omega, t):
    # Independent scalar complex dynamic-stiffness solution, not a time integrator.
    h = s.suspension_rate+1j*omega*s.damping
    a = h-s.sprung_mass*omega**2
    b = h+s.tire_rate-s.unsprung_mass*omega**2
    det = a*b-h*h
    zs, zu = s.tire_rate*h*amplitude/det, s.tire_rate*a*amplitude/det
    phase = cmath.exp(1j*omega*t)
    return tuple((v*phase).real for v in (zs,zu,1j*omega*zs,1j*omega*zu))


class RideVerification(unittest.TestCase):
    def run_case(self,s,road=flat_road,dt=.005,steps=2000,initial=(0.,0.,0.,0.)):
        result = simulate(s,road,road_source_id="manufactured-road",dt=dt,steps=steps,initial=initial)
        self.assertTrue(result.ok, result.failure_code)
        return result

    def test_hand_modes(self):
        modes = undamped_modes(system())
        for mode, eigenvalue, vector in zip(modes,(1.,6.),((2.,1.),(1.,-2.))):
            self.assertAlmostEqual(mode.eigenvalue,eigenvalue,places=13)
            for actual,expected in zip(mode.vector,vector):
                self.assertAlmostEqual(actual,expected/math.sqrt(5),places=13)
            self.assertLess(mode.residual,1e-14)
        s = replace(system(),sprung_mass=4.,unsprung_mass=2.)
        for mode in undamped_modes(s):
            x,y=mode.vector
            self.assertAlmostEqual(4*x*x+2*y*y,1.)
            self.assertLess(mode.residual,1e-13)

    def test_zero_equilibrium(self):
        result=self.run_case(system(.4))
        self.assertTrue(all(x.state==(0.,0.,0.,0.) and x.energy_residual==0 for x in result.samples))

    def test_free_modes_against_cosine(self):
        for eigenvalue,vector in ((1.,(2.,1.)),(6.,(1.,-2.))):
            initial=(.01*vector[0],.01*vector[1],0.,0.)
            result=self.run_case(system(),initial=initial)
            omega=math.sqrt(eigenvalue)
            error=0.
            for sample in result.samples:
                expected=tuple(.01*v*math.cos(omega*sample.time) for v in vector)+tuple(-.01*v*omega*math.sin(omega*sample.time) for v in vector)
                error=max(error,max(abs(a-b) for a,b in zip(sample.state,expected)))
            self.assertLess(error,3e-10)
            self.assertLess(max(abs(x.energy_residual) for x in result.samples),1e-11)

    def test_damped_free_decay(self):
        result=self.run_case(system(.4),initial=(.02,-.01,0.,0.))
        self.assertLess(result.samples[-1].energy,result.samples[0].energy*.1)
        self.assertTrue(all(b.energy <= a.energy+1e-14 for a,b in zip(result.samples,result.samples[1:])))
        self.assertLess(max(abs(x.energy_residual) for x in result.samples),1e-11)

    def test_harmonic_refinement(self):
        s=system(.4)
        amplitude,omega=.01,1.3
        errors=[]
        for dt in (.1,.05,.025):
            result=self.run_case(s,sine_road(amplitude,omega),dt,round(12/dt),harmonic_reference(s,amplitude,omega,0.))
            errors.append(max(max(abs(a-b) for a,b in zip(x.state,harmonic_reference(s,amplitude,omega,x.time))) for x in result.samples))
        for coarse,fine in zip(errors,errors[1:]):
            self.assertGreater(coarse/fine,12.)
            self.assertLess(coarse/fine,20.)
        self.assertLess(errors[-1],1e-8)

    def test_bump_balance_and_force_identity(self):
        s=system(.4)
        result=self.run_case(s,cosine_bump(.01,1.,2.))
        self.assertLess(max(abs(x.energy_residual) for x in result.samples),1e-9)
        for sample in result.samples:
            zs,zu,vs,vu=sample.state
            fs=-s.suspension_rate*(zs-zu)-s.damping*(vs-vu)
            delta=sample.normal_load-(s.sprung_mass+s.unsprung_mass)*s.gravity
            self.assertAlmostEqual(fs+(-fs+delta),delta)

    def test_explicit_failures(self):
        for s,road,initial,code in (
            (system(),flat_road,(0.,10.,0.,0.),"contact_loss"),
            (system(),flat_road,(2.,0.,0.,0.),"travel_exceeded"),
            (system(),lambda t: type(flat_road(t))(float('nan'),0.),(0.,0.,0.,0.),"nonfinite_state_or_road"),
        ):
            result=simulate(s,road,road_source_id="bad-fixture",dt=.01,steps=10,initial=initial)
            self.assertEqual(result.failure_code,code)
            self.assertEqual(result.samples,())
        result=simulate(replace(system(),extension_limit=.001),flat_road,road_source_id="flat",dt=.01,steps=100,initial=(0.,0.,1.,0.))
        self.assertEqual(result.failure_code,"travel_exceeded")
        self.assertEqual(len(result.samples),1)
        self.assertGreater(result.failure_time,result.samples[-1].time)

    def test_input_contract(self):
        for field,value in (("damping",-1.),("sprung_mass",0.),("tire_rate",float('nan')),("source_id","")):
            with self.assertRaises(ValueError): replace(system(),**{field:value})
        for kwargs in ({"dt":0.},{"steps":True},{"steps":1.5},{"initial":(0.,0.)},{"road_source_id":""}):
            args=dict(dt=.01,steps=10,road_source_id="flat")
            args.update(kwargs)
            with self.assertRaises(ValueError): simulate(system(),flat_road,**args)


class StiffnessVerification(unittest.TestCase):
    def test_nonlinear_map_energy_derivatives(self):
        definition=SpringDefinition("toy",SpringLawKind.LINEAR,.1,"manufactured","config",linear_rate_N_per_m=1000.)
        q=.02
        def x(q): return .03+.8*q+1.25*q*q
        def energy(q): return 500*x(q)**2
        spring=evaluate_spring_law(definition,x(q))
        mapping=CompressionMap("toy","config","wheel-up","analytic-polynomial",.8+2.5*q,2.5)
        result=local_stiffness(spring,mapping)
        self.assertGreater(result.geometric_N_per_m,0)
        errors=[]
        for h in (1e-3,5e-4):
            force=-(energy(q+h)-energy(q-h))/(2*h)
            stiffness=(energy(q+h)-2*energy(q)+energy(q-h))/h**2
            errors.append(abs(stiffness-result.total_N_per_m))
            self.assertLess(abs(force-result.generalized_force_N),.003)
        self.assertGreater(errors[0]/errors[1],3.9)
        negative=local_stiffness(spring,replace(mapping,curvature_per_m=-100.))
        self.assertLess(negative.total_N_per_m,0.)
        with self.assertRaises(ValueError): local_stiffness(spring,replace(mapping,configuration_id="other"))
        with self.assertRaises(ValueError): local_stiffness(evaluate_spring_law(definition,-1.),mapping)


if __name__ == "__main__": unittest.main()
