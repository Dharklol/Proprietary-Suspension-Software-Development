"""Manufactured verification and one explicit nominal native-tube diagnostic."""
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest
from pssd_suspension.reduced_inertia import RigidMemberKinematics, reduce_member_inertia
from pssd_suspension.geometry import load_optimumk_geometry_snapshot
from pssd_suspension.kinematics import rotate_point_about_hinge

ROOT=Path(__file__).resolve().parents[1]


def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def sub(a,b): return tuple(x-y for x,y in zip(a,b))


def main():
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_reduced_link_inertia.py')
    outcome=unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful(): return 1
    source=ROOT/'data_catalog/wufr26_front_lower_fore_tube_inertia_v0.json'
    data=json.loads(source.read_text())
    geometry=load_optimumk_geometry_snapshot(ROOT/'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml')
    arm=geometry.corner('front','left').wishbone
    fore,aft=arm.lower_fore_inboard.position_m,arm.lower_aft_inboard.position_m
    axis=sub(aft,fore)
    norm=math.sqrt(sum(v*v for v in axis))
    axis=tuple(v/norm for v in axis)
    cg=tuple(v*.0254 for v in data['cg_in'])
    budget_path=ROOT/'docs/reports/no_driver_mass_consistency_v0.1.0/results.json'
    body_cg=tuple(json.loads(budget_path.read_text())['cases'][1]['budget']['body']['cg_m'])
    hinge=cross(axis,sub(cg,fore))
    pitch=cross((0.,-1.,0.),sub(cg,body_cg))
    v=tuple((float(i==2),pitch[i],hinge[i]) for i in range(3))
    w=tuple((0.,-float(i==1),axis[i]) for i in range(3))
    errors=[]
    for h in (1e-3,5e-4):
        plus=rotate_point_about_hinge(cg,fore,aft,h)
        minus=rotate_point_about_hinge(cg,fore,aft,-h)
        numerical=tuple((a-b)/(2*h) for a,b in zip(plus,minus))
        errors.append(math.sqrt(sum((a-b)**2 for a,b in zip(numerical,hinge))))
    ratio=errors[0]/errors[1]
    relative=errors[1]/math.sqrt(sum(v*v for v in hinge))
    variants=[]
    unit=.45359237*.0254**2
    for policy,sign in (('as_entered_physical_tensor',1.),('negated_CAD_products',-1.)):
        tensor=tuple(tuple(data['centroidal_entries_lb_in2'][3*i+j]*unit*(1 if i==j else sign) for j in range(3)) for i in range(3))
        try:
            member=RigidMemberKinematics('SU-70107-AA-tube-2',data['source_url']+'#SU!B96:P96',
            'WUFR26-nominal-no-driver-CAD-diagnostic','CAD-xyz','nominal-qL-zero',
            ('body_heave','body_pitch_front_up','lower_arm_qL'),('m','rad','rad'),data['mass_lb']*.45359237,tensor,v,w)
        except ValueError as error:
            variants.append(dict(policy=policy,status='rejected',failure=str(error)))
            continue
        result=reduce_member_inertia((member,),expected_member_ids=(member.member_id,))
        rates=(.1,.2,-.3)
        linear=tuple(sum(v[i][j]*rates[j] for j in range(3)) for i in range(3))
        angular=tuple(sum(w[i][j]*rates[j] for j in range(3)) for i in range(3))
        direct=.5*member.mass_kg*sum(x*x for x in linear)+.5*sum(angular[i]*tensor[i][j]*angular[j] for i in range(3) for j in range(3))
        matrix_energy=result.kinetic_energy_J(rates)
        variants.append(dict(policy=policy,status='accepted',member=asdict(member),mass_matrix=result.matrix,
            sample_rates=rates,direct_energy_J=direct,matrix_energy_J=matrix_energy,
            energy_difference_J=matrix_energy-direct))
    passed=3.9<ratio<4.1 and relative<1e-6 and all(abs(v['energy_difference_J'])<1e-12 for v in variants if v['status']=='accepted')
    report=dict(scope='local manufactured reduction plus one nominal tube diagnostic; not full suspension effective mass',
        tests_run=outcome.testsRun,hinge_jacobian_errors=errors,error_ratio=ratio,fine_relative_error=relative,
        coordinate_units=('m','rad','rad'),body_reference_cg_m=body_cg,tensor_sign_variants=variants,
        verification_passed=passed,native_binding_gate_passed=all(v['status']=='accepted' for v in variants),
        native_gate_rule='Both declared sign interpretations must pass physical tensor checks; no interpretation selected automatically.',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (source,budget_path,Path(__file__),ROOT/'src/pssd_suspension/reduced_inertia.py',ROOT/'tests/test_reduced_link_inertia.py',ROOT/'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml')})
    output=ROOT/'docs/reports/reduced_link_inertia_v0.1.0'
    output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if passed else 1


if __name__=='__main__': raise SystemExit(main())
