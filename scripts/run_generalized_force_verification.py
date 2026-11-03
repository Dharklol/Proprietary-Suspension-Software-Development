"""BENCH-SUSP-0044: artificial force ports on the verified tube-only subsystem."""
import hashlib
import json
import math
from pathlib import Path
from pssd_suspension.generalized_forces import DeformationPort, evaluate_ports
from run_coupled_tube_inertia import TubeFixture, solve

ROOT=Path(__file__).resolve().parents[1]


class ForceFixture:
    def __init__(self):
        self.tubes=TubeFixture()
        self.indices=[next(i for i,r in enumerate(self.tubes.records) if r['side']==side and r['arm']=='lower' and r['leg']=='fore') for side in ('left','right')]
        self.reference=self.tubes.evaluate((0.,)*4,(0.,)*4)[2]

    def evaluate(self,t,q,v,moving):
        M,c,details=self.tubes.evaluate(q,v)
        ports=[]
        for j in (2,3):
            gradient=tuple(.2*math.cos(q[j]) if i==j else 0. for i in range(4))
            ports.append(DeformationPort('artificial-arm-spring-'+str(j),.2*math.sin(q[j]),gradient,0.,.3,.02))
        for n,index in enumerate(self.indices):
            # Artificial support at a selected tube CG; NOT wheel/road-contact geometry.
            phase=.4*n
            road=.0001*(math.sin(5*t+phase)-math.sin(phase)) if moving else 0.
            rate=.0005*math.cos(5*t+phase) if moving else 0.
            item=details[index]
            compression=.005+road-(item['position'][2]-self.reference[index]['position'][2])
            ports.append(DeformationPort('artificial-support-'+str(n),compression,tuple(-x for x in item['Jv'][2]),rate,.2,.03,True))
        return M,c,evaluate_ports(ports,v),ports


def integrate(fixture,n,moving):
    duration=.15;dt=duration/n
    y=(0.,0.,.002,-.002,0.,0.,.004,-.004,0.,0.)
    M,_,f,_=fixture.evaluate(0.,y[:4],y[4:8],moving)
    initial=M.kinetic_energy_J(y[4:8])+f.potential_J
    max_residual=0.;minimum_compression=math.inf
    def rhs(t,y):
        M,c,f,ports=fixture.evaluate(t,y[:4],y[4:8],moving)
        acceleration=solve(M.matrix,tuple(f.generalized_force[i]-c[i] for i in range(4)))
        return (*y[4:8],*acceleration,f.support_power_W,f.dissipation_W)
    for i in range(n):
        t=i*dt;k1=rhs(t,y)
        k2=rhs(t+dt/2,tuple(a+dt*b/2 for a,b in zip(y,k1)))
        k3=rhs(t+dt/2,tuple(a+dt*b/2 for a,b in zip(y,k2)))
        k4=rhs(t+dt,tuple(a+dt*b for a,b in zip(y,k3)))
        y=tuple(a+dt*(b+2*c+2*d+e)/6 for a,b,c,d,e in zip(y,k1,k2,k3,k4))
        M,_,f,ports=fixture.evaluate((i+1)*dt,y[:4],y[4:8],moving)
        energy=M.kinetic_energy_J(y[4:8])+f.potential_J
        max_residual=max(max_residual,abs(energy-initial-y[8]+y[9]))
        minimum_compression=min(minimum_compression,*(p.deformation_m for p in ports if p.compression_only))
    return dict(steps=n,moving_support=moving,initial_energy_J=initial,final_energy_J=energy,support_work_J=y[8],dissipated_J=y[9],
                maximum_balance_residual_J=max_residual,final_balance_residual_J=energy-initial-y[8]+y[9],
                minimum_support_compression_m=minimum_compression,final_state=y)


def main():
    fixture=ForceFixture()
    inventory=json.loads((ROOT/'data_catalog/wufr26_front_corner_inventory_v0.json').read_text())
    rows={r['sheet_row']:r for r in inventory['rows']}
    ledger=[dict(source_row=r['row'],member_id=r['member_id'],mass_kg=r['mass_lb']*.45359237,represented_once=True) for r in fixture.tubes.records]
    runs=[integrate(fixture,n,moving) for moving in (False,True) for n in (8,16,32)]
    # Contact and travel failure controls exercise the actual fixture/provider boundaries.
    controls={}
    try: fixture.evaluate(0.,(.02,0.,0.,0.),(0.,)*4,False)
    except ValueError as error: controls['contact_loss']=str(error)
    try: fixture.evaluate(0.,(0.,0.,.081,0.),(0.,)*4,False)
    except ValueError as error: controls['travel_boundary']=str(error)
    checks=dict(exact_eight_member_ledger=len(ledger)==8 and len({r['source_row'] for r in ledger})==8,
        unchanged_inventory_masses=all(rows[r['row']]['CAD_mass_lb']==r['mass_lb'] for r in fixture.tubes.records),
        represented_mass_closure=abs(sum(r['mass_kg'] for r in ledger)-.81555908126)<1e-12,
        reduced_heave_mass_matches_ledger=abs(fixture.tubes.evaluate((0.,)*4,(0.,)*4)[0].matrix[0][0]-sum(r['mass_kg'] for r in ledger))<1e-12,
        combined_energy=all(r['maximum_balance_residual_J']<1e-9 for r in runs),
        positive_dissipation=all(r['dissipated_J']>0 for r in runs),
        stationary_support_decay=all(r['final_energy_J']<r['initial_energy_J'] and r['support_work_J']==0 for r in runs if not r['moving_support']),
        contact_valid_runs=all(r['minimum_support_compression_m']>0 for r in runs),
        contact_loss_stops='Contact-valid branch ended' in controls.get('contact_loss',''),
        travel_boundary_stops='Outside declared numerical fixture envelope' in controls.get('travel_boundary',''),
        omitted_support_work_detected=abs(runs[-1]['support_work_J'])>100*runs[-1]['maximum_balance_residual_J'],
        omitted_dissipation_detected=runs[-1]['dissipated_J']>100*runs[-1]['maximum_balance_residual_J'])
    report=dict(scope='Eight native tubes with artificial massless spring/damper/support ports; not native ride or wheel contact',
        mass_ledger=ledger,excluded_mass_policy='All other front inventory/body/wheel/rear masses excluded; no whole-car or HalfCar lump is augmented.',
        integration=runs,failure_controls=controls,checks=checks,passed=all(checks.values()))
    report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'src/pssd_suspension/generalized_forces.py',ROOT/'scripts/run_coupled_tube_inertia.py',ROOT/'scripts/run_front_tube_travel.py',ROOT/'scripts/run_front_arm_tube_inertia.py',ROOT/'src/pssd_suspension/reduced_inertia.py',ROOT/'src/pssd_suspension/kinematics.py',ROOT/'data_catalog/wufr26_front_arm_tubes_inertia_v0.json',ROOT/'data_catalog/wufr26_front_corner_inventory_v0.json',ROOT/'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml',ROOT/'docs/reports/no_driver_mass_consistency_v0.1.0/results.json')}
    output=ROOT/'docs/reports/generalized_force_verification_v0.1.0';output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
