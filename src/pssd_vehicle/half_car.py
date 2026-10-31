"""Manufactured longitudinal heave/pitch and two unsprung DOFs (AUTH-VEH-0014)."""
from dataclasses import dataclass
import math
from typing import Callable
from .reduced_ride import RoadSample


@dataclass(frozen=True)
class HalfCar:
    sprung_mass: float
    pitch_inertia: float
    front_distance: float
    rear_distance: float
    front_unsprung_mass: float
    rear_unsprung_mass: float
    front_rate: float
    rear_rate: float
    front_tire_rate: float
    rear_tire_rate: float
    front_damping: float
    rear_damping: float
    compression_limit: float
    extension_limit: float
    source_id: str
    configuration_id: str
    gravity: float = 9.80665

    def __post_init__(self):
        positive = (self.sprung_mass,self.pitch_inertia,self.front_distance,self.rear_distance,
                    self.front_unsprung_mass,self.rear_unsprung_mass,self.front_rate,self.rear_rate,
                    self.front_tire_rate,self.rear_tire_rate,self.compression_limit,
                    self.extension_limit,self.gravity)
        if any(not math.isfinite(v) or v <= 0 for v in positive):
            raise ValueError("Mass, inertia, distances, rates, travel and gravity must be positive finite")
        if any(not math.isfinite(v) or v < 0 for v in (self.front_damping,self.rear_damping)):
            raise ValueError("Damping must be finite and nonnegative")
        if not self.source_id or not self.configuration_id:
            raise ValueError("Source and configuration identities required")


@dataclass(frozen=True)
class HalfCarEvaluation:
    derivative: tuple[float, ...]
    suspension_forces: tuple[float,float]
    incremental_normals: tuple[float,float]
    normal_loads: tuple[float,float]
    extensions: tuple[float,float]
    energy: float
    loss_power: float
    road_power: float


def evaluate(s: HalfCar, state: tuple[float,...], front: RoadSample, rear: RoadSample) -> HalfCarEvaluation:
    """Scalar force balances and energy; no clipping and no implicit gravity forcing."""
    if len(state)!=8 or not all(math.isfinite(v) for v in (*state,front.displacement,front.velocity,rear.displacement,rear.velocity)):
        raise ValueError("Eight finite states and finite road samples required")
    z,theta,uf,ur,v,w,vf,vr=state
    ef,er=z+s.front_distance*theta-uf,z-s.rear_distance*theta-ur
    edf,edr=v+s.front_distance*w-vf,v-s.rear_distance*w-vr
    ff,fr=-s.front_rate*ef-s.front_damping*edf,-s.rear_rate*er-s.rear_damping*edr
    nf,nr=s.front_tire_rate*(front.displacement-uf),s.rear_tire_rate*(rear.displacement-ur)
    basef=s.sprung_mass*s.gravity*s.rear_distance/(s.front_distance+s.rear_distance)+s.front_unsprung_mass*s.gravity
    baser=s.sprung_mass*s.gravity*s.front_distance/(s.front_distance+s.rear_distance)+s.rear_unsprung_mass*s.gravity
    derivative=(v,w,vf,vr,(ff+fr)/s.sprung_mass,
                (s.front_distance*ff-s.rear_distance*fr)/s.pitch_inertia,
                (nf-ff)/s.front_unsprung_mass,(nr-fr)/s.rear_unsprung_mass)
    energy=(s.sprung_mass*v*v+s.pitch_inertia*w*w+s.front_unsprung_mass*vf*vf+
            s.rear_unsprung_mass*vr*vr+s.front_rate*ef*ef+s.rear_rate*er*er+
            s.front_tire_rate*(uf-front.displacement)**2+s.rear_tire_rate*(ur-rear.displacement)**2)/2
    loss=s.front_damping*edf*edf+s.rear_damping*edr*edr
    power=nf*front.velocity+nr*rear.velocity
    values=(*derivative,ff,fr,nf,nr,basef+nf,baser+nr,energy,loss,power)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Nonfinite force/energy evaluation")
    return HalfCarEvaluation(derivative,(ff,fr),(nf,nr),(basef+nf,baser+nr),(ef,er),energy,loss,power)


@dataclass(frozen=True)
class HalfCarSample:
    time: float
    state: tuple[float,...]
    front_road: RoadSample
    rear_road: RoadSample
    evaluation: HalfCarEvaluation
    dissipated: float
    road_work: float
    energy_residual: float


@dataclass(frozen=True)
class HalfCarResult:
    samples: tuple[HalfCarSample,...]
    failure_code: str | None
    failure_time: float | None
    system: HalfCar
    road_source_ids: tuple[str,str]

    @property
    def ok(self):
        return self.failure_code is None


class _Failure(Exception):
    def __init__(self,code,time):
        self.code,self.time=code,time


def simulate_half_car(s: HalfCar, front_road: Callable[[float],RoadSample], rear_road: Callable[[float],RoadSample],
                      *, road_source_ids: tuple[str,str], dt: float, steps: int,
                      initial=(0.,)*8, t0: float=0.) -> HalfCarResult:
    """Fixed-step RK4 with sampled stage guards and two same-stage energy integrals."""
    if not math.isfinite(dt) or dt <= 0 or not math.isfinite(t0):
        raise ValueError("Finite time and positive dt required")
    if isinstance(steps,bool) or not isinstance(steps,int) or not 1 <= steps <= 1_000_000:
        raise ValueError("Integer steps in [1,1000000] required")
    if len(initial)!=8 or not all(math.isfinite(v) for v in initial):
        raise ValueError("Eight finite initial states required")
    if len(road_source_ids)!=2 or not all(road_source_ids):
        raise ValueError("Separate front and rear road identities required")
    if not math.isfinite(t0+steps*dt) or t0+dt==t0:
        raise ValueError("Unrepresentable time grid")
    history=[]
    y=tuple(initial)+(0.,0.)
    def stage(t,q):
        try:
            front,rear=front_road(t),rear_road(t)
            if not all(math.isfinite(v) for v in q):
                raise ValueError("Nonfinite state")
            result=evaluate(s,q[:8],front,rear)
        except (ValueError,OverflowError) as exc:
            raise _Failure("nonfinite_evaluation",t) from exc
        if any(n<=0 for n in result.normal_loads):
            raise _Failure("contact_loss",t)
        if any(e>s.extension_limit or -e>s.compression_limit for e in result.extensions):
            raise _Failure("travel_exceeded",t)
        return (*result.derivative,result.loss_power,result.road_power),result,front,rear
    try:
        _,result,front,rear=stage(t0,y)
        energy0=result.energy
        history.append(HalfCarSample(t0,y[:8],front,rear,result,0.,0.,0.))
        for n in range(steps):
            t=t0+n*dt
            k1=stage(t,y)[0]
            k2=stage(t+dt/2,tuple(v+dt*k/2 for v,k in zip(y,k1)))[0]
            k3=stage(t+dt/2,tuple(v+dt*k/2 for v,k in zip(y,k2)))[0]
            k4=stage(t+dt,tuple(v+dt*k for v,k in zip(y,k3)))[0]
            y=tuple(v+dt*(a+2*b+2*c+d)/6 for v,a,b,c,d in zip(y,k1,k2,k3,k4))
            end=t0+(n+1)*dt
            _,result,front,rear=stage(end,y)
            history.append(HalfCarSample(end,y[:8],front,rear,result,y[8],y[9],result.energy+y[8]-y[9]-energy0))
    except _Failure as failure:
        return HalfCarResult(tuple(history),failure.code,failure.time,s,road_source_ids)
    return HalfCarResult(tuple(history),None,None,s,road_source_ids)
