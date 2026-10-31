"""Exploratory nominal-geometry ride sensitivity; not installed vehicle prediction."""
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import tomllib

from pssd_suspension import (load_optimumk_geometry_snapshot, load_wufr26_wheel_reference_profile,
    build_nominal_wheel_reference, solve_body_vertical_actuation_state, PhysicalStateSolverConfig)
from pssd_suspension.spring_force import load_wufr27_spring_package, evaluate_spring_law
from pssd_suspension.local_stiffness import CompressionMap, local_stiffness
from pssd_vehicle.reduced_ride import RideSystem, simulate, cosine_bump, undamped_modes

ROOT=Path(__file__).resolve().parents[1]


def native_stiffness(axle, side, q_center=0.):
    geometry=load_optimumk_geometry_snapshot(ROOT/'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml')
    wheel=load_wufr26_wheel_reference_profile(ROOT/'benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml')
    package=load_wufr27_spring_package(ROOT/'data_catalog/wufr27_spring_package_v0.toml')
    spring=getattr(package,axle)
    corner=geometry.corner(axle,side)
    nominal=build_nominal_wheel_reference(wheel,axle,side)
    config=PhysicalStateSolverConfig(q_L_min_rad=math.radians(-4),q_L_max_rad=math.radians(4),displacement_tolerance_m=1e-12,q_L_tolerance_rad=1e-12)
    def compression(q):
        state=solve_body_vertical_actuation_state(corner,nominal,q_center+q,config,
            geometry_id=geometry.geometry_id,source_authority=geometry.authority)
        if not state.ok:
            raise ValueError(state.message)
        return .1857-state.current_coilover_length_m
    x0=compression(0.)
    law=evaluate_spring_law(spring,x0)
    derivatives=[]
    for h in (.001,.0005):
        xp,xm=compression(h),compression(-h)
        rho=(xp-xm)/(2*h)
        eta=(xp-2*x0+xm)/h**2
        mapping=CompressionMap(spring.spring_id,package.configuration_id,'wheel_center_body_up',
                               'centered-native-compression',rho,eta)
        stiffness=local_stiffness(law,mapping)
        ep=evaluate_spring_law(spring,xp).stored_energy_J
        em=evaluate_spring_law(spring,xm).stored_energy_J
        energy_tangent=(ep-2*law.stored_energy_J+em)/h**2
        derivatives.append(dict(h_m=h,rho=rho,eta_per_m=eta,elastic_N_per_m=stiffness.elastic_N_per_m,
            geometric_N_per_m=stiffness.geometric_N_per_m,total_N_per_m=stiffness.total_N_per_m,
            independent_energy_tangent_N_per_m=energy_tangent))
    coarse,fine=derivatives
    checks={key:abs(coarse[key]-fine[key]) <= max(floor,rel*abs(fine[key])) for key,rel,floor in
            (('rho',.002,1e-6),('eta_per_m',.02,1e-3),('total_N_per_m',.002,1.))}
    checks['energy_tangent']=abs(fine['total_N_per_m']-fine['independent_energy_tangent_N_per_m'])<=max(1.,.002*abs(fine['total_N_per_m']))
    return dict(axle=axle,side=side,wheel_coordinate_m=q_center,compression_m=x0,spring_force_N=law.force_N,
                derivatives=derivatives,checks=checks,ok=all(checks.values()))


def metrics(s,dt):
    run=simulate(s,cosine_bump(.001,.1,.2),road_source_id='study-1mm-0.2s-cosine',dt=dt,steps=round(1/dt))
    if not run.ok:
        return dict(ok=False,failure_code=run.failure_code,failure_time=run.failure_time)
    accel=[abs((-s.suspension_rate*(x.state[0]-x.state[1])-s.damping*(x.state[2]-x.state[3]))/s.sprung_mass) for x in run.samples]
    return dict(ok=True,peak_body_acceleration_m_per_s2=max(accel),
        peak_incremental_normal_N=max(abs(x.normal_load-(s.sprung_mass+s.unsprung_mass)*s.gravity) for x in run.samples),
        max_energy_residual_J=max(abs(x.energy_residual) for x in run.samples))


def main():
    mass=tomllib.loads((ROOT/'data_catalog/wufr27_static_gravity_allocation_v0.toml').read_text())
    scenario=tomllib.loads((ROOT/'data_catalog/ride_parameter_study_v0.toml').read_text())
    local=[]
    cases=[]
    for index,(axle,side) in enumerate((('front','left'),('front','right'),('rear','left'),('rear','right'))):
        tangent=native_stiffness(axle,side)
        local.append(tangent)
        if not tangent['ok']:
            continue
        ms=mass['source']['reviewed_corner_scale_lb'][index]*mass['source']['lb_to_kg']-5.
        ks=tangent['derivatives'][-1]['total_N_per_m']
        for tire_multiplier in (.8,1.,1.2):
            for zeta in scenario['damping_scenario']['zeta_proxy']:
                s=RideSystem(ms,5.,ks,scenario['tire_scenario']['rate_N_per_m'][index]*tire_multiplier,
                    2*zeta*math.sqrt(ms*ks),.01,.01,'exploratory-mixed-source-scenario',f'{axle}-{side}-kt{tire_multiplier}-z{zeta}',gravity=9.81)
                coarse,fine=metrics(s,.0002),metrics(s,.0001)
                converged=coarse['ok'] and fine['ok']
                if converged:
                    converged=all(abs(coarse[k]-fine[k]) <= max(floor,.005*abs(fine[k])) for k,floor in
                        (('peak_body_acceleration_m_per_s2',1e-5),('peak_incremental_normal_N',1e-4))) and fine['max_energy_residual_J']<1e-6
                cases.append(dict(system=asdict(s),tire_multiplier=tire_multiplier,isolated_oscillator_zeta_proxy=zeta,
                    undamped_modes=[asdict(m) for m in undamped_modes(s)],coarse=coarse,fine=fine,converged=converged))
    report=dict(scope='exploratory nominal CAD + static corner mass proxies + legacy tire scenarios + assumed damping; not vehicle predictions',
                scenario=scenario,source_sha256={str(p):hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
                    'data_catalog/ride_parameter_study_v0.toml','data_catalog/wufr27_static_gravity_allocation_v0.toml',
                    'data_catalog/wufr27_spring_package_v0.toml','data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml',
                    'benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml','scripts/run_ride_parameter_study.py',
                    'src/pssd_vehicle/reduced_ride.py','src/pssd_suspension/actuation.py','src/pssd_suspension/local_stiffness.py')},
                local_stiffness=local,cases=cases,passed=all(x['ok'] for x in local) and len(cases)==36 and all(x['converged'] for x in cases))
    output=ROOT/'docs/reports/ride_parameter_study_v0.1.0'
    output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=report['passed'],local=[dict(axle=x['axle'],side=x['side'],checks=x['checks'],fine=x['derivatives'][-1]) for x in local],case_count=len(cases)),indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
