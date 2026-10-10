"""Bounded provider-neutral development equilibrium under AUTH-VEH-0012.

This composes explicit geometry, spring and forward signed tire providers. It
never calls the conservative static solver or supplies WUFR defaults. Coordinates
are (z_s, phi, theta, beta, rack, hold, Fz_FL, Fz_FR, Fz_RL, Fz_RR).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Callable

from .force_coordinates import AppliedWrench, PointReference, ResultantWrench, assemble_wrenches
from .operating_states import WheelPosition
from .planar_kinematics import PlanarMotionSample, WheelPlanarLocation, tire_slip_kinematics
from .steady_cornering_motion import (
    CurrentMassPoint, ManeuverInertia, SteadyCorneringMotion, VirtualSpeedHold,
    maneuver_inertia, steady_cornering_motion, virtual_speed_hold,
)

Vector = tuple[float, ...]
Matrix = tuple[Vector, ...]
CORNERS = ("front_left", "front_right", "rear_left", "rear_right")
ASSUMPTIONS = ("ASM-VEH-0006", "ASM-VEH-0007", "ASM-VEH-0008")
RESULT_LABEL = "uncorrelated_design_intent_steady_cornering_with_virtual_speed_hold"


class CorneringFailure(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise CorneringFailure(code, message)


def _vector(values: Vector, size: int, label: str) -> None:
    _require(len(values) == size and all(math.isfinite(v) for v in values),
             "invalid_contract", f"{label} requires {size} finite entries")


def _matrix(values: Matrix, rows: int, columns: int, label: str) -> None:
    _require(len(values) == rows, "invalid_contract", f"{label} requires {rows} rows")
    for row in values:
        _vector(row, columns, label)


@dataclass(frozen=True)
class CorneringCase:
    state_id: str
    configuration_id: str
    geometry_revision: str
    setup_revision: str
    tire_revision: str
    heading_frame_id: str
    origin_id: str
    speed_m_s: float
    curvature_per_m: float
    pressures_pa: Vector
    gravity_m_s2: float
    front_arb_setting: int
    rear_arb_setting: int
    spring_reference_id: str
    source_tire_id: str
    intended_tire_id: str
    tire_convention_id: str
    accepted_assumptions: tuple[str, ...]
    inertia_policy: str
    speed_hold_policy: str
    radius_policy: str
    result_role: str
    state_weight: float

    def __post_init__(self) -> None:
        for name in ("state_id", "configuration_id", "geometry_revision", "setup_revision",
                     "tire_revision", "heading_frame_id", "origin_id", "spring_reference_id",
                     "source_tire_id", "intended_tire_id", "tire_convention_id"):
            _require(bool(getattr(self, name).strip()), "missing_source", f"{name} is required")
        _vector(self.pressures_pa, 4, "pressures")
        _require(all(p > 0 for p in self.pressures_pa), "missing_pressure", "Four positive pressures required")
        _require(math.isfinite(self.gravity_m_s2) and self.gravity_m_s2 > 0,
                 "invalid_contract", "Explicit positive gravity required")
        _require(set(self.accepted_assumptions) == set(ASSUMPTIONS),
                 "assumptions_not_authorized", "Accept all three development assumptions")
        _require(self.inertia_policy == "uniform_acceleration_current_mass_lumps",
                 "inertia_not_authorized", "Explicit uniform inertia policy required")
        _require(self.speed_hold_policy == "virtual_tangential_force_at_current_total_cg",
                 "speed_hold_not_authorized", "Explicit virtual holding policy required")
        _require(self.radius_policy == "fixed_radius_zero_width_rigid_circle",
                 "radius_not_authorized", "Explicit maneuver rigid-circle policy required")
        _require(self.result_role == "evidence_only" and self.state_weight == 0,
                 "authority_not_authorized", "Development results must be zero-weight evidence")
        _require(type(self.front_arb_setting) is int and type(self.rear_arb_setting) is int
                 and self.front_arb_setting in range(1, 6) and self.rear_arb_setting in range(1, 6),
                 "invalid_setup", "ARB settings must be explicit discrete 1..5")
        steady_cornering_motion(speed_m_s=self.speed_m_s, curvature_per_m=self.curvature_per_m,
                               sideslip_rad=0)


@dataclass(frozen=True)
class KinematicPoint:
    point: PointReference
    J_body: Matrix  # 3 spatial rows x 3 body coordinates, holding wheel coordinates fixed
    J_wheel: Matrix  # 3 spatial rows x 4 physical wheel coordinates
    jacobian_role: str  # material_application_point; never moving_contact_locus


@dataclass(frozen=True)
class CorneringMass:
    mass_kg: float
    point: KinematicPoint


@dataclass(frozen=True)
class CorneringWheel:
    corner_id: str
    center: KinematicPoint
    contact: KinematicPoint
    forward_heading: Vector  # already projected into horizontal road and normalized
    inclination_rad: float  # fully steered plane, mapped by source-owned tire convention
    steering_owner: str  # front_tie_rod_once or rear_native_toe_link


@dataclass(frozen=True)
class CorneringGeometry:
    body_coordinates: Vector
    rack_m: float
    state_id: str
    configuration_id: str
    geometry_revision: str
    setup_revision: str
    wheel_coordinates_m: Vector
    J_wb: Matrix  # 4 x 3, from fully steered contact compatibility
    contact_coefficients: Vector
    contact_gaps_m: Vector
    suspension_force_n: Vector
    masses: tuple[CorneringMass, ...]
    wheels: tuple[CorneringWheel, ...]
    source_ids: tuple[str, ...]
    branch_id: str


@dataclass(frozen=True)
class CorneringTireQuery:
    state_id: str
    corner_id: str
    source_tire_id: str
    intended_tire_id: str
    tire_revision: str
    convention_id: str
    slip_angle_rad: float
    normal_load_n: float
    inclination_rad: float
    pressure_pa: float


@dataclass(frozen=True)
class CorneringTireResponse:
    query: CorneringTireQuery
    lateral_force_n: float
    source_ids: tuple[str, ...]
    branch_id: str


@dataclass(frozen=True)
class CorneringEvaluation:
    coordinates: Vector
    geometry: CorneringGeometry
    motion: SteadyCorneringMotion
    inertia: ManeuverInertia
    holder: VirtualSpeedHold
    tires: tuple[CorneringTireResponse, ...]
    body_direct_force: Vector
    wheel_external_force: Vector
    residual: Vector
    physical_wrench: ResultantWrench

    @property
    def branch_signature(self) -> tuple[str, ...]:
        return (self.geometry.branch_id, *(t.branch_id for t in self.tires))


GeometryProvider = Callable[[CorneringCase, Vector, float], CorneringGeometry]
TireProvider = Callable[[CorneringTireQuery], CorneringTireResponse]


def _validate_geometry(case: CorneringCase, x: Vector, geometry: CorneringGeometry) -> None:
    _require((geometry.state_id, geometry.configuration_id, geometry.geometry_revision,
              geometry.setup_revision, geometry.body_coordinates, geometry.rack_m) ==
             (case.state_id, case.configuration_id, case.geometry_revision,
              case.setup_revision, x[:3], x[4]), "source_mismatch", "Geometry must match trial and case")
    for label, values in (("wheel coordinates", geometry.wheel_coordinates_m),
                          ("contact coefficients", geometry.contact_coefficients),
                          ("contact gaps", geometry.contact_gaps_m),
                          ("suspension forces", geometry.suspension_force_n)):
        _vector(values, 4, label)
    _matrix(geometry.J_wb, 4, 3, "J_wb")
    _require(all(abs(c) > 1e-10 for c in geometry.contact_coefficients),
             "singular_contact", "Contact coefficient is singular")
    _require(max(abs(g) for g in geometry.contact_gaps_m) <= 1e-9,
             "compatibility_failure", "Fully steered road roots did not close")
    _require(tuple(w.corner_id for w in geometry.wheels) == CORNERS,
             "invalid_contract", "Wheel order must be FL, FR, RL, RR")
    _require(bool(geometry.source_ids) and all(geometry.source_ids) and bool(geometry.branch_id),
             "missing_source", "Geometry source and branch provenance required")
    _require(bool(geometry.masses), "missing_mass", "Explicit current mass points required")
    points = [m.point for m in geometry.masses]
    for index, wheel in enumerate(geometry.wheels):
        points.extend((wheel.center, wheel.contact))
        _vector(wheel.forward_heading, 3, "forward direction")
        _require(abs(wheel.forward_heading[2]) <= 1e-12 and
                 abs(math.hypot(*wheel.forward_heading)-1) <= 1e-10,
                 "frame_error", "Wheel forward direction must be a horizontal unit vector")
        _require(math.isfinite(wheel.inclination_rad), "invalid_contract", "Finite inclination required")
        owner = "front_tie_rod_once" if index < 2 else "rear_native_toe_link"
        _require(wheel.steering_owner == owner, "steering_ownership_error", f"{wheel.corner_id}: {owner} required")
        _require(abs(wheel.contact.point.position_m[2]) <= 1e-9,
                 "compatibility_failure", "Contact must lie on heading-frame z=0 road")
    for i, wheel in enumerate(geometry.wheels):
        c = geometry.contact_coefficients[i]
        _require(abs(wheel.contact.J_wheel[2][i]-c) <= 1e-6,
                 "compatibility_derivative_error", "Normal virtual work must match contact coefficient")
        _require(all(abs(wheel.contact.J_wheel[2][j]) <= 1e-10 for j in range(4) if j != i),
                 "compatibility_derivative_error", "Diagonal contact contract does not permit cross-wheel gaps")
        _require(all(abs(wheel.contact.J_body[2][j]+c*geometry.J_wb[i][j]) <= 1e-6
                     for j in range(3)), "compatibility_derivative_error",
                 "Implicit contact reduction disagrees with normal virtual work")
    for point in points:
        _require((point.point.frame_id, point.point.origin_id, point.point.configuration_id) ==
                 (case.heading_frame_id, case.origin_id, case.configuration_id),
                 "frame_error", "Point frame/origin/configuration mismatch")
        _require(point.jacobian_role == "material_application_point",
                 "application_point_error", "Virtual work requires material-point Jacobians")
        _matrix(point.J_body, 3, 3, "point J_body")
        _matrix(point.J_wheel, 3, 4, "point J_wheel")


def point_generalized_force(point: KinematicPoint, force_n: Vector) -> tuple[Vector, Vector]:
    """Direct and wheel terms, with instantaneous applied force held fixed."""
    _require(point.jacobian_role == "material_application_point",
             "application_point_error", "Force mapping requires material-point Jacobians")
    _vector(force_n, 3, "point force")
    _matrix(point.J_body, 3, 3, "point J_body")
    _matrix(point.J_wheel, 3, 4, "point J_wheel")
    return (tuple(sum(point.J_body[i][j]*force_n[i] for i in range(3)) for j in range(3)),
            tuple(sum(point.J_wheel[i][j]*force_n[i] for i in range(3)) for j in range(4)))


def evaluate_cornering(case: CorneringCase, coordinates: Vector, *,
                        geometry_provider: GeometryProvider, tire_provider: TireProvider) -> CorneringEvaluation:
    _vector(coordinates, 10, "trial coordinates")
    _require(all(v > 0 for v in coordinates[6:]), "negative_reaction", "Four active contacts require positive Fz")
    geometry = geometry_provider(case, coordinates[:3], coordinates[4])
    _validate_geometry(case, coordinates, geometry)
    motion = steady_cornering_motion(speed_m_s=case.speed_m_s,
                                    curvature_per_m=case.curvature_per_m, sideslip_rad=coordinates[3])
    inertia = maneuver_inertia(motion, mass_points=tuple(
        CurrentMassPoint(f"{m.point.point.source_id}:{m.point.point.point_id}",
                         m.mass_kg, m.point.point.position_m)
        for m in geometry.masses), policy=case.inertia_policy)
    total_mass = math.fsum(m.mass_kg for m in geometry.masses)
    cg_reference = PointReference("current_total_cg", case.heading_frame_id, case.origin_id,
                                  inertia.current_total_cg_heading_m, "current_total_cg",
                                  "+".join(geometry.source_ids), case.configuration_id,
                                  "AUTH-VEH-0012", fixed_role="current_mass_weighted_point")
    cg = KinematicPoint(cg_reference,
        tuple(tuple(sum(m.mass_kg/total_mass*m.point.J_body[i][j] for m in geometry.masses)
                    for j in range(3)) for i in range(3)),
        tuple(tuple(sum(m.mass_kg/total_mass*m.point.J_wheel[i][j] for m in geometry.masses)
                    for j in range(4)) for i in range(3)), "material_application_point")
    holder = virtual_speed_hold(motion, force_n=coordinates[5], policy=case.speed_hold_policy)
    loads: list[tuple[KinematicPoint, AppliedWrench, bool]] = []

    def add_load(point: KinematicPoint, force: Vector, name: str, source: str,
                 reduced: bool = True) -> None:
        loads.append((point, AppliedWrench(name, case.heading_frame_id, case.origin_id,
                      point.point, force_N=force, source_id=source, authority="AUTH-VEH-0012"), reduced))

    for index, (mass, inertial_force) in enumerate(zip(geometry.masses, inertia.forces_heading_n)):
        add_load(mass.point, (0., 0., -mass.mass_kg*case.gravity_m_s2),
                 f"gravity_{index}", mass.point.point.source_id)
        add_load(mass.point, inertial_force, f"inertia_{index}", "ASM-VEH-0006")
    add_load(cg, holder.force_heading_n, "virtual_speed_hold", "ASM-VEH-0007")
    planar = PlanarMotionSample(motion.forward_velocity_m_s, motion.lateral_velocity_m_s,
                               motion.yaw_rate_rad_s)
    tires = []
    for index, wheel in enumerate(geometry.wheels):
        center = wheel.center.point.position_m
        location = WheelPlanarLocation(WheelPosition(wheel.corner_id),
            center[0]-cg_reference.position_m[0], center[1]-cg_reference.position_m[1])
        slip = tire_slip_kinematics(planar, location,
                                   math.atan2(wheel.forward_heading[1], wheel.forward_heading[0]))
        query = CorneringTireQuery(case.state_id, wheel.corner_id, case.source_tire_id,
            case.intended_tire_id, case.tire_revision, case.tire_convention_id,
            slip.slip_angle_rad, coordinates[6+index], wheel.inclination_rad, case.pressures_pa[index])
        tire = tire_provider(query)
        _require(tire.query == query, "source_mismatch", "Tire query was substituted")
        _require(math.isfinite(tire.lateral_force_n), "invalid_contract", "Finite signed Fy required")
        _require(bool(tire.source_ids) and all(tire.source_ids) and bool(tire.branch_id),
                 "missing_source", "Tire source and branch provenance required")
        tires.append(tire)
        ex, ey, _ = wheel.forward_heading
        add_load(wheel.contact, (-ey*tire.lateral_force_n, ex*tire.lateral_force_n, 0.),
                 f"lateral_{wheel.corner_id}", "+".join(tire.source_ids))
        # Normal reaction belongs only in constrained wheel balance and full wrench.
        add_load(wheel.contact, (0., 0., coordinates[6+index]),
                 f"normal_{wheel.corner_id}", "EQ-VEH-0025", reduced=False)
    body = [0.]*3
    wheel_force = [0.]*4
    for point, load, reduced in loads:
        if reduced:
            direct, mapped = point_generalized_force(point, load.force_N)
            body = [a+b for a,b in zip(body, direct)]
            wheel_force = [a+b for a,b in zip(wheel_force, mapped)]
    wheel_total = tuple(wheel_force[i]+geometry.suspension_force_n[i] for i in range(4))
    body_residual = tuple(body[j]+sum(geometry.J_wb[i][j]*wheel_total[i]
                                   for i in range(4)) for j in range(3))
    wheel_residual = tuple(wheel_total[i]+geometry.contact_coefficients[i]*coordinates[6+i]
                          for i in range(4))
    physical = assemble_wrenches(tuple(load for _,load,_ in loads), cg_reference)
    residual = (*body_residual, *wheel_residual, *physical.resultant_force_N[:2],
                physical.resultant_moment_Nm[2])
    _vector(residual, 10, "assembled residual")
    return CorneringEvaluation(coordinates, geometry, motion, inertia, holder, tuple(tires),
                              tuple(body), tuple(wheel_force), residual, physical)


@dataclass(frozen=True)
class CorneringSolverConfig:
    coordinate_scales: Vector
    residual_scales: Vector
    lower_bounds: Vector
    upper_bounds: Vector
    fd_steps: Vector
    scaled_residual_tolerance: float
    minimum_reciprocal_pivot_ratio: float
    max_iterations: int
    max_backtracks: int

    def __post_init__(self) -> None:
        for name in ("coordinate_scales", "residual_scales", "lower_bounds", "upper_bounds", "fd_steps"):
            _vector(getattr(self, name), 10, name)
        _require(all(v > 0 for v in (*self.coordinate_scales, *self.residual_scales, *self.fd_steps)),
                 "invalid_contract", "Scales and derivative steps must be positive")
        _require(all(a < b for a,b in zip(self.lower_bounds, self.upper_bounds)),
                 "invalid_contract", "Each coordinate requires a nonempty bounded interval")
        _require(self.lower_bounds[6] > 0 and all(v > 0 for v in self.lower_bounds[6:]),
                 "invalid_contract", "Four-active-contact reaction bounds must be positive")
        _require(math.isfinite(self.scaled_residual_tolerance) and self.scaled_residual_tolerance > 0
                 and math.isfinite(self.minimum_reciprocal_pivot_ratio)
                 and 0 < self.minimum_reciprocal_pivot_ratio <= 1,
                 "invalid_contract", "Finite positive solver thresholds required")
        _require(type(self.max_iterations) is int and type(self.max_backtracks) is int
                 and self.max_iterations > 0 and self.max_backtracks > 0,
                 "invalid_contract", "Finite iteration/backtrack limits required")


@dataclass(frozen=True)
class CorneringSolveResult:
    ok: bool
    case: CorneringCase
    coordinates: Vector
    evaluation: CorneringEvaluation | None
    iterations: int
    scaled_residual_norm: float | None
    reciprocal_pivot_ratio: float | None
    residual_history: Vector
    trial_failures: tuple[tuple[str, str], ...]
    failure_code: str | None = None
    message: str = ""
    result_label: str | None = None


def _linear_solve(matrix: Matrix, rhs: Vector, minimum_ratio: float) -> tuple[Vector, float]:
    """Partial-pivot elimination on the explicitly scaled 10x10 residual tangent."""
    _matrix(matrix, 10, 10, "scaled tangent")
    a, b, pivots = [list(row) for row in matrix], list(rhs), []
    for k in range(10):
        row = max(range(k, 10), key=lambda i: abs(a[i][k]))
        _require(abs(a[row][k]) > 1e-14, "singular_tangent", f"Singular tangent pivot {k}")
        a[k], a[row] = a[row], a[k]
        b[k], b[row] = b[row], b[k]
        pivots.append(abs(a[k][k]))
        for i in range(k+1, 10):
            factor = a[i][k]/a[k][k]
            for j in range(k+1, 10):
                a[i][j] -= factor*a[k][j]
            b[i] -= factor*b[k]
    ratio = min(pivots)/max(pivots)
    _require(ratio >= minimum_ratio, "singular_tangent", f"Reciprocal pivot ratio {ratio:g} below threshold")
    x = [0.]*10
    for i in range(9, -1, -1):
        x[i] = (b[i]-sum(a[i][j]*x[j] for j in range(i+1, 10)))/a[i][i]
    _vector(tuple(x), 10, "Newton increment")
    return tuple(x), ratio


def solve_cornering(case: CorneringCase, initial: Vector, *, geometry_provider: GeometryProvider,
                     tire_provider: TireProvider, config: CorneringSolverConfig) -> CorneringSolveResult:
    x, evaluation, norm, ratio, iterations = initial, None, None, None, 0
    history, failures = [], []

    def inside(point: Vector) -> bool:
        return all(a <= v <= b for v,a,b in zip(point, config.lower_bounds, config.upper_bounds))

    def evaluate(point: Vector) -> CorneringEvaluation:
        _require(inside(point), "bounds_failure", "Trial leaves explicit coordinate bounds")
        try:
            return evaluate_cornering(case, point, geometry_provider=geometry_provider,
                                      tire_provider=tire_provider)
        except CorneringFailure:
            raise
        except ValueError as exc:
            # Preserve source-specific tire/contact failures without repairing inputs.
            raise CorneringFailure(str(getattr(exc, "failure_code", "provider_failure")), str(exc)) from exc

    try:
        _vector(x, 10, "initial coordinates")
        for iterations in range(config.max_iterations+1):
            evaluation = evaluate(x)
            norm = max(abs(r)/s for r,s in zip(evaluation.residual, config.residual_scales))
            history.append(norm)
            columns = []
            # Check rank even at a root; a residual-zero manifold is not a unique equilibrium.
            for j, step in enumerate(config.fd_steps):
                probes = []
                for sign in (-1., 1.):
                    point = tuple(v+sign*step if i == j else v for i,v in enumerate(x))
                    if not inside(point):
                        continue
                    try:
                        probe = evaluate(point)
                        _require(probe.branch_signature == evaluation.branch_signature,
                                 "branch_change", "Tangent probe changes source branch")
                        probes.append((sign*step, probe))
                    except CorneringFailure as exc:
                        failures.append((exc.code, str(exc)))
                _require(bool(probes), "tangent_provider_failure", f"No valid derivative probe on axis {j}")
                if len(probes) == 2:
                    low, high = probes
                else:
                    low, high = (0., evaluation), probes[0]
                column = tuple((b-a)/(high[0]-low[0])*config.coordinate_scales[j]/config.residual_scales[i]
                               for i,(a,b) in enumerate(zip(low[1].residual, high[1].residual)))
                columns.append(column)
            tangent = tuple(tuple(columns[j][i] for j in range(10)) for i in range(10))
            increment, ratio = _linear_solve(tangent,
                tuple(-r/s for r,s in zip(evaluation.residual, config.residual_scales)),
                config.minimum_reciprocal_pivot_ratio)
            if norm <= config.scaled_residual_tolerance:
                wrench = evaluation.physical_wrench
                _require(math.hypot(*wrench.resultant_force_N) <= 1e-6 and
                         math.hypot(*wrench.resultant_moment_Nm) <= 1e-6,
                         "physical_closure_failure", "Independent force/moment closure exceeds 1e-6 N / N*m")
                return CorneringSolveResult(True, case, x, evaluation, iterations, norm, ratio,
                                           tuple(history), tuple(failures), result_label=RESULT_LABEL)
            _require(iterations < config.max_iterations, "nonconvergence", "Iteration limit reached")
            accepted = False
            for backtrack in range(config.max_backtracks):
                factor = 0.5**backtrack
                point = tuple(v+factor*d*s for v,d,s in zip(x, increment, config.coordinate_scales))
                if not inside(point):
                    continue
                try:
                    trial = evaluate(point)
                    _require(trial.branch_signature == evaluation.branch_signature,
                             "branch_change", "Newton trial changes source branch")
                    trial_norm = max(abs(r)/s for r,s in zip(trial.residual, config.residual_scales))
                    if trial_norm < norm*(1-1e-4*factor):
                        x, accepted = point, True
                        break
                except CorneringFailure as exc:
                    failures.append((exc.code, str(exc)))
            _require(accepted, "line_search_failure", "No admissible decreasing Newton trial")
    except CorneringFailure as exc:
        return CorneringSolveResult(False, case, x, evaluation, iterations, norm, ratio,
                                   tuple(history), tuple(failures), exc.code, str(exc))
    raise AssertionError("Unreachable bounded solver state")


@dataclass(frozen=True)
class CorneringContinuation:
    branch_id: str
    results: tuple[CorneringSolveResult, ...]
    complete: bool


def continue_cornering(cases: tuple[CorneringCase, ...], initial: Vector, *, branch_id: str,
                       geometry_provider: GeometryProvider, tire_provider: TireProvider,
                       config: CorneringSolverConfig) -> CorneringContinuation:
    """Solve an explicit zero-curvature seed then ordered curvature controls.

    Failed points are retained and terminate this branch. No step invention,
    branch switch, inferred pressure or arbitrary rack grid is performed.
    """
    _require(bool(cases) and cases[0].curvature_per_m == 0, "invalid_continuation",
             "Continuation starts with an explicit zero-curvature case")
    _require(bool(branch_id.strip()), "missing_source", "Continuation branch ID required")
    first = cases[0]
    invariant_names = tuple(name for name in first.__dataclass_fields__
                            if name not in ("state_id", "curvature_per_m"))
    _require(all(all(getattr(case, name) == getattr(first, name) for name in invariant_names)
                 for case in cases), "source_mismatch", "Continuation controls must share explicit sources/setup/speed")
    results = []
    signature = None
    for case in cases:
        result = solve_cornering(case, initial, geometry_provider=geometry_provider,
                                 tire_provider=tire_provider, config=config)
        if result.ok:
            current = result.evaluation.branch_signature
            if signature is not None and current != signature:
                result = replace(result, ok=False, failure_code="branch_change",
                                 message="Continuation changed source branch", result_label=None)
            signature = current
        results.append(result)
        if not result.ok:
            return CorneringContinuation(branch_id, tuple(results), False)
        initial = result.coordinates
    return CorneringContinuation(branch_id, tuple(results), True)
