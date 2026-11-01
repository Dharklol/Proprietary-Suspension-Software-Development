"""Source-complete dry mass/static balance and centered-rack contact geometry audit."""
import hashlib
import json
import math
import tomllib
from pathlib import Path
from run_no_driver_pitch_study import reconstruct, LB, IN
from run_coupled_tube_inertia import pitch, sub, add, cross, B
from pssd_vehicle.static_balance import reaction_family
from pssd_vehicle.wufr_road_contact import load_wufr_road_contact_provider, evaluate_corner_point_state, ideal_rigid_circle_contact

ROOT=Path(__file__).resolve().parents[1]
CORNERS=('front_left','front_right','rear_left','rear_right')


def main():
    source_path=ROOT/'data_catalog/wufr26_com_pitch_snapshot_v0.json'
    source=json.loads(source_path.read_text());rebuilt=reconstruct(source)
    whole=rebuilt['dry_whole_with_electrical'];cg=whole['cg_m'];mass=whole['mass_kg']
    tubes=json.loads((ROOT/'data_catalog/wufr26_front_arm_tubes_inertia_v0.json').read_text())['members']
    tube_keys={('SU',r['row']) for r in tubes}
    categories={};keys=[];moments=[0.,0.,0.];summed_mass=0.
    mixed={'A0701 - FRONT CORNERS','A0702 - REAR CORNERS','A0206 - DRIVESHAFTS','A0605 - TIE RODS'}
    for group in source['groups']:
        for row,m,x,y,z,j in group['rows']:
            if row==group.get('excluded_fuel_row'): continue
            key=(group['sheet'],row);keys.append(key)
            category=('verified_front_tubes' if key in tube_keys else 'unresolved_mixed_members' if group['assembly'] in mixed
                else 'outboard_inventory' if group['sheet']=='WT' or group['assembly'] in {'A0101 - BRAKE DISCS','A0103 - CALIPERS & BRAKE PADS'} else 'body_inventory_candidates')
            entry=categories.setdefault(category,dict(rows=0,mass_kg=0.))
            entry['rows']+=1;entry['mass_kg']+=m*LB
            summed_mass+=m*LB
            for i,v in enumerate((x,y,z)): moments[i]+=m*LB*v*IN
    ep=rebuilt['electrical_point'];categories['electrical_CG_approximation']=dict(rows=1,mass_kg=ep[0])
    summed_mass+=ep[0]
    for i in range(3): moments[i]+=ep[0]*ep[i+1]
    frame_path=ROOT/'data_catalog/wufr26_whole_vehicle_frame_v0.toml'
    frame=tomllib.loads(frame_path.read_text());geo=frame['geometry']
    paths=dict(source_path='data_catalog/wufr26_road_contact_reference_v0.toml',suspension_geometry_path='data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml',
        wheel_profile_path='benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml',steering_geometry_path='configurations/steering/WUFR27_STEERING_BASELINE_V0.toml',whole_vehicle_path='data_catalog/wufr26_whole_vehicle_frame_v0.toml')
    provider=load_wufr_road_contact_provider(**{k:ROOT/v for k,v in paths.items()})
    # Use source-frame center and centered-rack plane only. Discard driver-referenced body point.
    def contact(corner,z,h,p):
        state=evaluate_corner_point_state(provider,corner,z)
        center=add(tuple(cg),(0.,0.,h),pitch(sub(state.wheel_center_source_m,cg),p))
        plane=pitch(state.wheel_plane_normal_body,p)
        result=ideal_rigid_circle_contact(center,plane,(0.,0.,1.),provider.tire_radius_m)
        return state,result,center
    samples=[]
    for corner in CORNERS:
        for z,h,p in ((0.,0.,0.),(.002,.003,.02),(-.002,-.002,-.02)):
            state,result,center=contact(corner,z,h,p)
            derivatives=[]
            for step in (.0002,.0001):
                sm,cm,_=contact(corner,z-step,h,p);sp,cp,_=contact(corner,z+step,h,p)
                dz=(cp.contact_point_m[2]-cm.contact_point_m[2])/(2*step)
                dq=(sp.q_L_rad-sm.q_L_rad)/(2*step)
                if abs(dq)<1e-6: raise ValueError('Wheel/qL map near-singular')
                derivatives.append(dict(wheel_step_m=step,dgap_dwheel=dz,dqL_dwheel=dq,dgap_dqL=dz/dq))
            eps=.0001
            _,ch,_=contact(corner,z,h+eps,p)
            _,cl,_=contact(corner,z,h-eps,p)
            heave=(ch.contact_point_m[2]-cl.contact_point_m[2])/(2*eps)
            _,cp,_=contact(corner,z,h,p+eps);_,cm,_=contact(corner,z,h,p-eps)
            pitch_derivative=(cp.contact_point_m[2]-cm.contact_point_m[2])/(2*eps)
            # Envelope theorem: normal velocity at the instantaneous geometric contact
            # under rigid pitch equals the derivative of minimum circle height.
            expected_pitch=cross(B,sub(result.contact_point_m,add(tuple(cg),(0.,0.,h))))[2]
            samples.append(dict(corner=corner,wheel_coordinate_m=z,qL_rad=state.q_L_rad,heave_m=h,pitch_rad=p,
                wheel_center_source_m=state.wheel_center_source_m,contact_world_m=result.contact_point_m,
                steering_rotation_rad=state.steering_rotation_rad,steering_closure_residual_m=state.steering_closure_residual_m,
                transform_role=state.suspension_transform_role,derivatives=derivatives,
                heave_derivative_error=heave-1.,pitch_virtual_work_error_m_per_rad=pitch_derivative-expected_pitch))
    nominal_points=[next(s['contact_world_m'] for s in samples if s['corner']==corner and s['wheel_coordinate_m']==0.) for corner in CORNERS]
    family=reaction_family(mass,cg,nominal_points[0][0],nominal_points[2][0],nominal_points[0][1],nominal_points[2][1])
    stations=[(p[0],p[1]) for p in nominal_points]
    closure=[]
    for loads in family['endpoint_loads_N']:
        closure.append(dict(force_N=sum(loads)-family['weight_N'],pitch_first_moment_Nm=sum(f*x for f,(x,y) in zip(loads,stations))-family['weight_N']*cg[0],
                            roll_first_moment_Nm=sum(f*y for f,(x,y) in zip(loads,stations))-family['weight_N']*cg[1]))
    checks=dict(unique_dry_rows=len(keys)==2468 and len(set(keys))==2468,
        represented_mass=abs(summed_mass-mass)<1e-9,
        represented_first_moments=max(abs(moments[i]-mass*cg[i]) for i in range(3))<1e-9,
        extracted_tube_mass=abs(categories['verified_front_tubes']['mass_kg']-sum(r['mass_lb']*LB for r in tubes))<1e-12,
        nominal_contact_symmetry=all(abs(nominal_points[i][0]-nominal_points[i+1][0])<1e-12 and abs(nominal_points[i][1]+nominal_points[i+1][1])<1e-12 and abs(nominal_points[i][2])<1e-12 for i in (0,2)),
        force_moment_closure=all(max(abs(v) for v in c.values())<1e-9 for c in closure),
        reaction_family_nonnegative=all(min(loads)>-1e-9 for loads in family['endpoint_loads_N']),
        front_centered_rack=all(s['steering_closure_residual_m'] is not None and abs(s['steering_closure_residual_m'])<1e-8 for s in samples if s['corner'].startswith('front')),
        wheel_qL_derivative=all(abs(s['derivatives'][0]['dgap_dqL']-s['derivatives'][1]['dgap_dqL'])<1e-4 for s in samples),
        heave_contact_virtual_work=all(abs(s['heave_derivative_error'])<1e-10 for s in samples),
        pitch_contact_virtual_work=all(abs(s['pitch_virtual_work_error_m_per_rad'])<1e-7 for s in samples))
    report=dict(scope='CAD dry no-driver total-mass/static balance and source-rebased ideal-circle geometry only; not full suspension equilibrium',
        state_id='WUFR26_CAD_NO_DRIVER_NO_FUEL_RECONSTRUCTED',reference_cg_source_m=cg,total_mass_kg=mass,mass_categories=categories,
        mass_residual_kg=summed_mass-mass,scale_mass_gap_lb=477.-mass/LB,scale_gap_policy='Unresolved; no scaling or invented ballast',
        static_reaction_family=family,nominal_support_points_source_m=nominal_points,endpoint_closure=closure,contact_samples=samples,
        full_native_static_equilibrium_passed=False,
        blocking_dependencies=['Unresolved member ownership for compatible generalized gravity and inertia','Wheel/body inventory and tire law/contact compliance','No-driver equilibrium must not inherit driver/no-fuel source gravity or CG'],
        checks=checks,passed=all(checks.values()))
    path_list=(source_path,frame_path,Path(__file__),ROOT/'src/pssd_vehicle/static_balance.py',ROOT/'scripts/run_no_driver_pitch_study.py',ROOT/'scripts/run_coupled_tube_inertia.py',ROOT/'data_catalog/wufr26_front_arm_tubes_inertia_v0.json',ROOT/'src/pssd_vehicle/wufr_road_contact.py',*(ROOT/v for v in paths.values()))
    report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in path_list}
    output=ROOT/'docs/reports/dry_static_contact_audit_v0.1.0';output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
