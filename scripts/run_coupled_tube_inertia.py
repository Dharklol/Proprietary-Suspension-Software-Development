"""BENCH-SUSP-0043: finite-pitch tube-only mass and convective dynamics."""
import hashlib
import json
import math
from pathlib import Path
from pssd_suspension.geometry import load_optimumk_geometry_snapshot
from pssd_suspension.kinematics import rotate_point_about_hinge
from pssd_suspension.reduced_inertia import RigidMemberKinematics, physical_tensor_from_entries, reduce_member_inertia
from run_front_arm_tube_inertia import axis, cross, dot, sub, norm
from run_front_tube_travel import closure, rotate_tensor

ROOT=Path(__file__).resolve().parents[1]
B=(0.,-1.,0.)


def add(*vectors): return tuple(sum(v[i] for v in vectors) for i in range(3))
def scale(s,v): return tuple(s*x for x in v)
def pitch(v,p): return rotate_point_about_hinge(v,(0.,0.,0.),B,p)
def mv(a,v): return tuple(dot(row,v) for row in a)


class TubeFixture:
    def __init__(self):
        self.geometry=load_optimumk_geometry_snapshot(ROOT/'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml')
        self.records=json.loads((ROOT/'data_catalog/wufr26_front_arm_tubes_inertia_v0.json').read_text())['members']
        self.reference=json.loads((ROOT/'docs/reports/no_driver_mass_consistency_v0.1.0/results.json').read_text())['cases'][1]['budget']['body']['cg_m']

    def evaluate(self,q,qd):
        if len(q)!=4 or len(qd)!=4 or not all(math.isfinite(x) for x in (*q,*qd)):
            raise ValueError('Four finite coordinates and rates required')
        if abs(q[1])>.1 or max(abs(q[2]),abs(q[3]))>.08:
            raise ValueError('Outside declared numerical fixture envelope')
        members=[];bias=[0.]*4;details=[]
        states={side:closure(self.geometry.corner('front',side),q[j],self.geometry.geometry_id) for side,j in (('left',2),('right',3))}
        for record in self.records:
            side=record['side'];j=2 if side=='left' else 3
            arm=self.geometry.corner('front',side).wishbone;prefix=record['arm']
            fore=getattr(arm,prefix+'_fore_inboard').position_m
            aft=getattr(arm,prefix+'_aft_inboard').position_m
            u=axis(fore,aft);qU,s,sp=states[side]
            if prefix=='lower': angle=q[j];s=1.;sp=0.
            else: angle=qU
            cg0=tuple(v*.0254 for v in record['cg_in'])
            r=rotate_point_about_hinge(cg0,fore,aft,angle)
            a=sub(r,self.reference)
            base=cross(u,sub(r,fore))
            rp=scale(s,base)
            rpp=add(scale(sp,base),scale(s*s,cross(u,base)))
            columns=[(0.,0.,1.),pitch(cross(B,a),q[1]),(0.,0.,0.),(0.,0.,0.)]
            columns[j]=pitch(rp,q[1])
            angular=[(0.,0.,0.),B,(0.,0.,0.),(0.,0.,0.)]
            angular[j]=pitch(scale(s,u),q[1])
            Jv=tuple(tuple(c[i] for c in columns) for i in range(3))
            Jw=tuple(tuple(c[i] for c in angular) for i in range(3))
            entries=record['centroidal_entries_lb_in2']
            I0=physical_tensor_from_entries(tuple(tuple(entries[3*i+k]*.45359237*.0254**2 for k in range(3)) for i in range(3)),convention=record['entry_convention'])
            Ia=rotate_tensor(I0,fore,aft,angle)
            I=rotate_tensor(Ia,(0.,0.,0.),B,q[1])
            mass=record['mass_lb']*.45359237
            m=RigidMemberKinematics(record['member_id'],'COM SU '+str(record['row']),'tube-only-finite-pitch','world-xyz',repr(tuple(q)),
                ('heave','pitch_front_up','left_qL','right_qL'),('m','rad','rad','rad'),mass,I,Jv,Jw)
            members.append(m)
            abias=pitch(add(scale(qd[1]**2,cross(B,cross(B,a))),scale(2*qd[1]*qd[j],cross(B,rp)),scale(qd[j]**2,rpp)),q[1])
            alphabias=pitch(add(scale(qd[1]*qd[j]*s,cross(B,u)),scale(sp*qd[j]**2,u)),q[1])
            omega=mv(Jw,qd)
            wrench=add(mv(I,alphabias),cross(omega,mv(I,omega)))
            for k in range(4): bias[k]+=mass*dot(columns[k],abias)+dot(angular[k],wrench)
            position=add(tuple(self.reference),(0.,0.,q[0]),pitch(a,q[1]))
            details.append(dict(position=position,omega=omega,Jv=Jv,Jw=Jw,mass=mass,I=I,abias=abias,alphabias=alphabias))
        matrix=reduce_member_inertia(members,expected_member_ids=[r['member_id'] for r in self.records])
        return matrix,tuple(bias),details


def christoffel(fixture,q,qd,h):
    derivatives=[]
    for j in range(4):
        minus=list(q);plus=list(q);minus[j]-=h;plus[j]+=h
        a=fixture.evaluate(minus,qd)[0].matrix;b=fixture.evaluate(plus,qd)[0].matrix
        derivatives.append(tuple(tuple((b[i][k]-a[i][k])/(2*h) for k in range(4)) for i in range(4)))
    c=tuple(.5*sum((derivatives[j][i][k]+derivatives[k][i][j]-derivatives[i][j][k])*qd[j]*qd[k] for j in range(4) for k in range(4)) for i in range(4))
    return c,derivatives


def solve(a,b):
    rows=[list(row)+[rhs] for row,rhs in zip(a,b)]
    for j in range(len(b)):
        p=max(range(j,len(b)),key=lambda i:abs(rows[i][j]))
        rows[j],rows[p]=rows[p],rows[j]
        if abs(rows[j][j])<1e-12: raise ValueError('Singular tube fixture mass matrix')
        pivot=rows[j][j];rows[j]=[v/pivot for v in rows[j]]
        for i in range(len(b)):
            if i==j: continue
            multiplier=rows[i][j];rows[i]=[v-multiplier*w for v,w in zip(rows[i],rows[j])]
    return tuple(row[-1] for row in rows)


def integrate(fixture,n,forced):
    duration=.08;dt=duration/n
    y=(0.,.02,.01,-.015,.02,.03,.04,-.025,0.)
    initial=fixture.evaluate(y[:4],y[4:8])[0].kinetic_energy_J(y[4:8])
    def rhs(t,y):
        M,c,_=fixture.evaluate(y[:4],y[4:8])
        tau=(.01*math.cos(9*t),.001*math.sin(7*t),.0002*math.cos(5*t),-.0001*math.sin(6*t)) if forced else (0.,)*4
        acceleration=solve(M.matrix,tuple(tau[i]-c[i] for i in range(4)))
        return (*y[4:8],*acceleration,dot4(tau,y[4:8]))
    for i in range(n):
        t=i*dt;k1=rhs(t,y)
        k2=rhs(t+dt/2,tuple(v+dt*w/2 for v,w in zip(y,k1)))
        k3=rhs(t+dt/2,tuple(v+dt*w/2 for v,w in zip(y,k2)))
        k4=rhs(t+dt,tuple(v+dt*w for v,w in zip(y,k3)))
        y=tuple(v+dt*(a+2*b+2*c+d)/6 for v,a,b,c,d in zip(y,k1,k2,k3,k4))
    final=fixture.evaluate(y[:4],y[4:8])[0].kinetic_energy_J(y[4:8])
    return dict(steps=n,forced=forced,final_state=y,initial_energy_J=initial,final_energy_J=final,work_J=y[8],residual_J=final-initial-y[8])


def dot4(a,b): return sum(x*y for x,y in zip(a,b))


def main():
    fixture=TubeFixture();cases=[]
    for q,qd in (((0.,0.,0.,0.),(.1,.2,-.3,.4)),((.003,.04,-.03,.025),(.03,-.12,.25,-.15)),((-.002,-.035,.04,-.02),(-.02,.17,-.2,.1))):
        M,c,details=fixture.evaluate(q,qd)
        errors=[]
        for h in (.001,.0005):
            numerical,D=christoffel(fixture,q,qd,h)
            errors.append(max(abs(a-b) for a,b in zip(c,numerical)))
        power=.5*sum(D[k][i][j]*qd[k]*qd[i]*qd[j] for i in range(4) for j in range(4) for k in range(4))
        # Independent finite differences of the prescribed pose path q(t)=q+qd*t.
        h=.01
        plus=fixture.evaluate(tuple(q[i]+h*qd[i] for i in range(4)),qd)[2]
        minus=fixture.evaluate(tuple(q[i]-h*qd[i] for i in range(4)),qd)[2]
        plus2=fixture.evaluate(tuple(q[i]+2*h*qd[i] for i in range(4)),qd)[2]
        minus2=fixture.evaluate(tuple(q[i]-2*h*qd[i] for i in range(4)),qd)[2]
        acceleration_error=angular_error=0.
        for item,p,m,p2,m2 in zip(details,plus,minus,plus2,minus2):
            acceleration=tuple((-p2['position'][i]+16*p['position'][i]-30*item['position'][i]+16*m['position'][i]-m2['position'][i])/(12*h**2) for i in range(3))
            alpha=tuple((-p2['omega'][i]+8*p['omega'][i]-8*m['omega'][i]+m2['omega'][i])/(12*h) for i in range(3))
            acceleration_error=max(acceleration_error,norm(sub(acceleration,item['abias'])))
            angular_error=max(angular_error,norm(sub(alpha,item['alphabias'])))
        direct=sum(.5*d['mass']*dot(mv(d['Jv'],qd),mv(d['Jv'],qd))+.5*dot(d['omega'],mv(d['I'],d['omega'])) for d in details)
        cases.append(dict(q=q,qd=qd,matrix=M.matrix,bias=c,christoffel_errors=errors,power_error_W=dot4(qd,c)-power,
            omitted_bias_power_W=power,pose_acceleration_error_m_s2=acceleration_error,angular_acceleration_error_rad_s2=angular_error,
            direct_energy_error_J=M.kinetic_energy_J(qd)-direct))
    nominal=json.loads((ROOT/'docs/reports/front_arm_tube_inertia_v0.1.0/results.json').read_text())['mass_matrix']
    runs=[integrate(fixture,n,forced) for forced in (False,True) for n in (2,4,8)]
    checks=dict(nominal_matrix=max(abs(cases[0]['matrix'][i][j]-nominal[i][j]) for i in range(4) for j in range(4))<1e-12,
        christoffel=all(c['christoffel_errors'][-1]<1e-7 for c in cases),
        power_identity=all(abs(c['power_error_W'])<1e-8 for c in cases),
        direct_energy=all(abs(c['direct_energy_error_J'])<1e-12 for c in cases),
        pose_acceleration=all(c['pose_acceleration_error_m_s2']<2e-6 for c in cases),
        angular_acceleration=all(c['angular_acceleration_error_rad_s2']<1e-7 for c in cases),
        negative_control=max(abs(c['omitted_bias_power_W']) for c in cases)>1e-5,
        integrated_work_energy=all(abs(r['residual_J'])<1e-9 for r in runs),
        free_endpoint_stability=max(abs(runs[0]['final_state'][i]-runs[2]['final_state'][i]) for i in range(8))<1e-11,
        forced_endpoint_refinement=max(abs(runs[3]['final_state'][i]-runs[4]['final_state'][i]) for i in range(8))>8*max(abs(runs[4]['final_state'][i]-runs[5]['final_state'][i]) for i in range(8)))
    report=dict(scope='Eight front tubes only; finite-pitch world-frame heave/pitch/left-qL/right-qL; no housing/body/wheel lumps',
        cases=cases,integration=runs,checks=checks,passed=all(checks.values()))
    report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'scripts/run_front_tube_travel.py',ROOT/'scripts/run_front_arm_tube_inertia.py',ROOT/'src/pssd_suspension/reduced_inertia.py',ROOT/'src/pssd_suspension/kinematics.py',ROOT/'data_catalog/wufr26_front_arm_tubes_inertia_v0.json',ROOT/'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml',ROOT/'docs/reports/no_driver_mass_consistency_v0.1.0/results.json',ROOT/'docs/reports/front_arm_tube_inertia_v0.1.0/results.json')}
    output=ROOT/'docs/reports/coupled_tube_inertia_v0.1.0';output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
