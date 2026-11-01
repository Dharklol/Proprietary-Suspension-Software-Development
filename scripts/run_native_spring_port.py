"""BENCH-SUSP-0045: native spring closure, compression and virtual-work binding."""
import hashlib
import json
import math
from pathlib import Path
from pssd_suspension import load_optimumk_geometry_snapshot, load_wufr26_wheel_reference_profile, build_nominal_wheel_reference
from pssd_suspension.spring_force import load_wufr27_spring_package
from pssd_suspension.native_spring_port import bind_front_spring_port
from pssd_suspension.generalized_forces import evaluate_ports
from run_coupled_tube_inertia import pitch, cross, sub, dot, add, scale, B

ROOT=Path(__file__).resolve().parents[1]


class NativeSpringFixture:
    def __init__(self):
        self.geometry=load_optimumk_geometry_snapshot(ROOT/'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml')
        self.wheel=load_wufr26_wheel_reference_profile(ROOT/'benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml')
        self.package=load_wufr27_spring_package(ROOT/'data_catalog/wufr27_spring_package_v0.toml')

    def bind(self,side,q):
        return bind_front_spring_port(self.geometry.corner('front',side),build_nominal_wheel_reference(self.wheel,'front',side),self.package,q,
            geometry_id=self.geometry.geometry_id,source_authority=self.geometry.authority)


def main():
    fixture=NativeSpringFixture();samples=[]
    rates=(.03,.12,-.2,.15)
    for side in ('left','right'):
        j=2 if side=='left' else 3
        for q in (-.04,-.02,0.,.02,.04):
            bound=fixture.bind(side,q);p=bound.port;spring=bound.spring_state
            f=evaluate_ports((p,),rates)
            errors=[]
            for h in (.001,.0005):
                minus=fixture.bind(side,q-h);plus=fixture.bind(side,q+h)
                minus2=fixture.bind(side,q-2*h);plus2=fixture.bind(side,q+2*h)
                errors.append(dict(compression_gradient=abs((-plus2.port.deformation_m+8*plus.port.deformation_m-8*minus.port.deformation_m+minus2.port.deformation_m)/(12*h)-p.gradient[j]),
                    energy_force=abs(-(-plus2.spring_state.stored_energy_J+8*plus.spring_state.stored_energy_J-8*minus.spring_state.stored_energy_J+minus2.spring_state.stored_energy_J)/(12*h)-f.generalized_force[j])))
            # Direct physical spring-eye power, retaining arbitrary chassis heave/pitch.
            a=fixture.geometry.corner('front',side).actuation
            rocker=bound.actuation_state.rocker_coilover_point_m;chassis=a.chassis_attachment.position_m
            direction=tuple(x/bound.actuation_state.current_coilover_length_m for x in sub(rocker,chassis))
            angle=.045
            world_force=pitch(scale(spring.force_N,direction),angle)
            v_rocker=add((0.,0.,rates[0]),pitch(add(scale(rates[1],cross(B,rocker)),scale(rates[j],bound.coil_point_derivative_m_per_rad)),angle))
            v_chassis=add((0.,0.,rates[0]),pitch(scale(rates[1],cross(B,chassis)),angle))
            physical_power=dot(world_force,sub(v_rocker,v_chassis))
            generalized_power=sum(x*y for x,y in zip(f.generalized_force,rates))
            samples.append(dict(side=side,qL=q,compression_m=p.deformation_m,force_N=spring.force_N,energy_J=f.potential_J,
                gradient=p.gradient,generalized_force=f.generalized_force,finite_difference_errors=errors,
                provider_force_error=max(abs(x-y) for x,y in zip(f.generalized_force,spring.generalized_force)),
                provider_energy_error_J=f.potential_J-spring.stored_energy_J,
                eye_power_error_W=physical_power-generalized_power,
                configuration_id=bound.configuration_id,geometry_id=bound.geometry_id,source_id=bound.spring_source_id,
                assumption_ids=bound.assumption_ids,installed_as_built_authority=bound.installed_as_built_authority))
    # Prescribed arm cycle; work must equal negative elastic-energy change.
    duration=.4
    def cycle(n):
        dt=duration/n;power=[];energies=[]
        for i in range(n+1):
            t=i*dt;q=.02*math.sin(6*t);v=.12*math.cos(6*t)
            bound=fixture.bind('left',q);f=evaluate_ports((bound.port,),(0.,0.,v,0.))
            power.append(f.generalized_force[2]*v);energies.append(f.potential_J)
        work=dt*(sum(power)-.5*(power[0]+power[-1]))
        return dict(steps=n,spring_work_J=work,energy_change_J=energies[-1]-energies[0],residual_J=work+energies[-1]-energies[0])
    cycles=[cycle(n) for n in (100,200,400)]
    checks=dict(ten_native_states=len(samples)==10,
        compression_gradient=all(s['finite_difference_errors'][-1]['compression_gradient']<1e-7 for s in samples),
        energy_gradient=all(s['finite_difference_errors'][-1]['energy_force']<1e-4 for s in samples),
        existing_provider_force=all(s['provider_force_error']<1e-10 for s in samples),
        existing_provider_energy=all(abs(s['provider_energy_error_J'])<1e-12 for s in samples),
        direct_eye_virtual_work=all(abs(s['eye_power_error_W'])<1e-10 for s in samples),
        no_rigid_body_spring_force=all(s['gradient'][0]==0 and s['gradient'][1]==0 for s in samples),
        nominal_compression=all(abs(s['compression_m']-.02110065294783212)<1e-10 for s in samples if s['qL']==0),
        authority_preserved=all(not s['installed_as_built_authority'] and 'ASM-SUSP-0002' in s['assumption_ids'] for s in samples),
        spring_work_energy=abs(cycles[-1]['residual_J'])<1e-5,
        cycle_refines=all(abs(cycles[i]['residual_J'])>3*abs(cycles[i+1]['residual_J']) for i in (0,1)))
    report=dict(scope='Front spring design-intent geometry/rate/reference to generalized force; no vehicle equilibrium/damping/ride prediction',
        samples=samples,cycles=cycles,checks=checks,passed=all(checks.values()),
        preload_policy='x=185.7mm-L; zero intentional preload at full extension, positive nominal compression from CAD length; no added preload offset')
    paths=('scripts/run_native_spring_port.py','scripts/run_coupled_tube_inertia.py','src/pssd_suspension/native_spring_port.py','src/pssd_suspension/generalized_forces.py','src/pssd_suspension/actuation.py','src/pssd_suspension/kinematics.py','src/pssd_suspension/wheel_reference.py','src/pssd_suspension/spring_force.py','data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml','benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml','data_catalog/wufr27_spring_package_v0.toml')
    report['source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    output=ROOT/'docs/reports/native_spring_port_v0.1.0';output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
