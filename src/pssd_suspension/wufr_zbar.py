"""Source-bounded WUFR Z-bar two-arm mechanism solver.

Consumes the named ``WUFR26_ZBAR_MECHANISM_V0`` fixture and rocker angles from
MOD-SUSP-0003.  Each blade arm is a cantilever with transverse elastic tip
coordinate d_i.  The central housing is an ideal frictionless rotation about the
fixture +z axis.  For prescribed rocker states the two rigid-link constraints are
solved while the free housing angle minimizes the authorized two-arm elastic
energy.  No body-roll, track-width, wheel-travel, or scalar motion-ratio shortcut
is used.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Sequence

Point3 = tuple[float, float, float]


class WufrZBarError(ValueError):
    pass


class ZBarStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class ZBarFailureCode(str, Enum):
    NONFINITE_INPUT = "nonfinite_input"
    SOURCE_MISMATCH = "source_mismatch"
    LINK_CLOSURE_UNREACHABLE = "link_closure_unreachable"
    HOUSING_MINIMUM_UNAVAILABLE = "housing_minimum_unavailable"
    CLOSURE_RESIDUAL = "closure_residual"
    JACOBIAN_UNAVAILABLE = "jacobian_unavailable"


@dataclass(frozen=True)
class ZBarSolverConfig:
    housing_search_half_width_rad: float = math.pi
    coarse_samples: int = 361
    golden_iterations: int = 80
    discriminant_tolerance_m2: float = 1.0e-12
    closure_residual_tolerance_m: float = 1.0e-9
    jacobian_step_rad: float = 1.0e-5
    jacobian_second_step_rad: float = 5.0e-6
    jacobian_agreement_tolerance_m_per_rad: float = 5.0e-4

    def __post_init__(self) -> None:
        vals = (
            self.housing_search_half_width_rad,
            self.discriminant_tolerance_m2,
            self.closure_residual_tolerance_m,
            self.jacobian_step_rad,
            self.jacobian_second_step_rad,
            self.jacobian_agreement_tolerance_m_per_rad,
        )
        if not all(math.isfinite(x) and x > 0.0 for x in vals):
            raise WufrZBarError("Z-bar solver tolerances/search widths must be finite and positive")
        if self.coarse_samples < 5 or self.coarse_samples % 2 == 0:
            raise WufrZBarError("coarse_samples must be odd and at least 5")
        if self.golden_iterations < 8:
            raise WufrZBarError("golden_iterations must be at least 8")


@dataclass(frozen=True)
class ZBarAxleFixture:
    fixture_id: str
    configuration_id: str
    axle: str
    housing_pivot_m: Point3
    housing_axis_unit: Point3
    blade_link_joint_left_m: Point3
    blade_link_joint_right_m: Point3
    rocker_pickup_left_m: Point3
    rocker_pickup_right_m: Point3
    rocker_pivot_left_m: Point3
    rocker_pivot_right_m: Point3
    rocker_axis_unit: Point3
    link_length_left_m: float
    link_length_right_m: float


@dataclass(frozen=True)
class ZBarMechanismResult:
    status: ZBarStatus
    axle: str = ""
    rocker_theta_left_rad: float | None = None
    rocker_theta_right_rad: float | None = None
    housing_theta_rad: float | None = None
    d_left_m: float | None = None
    d_right_m: float | None = None
    blade_tip_left_m: Point3 | None = None
    blade_tip_right_m: Point3 | None = None
    rocker_pickup_left_m: Point3 | None = None
    rocker_pickup_right_m: Point3 | None = None
    link_residual_left_m: float | None = None
    link_residual_right_m: float | None = None
    objective_d2_m2: float | None = None
    J_d_m_per_rad: tuple[tuple[float, float], tuple[float, float]] = ()
    jacobian_step_rad: float | None = None
    jacobian_second_step_rad: float | None = None
    jacobian_max_disagreement_m_per_rad: float | None = None
    failure_code: ZBarFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is ZBarStatus.SUCCESS


@dataclass(frozen=True)
class ZBarForceResult:
    status: ZBarStatus
    setting: int
    stiffness_N_per_m: float
    d_left_m: float | None = None
    d_right_m: float | None = None
    force_left_N: float | None = None
    force_right_N: float | None = None
    stored_energy_J: float | None = None
    generalized_rocker_torque_Nm: tuple[float, float] = ()
    failure_code: ZBarFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is ZBarStatus.SUCCESS


def _p(values: Sequence[float]) -> Point3:
    if len(values) != 3:
        raise WufrZBarError("fixture point must have three components")
    result = (float(values[0]), float(values[1]), float(values[2]))
    if not all(math.isfinite(x) for x in result):
        raise WufrZBarError("fixture point components must be finite")
    return result


def _add(a: Point3, b: Point3) -> Point3:
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])


def _sub(a: Point3, b: Point3) -> Point3:
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def _scale(a: Point3, s: float) -> Point3:
    return (a[0]*s, a[1]*s, a[2]*s)


def _dot(a: Point3, b: Point3) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def _cross(a: Point3, b: Point3) -> Point3:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _norm(a: Point3) -> float:
    return math.sqrt(_dot(a, a))


def _unit(a: Point3) -> Point3:
    n = _norm(a)
    if n <= 1.0e-14 or not math.isfinite(n):
        raise WufrZBarError("fixture axis/vector is degenerate")
    return _scale(a, 1.0/n)


def _distance(a: Point3, b: Point3) -> float:
    return _norm(_sub(a, b))


def _rotate_about_axis(point: Point3, origin: Point3, axis: Point3, angle: float) -> Point3:
    u = _unit(axis)
    v = _sub(point, origin)
    c, s = math.cos(angle), math.sin(angle)
    rotated = _add(_add(_scale(v, c), _scale(_cross(u, v), s)), _scale(u, _dot(u, v)*(1.0-c)))
    return _add(origin, rotated)


def load_wufr_zbar_fixture(path: str | Path, axle: str) -> ZBarAxleFixture:
    with Path(path).open("rb") as stream:
        data = tomllib.load(stream)
    if axle not in ("front", "rear"):
        raise WufrZBarError("axle must be front or rear")
    section = data[axle]
    fixture = ZBarAxleFixture(
        fixture_id=str(data["fixture_id"]),
        configuration_id=str(data["configuration_id"]),
        axle=axle,
        housing_pivot_m=_p(section["blade_housing_pivot_m"]),
        housing_axis_unit=_p(section["blade_housing_axis_unit"]),
        blade_link_joint_left_m=_p(section["blade_link_joint_left_m"]),
        blade_link_joint_right_m=_p(section["blade_link_joint_right_m"]),
        rocker_pickup_left_m=_p(section["rocker_arb_pickup_left_m"]),
        rocker_pickup_right_m=_p(section["rocker_arb_pickup_right_m"]),
        rocker_pivot_left_m=_p(section["rocker_pivot_left_m"]),
        rocker_pivot_right_m=_p(section["rocker_pivot_right_m"]),
        rocker_axis_unit=_p(section["rocker_axis_unit"]),
        link_length_left_m=float(section["link_joint_center_length_left_m"]),
        link_length_right_m=float(section["link_joint_center_length_right_m"]),
    )
    if _distance(fixture.housing_pivot_m, _scale(_add(fixture.blade_link_joint_left_m, fixture.blade_link_joint_right_m), 0.5)) > 1.0e-9:
        raise WufrZBarError("blade-end midpoint does not match the frozen housing pivot")
    return fixture


def _arm_tip_for(theta_h: float, d: float, C: Point3, B_nom: Point3, axis: Point3) -> Point3:
    arm = _sub(B_nom, C)
    arm_hat = _unit(arm)
    transverse = _unit(_cross(axis, arm_hat))
    rigid_tip = _rotate_about_axis(B_nom, C, axis, theta_h)
    transverse_rot = _rotate_about_axis(_add(C, transverse), C, axis, theta_h)
    n = _unit(_sub(transverse_rot, C))
    return _add(rigid_tip, _scale(n, d))


def _arm_deflection_roots(theta_h: float, rocker_pickup: Point3, C: Point3, B_nom: Point3, axis: Point3, link_length: float, cfg: ZBarSolverConfig) -> tuple[float, float] | None:
    arm = _sub(B_nom, C)
    arm_hat = _unit(arm)
    transverse = _unit(_cross(axis, arm_hat))
    rigid_tip = _rotate_about_axis(B_nom, C, axis, theta_h)
    transverse_rot = _rotate_about_axis(_add(C, transverse), C, axis, theta_h)
    n = _unit(_sub(transverse_rot, C))
    b = _sub(rocker_pickup, rigid_tip)
    projection = _dot(b, n)
    discriminant = projection*projection - (_dot(b, b) - link_length*link_length)
    if discriminant < -cfg.discriminant_tolerance_m2:
        return None
    root = math.sqrt(max(0.0, discriminant))
    return (projection-root, projection+root)


def _nearest_zero_root(roots: tuple[float, float] | None) -> float | None:
    if roots is None:
        return None
    return roots[0] if abs(roots[0]) <= abs(roots[1]) else roots[1]


def _state_at_housing_angle(theta_h: float, pickup_l: Point3, pickup_r: Point3, fixture: ZBarAxleFixture, cfg: ZBarSolverConfig) -> tuple[float, float, Point3, Point3] | None:
    dl = _nearest_zero_root(_arm_deflection_roots(theta_h, pickup_l, fixture.housing_pivot_m, fixture.blade_link_joint_left_m, fixture.housing_axis_unit, fixture.link_length_left_m, cfg))
    dr = _nearest_zero_root(_arm_deflection_roots(theta_h, pickup_r, fixture.housing_pivot_m, fixture.blade_link_joint_right_m, fixture.housing_axis_unit, fixture.link_length_right_m, cfg))
    if dl is None or dr is None:
        return None
    bl = _arm_tip_for(theta_h, dl, fixture.housing_pivot_m, fixture.blade_link_joint_left_m, fixture.housing_axis_unit)
    br = _arm_tip_for(theta_h, dr, fixture.housing_pivot_m, fixture.blade_link_joint_right_m, fixture.housing_axis_unit)
    return dl, dr, bl, br


def _objective(theta_h: float, pickup_l: Point3, pickup_r: Point3, fixture: ZBarAxleFixture, cfg: ZBarSolverConfig) -> float:
    state = _state_at_housing_angle(theta_h, pickup_l, pickup_r, fixture, cfg)
    if state is None:
        return math.inf
    return state[0]*state[0] + state[1]*state[1]


def _golden_minimize(lo: float, hi: float, fn, iterations: int) -> tuple[float, float]:
    phi = (1.0 + math.sqrt(5.0))/2.0
    c = hi - (hi-lo)/phi
    d = lo + (hi-lo)/phi
    fc, fd = fn(c), fn(d)
    for _ in range(iterations):
        if fc <= fd:
            hi, d, fd = d, c, fc
            c = hi - (hi-lo)/phi
            fc = fn(c)
        else:
            lo, c, fc = c, d, fd
            d = lo + (hi-lo)/phi
            fd = fn(d)
    x = 0.5*(lo+hi)
    return x, fn(x)


def _solve_core(fixture: ZBarAxleFixture, theta_l: float, theta_r: float, cfg: ZBarSolverConfig, predecessor_housing_rad: float = 0.0) -> ZBarMechanismResult:
    if not all(math.isfinite(x) for x in (theta_l, theta_r, predecessor_housing_rad)):
        return ZBarMechanismResult(ZBarStatus.FAILURE, axle=fixture.axle, failure_code=ZBarFailureCode.NONFINITE_INPUT, message="rocker/housing angles must be finite")
    pickup_l = _rotate_about_axis(fixture.rocker_pickup_left_m, fixture.rocker_pivot_left_m, fixture.rocker_axis_unit, theta_l)
    pickup_r = _rotate_about_axis(fixture.rocker_pickup_right_m, fixture.rocker_pivot_right_m, fixture.rocker_axis_unit, theta_r)
    lo = predecessor_housing_rad - cfg.housing_search_half_width_rad
    hi = predecessor_housing_rad + cfg.housing_search_half_width_rad
    step = (hi-lo)/(cfg.coarse_samples-1)
    samples = [(lo+i*step, _objective(lo+i*step, pickup_l, pickup_r, fixture, cfg)) for i in range(cfg.coarse_samples)]
    finite = [(i, x, f) for i, (x, f) in enumerate(samples) if math.isfinite(f)]
    if not finite:
        return ZBarMechanismResult(ZBarStatus.FAILURE, axle=fixture.axle, failure_code=ZBarFailureCode.LINK_CLOSURE_UNREACHABLE, message="no reachable housing angle in search domain")
    best_i, _, _ = min(finite, key=lambda row: (row[2], abs(row[1]-predecessor_housing_rad)))
    left_i = max(0, best_i-1)
    right_i = min(cfg.coarse_samples-1, best_i+1)
    theta_h, obj = _golden_minimize(samples[left_i][0], samples[right_i][0], lambda x: _objective(x, pickup_l, pickup_r, fixture, cfg), cfg.golden_iterations)
    state = _state_at_housing_angle(theta_h, pickup_l, pickup_r, fixture, cfg)
    if state is None or not math.isfinite(obj):
        return ZBarMechanismResult(ZBarStatus.FAILURE, axle=fixture.axle, failure_code=ZBarFailureCode.HOUSING_MINIMUM_UNAVAILABLE, message="housing energy minimum could not be evaluated")
    dl, dr, bl, br = state
    rl = _distance(bl, pickup_l)-fixture.link_length_left_m
    rr = _distance(br, pickup_r)-fixture.link_length_right_m
    if max(abs(rl), abs(rr)) > cfg.closure_residual_tolerance_m:
        return ZBarMechanismResult(ZBarStatus.FAILURE, axle=fixture.axle, housing_theta_rad=theta_h, d_left_m=dl, d_right_m=dr, link_residual_left_m=rl, link_residual_right_m=rr, failure_code=ZBarFailureCode.CLOSURE_RESIDUAL, message="Z-bar rigid-link closure residual exceeds tolerance")
    return ZBarMechanismResult(ZBarStatus.SUCCESS, axle=fixture.axle, rocker_theta_left_rad=theta_l, rocker_theta_right_rad=theta_r, housing_theta_rad=theta_h, d_left_m=dl, d_right_m=dr, blade_tip_left_m=bl, blade_tip_right_m=br, rocker_pickup_left_m=pickup_l, rocker_pickup_right_m=pickup_r, link_residual_left_m=rl, link_residual_right_m=rr, objective_d2_m2=obj)


def solve_zbar_mechanism(fixture: ZBarAxleFixture, theta_left_rad: float, theta_right_rad: float, *, config: ZBarSolverConfig | None = None, with_jacobian: bool = True) -> ZBarMechanismResult:
    cfg = config or ZBarSolverConfig()
    base = _solve_core(fixture, theta_left_rad, theta_right_rad, cfg)
    if not base.ok or not with_jacobian:
        return base
    assert base.housing_theta_rad is not None and base.d_left_m is not None and base.d_right_m is not None

    def derivative(h: float) -> tuple[tuple[float, float], tuple[float, float]] | None:
        columns = []
        for q_index in (0, 1):
            plus = [theta_left_rad, theta_right_rad]
            minus = [theta_left_rad, theta_right_rad]
            plus[q_index] += h
            minus[q_index] -= h
            rp = _solve_core(fixture, plus[0], plus[1], cfg, base.housing_theta_rad)
            rm = _solve_core(fixture, minus[0], minus[1], cfg, base.housing_theta_rad)
            if not rp.ok or not rm.ok or rp.d_left_m is None or rp.d_right_m is None or rm.d_left_m is None or rm.d_right_m is None:
                return None
            columns.append(((rp.d_left_m-rm.d_left_m)/(2*h), (rp.d_right_m-rm.d_right_m)/(2*h)))
        return ((columns[0][0], columns[1][0]), (columns[0][1], columns[1][1]))

    j1 = derivative(cfg.jacobian_step_rad)
    j2 = derivative(cfg.jacobian_second_step_rad)
    if j1 is None or j2 is None:
        return ZBarMechanismResult(**{**base.__dict__, "status": ZBarStatus.FAILURE, "failure_code": ZBarFailureCode.JACOBIAN_UNAVAILABLE, "message": "branch-preserving finite-difference Jacobian unavailable"})
    disagreement = max(abs(j1[i][j]-j2[i][j]) for i in range(2) for j in range(2))
    if disagreement > cfg.jacobian_agreement_tolerance_m_per_rad:
        return ZBarMechanismResult(**{**base.__dict__, "status": ZBarStatus.FAILURE, "failure_code": ZBarFailureCode.JACOBIAN_UNAVAILABLE, "message": "two-step Jacobian agreement exceeds tolerance", "jacobian_max_disagreement_m_per_rad": disagreement})
    return ZBarMechanismResult(**{**base.__dict__, "J_d_m_per_rad": j2, "jacobian_step_rad": cfg.jacobian_step_rad, "jacobian_second_step_rad": cfg.jacobian_second_step_rad, "jacobian_max_disagreement_m_per_rad": disagreement})


def evaluate_two_arm_force(mechanism: ZBarMechanismResult, *, setting: int, stiffness_N_per_m: float) -> ZBarForceResult:
    if not mechanism.ok or mechanism.d_left_m is None or mechanism.d_right_m is None:
        return ZBarForceResult(ZBarStatus.FAILURE, setting=setting, stiffness_N_per_m=stiffness_N_per_m, failure_code=mechanism.failure_code, message=mechanism.message or "mechanism state unavailable")
    if isinstance(setting, bool) or setting not in (1, 2, 3, 4, 5) or not math.isfinite(stiffness_N_per_m) or stiffness_N_per_m <= 0.0:
        return ZBarForceResult(ZBarStatus.FAILURE, setting=setting, stiffness_N_per_m=stiffness_N_per_m, failure_code=ZBarFailureCode.SOURCE_MISMATCH, message="discrete setting 1..5 and positive per-arm stiffness are required")
    dl, dr = mechanism.d_left_m, mechanism.d_right_m
    fl, fr = stiffness_N_per_m*dl, stiffness_N_per_m*dr
    energy = 0.5*stiffness_N_per_m*(dl*dl+dr*dr)
    q: tuple[float, float] = ()
    if mechanism.J_d_m_per_rad:
        j = mechanism.J_d_m_per_rad
        q = (-(j[0][0]*fl+j[1][0]*fr), -(j[0][1]*fl+j[1][1]*fr))
    return ZBarForceResult(ZBarStatus.SUCCESS, setting=setting, stiffness_N_per_m=stiffness_N_per_m, d_left_m=dl, d_right_m=dr, force_left_N=fl, force_right_N=fr, stored_energy_J=energy, generalized_rocker_torque_Nm=q)
