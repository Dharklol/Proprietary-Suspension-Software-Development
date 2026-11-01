"""Source-bounded static equilibrium followed by local spring-only tangents."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from pssd_vehicle.wufr_static_equilibrium import load_wufr_static_equilibrium_provider, solve_wufr_static_equilibrium
from run_ride_parameter_study import native_stiffness

ROOT=Path(__file__).resolve().parents[1]


def main():
    paths=dict(source_path='data_catalog/wufr27_static_equilibrium_composition_v1.toml',
        road_contact_source_path='data_catalog/wufr26_road_contact_reference_v0.toml',
        suspension_geometry_path='data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml',
        wheel_profile_path='benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml',
        steering_geometry_path='configurations/steering/WUFR27_STEERING_BASELINE_V0.toml',
        whole_vehicle_path='data_catalog/wufr26_whole_vehicle_frame_v0.toml',
        gravity_path='data_catalog/wufr27_static_gravity_allocation_v0.toml',
        spring_package_path='data_catalog/wufr27_spring_package_v0.toml',
        zbar_fixture_path='benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml')
    provider=load_wufr_static_equilibrium_provider(**{k:ROOT/v for k,v in paths.items()})
    result=solve_wufr_static_equilibrium(provider,front_arb_setting=1,rear_arb_setting=1)
    report=dict(scope='included-load rigid-contact static equilibrium and spring-only fixed-body wheel tangents; no vehicle modal prediction',
        front_arb_setting=1,rear_arb_setting=1,static_ok=result.ok,
        complete_static_road_reaction=result.complete_static_road_reaction,
        failure_code=result.failure_code,message=result.message,
        physical_closure=asdict(result.physical_closure) if result.physical_closure else None,
        local_stiffness=[],source_sha256={v:hashlib.sha256((ROOT/v).read_bytes()).hexdigest() for v in (*paths.values(),'scripts/run_equilibrium_local_stiffness.py','scripts/run_ride_parameter_study.py')})
    if result.solve:
        report['solve']=asdict(result.solve)
    if result.contact_recovery:
        report['contact_recovery']=asdict(result.contact_recovery)
    if result.ok and result.complete_static_road_reaction:
        for (axle,side),q in zip((('front','left'),('front','right'),('rear','left'),('rear','right')),result.solve.wheel_coordinates):
            report['local_stiffness'].append(native_stiffness(axle,side,q))
    report['passed']=result.ok and result.complete_static_road_reaction and len(report['local_stiffness'])==4 and all(x['ok'] for x in report['local_stiffness'])
    output=ROOT/'docs/reports/equilibrium_local_stiffness_v0.1.0'
    output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
