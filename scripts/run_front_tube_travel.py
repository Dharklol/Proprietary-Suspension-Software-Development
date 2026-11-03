"""Fixed-chassis 1-DOF tube metric and convective-inertia verification.

BENCH-SUSP-0042 / MOD-SUSP-0013. No HalfCar substitution or joint-lump promotion.
"""
import hashlib
import json
import math
from pathlib import Path
from pssd_suspension.geometry import load_optimumk_geometry_snapshot
from pssd_suspension.kinematics import rotate_point_about_hinge, solve_corner_state
from pssd_suspension.reduced_inertia import RigidMemberKinematics, physical_tensor_from_entries, reduce_member_inertia
from run_front_arm_tube_inertia import axis, cross, dot, norm, sub

ROOT=Path(__file__).resolve().parents[1]


def rotate_tensor(tensor, fore, aft, angle):
    """Build R by rotating basis vectors; transport physical tensor as R I R^T."""
    origin=rotate_point_about_hinge((0.,0.,0.),fore,aft,angle)
    columns=[sub(rotate_point_about_hinge(tuple(float(i==j) for i in range(3)),fore,aft,angle),origin) for j in range(3)]
    return tuple(tuple(sum(columns[k][i]*tensor[k][l]*columns[l][j] for k in range(3) for l in range(3)) for j in range(3)) for i in range(3))


def closure(corner,q,geometry_id):
    state=solve_corner_state(corner,q,geometry_id=geometry_id)
    if not state.ok: raise ValueError('Native closure failed: '+state.message)
    arm=corner.wishbone
    vectors={}
    for prefix,angle in (('lower',q),('upper',state.q_U_rad)):
        fore=getattr(arm,prefix+'_fore_inboard').position_m
        aft=getattr(arm,prefix+'_aft_inboard').position_m
        point=rotate_point_about_hinge(getattr(arm,prefix+'_upright').position_m,fore,aft,angle)
        u=axis(fore,aft)
        first=cross(u,sub(point,fore))
        vectors[prefix]=(point,first,cross(u,first))
    U,du,duu=vectors['upper'];L,dl,dll=vectors['lower']
    d=sub(U,L);den=dot(d,du)
    if abs(den)<1e-10: raise ValueError('Near-singular closure')
    s=dot(d,dl)/den
    gLL=dot(dl,dl)-dot(d,dll)
    gLU=-dot(du,dl)
    gUU=dot(du,du)+dot(d,duu)
    second=-(gLL+2*gLU*s+gUU*s*s)/den
    return state.q_U_rad,s,second


def evaluate(geometry,records,side,q):
    corner=geometry.corner('front',side)
    qU,s,second=closure(corner,q,geometry.geometry_id)
    members=[];derivative=0.;direct=0.;transport_error=0.
    for record in records:
        if record['side']!=side: continue
        arm=corner.wishbone;prefix=record['arm']
        fore=getattr(arm,prefix+'_fore_inboard').position_m
        aft=getattr(arm,prefix+'_aft_inboard').position_m
        u=axis(fore,aft)
        angle=qU if prefix=='upper' else q
        scale=s if prefix=='upper' else 1.
        scale_prime=second if prefix=='upper' else 0.
        cg0=tuple(x*.0254 for x in record['cg_in'])
        cg=rotate_point_about_hinge(cg0,fore,aft,angle)
        a=record['centroidal_entries_lb_in2']
        I0=physical_tensor_from_entries(tuple(tuple(a[3*i+j]*.45359237*.0254**2 for j in range(3)) for i in range(3)),convention=record['entry_convention'])
        I=rotate_tensor(I0,fore,aft,angle)
        base=cross(u,sub(cg,fore))
        v=tuple(scale*x for x in base);w=tuple(scale*x for x in u)
        mass=record['mass_lb']*.45359237
        m=RigidMemberKinematics(record['member_id'],'COM SU row '+str(record['row']),
            'WUFR26-tubes-fixed-chassis', 'CAD-xyz',side+':'+repr(q),('qL',),('rad',),mass,I,
            tuple((x,) for x in v),tuple((x,) for x in w))
        members.append(m)
        # For rotation about a fixed hinge, base norm and axial moment are invariant.
        coefficient=mass*dot(base,base)+dot(u,tuple(dot(row,u) for row in I))
        derivative+=2*coefficient*scale*scale_prime
        direct+=.5*(mass*dot(v,v)+dot(w,tuple(dot(row,w) for row in I)))
        transport_error=max(transport_error,abs(sum(I[i][i] for i in range(3))-sum(I0[i][i] for i in range(3))))
    reduced=reduce_member_inertia(members,expected_member_ids=[r['member_id'] for r in records if r['side']==side])
    return dict(metric=reduced.matrix[0][0],metric_derivative=derivative,qU=qU,ratio=s,ratio_derivative=second,
                energy_error=reduced.kinetic_energy_J((1.,))-direct,trace_error=transport_error)


def main():
    source=ROOT/'data_catalog/wufr26_front_arm_tubes_inertia_v0.json'
    geometry_path=ROOT/'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml'
    records=json.loads(source.read_text())['members']
    geometry=load_optimumk_geometry_snapshot(geometry_path)
    samples=[]
    for side in ('left','right'):
        for q in (-.06,-.03,0.,.03,.06):
            e=evaluate(geometry,records,side,q)
            errors=[]
            for h in (.001,.0005):
                minus=evaluate(geometry,records,side,q-h);plus=evaluate(geometry,records,side,q+h)
                errors.append(dict(metric_derivative=abs((plus['metric']-minus['metric'])/(2*h)-e['metric_derivative']),
                    ratio_derivative=abs((plus['ratio']-minus['ratio'])/(2*h)-e['ratio_derivative'])))
            cg_errors=[]
            corner=geometry.corner('front',side)
            h=.0005
            qUminus=closure(corner,q-h,geometry.geometry_id)[0]
            qUplus=closure(corner,q+h,geometry.geometry_id)[0]
            for record in records:
                if record['side']!=side: continue
                prefix=record['arm'];arm=corner.wishbone
                fore=getattr(arm,prefix+'_fore_inboard').position_m
                aft=getattr(arm,prefix+'_aft_inboard').position_m
                cg0=tuple(v*.0254 for v in record['cg_in'])
                angles=(qUminus,qUplus) if prefix=='upper' else (q-h,q+h)
                minus,plus=[rotate_point_about_hinge(cg0,fore,aft,a) for a in angles]
                numerical=tuple(v/(2*h) for v in sub(plus,minus))
                angle=e['qU'] if prefix=='upper' else q
                scale=e['ratio'] if prefix=='upper' else 1.
                current=rotate_point_about_hinge(cg0,fore,aft,angle)
                analytic=tuple(scale*v for v in cross(axis(fore,aft),sub(current,fore)))
                cg_errors.append(norm(sub(numerical,analytic)))
            e.update(side=side,qL=q,finite_difference_errors=errors,CG_derivative_max_error_m_per_rad=max(cg_errors))
            samples.append(e)
    # Prescribed motion is a verification fixture, not a force-driven vehicle prediction.
    duration=.8
    def work_case(n,convective):
        dt=duration/n;power=[];energies=[]
        for i in range(n+1):
            t=i*dt;q=.04*math.sin(7*t);qd=.28*math.cos(7*t);qdd=-1.96*math.sin(7*t)
            e=evaluate(geometry,records,'left',q)
            torque=e['metric']*qdd+( .5*e['metric_derivative']*qd*qd if convective else 0.)
            power.append(torque*qd);energies.append(.5*e['metric']*qd*qd)
        work=dt*(sum(power)-.5*(power[0]+power[-1]))
        change=energies[-1]-energies[0]
        return dict(steps=n,work_J=work,kinetic_energy_change_J=change,residual_J=work-change)
    work=[work_case(n,True) for n in (200,400,800)]
    negative=work_case(800,False)
    housing_path=ROOT/'data_catalog/wufr26_front_housings_inertia_v0.json'
    housing=[]
    for record in json.loads(housing_path.read_text())['members']:
        variants={}
        for convention in ('positive_products','physical_tensor'):
            a=record['centroidal_entries_lb_in2']
            I=physical_tensor_from_entries(tuple(tuple(a[3*i+j]*.45359237*.0254**2 for j in range(3)) for i in range(3)),convention=convention)
            try:
                RigidMemberKinematics(record['member_id'],'COM','candidate','CAD','nominal',('q',),('rad',),record['mass_lb']*.45359237,I,((0.,),(0.,),(0.,)),((0.,),(0.,),(0.,)))
                variants[convention]='physicality_pass'
            except ValueError as error: variants[convention]=str(error)
        housing.append(dict(row=record['row'],variants=variants,source_binding_passed=False,reason='Physicality does not discriminate signs; housing-specific orientation evidence pending.'))
    manufactured=rotate_tensor(((2.,.3,.4),(.3,3.,.5),(.4,.5,4.)),(0.,0.,0.),(0.,0.,1.),math.pi/2)
    expected=((3.,-.3,-.5),(-.3,2.,.4),(-.5,.4,4.))
    checks=dict(manufactured_tensor_rotation=max(abs(manufactured[i][j]-expected[i][j]) for i in range(3) for j in range(3))<1e-12,
        reflected_metrics=all(abs(samples[i]['metric']-samples[9-i]['metric'])<1e-12 for i in range(5)),
        reflected_derivatives=all(abs(samples[i]['metric_derivative']+samples[9-i]['metric_derivative'])<1e-12 for i in range(5)),
        ten_native_states=len(samples)==10,
        positive_metrics=all(e['metric']>0 for e in samples),
        metric_derivative=all(e['finite_difference_errors'][-1]['metric_derivative']<1e-7 for e in samples),
        closure_second_derivative=all(e['finite_difference_errors'][-1]['ratio_derivative']<1e-5 for e in samples),
        CG_transport=all(e['CG_derivative_max_error_m_per_rad']<1e-7 for e in samples),
        direct_energy=all(abs(e['energy_error'])<1e-12 for e in samples),
        tensor_trace=all(e['trace_error']<1e-12 for e in samples),
        work_energy=abs(work[-1]['residual_J'])<1e-8,
        work_refines=all(abs(work[i]['residual_J'])>3*abs(work[i+1]['residual_J']) for i in range(2)),
        omitted_convective_term_detected=abs(negative['residual_J'])>10*abs(work[-1]['residual_J']))
    nominal=json.loads((ROOT/'docs/reports/front_arm_tube_inertia_v0.1.0/results.json').read_text())
    checks['nominal_matrix_anchor']=abs(samples[2]['metric']-nominal['mass_matrix'][2][2])<1e-12 and nominal['passed']
    checks['housing_candidates_unbound']=len(housing)==4 and not any(r['source_binding_passed'] for r in housing)
    report=dict(scope='Four tubes per corner; fixed chassis; independent 1-DOF qL; nominal source tensors transported through sampled travel',
        samples=samples,work_energy_cases=work,omitted_convective_negative_control=negative,housing_diagnostics=housing,
        checks=checks,passed=all(checks.values()),
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,geometry_path,housing_path,Path(__file__),ROOT/'src/pssd_suspension/reduced_inertia.py',ROOT/'src/pssd_suspension/kinematics.py',ROOT/'scripts/run_front_arm_tube_inertia.py',ROOT/'docs/reports/front_arm_tube_inertia_v0.1.0/results.json')})
    output=ROOT/'docs/reports/front_tube_travel_v0.1.0';output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
