"""Mass/first-moment-consistent CAD partitions and exploratory half-car cases."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from run_no_driver_pitch_study import ROOT, LB, IN, combine, reconstruct, metrics
from pssd_vehicle.half_car import HalfCar, evaluate
from pssd_vehicle.reduced_ride import flat_road

MIXED={'A0701 - FRONT CORNERS','A0702 - REAR CORNERS','A0206 - DRIVESHAFTS','A0605 - TIE RODS'}


def partition(source,f):
    if f not in (0.,.5,1.): raise ValueError('Explicit reviewed allocation scenarios only')
    rebuilt=reconstruct(source)
    body=[rebuilt['electrical_point']]
    front,rear=[],[]
    whole=[rebuilt['electrical_point']]
    for g in source['groups']:
        for row,m,x,y,z,j in g['rows']:
            if row==g.get('excluded_fuel_row'): continue
            record=[m*LB,x*IN,y*IN,z*IN,j*LB*IN**2]
            whole.append(record)
            outboard=g['sheet']=='WT' or g['assembly'] in {'A0101 - BRAKE DISCS','A0103 - CALIPERS & BRAKE PADS'}
            retained=f if g['assembly'] in MIXED else 0. if outboard else 1.
            mass,x,y,z,j=record
            body.append([retained*mass,x,y,z,retained*j])
            if retained<1:
                axle=front if abs(x)<=abs(x+1.5624) else rear
                axle.append([(1-retained)*mass,x,y,z,(1-retained)*j])
    groups=[combine(records) for records in (body,front,rear)]
    total=combine(whole)
    mass_residual=sum(g['mass_kg'] for g in groups)-total['mass_kg']
    moment_residual=[sum(g['mass_kg']*g['cg_m'][i] for g in groups)-total['mass_kg']*total['cg_m'][i] for i in range(3)]
    if abs(mass_residual)>1e-9 or max(map(abs,moment_residual))>1e-9:
        raise ValueError('Mass/first-moment budget failed')
    b,fr,rr=groups
    projected_moment=fr['mass_kg']*(0-fr['cg_m'][0])+rr['mass_kg']*(-1.5624-rr['cg_m'][0])
    return dict(mixed_fraction_retained=f,body=b,front_axle=fr,rear_axle=rr,total=total,
        mass_residual_kg=mass_residual,first_moment_residual_kg_m=moment_residual,
        axle_station_projection_x_moment_residual_kg_m=projected_moment)


def main():
    source=ROOT/'data_catalog/wufr26_com_pitch_snapshot_v0.json'
    snapshot=json.loads(source.read_text())
    cases=[]
    for f in (0.,.5,1.):
        budget=partition(snapshot,f)
        b,fr,rr=budget['body'],budget['front_axle'],budget['rear_axle']
        a=-b['cg_m'][0]
        s=HalfCar(b['mass_kg'],b['pitch_inertia_kg_m2'],a,1.5624-a,fr['mass_kg'],rr['mass_kg'],
            50000.,65000.,360000.,380000.,800.,800.,.01,.01,
            'owner-axis-confirmed-CAD-budget-illustrative-forces',f'no-driver-mass-consistent-f{f}')
        coarse,cm=metrics(s,.0002)
        fine,fm=metrics(s,.0001)
        error=max(max(abs(v-w) for v,w in zip(x.state,y.state)) for x,y in zip(coarse.samples,fine.samples[::2]))
        baseline=evaluate(s,(0.,)*8,flat_road(0),flat_road(0)).normal_loads
        length=s.front_distance+s.rear_distance
        weight=(s.sprung_mass+s.front_unsprung_mass+s.rear_unsprung_mass)*s.gravity
        force_error=sum(baseline)-weight
        moment_error=baseline[0]*length-(s.sprung_mass*s.gravity*s.rear_distance+s.front_unsprung_mass*s.gravity*length)
        checks=dict(mass_budget=abs(budget['mass_residual_kg'])<1e-9,
            first_moments=max(map(abs,budget['first_moment_residual_kg_m']))<1e-9,
            static_force=abs(force_error)<1e-9,static_moment=abs(moment_error)<1e-9,
            state_refinement=error<1e-6,energy=fm['max_energy_residual_J']<1e-6,
            peak_refinement=all(abs(cm[k]-fm[k])<=max(1e-4 if k=='peak_normal_load_N' else 1e-5,.005*abs(fm[k]))
                for k in ('peak_normal_load_N','peak_abs_pitch_acceleration_rad_s2','peak_abs_body_acceleration_m_s2')))
        cases.append(dict(budget=budget,system=asdict(s),baseline_normal_loads_N=baseline,
            baseline_force_error_N=force_error,baseline_pitch_moment_error_Nm=moment_error,
            coarse_dt_s=.0002,fine_dt_s=.0001,duration_s=2.,coarse_metrics=cm,fine_metrics=fm,
            max_matching_state_difference=error,checks=checks,passed=all(checks.values())))
    report=dict(scope='no-driver/no-fuel CAD-consistent bookkeeping; exploratory axle-lump dynamics only',
        axis_confirmation='Owner confirmed COM export axes match software on 2026-11-01',
        force_parameters='Explicit illustrative values; no new KW calibration',cases=cases,
        passed=all(c['passed'] for c in cases),source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (source,Path(__file__),ROOT/'scripts/run_no_driver_pitch_study.py',ROOT/'src/pssd_vehicle/half_car.py')})
    output=ROOT/'docs/reports/no_driver_mass_consistency_v0.1.0'
    output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
