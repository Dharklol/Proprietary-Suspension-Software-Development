"""BENCH-VEH-0026: source-supported welded-arm ownership and generalized gravity."""
import hashlib
import json
import math
import tomllib
from pathlib import Path
from pssd_suspension.geometry import load_optimumk_geometry_snapshot
from pssd_suspension.kinematics import rotate_point_about_hinge
from run_front_tube_travel import closure
from run_coupled_tube_inertia import pitch, cross, sub, add, scale, B
from run_front_arm_tube_inertia import axis, dot, norm
from run_no_driver_pitch_study import reconstruct, LB, IN

ROOT=Path(__file__).resolve().parents[1]
JIGS={('front','upper'):'2212894192309',('front','lower'):'2212884754818',('rear','upper'):'2212897983602',('rear','lower'):'2212895802675'}
PARTS={'SU-70103':('front','upper','housing'),'SU-70104':('front','lower','housing'),
       'SU-70105':('front','upper','fore'),'SU-70106':('front','upper','aft'),
       'SU-70107':('front','lower','fore'),'SU-70108':('front','lower','aft'),
       'SU-70203':('rear','upper','housing'),'SU-70204':('rear','lower','housing'),
       'SU-70205':('rear','upper','fore'),'SU-70206':('rear','upper','aft'),
       'SU-70207':('rear','lower','fore'),'SU-70208':('rear','lower','aft'),
       'SU-70110':('front','upper','attachment'),'SU-70111':('front','upper','attachment'),
       'SU-70210':('rear','lower','attachment'),'SU-70211':('rear','lower','attachment')}


class WeldedArmGravity:
    def __init__(self):
        self.geometry=load_optimumk_geometry_snapshot(ROOT/'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml')
        self.snapshot=json.loads((ROOT/'data_catalog/wufr26_com_pitch_snapshot_v0.json').read_text())
        self.whole=reconstruct(self.snapshot)['dry_whole_with_electrical']
        self.cg=self.whole['cg_m']
        frame=tomllib.loads((ROOT/'data_catalog/wufr26_whole_vehicle_frame_v0.toml').read_text())
        self.origins={a:frame['geometry'][a+'_axle_source_position_m'][0] for a in ('front','rear')}
        self.confirmation=json.loads((ROOT/'data_catalog/wufr26_endcap_attachment_confirmation_v0.json').read_text())
        self.members=[]
        for name in ('front','rear'):
            data=json.loads((ROOT/f'data_catalog/wufr26_{name}_corner_inventory_v0.json').read_text())
            for r in data['rows']:
                matches=[k for k in PARTS if k+'-AA' in r['part_name']]
                endcap=self.confirmation['arm_endcap_rows'].get(str(r['sheet_row']))
                if endcap:
                    if 'SU-70112-AA' not in r['part_name']: raise ValueError('Endcap part mismatch')
                    axle,arm,leg=endcap
                else:
                    if not matches: continue
                    if len(matches)!=1: raise ValueError('Ambiguous part number')
                    axle,arm,leg=PARTS[matches[0]]
                side='left' if r['cg_in'][1]>0 else 'right'
                evidence_id=None if endcap else ('2212895915302' if axle=='front' else '2212894105772') if leg=='attachment' else JIGS[(axle,arm)]
                self.members.append(dict(r,axle=axle,arm=arm,leg=leg,side=side,owner=f'{axle}_{side}_{arm}_arm',
                    attachment_owner_confirmed=bool(endcap),
                    evidence_box_id=evidence_id,mass_kg=r['CAD_mass_lb']*LB))
        if len(self.members)!=52 or len({r['sheet_row'] for r in self.members})!=52:
            raise ValueError('Exactly 52 unique arm-attached rows required')

    def evaluate(self,q):
        if len(q)!=6 or not all(math.isfinite(x) for x in q): raise ValueError('Six finite coordinates required')
        if abs(q[1])>.1 or max(map(abs,q[2:]))>.06: raise ValueError('Outside gravity fixture envelope')
        energy=0.;gradient=[0.]*6;records=[]
        for r in self.members:
            j=2+(0 if r['axle']=='front' else 2)+(0 if r['side']=='left' else 1)
            corner=self.geometry.corner(r['axle'],r['side']);arm=corner.wishbone
            upper,ratio,_=closure(corner,q[j],self.geometry.geometry_id)
            angle=upper if r['arm']=='upper' else q[j]
            s=ratio if r['arm']=='upper' else 1.
            origin=(self.origins[r['axle']],0.,0.)
            fore=add(getattr(arm,r['arm']+'_fore_inboard').position_m,origin)
            aft=add(getattr(arm,r['arm']+'_aft_inboard').position_m,origin)
            cg0=tuple(x*IN for x in r['cg_in'])
            current=rotate_point_about_hinge(cg0,fore,aft,angle)
            a=sub(current,self.cg);world=add(tuple(self.cg),(0.,0.,q[0]),pitch(a,q[1]))
            derivative=pitch(scale(s,cross(axis(fore,aft),sub(current,fore))),q[1])
            mass=r['mass_kg'];energy+=mass*9.81*world[2]
            gradient[0]+=mass*9.81
            gradient[1]+=mass*9.81*pitch(cross(B,a),q[1])[2]
            gradient[j]+=mass*9.81*derivative[2]
            distance=None
            if r['leg'] in ('fore','aft'):
                start=fore if r['leg']=='fore' else aft
                end=add(getattr(arm,r['arm']+'_upright').position_m,origin)
                unit=axis(start,end);v=sub(cg0,start)
                distance=norm(sub(v,scale(dot(v,unit),unit)))
            records.append(dict(source_row=r['sheet_row'],world_CG_m=world,reference_leg_distance_m=distance))
        return dict(potential_J=energy,generalized_gravity=tuple(-v for v in gradient),members=records)


def main():
    fixture=WeldedArmGravity();reference={(g['sheet'],r[0]):r for g in fixture.snapshot['groups'] for r in g['rows']}
    cases=[]
    for q in ((0.,)*6,(.003,.025,.02,-.015,-.02,.01)):
        result=fixture.evaluate(q);errors=[]
        for h in (.001,.0005):
            differences=[]
            for j in range(6):
                minus=list(q);plus=list(q);minus[j]-=h;plus[j]+=h
                numeric=-(fixture.evaluate(plus)['potential_J']-fixture.evaluate(minus)['potential_J'])/(2*h)
                differences.append(abs(numeric-result['generalized_gravity'][j]))
            errors.append(differences)
        cases.append(dict(q=q,**result,energy_gradient_errors=errors))
    total=fixture.whole['mass_kg'];mass=sum(r['mass_kg'] for r in fixture.members)
    moment=[sum(r['mass_kg']*r['cg_in'][i]*IN for r in fixture.members) for i in range(3)]
    residual_mass=total-mass
    residual_CG=[(total*fixture.cg[i]-moment[i])/residual_mass for i in range(3)]
    evidence=json.loads((ROOT/'data_catalog/wufr26_welded_arm_ownership_evidence_v0.json').read_text())
    evidence_by_id={r['box_file_id']:r for r in evidence['records']}
    rod_endcaps=[]
    for axle,rows in fixture.confirmation['rod_endcap_rows'].items():
        inventory=json.loads((ROOT/f'data_catalog/wufr26_{axle}_corner_inventory_v0.json').read_text())
        for r in inventory['rows']:
            if r['sheet_row'] in rows:
                side='left' if r['cg_in'][1]>0 else 'right'
                rod_endcaps.append(dict(r,owner=f'{axle}_{side}_'+('pullrod' if axle=='front' else 'pushrod'),gravity_pose_bound=False))
    checks=dict(rod_endcap_manifest=len(rod_endcaps)==8 and len({r['sheet_row'] for r in rod_endcaps})==8 and all('END CAP, 0.75 OD TURNBUCKLE' in r['part_name'] for r in rod_endcaps),
        source_ownership_evidence=all((r['attachment_owner_confirmed'] and str(r['sheet_row']) in fixture.confirmation['arm_endcap_rows']) or (any(part+'-AA' in r['part_name'] for part in evidence_by_id[r['evidence_box_id']]['parts']) and evidence_by_id[r['evidence_box_id']]['owner']==r['axle']+'_'+r['arm']+'_arm') for r in fixture.members),
        exact_52_manifest=len(fixture.members)==52,
        source_mass_CG_unchanged=all(r['CAD_mass_lb']==reference[('SU',r['sheet_row'])][1] and r['cg_in']==reference[('SU',r['sheet_row'])][2:5] for r in fixture.members),
        eight_arm_owners=len({r['owner'] for r in fixture.members})==8 and all(sum(x['owner']==r['owner'] for x in fixture.members)==(8 if (r['axle'],r['arm']) in (('front','upper'),('rear','lower')) else 5) for r in fixture.members),
        tube_geometry=all(m['reference_leg_distance_m'] is None or m['reference_leg_distance_m']<1e-4 for m in cases[0]['members']),
        gravity_energy_gradient=all(max(c['energy_gradient_errors'][-1])<1e-5 for c in cases),
        total_vertical_weight=all(abs(c['generalized_gravity'][0]+mass*9.81)<1e-12 for c in cases),
        remaining_mass_not_added=abs(residual_mass+mass-total)<1e-12,
        remaining_first_moments=max(abs(residual_mass*residual_CG[i]+moment[i]-total*fixture.cg[i]) for i in range(3))<1e-12)
    report=dict(scope='Welding-jig-supported tube/housing/tab/connector ownership and gravity only; not complete mass/inertia/static equilibrium',
        mapped_members=fixture.members,confirmed_rod_endcaps=rod_endcaps,mapped_mass_kg=mass,remaining_inventory_mass_kg=residual_mass,remaining_inventory_CG_m=residual_CG,
        remaining_inventory_is_rigid_body=False,cases=cases,checks=checks,passed=all(checks.values()),
        source_conflicts=['Rear upper jig BOM lists SU-70205/6 but its contact note says SU-70105/6. Retain typo conflict; matching rear corner BOM independently corroborates SU-70205/6.'],
        drawing_weight_policy='Jig assembly weights include the tooling; never use as arm mass.',
        unresolved=['Rod-tube/endcap pose and gravity mapping','Fastener clamping ownership','Joint mass distribution or explicit centered-ball/static approximation','Separate 27.851 lb scale mass gap'],
        tensor_policy='Gravity uses mass and CG only; no housing tensor sign or rear inertia authority is implied.')
    paths=('scripts/run_welded_arm_gravity.py','scripts/run_front_tube_travel.py','scripts/run_front_arm_tube_inertia.py','scripts/run_coupled_tube_inertia.py','scripts/run_no_driver_pitch_study.py','src/pssd_suspension/kinematics.py','data_catalog/wufr26_com_pitch_snapshot_v0.json','data_catalog/wufr26_front_corner_inventory_v0.json','data_catalog/wufr26_rear_corner_inventory_v0.json','data_catalog/wufr26_welded_arm_ownership_evidence_v0.json','data_catalog/wufr26_endcap_attachment_confirmation_v0.json','data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml','data_catalog/wufr26_whole_vehicle_frame_v0.toml')
    report['source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    out=ROOT/'docs/reports/welded_arm_gravity_v0.1.0';out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
