"""Manufactured linear two-DOF ride model, about static equilibrium.

AUTH-VEH-0013. SI units; vertical positive upward. No installed WUFR authority.
Stage guards detect sampled violations, not exact continuous contact events.
"""
from dataclasses import dataclass
import math
from typing import Callable


@dataclass(frozen=True)
class RideSystem:
    sprung_mass: float
    unsprung_mass: float
    suspension_rate: float
    tire_rate: float
    damping: float
    compression_limit: float
    extension_limit: float
    source_id: str
    configuration_id: str
    gravity: float = 9.80665

    def __post_init__(self):
        positive = (self.sprung_mass, self.unsprung_mass, self.suspension_rate,
                    self.tire_rate, self.compression_limit, self.extension_limit, self.gravity)
        if any(not math.isfinite(x) or x <= 0 for x in positive):
            raise ValueError("Masses, rates, travel and gravity must be finite and positive")
        if not math.isfinite(self.damping) or self.damping < 0:
            raise ValueError("Damping must be finite and nonnegative")
        if not self.source_id or not self.configuration_id:
            raise ValueError("Explicit manufactured source and configuration required")


@dataclass(frozen=True)
class RoadSample:
    displacement: float
    velocity: float


def flat_road(t: float) -> RoadSample:
    return RoadSample(0., 0.)


def sine_road(amplitude: float, omega: float) -> Callable[[float], RoadSample]:
    if not all(math.isfinite(x) for x in (amplitude, omega)) or omega <= 0:
        raise ValueError("Finite amplitude and positive frequency required")
    return lambda t: RoadSample(amplitude * math.cos(omega*t),
                                -amplitude * omega * math.sin(omega*t))


def cosine_bump(height: float, start: float, duration: float) -> Callable[[float], RoadSample]:
    if not all(math.isfinite(x) for x in (height, start, duration)) or duration <= 0:
        raise ValueError("Finite bump parameters and positive duration required")
    def sample(t):
        if t <= start or t >= start + duration:
            return RoadSample(0., 0.)
        phase = 2*math.pi*(t-start)/duration
        return RoadSample(height*(1-math.cos(phase))/2,
                          height*math.pi*math.sin(phase)/duration)
    return sample


@dataclass(frozen=True)
class Mode:
    eigenvalue: float
    omega: float
    frequency_hz: float
    vector: tuple[float, float]  # mass normalized; sprung component positive
    residual: float


def undamped_modes(s: RideSystem) -> tuple[Mode, Mode]:
    a = s.suspension_rate/s.sprung_mass
    d = (s.suspension_rate+s.tire_rate)/s.unsprung_mass
    b = -math.sqrt(s.suspension_rate)*math.sqrt(s.suspension_rate)/math.sqrt(s.sprung_mass)/math.sqrt(s.unsprung_mass)
    high = (a+d+math.hypot(a-d, 2*b))/2
    low = (s.suspension_rate/s.sprung_mass)*(s.tire_rate/s.unsprung_mass)/high
    if not all(math.isfinite(x) and x > 0 for x in (low, high)):
        raise ValueError("Unrepresentable modal system")
    modes = []
    for eigenvalue in (low, high):
        # Choose the larger of two equivalent eigenvector constructions.
        v = (b, eigenvalue-a) if abs(b)+abs(eigenvalue-a) >= abs(eigenvalue-d)+abs(b) else (eigenvalue-d, b)
        norm = math.hypot(*v)
        sign = 1 if v[0] >= 0 else -1
        x, y = sign*v[0]/norm/math.sqrt(s.sprung_mass), sign*v[1]/norm/math.sqrt(s.unsprung_mass)
        r = math.hypot(s.suspension_rate*(x-y)-eigenvalue*s.sprung_mass*x,
                       -s.suspension_rate*x+(s.suspension_rate+s.tire_rate)*y-eigenvalue*s.unsprung_mass*y)
        omega = math.sqrt(eigenvalue)
        modes.append(Mode(eigenvalue, omega, omega/(2*math.pi), (x,y), r))
    return tuple(modes)


@dataclass(frozen=True)
class RideSample:
    time: float
    state: tuple[float, float, float, float]
    road: RoadSample
    normal_load: float
    energy: float
    dissipated: float
    road_work: float
    energy_residual: float


@dataclass(frozen=True)
class RideResult:
    samples: tuple[RideSample, ...]
    failure_code: str | None
    failure_time: float | None
    system: RideSystem
    road_source_id: str

    @property
    def ok(self):
        return self.failure_code is None


class _Guard(Exception):
    def __init__(self, code, time):
        self.code, self.time = code, time


def simulate(s: RideSystem, road: Callable[[float], RoadSample], *, road_source_id: str,
             dt: float, steps: int, initial=(0.,0.,0.,0.), t0: float = 0.) -> RideResult:
    """Fixed-step RK4 with same-stage energy quadratures; completion is not accuracy proof."""
    if not math.isfinite(dt) or dt <= 0 or not math.isfinite(t0):
        raise ValueError("Finite positive dt and finite initial time required")
    if isinstance(steps, bool) or not isinstance(steps, int) or not 1 <= steps <= 1_000_000:
        raise ValueError("Integer steps in [1, 1000000] required")
    if not road_source_id or len(initial) != 4 or not all(math.isfinite(v) for v in initial):
        raise ValueError("Road provenance and four finite initial states required")
    if not math.isfinite(t0+steps*dt) or t0+dt == t0:
        raise ValueError("Unrepresentable time grid")
    y = tuple(initial)+(0.,0.)
    samples = []
    def evaluate(t, q):
        r = road(t)
        if not all(math.isfinite(v) for v in (*q, r.displacement, r.velocity)):
            raise _Guard("nonfinite_state_or_road", t)
        zs, zu, vs, vu, loss, work = q
        extension = zs-zu
        normal_increment = s.tire_rate*(r.displacement-zu)
        normal = (s.sprung_mass+s.unsprung_mass)*s.gravity+normal_increment
        if normal <= 0:
            raise _Guard("contact_loss", t)
        if extension > s.extension_limit or -extension > s.compression_limit:
            raise _Guard("travel_exceeded", t)
        force = -s.suspension_rate*extension-s.damping*(vs-vu)
        energy = (s.sprung_mass*vs**2+s.unsprung_mass*vu**2+
                  s.suspension_rate*extension**2+s.tire_rate*(zu-r.displacement)**2)/2
        derivative = (vs, vu, force/s.sprung_mass, (-force+normal_increment)/s.unsprung_mass,
                      s.damping*(vs-vu)**2, normal_increment*r.velocity)
        if not all(math.isfinite(v) for v in (*derivative, energy, normal)):
            raise _Guard("nonfinite_evaluation", t)
        return derivative, r, normal, energy
    try:
        _, r, normal, energy0 = evaluate(t0, y)
        samples.append(RideSample(t0, y[:4], r, normal, energy0, 0., 0., 0.))
        for n in range(steps):
            t = t0+n*dt
            k1 = evaluate(t,y)[0]
            k2 = evaluate(t+dt/2, tuple(v+dt*k/2 for v,k in zip(y,k1)))[0]
            k3 = evaluate(t+dt/2, tuple(v+dt*k/2 for v,k in zip(y,k2)))[0]
            k4 = evaluate(t+dt, tuple(v+dt*k for v,k in zip(y,k3)))[0]
            y = tuple(v+dt*(a+2*b+2*c+d)/6 for v,a,b,c,d in zip(y,k1,k2,k3,k4))
            end = t0+(n+1)*dt
            _,r,normal,energy = evaluate(end,y)
            samples.append(RideSample(end,y[:4],r,normal,energy,y[4],y[5],energy+y[4]-y[5]-energy0))
    except _Guard as failure:
        return RideResult(tuple(samples), failure.code, failure.time, s, road_source_id)
    return RideResult(tuple(samples), None, None, s, road_source_id)
