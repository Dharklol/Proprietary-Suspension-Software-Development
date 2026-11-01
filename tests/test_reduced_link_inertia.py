from dataclasses import replace
import math
import unittest
from pssd_suspension.reduced_inertia import RigidMemberKinematics, reduce_member_inertia, physical_tensor_from_entries

ZERO=((0.,0.,0.),)*3


def member(m=3.,tensor=ZERO,v=((0.,),(0.,),(1.,)),w=((0.,),(0.,),(0.,)),ids=('q',)):
    return RigidMemberKinematics('member','manufactured','fixture','xyz','origin',ids,tuple('m' for _ in ids),m,tensor,v,w)


def rod(m=3.,length=2.):
    inertia=m*length**2/12
    return member(m,((0.,0.,0.),(0.,inertia,0.),(0.,0.,inertia)),
        ((0.,0.),(0.,0.),(.5,.5)),((0.,0.),(1/length,-1/length),(0.,0.)),('end_A','end_B'))


def reduce(m): return reduce_member_inertia((m,),expected_member_ids=(m.member_id,))


class ReducedLinkInertiaTests(unittest.TestCase):
    def test_point_mass_and_independent_energy(self):
        m=member(v=((1.,0.),(0.,1.),(0.,0.)),w=((0.,0.),)*3,ids=('x','y'))
        result=reduce(m)
        self.assertEqual(result.matrix,((3.,0.),(0.,3.)))
        self.assertEqual(result.kinetic_energy_J((2.,-4.)),.5*3*(2**2+4**2))

    def test_uniform_rod_exact_integral_and_coupling(self):
        m,L=3.,2.
        result=reduce(rod(m,L))
        self.assertEqual(result.matrix,((1.,.5),(.5,1.)))
        for a,b in ((0.,1.),(1.,1.),(1.,-1.),(.3,-.7)):
            exact=m*(a*a+a*b+b*b)/6
            self.assertAlmostEqual(result.kinetic_energy_J((a,b)),exact,places=12)
        self.assertAlmostEqual(2*result.kinetic_energy_J((0.,1.)),m/3)
        self.assertAlmostEqual(2*result.kinetic_energy_J((1.,1.)),m)
        self.assertNotEqual(result.matrix[1][1],m/2)

    def test_hinge_parallel_axis_and_numerical_jacobian(self):
        m,r,I=2.,.4,.07
        fixture=member(m,((I,0.,0.),(0.,I,0.),(0.,0.,I)),
            ((0.,),(r,),(0.,)),((0.,),(0.,),(1.,)),('angle',))
        fixture=replace(fixture,coordinate_units=('rad',))
        self.assertAlmostEqual(reduce(fixture).matrix[0][0],m*r*r+I,places=12)
        errors=[]
        for h in (1e-3,5e-4):
            # CG=(r*cos(q),r*sin(q),0), exact tangent at q=0 is (0,r,0).
            numerical=r*(math.sin(h)-math.sin(-h))/(2*h)
            errors.append(abs(numerical-r))
        self.assertGreater(errors[0]/errors[1],3.9)
        self.assertLess(errors[0]/errors[1],4.1)
        self.assertLess(errors[-1]/r,1e-6)

    def test_orthonormal_frame_rotation(self):
        base=rod()
        # Proper 90-degree rotation around x: x'=x,y'=-z,z'=y.
        def transform(j): return (j[0],tuple(-v for v in j[2]),j[1])
        R=((1.,0.,0.),(0.,0.,-1.),(0.,1.,0.))
        I=base.centroidal_tensor_kg_m2
        rotated=tuple(tuple(sum(R[i][k]*I[k][l]*R[j][l] for k in range(3) for l in range(3)) for j in range(3)) for i in range(3))
        other=replace(base,frame_id='rotated',centroidal_tensor_kg_m2=rotated,
            cg_velocity_jacobian=transform(base.cg_velocity_jacobian),angular_velocity_jacobian=transform(base.angular_velocity_jacobian))
        self.assertEqual(reduce(base).matrix,reduce(other).matrix)

    def test_addition_and_manifest(self):
        a=rod()
        b=replace(a,member_id='second',mass_kg=6.,centroidal_tensor_kg_m2=tuple(tuple(2*v for v in r) for r in a.centroidal_tensor_kg_m2))
        result=reduce_member_inertia((a,b),expected_member_ids=('member','second'))
        self.assertAlmostEqual(result.kinetic_energy_J((.2,-.4)),3*reduce(a).kinetic_energy_J((.2,-.4)))
        for members,expected in (((a,a),('member',)),((a,),('member','missing')),((a,),('member','member'))):
            with self.assertRaises(ValueError): reduce_member_inertia(members,expected_member_ids=expected)
        for changes in ({'frame_id':'other'},{'state_id':'other'},{'coordinate_units':('rad','m')},{'configuration_id':'other'}):
            with self.assertRaises(ValueError): reduce_member_inertia((a,replace(b,**changes)),expected_member_ids=('member','second'))

    def test_invalid_tensor_and_inputs(self):
        a=rod()
        for tensor in (((-1.,0.,0.),(0.,1.,0.),(0.,0.,1.)),((1.,1.,0.),(0.,1.,0.),(0.,0.,1.)),
            ((1.,0.,0.),(0.,1.,0.),(0.,0.,10.)),((float('nan'),0.,0.),)*3):
            with self.assertRaises(ValueError): replace(a,centroidal_tensor_kg_m2=tensor)
        for changes in ({'mass_kg':0.},{'source_id':''},{'coordinate_ids':('q','q')},{'cg_velocity_jacobian':((1.,),)},{'angular_velocity_jacobian':((float('inf'),0.),)*3}):
            with self.assertRaises(ValueError): replace(a,**changes)
        result=reduce(a)
        for rates in ((1.,),(float('nan'),0.)):
            with self.assertRaises(ValueError): result.kinetic_energy_J(rates)

    def test_explicit_positive_products_against_off_axis_point_masses(self):
        # Two 2 kg point masses at ±(1,2,3): independently integrate products.
        r=(1.,2.,3.)
        mass=4.
        entries=tuple(tuple(mass*(sum(x*x for x in r)-r[i]*r[i]) if i==j
                            else mass*r[i]*r[j] for j in range(3)) for i in range(3))
        physical=physical_tensor_from_entries(entries,convention='positive_products')
        self.assertEqual(tuple(physical[i][i] for i in range(3)),tuple(entries[i][i] for i in range(3)))
        self.assertEqual(physical[0][1],-8.)
        omega=(.4,-.2,.7)
        tensor_energy=.5*sum(omega[i]*physical[i][j]*omega[j] for i in range(3) for j in range(3))
        velocity=(omega[1]*r[2]-omega[2]*r[1],omega[2]*r[0]-omega[0]*r[2],omega[0]*r[1]-omega[1]*r[0])
        direct_energy=2*(.5*2*sum(v*v for v in velocity))
        self.assertAlmostEqual(tensor_energy,direct_energy,places=12)
        self.assertEqual(physical_tensor_from_entries(physical,convention='physical_tensor'),physical)
        for convention in ('', 'auto', 'guess'):
            with self.assertRaises(ValueError): physical_tensor_from_entries(entries,convention=convention)
        with self.assertRaises(ValueError): physical_tensor_from_entries(((1.,),),convention='physical_tensor')

    def test_rank_deficiency_is_explicitly_allowed(self):
        a=member(v=((1.,0.),(0.,0.),(0.,0.)),w=((0.,0.),)*3,ids=('active','inactive'))
        self.assertEqual(reduce(a).matrix,((3.,0.),(0.,0.)))
        self.assertEqual(reduce(a).kinetic_energy_J((0.,7.)),0.)


if __name__=='__main__': unittest.main()
