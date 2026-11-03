"""BENCH-VEH-0027: fixed tube/endcap rod pose and conditional gravity mapping."""
import hashlib
import json
import math
from pathlib import Path
from pssd_suspension import load_wufr26_wheel_reference_profile, build_nominal_wheel_reference
from pssd_suspension.actuation import solve_actuation_q_L_state
from pssd_suspension.kinematics import KinematicsSolverConfig
from pssd_suspension.rod_pose import transport_rod_offset
from run_welded_arm_gravity import WeldedArmGravity, ROOT, LB, IN
from run_front_arm_tube_inertia import axis, dot, norm, cross, sub
from run_coupled_tube_inertia import add, scale, pitch, B
from run_front_tube_travel import closure


class RodGravity:
    def __init__(self):
        self.arms=WeldedArmGravity();self.geometry=self.arms.geometry
        self.wheel=load_wufr26_wheel_reference_profile(ROOT/'benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml')
        self.nominal={};self.members=[]
        for axle in ('front','rear'):
            for side in ('left','right'): self.nominal[(axle,side)]=self.endpoints(axle,side,0.)
            data=json.loads((ROOT/f'data_catalog/wufr26_{axle}_corner_inventory_v0.json').read_text())
            for r in data['rows']:
                tube=('SU-70109-AA' if axle=='front' else 'SU-70209-AA') in r['part_name']
                cap=r['sheet_row'] in self.arms.confirmation['rod_endcap_rows'][axle]
                if not (tube or cap): continue
                side='left' if r['cg_in'][1]>0 else 'right'
                a,b,_,_=self.nominal[(axle,side)];d=sub(b,a);length=norm(d);u=scale(1/length,d)
                cg=tuple(v*IN for v in r['cg_in']);v=sub(cg,a)
                fraction=dot(v,u)/length;offset=sub(v,scale(fraction,d))
                if not 0<fraction<1 or norm(offset)>1e-4:
                    raise ValueError('Source CG is not inside the declared rod reference line')
                self.members.append(dict(r,axle=axle,side=side,mass_kg=r['CAD_mass_lb']*LB,
                    fraction=fraction,offset_m=offset,radial_offset_m=norm(offset),kind='tube' if tube else 'confirmed_endcap'))
        if len(self.members)!=12 or len({r['sheet_row'] for r in self.members})!=12:
            raise ValueError('Exactly four rod tubes and eight endcaps required')

    def endpoints(self,axle,side,q):
        corner=self.geometry.corner(axle,side)
        nominal=build_nominal_wheel_reference(self.wheel,axle,side)
        state=solve_actuation_q_L_state(corner,nominal,q,geometry_id=self.geometry.geometry_id,
            source_authority=self.geometry.authority,kinematics_config=KinematicsSolverConfig(length_residual_tolerance_m=1e-13,squared_residual_zero_tolerance_m2=1e-20,root_angle_tolerance_rad=1e-13))
        if not state.ok: raise ValueError('Native rod closure failed: '+state.message)
        prefix='upper' if axle=='front' else 'lower';arm=corner.wishbone
        fore=getattr(arm,prefix+'_fore_inboard').position_m;a=state.arm_attachment_m;b=state.rocker_rod_point_m
        s=closure(corner,q,self.geometry.geometry_id)[1] if axle=='front' else 1.
        ap=scale(s,cross(axis(fore,getattr(arm,prefix+'_aft_inboard').position_m),sub(a,fore)))
        pivot=corner.actuation.rocker_pivot.position_m
        tangent=cross(axis(pivot,corner.actuation.rocker_axis_reference.position_m),sub(b,pivot))
        denominator=dot(sub(b,a),tangent)
        if abs(denominator)<1e-10: raise ValueError('Near-singular rod/rocker closure')
        theta=dot(sub(b,a),ap)/denominator
        bp=scale(theta,tangent)
        origin=(self.arms.origins[axle],0.,0.)
        return add(a,origin),add(b,origin),ap,bp

    def evaluate(self,q):
        if len(q)!=6 or not all(math.isfinite(v) for v in q): raise ValueError('Six finite coordinates required')
        if abs(q[1])>.1 or max(map(abs,q[2:]))>.06: raise ValueError('Outside rod fixture envelope')
        endpoints={};energy=0.;gradient=[0.]*6;details=[]
        for r in self.members:
            j=2+(0 if r['axle']=='front' else 2)+(0 if r['side']=='left' else 1)
            key=(r['axle'],r['side'])
            if key not in endpoints: endpoints[key]=self.endpoints(*key,q[j])
            a,b,ap,bp=endpoints[key];a0,b0,_,_=self.nominal[key]
            d=sub(b,a);dp=sub(bp,ap);length=norm(d);u=scale(1/length,d)
            up=scale(1/length,sub(dp,scale(dot(u,dp),u)))
            o,op=transport_rod_offset(axis(a0,b0),u,up,r['offset_m'])
            cg=add(a,scale(r['fraction'],d),o)
            cgp=add(ap,scale(r['fraction'],dp),op)
            relative=sub(cg,self.arms.cg)
            world=add(tuple(self.arms.cg),(0.,0.,q[0]),pitch(relative,q[1]))
            m=r['mass_kg'];energy+=m*9.81*world[2]
            gradient[0]+=m*9.81;gradient[1]+=m*9.81*pitch(cross(B,relative),q[1])[2]
            gradient[j]+=m*9.81*pitch(cgp,q[1])[2]
            details.append(dict(source_row=r['sheet_row'],source_CG_m=cg,world_CG_m=world,
                CG_derivative_m_per_rad=cgp,rod_length_error_m=length-norm(sub(b0,a0)),
                distance_to_arm_end_m=norm(sub(cg,a)),distance_to_rocker_end_m=norm(sub(cg,b))))
        return dict(potential_J=energy,generalized_gravity=tuple(-v for v in gradient),members=details)


def main():
    fixture=RodGravity();cases=[]
    for q in ((0.,)*6,(.003,.02,.02,-.015,-.02,.01)):
        result=fixture.evaluate(q);errors=[]
        for h in (.001,.0005):
            e=[]
            for j in range(6):
                minus=list(q);plus=list(q);minus[j]-=h;plus[j]+=h
                e.append(abs(-(fixture.evaluate(plus)['potential_J']-fixture.evaluate(minus)['potential_J'])/(2*h)-result['generalized_gravity'][j]))
            errors.append(e)
        cases.append(dict(q=q,**result,energy_gradient_errors=errors))
    mass=sum(r['mass_kg'] for r in fixture.members);arms=fixture.arms.members
    all_members=arms+fixture.members;total=fixture.arms.whole['mass_kg']
    remaining=total-sum(r['mass_kg'] for r in all_members)
    moments=[sum(r['mass_kg']*r['cg_in'][i]*IN for r in all_members) for i in range(3)]
    remainder_CG=[(total*fixture.arms.cg[i]-moments[i])/remaining for i in range(3)]
    nominal_by_row={r['sheet_row']:r for r in fixture.members}
    nominal_error=max(norm(sub(d['source_CG_m'],tuple(v*IN for v in nominal_by_row[d['source_row']]['cg_in']))) for d in cases[0]['members'])
    rigid_errors=[]
    for a,b in zip(cases[0]['members'],cases[1]['members']):
        rigid_errors.extend(abs(a[k]-b[k]) for k in ('distance_to_arm_end_m','distance_to_rocker_end_m'))
    gravity_bound=sum(2*r['mass_kg']*9.81*r['radial_offset_m'] for r in fixture.members)
    checks=dict(exact_12_manifest=len(fixture.members)==12 and sum(r['kind']=='confirmed_endcap' for r in fixture.members)==8,
        nominal_CG_preserved=nominal_error<1e-12,
        native_length_closure=all(abs(d['rod_length_error_m'])<1e-9 for c in cases for d in c['members']),
        rigid_endpoint_distances=max(rigid_errors)<1e-9,
        gravity_energy_gradient=all(max(c['energy_gradient_errors'][-1])<1e-5 for c in cases),
        combined_64_unique=len(all_members)==64 and len({r['sheet_row'] for r in all_members})==64,
        combined_mass_closure=abs(remaining+sum(r['mass_kg'] for r in all_members)-total)<1e-12,
        combined_first_moments=max(abs(remaining*remainder_CG[i]+moments[i]-total*fixture.arms.cg[i]) for i in range(3))<1e-12)
    report=dict(scope='Four rods plus eight fixed endcaps; conditional no-axial-spin CG transport and gravity, not full rod inertia',
        members=fixture.members,mapped_rod_mass_kg=mass,cases=cases,checks=checks,passed=all(checks.values()),
        nominal_CG_max_error_m=nominal_error,rigid_distance_max_error_m=max(rigid_errors),
        unknown_axial_spin_potential_difference_bound_J=gravity_bound,
        spin_policy='Shortest rotation from nominal rod direction. Axial spin is not source-defined; only the pose-wise gravitational potential difference is bounded. No torque/rate or full rotational inertia bound claimed.',
        combined_arm_and_rod_mass_kg=sum(r['mass_kg'] for r in all_members),remaining_inventory_mass_kg=remaining,
        remaining_inventory_CG_m=remainder_CG,remaining_is_rigid_body=False)
    paths=('scripts/run_rod_gravity_map.py','scripts/run_welded_arm_gravity.py','scripts/run_front_tube_travel.py','scripts/run_front_arm_tube_inertia.py','scripts/run_coupled_tube_inertia.py','data_catalog/wufr26_front_corner_inventory_v0.json','data_catalog/wufr26_rear_corner_inventory_v0.json','data_catalog/wufr26_endcap_attachment_confirmation_v0.json','data_catalog/wufr26_com_pitch_snapshot_v0.json','data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml','data_catalog/wufr26_whole_vehicle_frame_v0.toml','benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml','src/pssd_suspension/rod_pose.py','src/pssd_suspension/actuation.py','src/pssd_suspension/kinematics.py')
    report['source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    out=ROOT/'docs/reports/rod_gravity_map_v0.1.0';out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
