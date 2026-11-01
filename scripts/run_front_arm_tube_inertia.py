"""Nominal bilateral tube subset with compatible upper/lower inertia columns."""
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
from pssd_suspension.reduced_inertia import RigidMemberKinematics, reduce_member_inertia, physical_tensor_from_entries
from pssd_suspension.geometry import load_optimumk_geometry_snapshot
from pssd_suspension.kinematics import rotate_point_about_hinge, solve_corner_state

ROOT=Path(__file__).resolve().parents[1]


def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def norm(a): return math.sqrt(dot(a,a))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def axis(a,b):
    v=sub(b,a)
    return tuple(x/norm(v) for x in v)


def closure_ratio(arm):
    uL=axis(arm.lower_fore_inboard.position_m,arm.lower_aft_inboard.position_m)
    uU=axis(arm.upper_fore_inboard.position_m,arm.upper_aft_inboard.position_m)
    d=sub(arm.upper_upright.position_m,arm.lower_upright.position_m)
    dl=cross(uL,sub(arm.lower_upright.position_m,arm.lower_fore_inboard.position_m))
    du=cross(uU,sub(arm.upper_upright.position_m,arm.upper_fore_inboard.position_m))
    denominator=dot(d,du)
    if abs(denominator)<1e-10: raise ValueError('Near-singular upper closure tangent')
    return dot(d,dl)/denominator


def main():
    path=ROOT/'data_catalog/wufr26_front_arm_tubes_inertia_v0.json'
    data=json.loads(path.read_text())
    geometry_path=ROOT/'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml'
    geometry=load_optimumk_geometry_snapshot(geometry_path)
    budget_path=ROOT/'docs/reports/no_driver_mass_consistency_v0.1.0/results.json'
    body_cg=json.loads(budget_path.read_text())['cases'][1]['budget']['body']['cg_m']
    members=[]
    diagnostics=[]
    ratios={}
    for side in ('left','right'):
        corner=geometry.corner('front',side)
        arm=corner.wishbone
        ratio=closure_ratio(arm)
        errors=[]
        for h in (.001,.0005):
            states=[solve_corner_state(corner,q,geometry_id=geometry.geometry_id) for q in (-h,h)]
            if not all(s.ok for s in states): raise ValueError('Native upper closure unavailable')
            numerical=(states[1].q_U_rad-states[0].q_U_rad)/(2*h)
            errors.append(abs(numerical-ratio)/abs(ratio))
        ratios[side]=dict(analytic_dqU_dqL=ratio,relative_errors=errors,passed=errors[-1]<1e-6)
    for record in data['members']:
        item=dict(member_id=record['member_id'],source_row=record['row'])
        try:
            side=record['side']
            corner=geometry.corner('front',side)
            arm=corner.wishbone
            prefix=record['arm']
            fore=getattr(arm,prefix+'_fore_inboard').position_m
            aft=getattr(arm,prefix+'_aft_inboard').position_m
            endpoint=getattr(arm,prefix+'_upright').position_m
            start=fore if record['leg']=='fore' else aft
            direction=axis(start,endpoint)
            cg=tuple(v*.0254 for v in record['cg_in'])
            projection=dot(sub(cg,start),direction)
            distance=norm(tuple(v-projection*u for v,u in zip(sub(cg,start),direction)))
            scale=ratios[side]['analytic_dqU_dqL'] if prefix=='upper' else 1.
            hinge=axis(fore,aft)
            relative=tuple(scale*v for v in cross(hinge,sub(cg,fore)))
            pitch=cross((0.,-1.,0.),sub(cg,body_cg))
            active=2 if side=='left' else 3
            v=tuple(tuple(float(i==2) if j==0 else pitch[i] if j==1 else relative[i] if j==active else 0. for j in range(4)) for i in range(3))
            w=tuple(tuple(-float(i==1) if j==1 else scale*hinge[i] if j==active else 0. for j in range(4)) for i in range(3))
            tensor=physical_tensor_from_entries(tuple(tuple(record['centroidal_entries_lb_in2'][3*i+j]*.45359237*.0254**2 for j in range(3)) for i in range(3)),convention=record['entry_convention'])
            ray=dot(direction,tuple(dot(row,direction) for row in tensor))/sum(tensor[i][i] for i in range(3))
            member=RigidMemberKinematics(record['member_id'],data['source_url']+f'#SU!B{record["row"]}:P{record["row"]}',
                'WUFR26-front-tube-subset-no-driver','CAD-xyz','nominal-qL-zero',
                ('body_heave','body_pitch_front_up','left_qL','right_qL'),('m','rad','rad','rad'),
                record['mass_lb']*.45359237,tensor,v,w)
            errors=[]
            for h in (.001,.0005):
                angles=[]
                for q in (-h,h):
                    state=solve_corner_state(corner,q,geometry_id=geometry.geometry_id)
                    if not state.ok: raise ValueError(state.message)
                    angles.append(state.q_U_rad if prefix=='upper' else q)
                minus,plus=[rotate_point_about_hinge(cg,fore,aft,q) for q in angles]
                numerical=tuple((a-b)/(2*h) for a,b in zip(plus,minus))
                errors.append(norm(sub(numerical,relative))/norm(relative))
            checks=dict(physical_tensor=True,CG_on_reference_leg=distance<1e-4,
                CG_inside_leg=0<projection<norm(sub(endpoint,start)),slender_axis=ray<.01,
                CG_derivative=errors[-1]<1e-6,upper_closure=ratios[side]['passed'])
            item.update(CG_line_distance_m=distance,axial_moment_trace_ratio=ray,
                CG_derivative_relative_errors=errors,checks=checks,passed=all(checks.values()),member=asdict(member))
            if item['passed']: members.append(member)
        except ValueError as error:
            item.update(passed=False,failure=str(error))
        diagnostics.append(item)
    if len(data['members'])!=8 or len({r['member_id'] for r in data['members']})!=8:
        raise ValueError('Expected exactly eight unique tube instances')
    report=dict(scope='nominal bilateral front wishbone tube subset only',members=diagnostics,
        upper_closure_derivatives=ratios,body_reference_CG_m=body_cg,passed=False)
    if all(d['passed'] for d in diagnostics):
        result=reduce_member_inertia(members,expected_member_ids=tuple(d['member_id'] for d in data['members']))
        rates=(.1,.2,-.3,.4)
        direct=0.
        for m in members:
            v=tuple(dot(row,rates) for row in m.cg_velocity_jacobian)
            w=tuple(dot(row,rates) for row in m.angular_velocity_jacobian)
            direct+=.5*m.mass_kg*dot(v,v)+.5*dot(w,tuple(dot(row,w) for row in m.centroidal_tensor_kg_m2))
        energy=result.kinetic_energy_J(rates)
        perm=(0,1,3,2);sign=(1,1,-1,-1)
        mirror_errors=[abs(result.matrix[i][j]-sign[i]*sign[j]*result.matrix[perm[i]][perm[j]]) for i in range(4) for j in range(4)]
        mirror_pass=all(abs(result.matrix[i][j]-sign[i]*sign[j]*result.matrix[perm[i]][perm[j]])<=max(1e-8,.005*abs(result.matrix[i][j])) for i in range(4) for j in range(4))
        mass=sum(m.mass_kg for m in members)
        report.update(mass_matrix=result.matrix,direct_energy_J=direct,reduced_energy_J=energy,
            energy_difference_J=energy-direct,total_tube_mass_kg=mass,
            front_corner_CAD_mass_kg=5.068*.45359237,mass_coverage_fraction=mass/(5.068*.45359237),
            reflection_max_entry_difference=max(mirror_errors),reflection_passed=mirror_pass,
            passed=abs(energy-direct)<1e-12 and mirror_pass)
    report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (path,geometry_path,budget_path,Path(__file__),ROOT/'src/pssd_suspension/reduced_inertia.py')}
    output=ROOT/'docs/reports/front_arm_tube_inertia_v0.1.0'
    output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
