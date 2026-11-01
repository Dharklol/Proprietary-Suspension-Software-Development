"""Rebuild COM pitch moments and run explicitly provisional inertia-only cases."""
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
from pssd_vehicle.half_car import HalfCar, simulate_half_car
from pssd_vehicle.reduced_ride import cosine_bump

ROOT=Path(__file__).resolve().parents[1]
LB=.45359237
IN=.0254


def combine(rows):
    """Rows are [mass kg,x m,y m,z m,centroidal Jy kg*m²]."""
    if not rows or any(not math.isfinite(v) for row in rows for v in row):
        raise ValueError('Finite represented mass records required')
    if any(r[0]<0 or r[4]<0 for r in rows):
        raise ValueError('Negative mass/inertia')
    mass=sum(r[0] for r in rows)
    if mass<=0: raise ValueError('Positive total mass required')
    cg=tuple(sum(r[0]*r[j] for r in rows)/mass for j in (1,2,3))
    inertia=sum(r[4]+r[0]*((r[1]-cg[0])**2+(r[3]-cg[2])**2) for r in rows)
    origin=sum(r[4]+r[0]*(r[1]**2+r[3]**2) for r in rows)
    independent=origin-mass*(cg[0]**2+cg[2]**2)
    if abs(inertia-independent)>1e-8: raise ValueError('Parallel-axis cross-check failed')
    return dict(mass_kg=mass,cg_m=cg,pitch_inertia_kg_m2=inertia,
                independent_origin_shift_kg_m2=independent)


def reconstruct(source):
    all_rows=[]
    for g in source['groups']:
        for row,m,x,y,z,jy in g['rows']:
            values=(m,x,y,z,jy)
            if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values):
                raise ValueError('Malformed snapshot row')
            all_rows.append((g['sheet'],g['assembly'],row,[m*LB,x*IN,y*IN,z*IN,jy*LB*IN**2],row==g.get('excluded_fuel_row')))
    if len(all_rows)!=2469: raise ValueError('Unexpected snapshot row count')
    electrical=source['electrical_mass_lb']*LB
    wet_mass=sum(p[3][0] for p in all_rows)+electrical
    if abs(wet_mass/LB-461.149)>1e-6: raise ValueError('CAD wet mass mismatch')
    fuel=[p for p in all_rows if p[4]]
    if len(fuel)!=1 or abs(fuel[0][3][0]/LB-12)>1e-9: raise ValueError('Fuel identity/mass mismatch')
    dry=[p for p in all_rows if not p[4]]
    whole=combine([p[3] for p in dry])
    ep=[electrical,*whole['cg_m'],0.]
    dry_with_electrical=combine([p[3] for p in dry]+[ep])
    if abs(dry_with_electrical['mass_kg']/LB-449.149)>1e-6: raise ValueError('Dry mass mismatch')
    mixed={'A0701 - FRONT CORNERS','A0702 - REAR CORNERS','A0206 - DRIVESHAFTS','A0605 - TIE RODS'}
    scenarios=[]
    assignments=[]
    for sheet,assembly,row,record,_ in dry:
        category=('outboard' if sheet=='WT' or assembly in {'A0101 - BRAKE DISCS','A0103 - CALIPERS & BRAKE PADS'}
                  else 'mixed' if assembly in mixed else 'body')
        assignments.append((category,record))
    for f in (0.,.5,1.):
        body=[ep]
        for category,record in assignments:
            if category=='outboard': continue
            m,x,y,z,jy=record
            scale=f if category=='mixed' else 1.
            body.append([scale*m,x,y,z,scale*jy])
        scenarios.append(dict(mixed_fraction_retained=f,**combine(body)))
    return dict(scope='CAD-derived provisional no-driver/no-fuel reconstruction; not native inertia authority',
        populated_dry_subset=whole,dry_whole_with_electrical=dry_with_electrical,
        electrical_point=ep,category_mass_kg={c:sum(r[0] for k,r in assignments if k==c) for c in ('body','mixed','outboard')},
        allocation_scenarios=scenarios)


def metrics(system,dt):
    run=simulate_half_car(system,cosine_bump(.001,.1,.2),cosine_bump(.001,.3,.2),
        road_source_ids=('illustrative-front','illustrative-rear-delayed'),dt=dt,steps=round(2/dt))
    if not run.ok: raise ValueError(f'{run.failure_code} at {run.failure_time}')
    return run,dict(peak_abs_pitch_rad=max(abs(x.state[1]) for x in run.samples),
        peak_abs_pitch_acceleration_rad_s2=max(abs(x.evaluation.derivative[5]) for x in run.samples),
        peak_abs_body_acceleration_m_s2=max(abs(x.evaluation.derivative[4]) for x in run.samples),
        peak_normal_load_N=max(max(x.evaluation.normal_loads) for x in run.samples),
        max_energy_residual_J=max(abs(x.energy_residual) for x in run.samples))


def main():
    snapshot=ROOT/'data_catalog/wufr26_com_pitch_snapshot_v0.json'
    source=json.loads(snapshot.read_text())
    report=reconstruct(source)
    middle=report['allocation_scenarios'][1]
    a=-middle['cg_m'][0]
    cases=[]
    for scenario in report['allocation_scenarios']:
        s=HalfCar(middle['mass_kg'],scenario['pitch_inertia_kg_m2'],a,1.5624-a,
            18.,18.,50000.,65000.,360000.,380000.,800.,800.,.01,.01,
            'provisional-COM-Jy-with-illustrative-axle-model',f'inertia-only-f{scenario["mixed_fraction_retained"]}')
        coarse,cm=metrics(s,.0002)
        fine,fm=metrics(s,.0001)
        difference=max(max(abs(v-w) for v,w in zip(x.state,y.state)) for x,y in zip(coarse.samples,fine.samples[::2]))
        changes={k:abs(cm[k]-fm[k]) for k in ('peak_abs_pitch_acceleration_rad_s2','peak_abs_body_acceleration_m_s2','peak_normal_load_N')}
        checks=dict(state_refinement=difference<1e-6,energy_balance=fm['max_energy_residual_J']<1e-6,
            peak_refinement=all(change<=max(1e-4 if k=='peak_normal_load_N' else 1e-5,.005*abs(fm[k])) for k,change in changes.items()))
        cases.append(dict(system=asdict(s),coarse_dt_s=.0002,fine_dt_s=.0001,duration_s=2.,
            coarse_metrics=cm,fine_metrics=fm,max_matching_state_difference=difference,peak_metric_changes=changes,checks=checks,passed=all(checks.values())))
    report.update(cases=cases,passed=all(c['passed'] for c in cases),
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (snapshot,Path(__file__),ROOT/'src/pssd_vehicle/half_car.py')})
    output=ROOT/'docs/reports/no_driver_pitch_study_v0.1.0'
    output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
