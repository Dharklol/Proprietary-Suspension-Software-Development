"""Reproduce the manufactured half-car verification and compact evidence."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from test_half_car import asymmetric
from pssd_vehicle.half_car import simulate_half_car
from pssd_vehicle.reduced_ride import cosine_bump


def main():
    outcome=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_half_car.py'))
    if not outcome.wasSuccessful(): return 1
    s=asymmetric()
    road=(cosine_bump(.01,.3,.8),cosine_bump(.008,.9,.6))
    runs=[simulate_half_car(s,*road,road_source_ids=('manufactured-front-bump','manufactured-rear-bump'),dt=dt,steps=round(4/dt)) for dt in (.002,.001)]
    coarse,fine=runs
    difference=max(max(abs(a-b) for a,b in zip(x.state,y.state)) for x,y in zip(coarse.samples,fine.samples[::2]))
    summary=dict(scope='manufactured heave/pitch verification only; no installed vehicle prediction',tests_run=outcome.testsRun,
        system=asdict(s),road=dict(front_height_m=.01,front_start_s=.3,front_duration_s=.8,rear_height_m=.008,rear_start_s=.9,rear_duration_s=.6),
        dt_s=[.002,.001],duration_s=4.,completed=[r.ok for r in runs],
        maximum_matching_state_difference=difference,state_difference_units='corresponding SI component units (m,rad,m/s,rad/s)',
        maximum_fine_energy_residual_J=max(abs(x.energy_residual) for x in fine.samples),
        final_dissipated_J=fine.samples[-1].dissipated,final_road_work_J=fine.samples[-1].road_work,
        minimum_sampled_normal_loads_N=[min(x.evaluation.normal_loads[i] for x in fine.samples) for i in (0,1)],
        maximum_abs_pitch_rad=max(abs(x.state[1]) for x in fine.samples),
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('src/pssd_vehicle/half_car.py','tests/test_half_car.py','scripts/run_half_car_verification.py')})
    output=ROOT/'docs/reports/half_car_verification_v0.1.0'
    output.mkdir(parents=True,exist_ok=True)
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return 0


if __name__=='__main__': raise SystemExit(main())
