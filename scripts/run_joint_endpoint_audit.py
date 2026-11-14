"""BENCH-VEH-0028: endpoint candidates, centered-bearing eligibility and source gates."""
import hashlib
import json
from math import dist
from run_rod_gravity_map import RodGravity
from run_welded_arm_gravity import ROOT, IN, LB
from run_front_arm_tube_inertia import axis, dot, sub


def audit():
    fixture=RodGravity();results=[];by_axle={}
    for axle in ('front','rear'):
        inventory=json.loads((ROOT/f'data_catalog/wufr26_{axle}_corner_inventory_v0.json').read_text())
        by_axle[axle]={r['sheet_row']:r for r in inventory['rows']}
        for row in inventory['rows']:
            bearing='HAB-4TG' in row['part_name']
            if not bearing and 'Rod End' not in row['part_name']: continue
            side='left' if row['cg_in'][1]>0 else 'right'
            corner=fixture.geometry.corner(axle,side)
            points={name:getattr(corner.wishbone,name).position_m for name in (
                'upper_fore_inboard','upper_aft_inboard','lower_fore_inboard',
                'lower_aft_inboard','upper_upright','lower_upright')}
            points.update(toe_inboard=corner.toe_link.inboard.position_m,toe_outboard=corner.toe_link.outboard.position_m)
            points={name:(p[0]+fixture.arms.origins[axle],*p[1:]) for name,p in points.items()}
            a,b,*_=fixture.nominal[axle,side];points.update(rod_arm=a,rod_rocker=b)
            cg=tuple(v*IN for v in row['cg_in'])
            ranked=sorted((dist(cg,p),name) for name,p in points.items())
            # A screening band distinguishes the observed repeated-source 7.6 mm
            # offsets, not a vendor dimension or evidence of clamping ownership.
            screen=(ranked[0][0]<5e-5 if bearing else .006<ranked[0][0]<.009)
            results.append(dict(axle=axle,side=side,row=row['sheet_row'],part_name=row['part_name'],
                mass_kg=row['CAD_mass_lb']*LB,CG_source_m=cg,kind='spherical_bearing' if bearing else 'rod_end',
                candidates=[dict(endpoint=name,distance_m=d,source_position_m=points[name]) for d,name in ranked[:2]],
                candidate_screen_passed=screen,ownership_confirmed=False))
    reference=[r['candidates'][0]['distance_m'] for r in results if r['axle']=='rear' and r['kind']=='rod_end' and 'XML4' in r['part_name'] and r['candidates'][0]['endpoint']=='rod_arm']
    reference_offset=sum(reference)/len(reference)
    conflicts=[]
    for row,bolt,side in ((116,45,'left'),(117,44,'right')):
        r=next(r for r in results if r['axle']=='front' and r['row']==row)
        a,b,*_=fixture.nominal['front',side];u=axis(a,b)
        center=tuple(v*IN for v in by_axle['front'][bolt]['cg_in'])
        projection=tuple(a[i]+dot(sub(center,a),u)*u[i] for i in range(3))
        rod_end_implied=tuple(r['CG_source_m'][i]-reference_offset*u[i] for i in range(3))
        conflicts.append(dict(side=side,rod_end_row=row,fastener_row=bolt,native_arm_pickup_m=a,
            fastener_CG_projected_on_rod_m=projection,
            projected_fastener_to_native_pickup_m=dist(projection,a),
            repeated_XML4_CG_offset_m=reference_offset,
            repeated_part_implied_joint_m=rod_end_implied,
            implied_joint_to_projected_fastener_m=dist(rod_end_implied,projection),
            status='reference_correspondence_unverified',inference='Fastener projection and repeated-part CG offset are cross-checks, not measured ball centers. A physical pickup displacement is not established.'))
    bearings=[r for r in results if r['kind']=='spherical_bearing']
    clarification=json.loads((ROOT/'data_catalog/wufr26_joint_geometry_clarification_v0.json').read_text())
    raw=clarification['verified_optimumk_source']
    snapshot=fixture.geometry.corner('front','left').actuation.outboard_attachment.position_m
    checks=dict(verified_source_transcription=dist(snapshot,(raw['left_raw_mm'][0]/1000,-raw['left_raw_mm'][1]/1000,raw['left_raw_mm'][2]/1000))<1e-12,
        exact_36_unique_rows=len(results)==36 and len({(r['axle'],r['row']) for r in results})==36,
        counts=sum(r['kind']=='rod_end' for r in results)==28 and len(bearings)==8,
        distinct_nearest_candidates=len({(r['axle'],r['side'],r['candidates'][0]['endpoint']) for r in results})==36,
        bearing_center_eligibility=all(r['candidate_screen_passed'] and r['candidates'][0]['endpoint'].endswith('_upright') for r in bearings),
        front_conflicts_preserved={(r['axle'],r['row']) for r in results if not r['candidate_screen_passed']}=={('front',116),('front',117)},
        conflict_crosscheck=all(.018<c['projected_fastener_to_native_pickup_m']<.0186 and c['implied_joint_to_projected_fastener_m']<5e-5 for c in conflicts),
        no_ownership_promotion=all(not r['ownership_confirmed'] for r in results))
    return dict(scope='Nominal endpoint screening and reference correspondence diagnosis; no joint/clamp gravity or full equilibrium promotion',
        owner_geometry_history=clarification['history_status'],
        physical_pickup_displacement_confirmed=False,
        reference_limit=clarification['reference_limit'],
        results=results,front_source_conflicts=conflicts,
        centered_bearing_point_potential_difference_bound_J=sum(r['mass_kg']*9.81*r['candidates'][0]['distance_m'] for r in bearings),
        bearing_policy='All eight whole-part CGs are within 50 micrometres of a joint center. This supports an explicitly approximate static point-mass treatment only; it does not verify inner-ball mass split or tensor rotation.',
        checks=checks,passed=all(checks.values()),joint_ownership_gate_passed=False)


def main():
    report=audit()
    paths=('scripts/run_joint_endpoint_audit.py','scripts/run_rod_gravity_map.py','scripts/run_welded_arm_gravity.py',
        'data_catalog/wufr26_front_corner_inventory_v0.json','data_catalog/wufr26_rear_corner_inventory_v0.json',
        'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml','data_catalog/wufr26_whole_vehicle_frame_v0.toml',
        'data_catalog/wufr26_joint_geometry_clarification_v0.json')
    report['source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    out=ROOT/'docs/reports/joint_endpoint_audit_v0.1.0';out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
