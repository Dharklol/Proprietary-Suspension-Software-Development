"""Reproduce analytical verification, summary and manufactured bump history."""
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_reduced_ride import system, harmonic_reference
from pssd_vehicle.reduced_ride import simulate, sine_road, cosine_bump, undamped_modes


def main():
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_reduced_ride.py")
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful():
        return 1
    output = ROOT / "docs/reports/reduced_ride_verification_v0.1.0"
    output.mkdir(parents=True, exist_ok=True)
    s = system(.4)
    errors=[]
    for dt in (.1,.05,.025):
        result=simulate(s,sine_road(.01,1.3),road_source_id="manufactured-cosine-A0.01-w1.3",dt=dt,steps=round(12/dt),initial=harmonic_reference(s,.01,1.3,0.))
        errors.append(max(max(abs(a-b) for a,b in zip(x.state,harmonic_reference(s,.01,1.3,x.time))) for x in result.samples))
    bump=simulate(s,cosine_bump(.01,1.,2.),road_source_id="manufactured-cosine-bump",dt=.005,steps=2000)
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
        "src/pssd_vehicle/reduced_ride.py", "src/pssd_suspension/local_stiffness.py", "tests/test_reduced_ride.py")}
    summary=dict(scope="manufactured verification only; no installed vehicle prediction",
                 tests_run=outcome.testsRun, system=asdict(s), modes=[asdict(m) for m in undamped_modes(s)],
                 harmonic_dt=[.1,.05,.025], harmonic_max_state_errors=errors,
                 harmonic_error_ratios=[a/b for a,b in zip(errors,errors[1:])],
                 ratio_acceptance=[12.,20.], bump_max_energy_residual_J=max(abs(x.energy_residual) for x in bump.samples),
                 bump_completed=bump.ok, source_sha256=hashes)
    (output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    with (output/"bump_history.csv").open("w",newline="") as f:
        writer=csv.writer(f, lineterminator="\n")
        writer.writerow(("time_s","zs_m","zu_m","vs_m_per_s","vu_m_per_s","road_m","normal_N","energy_J","dissipated_J","road_work_J","energy_residual_J"))
        for x in bump.samples:
            writer.writerow((x.time,*x.state,x.road.displacement,x.normal_load,x.energy,x.dissipated,x.road_work,x.energy_residual))
    print(json.dumps(summary,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
