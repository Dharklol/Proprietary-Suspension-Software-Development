import math
import unittest
from dataclasses import replace

from pssd_vehicle.steady_cornering import (
    CorneringFailure, continue_cornering, evaluate_cornering, point_generalized_force, solve_cornering,
)
from tests.steady_cornering_fixture import (
    case, compatible_wheels, config, geometry, initial, point, sprung_position, tire,
)


class SteadyCorneringTests(unittest.TestCase):
    def solve(self, c=None, guess=None, **changes):
        return solve_cornering(c or case(),guess or initial(),geometry_provider=geometry,
                              tire_provider=tire,config=config(**changes))

    def test_zero_curvature_recovers_existing_synthetic_static_solution(self):
        result=self.solve()
        self.assertTrue(result.ok, result.message)
        from tests.test_vehicle_quasi_static import (
            BODY_ORDER, BODY_UNITS, compatibility, suspension, body_external, config as static_config,
        )
        from pssd_vehicle.quasi_static import solve_quasi_static_equilibrium
        static = solve_quasi_static_equilibrium((0.,0.,0.), body_coordinate_order=BODY_ORDER,
            body_coordinate_units=BODY_UNITS, compatibility_provider=compatibility,
            suspension_provider=suspension, body_external_provider=body_external, config=static_config())
        self.assertTrue(static.ok, static.message)
        self.assertAlmostEqual(result.coordinates[0], .2+static.q_body[0], places=9)
        for angle in result.coordinates[1:5]:
            self.assertAlmostEqual(angle,0.,places=9)
        for load in result.coordinates[6:]:
            self.assertAlmostEqual(load,294.30,places=7)
        self.assertAlmostEqual(result.coordinates[5],0.,places=7)
        self.assertLess(math.hypot(*result.evaluation.physical_wrench.resultant_force_N),1e-6)
        self.assertLess(math.hypot(*result.evaluation.physical_wrench.resultant_moment_Nm),1e-6)

    def test_both_turn_signs_and_continuation(self):
        runs=[]
        for sign in (-1,1):
            cases=tuple(case(sign*k,state_id=f"synthetic_{sign}_{k}") for k in (0.,.005,.01,.02))
            run=continue_cornering(cases,initial(),branch_id=f"synthetic_sign_{sign}",
                                  geometry_provider=geometry,tire_provider=tire,config=config())
            self.assertTrue(run.complete,run.results[-1].message)
            self.assertEqual(len(run.results),4)
            for result in run.results:
                self.assertLess(math.hypot(*result.evaluation.physical_wrench.resultant_force_N),1e-6)
                self.assertLess(math.hypot(*result.evaluation.physical_wrench.resultant_moment_Nm),1e-6)
            runs.append(run.results[-1])
        left,right=runs[1].coordinates,runs[0].coordinates
        for index in (1,3,4):
            self.assertAlmostEqual(left[index],-right[index],places=7)
        for index in (0,2,5):
            self.assertAlmostEqual(left[index],right[index],places=7)
        self.assertAlmostEqual(left[6],right[7],places=7)
        self.assertAlmostEqual(left[8],right[9],places=7)
        self.assertGreater(left[4],0.)

    def test_direct_plus_mapped_virtual_work_at_two_scales(self):
        c=case(.01)
        q=(.18,.03,-.02)
        rack=.012
        w=compatible_wheels(q,rack)
        # An off-CG point depending on body AND wheel coordinates, not a CG-only shortcut.
        def position(qb,zw):
            from tests.steady_cornering_fixture import mv,rotation
            local=(.3+2*zw[0],-.2+zw[1],.4+zw[2])
            rotated=mv(rotation(qb),local)
            return tuple(v+(qb[0] if i==2 else 0.) for i,v in enumerate(rotated))
        p=point(c,q,w,"off_cg_probe",position)
        force=(43.,-71.,-19.)
        direct,wheel=point_generalized_force(p,force)
        jac=geometry(c,q,rack).J_wb
        reduced=tuple(direct[j]+sum(jac[i][j]*wheel[i] for i in range(4)) for j in range(3))
        for step in (1e-5,5e-6):
            for j in range(3):
                minus=tuple(v-step if i==j else v for i,v in enumerate(q))
                plus=tuple(v+step if i==j else v for i,v in enumerate(q))
                a=position(minus,compatible_wheels(minus,rack))
                b=position(plus,compatible_wheels(plus,rack))
                work=sum(f*(hi-lo)/(2*step) for f,lo,hi in zip(force,a,b))
                self.assertAlmostEqual(reduced[j],work,places=6)
        self.assertGreater(max(abs(reduced[i]-direct[i]) for i in range(3)),1.)

    def test_fully_steered_contact_recomputed_and_normals_not_duplicated(self):
        c=case(.01)
        x=(.18,.04,-.03,.01,0.,0.,300.,300.,300.,300.)
        first=evaluate_cornering(c,x,geometry_provider=geometry,tire_provider=tire)
        second=evaluate_cornering(c,(*x[:4],.02,*x[5:]),geometry_provider=geometry,tire_provider=tire)
        self.assertNotEqual(first.geometry.wheel_coordinates_m,second.geometry.wheel_coordinates_m)
        self.assertNotEqual(first.geometry.J_wb,second.geometry.J_wb)
        for i in range(4):
            expected=(first.wheel_external_force[i]+first.geometry.suspension_force_n[i]
                      +first.geometry.contact_coefficients[i]*x[6+i])
            self.assertAlmostEqual(first.residual[3+i],expected)
        normal=[c for c in first.physical_wrench.contributions if c.wrench_id.startswith("normal_")]
        self.assertEqual(len(normal),4)
        self.assertAlmostEqual(sum(c.force_N[2] for c in normal),1200.)

    def test_failure_gates(self):
        for changes,code in (({"speed_hold_policy":"none"},"speed_hold_not_authorized"),
                             ({"inertia_policy":"static"},"inertia_not_authorized"),
                             ({"radius_policy":"loaded"},"radius_not_authorized"),
                             ({"accepted_assumptions":()},"assumptions_not_authorized"),
                             ({"result_role":"ranking"},"authority_not_authorized"),
                             ({"pressures_pa":(0.,)*4},"missing_pressure")):
            with self.assertRaises(CorneringFailure) as raised:
                case(**changes)
            self.assertEqual(raised.exception.code,code)
        bad=self.solve(case(pressures_pa=(120000.,)*4))
        self.assertFalse(bad.ok)
        self.assertNotEqual(bad.failure_code,"nonconvergence")
        bad=self.solve(guess=(*initial()[:6],-1.,300.,300.,300.))
        self.assertEqual(bad.failure_code,"bounds_failure")

    def test_provider_source_and_physical_closure_failures(self):
        for modifier,code in (
            (lambda g:replace(g,rack_m=g.rack_m+1),"source_mismatch"),
            (lambda g:replace(g,contact_coefficients=(0.,)*4),"singular_contact"),
            (lambda g:replace(g,wheels=(replace(g.wheels[0],steering_owner="double_front"),*g.wheels[1:])),"steering_ownership_error"),
            (lambda g:replace(g,masses=(replace(g.masses[0],point=replace(g.masses[0].point,
                point=replace(g.masses[0].point.point,frame_id="body"))),*g.masses[1:])),"frame_error")):
            result=solve_cornering(case(),initial(),geometry_provider=lambda c,q,r:modifier(geometry(c,q,r)),
                                    tire_provider=tire,config=config())
            self.assertFalse(result.ok)
            self.assertEqual(result.failure_code,code)

    def test_nonconvergence_and_singular_zero_force_tire_manifold(self):
        result=self.solve(case(.02),max_iterations=1)
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code,"nonconvergence")
        def zero_tire(query):
            return replace(tire(query),lateral_force_n=0.)
        result=solve_cornering(case(),initial(),geometry_provider=geometry,
                              tire_provider=zero_tire,config=config())
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code,"singular_tangent")
        # The static limiting fixture is an evaluation check, not a unique tire equilibrium.
        static=(.175475,0.,0.,0.,0.,0.,294.3,294.3,294.3,294.3)
        ev=evaluate_cornering(case(),static,geometry_provider=geometry,tire_provider=zero_tire)
        self.assertLess(max(abs(r) for r in ev.residual),1e-6)
        self.assertLess(math.hypot(*ev.physical_wrench.resultant_moment_Nm),1e-6)

    def test_continuation_retains_failed_case_and_prohibits_setup_changes(self):
        cases=(case(),case(1.,state_id="impossible"),case(.01,state_id="later"))
        result=continue_cornering(cases,initial(),branch_id="explicit_failed_branch",
                                 geometry_provider=geometry,tire_provider=tire,config=config())
        self.assertFalse(result.complete)
        self.assertEqual(len(result.results),2)
        self.assertFalse(result.results[-1].ok)
        self.assertEqual(result.results[-1].case.state_id,"impossible")
        with self.assertRaises(CorneringFailure):
            continue_cornering((case(),case(.01,setup_revision="different")),initial(),branch_id="bad",
                              geometry_provider=geometry,tire_provider=tire,config=config())

    def test_moving_lowest_point_jacobian_cannot_pass_physical_closure(self):
        from tests.steady_cornering_fixture import contact_position
        def wrong_geometry(c,q,rack):
            g=geometry(c,q,rack)
            # Intentionally mislabel a locus derivative as material virtual work.
            # The independent physical wrench must expose this provider error.
            wheels=tuple(replace(w,contact=point(c,q,g.wheel_coordinates_m,"wrong_contact_"+w.corner_id,
                lambda qb,zw,i=i:contact_position(qb,zw,rack,i))) for i,w in enumerate(g.wheels))
            return replace(g,wheels=wheels)
        correct=self.solve(case(.02))
        self.assertTrue(correct.ok,correct.message)
        wrong=solve_cornering(case(.02),correct.coordinates,geometry_provider=wrong_geometry,
                             tire_provider=tire,config=config())
        self.assertFalse(wrong.ok)
        self.assertEqual(wrong.failure_code,"physical_closure_failure")
        self.assertLess(wrong.scaled_residual_norm,1e-11)
        self.assertGreater(math.hypot(*wrong.evaluation.physical_wrench.resultant_moment_Nm),1e-6)

    def test_distinct_tire_equilibrium_branches_are_not_collapsed(self):
        from pssd_vehicle.steady_cornering import CorneringTireResponse
        def multi_tire(query):
            a=query.slip_angle_rad
            branch="middle" if abs(a)<.1 else ("positive_outer" if a>0 else "negative_outer")
            value=6*a if abs(a)<.1 else (-6*(a-.2) if a>0 else -6*(a+.2))
            return CorneringTireResponse(query,query.normal_load_n*value,
                                        ("synthetic_multiple_root_surface",),branch)
        roots=[]
        for beta in (-.19,0.,.19):
            guess=(.175475,0.,0.,beta,0.,0.,294.3,294.3,294.3,294.3)
            root=solve_cornering(case(),guess,geometry_provider=geometry,tire_provider=multi_tire,config=config())
            self.assertTrue(root.ok,root.message)
            roots.append(root)
        for root,beta in zip(roots,(-.2,0.,.2)):
            self.assertAlmostEqual(root.coordinates[3],beta,places=8)
        self.assertEqual(len({root.evaluation.branch_signature for root in roots}),3)

    def test_rear_source_failure_and_query_substitution_are_not_repaired(self):
        def broken_rear(query):
            if query.corner_id=="rear_right":
                raise CorneringFailure("rear_tire_domain_missing","Synthetic rear cell unavailable")
            return tire(query)
        result=solve_cornering(case(),initial(),geometry_provider=geometry,tire_provider=broken_rear,config=config())
        self.assertEqual(result.failure_code,"rear_tire_domain_missing")
        def substituted(query):
            return replace(tire(query),query=replace(query,inclination_rad=abs(query.inclination_rad)))
        result=solve_cornering(case(),(.18,-.002,-.002,*initial()[3:]),geometry_provider=geometry,
                              tire_provider=substituted,config=config())
        # Start at negative roll so the first source query would be altered.
        if result.ok:
            raise AssertionError("Inclination substitution was silently accepted")
        self.assertEqual(result.failure_code,"source_mismatch")

    def test_virtual_holder_balances_steered_lateral_force_at_current_cg(self):
        result=self.solve(case(.02))
        self.assertTrue(result.ok,result.message)
        ev=result.evaluation
        loads=ev.physical_wrench.contributions
        holder=next(load for load in loads if load.wrench_id=="virtual_speed_hold")
        self.assertEqual(holder.moment_arm_m,(0.,0.,0.))
        self.assertEqual(holder.moment_Nm,(0.,0.,0.))
        lateral=[load for load in loads if load.wrench_id.startswith("lateral_")]
        self.assertGreater(abs(sum(load.force_N[0] for load in lateral)),1.)
        work=sum(sum(f*t for f,t in zip(load.force_N,ev.motion.travel_direction)) for load in lateral)
        self.assertAlmostEqual(result.coordinates[5],-work,places=7)
        self.assertAlmostEqual(ev.holder.power_w,result.coordinates[5]*result.case.speed_m_s)
        self.assertEqual(tuple(t.query.pressure_pa for t in ev.tires),result.case.pressures_pa)
        self.assertEqual(tuple(t.query.normal_load_n for t in ev.tires),result.coordinates[6:])
