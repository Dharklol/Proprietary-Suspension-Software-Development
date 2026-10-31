"""Manufactured analytical reference fixtures, never WUFR setup/tire inputs."""
from dataclasses import replace
import math

from pssd_tire.steady_state_lateral import (
    SteadyStateLateralOperatingState, evaluate_table,
)
from pssd_vehicle.steady_cornering import CorneringTireResponse, solve_cornering
from tests.steady_cornering_fixture import (
    SPRUNG_MASS, WHEEL_MASS, SPRING_K, RADIUS, POSITIONS,
    case, config, geometry, initial, table, rotation, mv,
)

MASS_KG = SPRUNG_MASS+4*WHEEL_MASS
FRONT_DISTANCE_M = POSITIONS[0][0]
REAR_DISTANCE_M = -POSITIONS[2][0]
RACK_GAIN_RAD_PER_M = 10.
CURVATURE_STEPS_PER_M = (.002, .001, .0005)
SPEEDS_M_S = (4., 8.)
AXLE_STIFFNESSES_N_PER_RAD = (
    ('equal_axles', 3200., 3200.),
    ('front_softer', 2400., 3600.),
    ('rear_softer', 3600., 2400.),
)


def single_track_reference(*, mass_kg, front_distance_m, rear_distance_m,
                           front_stiffness_n_per_rad, rear_stiffness_n_per_rad,
                           speed_m_s):
    """First-order reference from planar force/yaw balance, not a trim solve.

    alpha_f=delta-beta-a*k; alpha_r=-beta+b*k; Ff=Cf*alpha_f;
    Fr=Cr*alpha_r; Ff+Fr=m*V^2*k; a*Ff-b*Fr=0.
    C values describe whole axles, not individual tires.
    """
    values = (mass_kg, front_distance_m, rear_distance_m,
              front_stiffness_n_per_rad, rear_stiffness_n_per_rad, speed_m_s)
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError('Explicit finite positive manufactured inputs required')
    m, a, b, cf, cr, speed = values
    length = a+b
    ff = m*speed**2*b/length
    fr = m*speed**2*a/length
    return {'steer_per_curvature_m': length+ff/cf-fr/cr,
            'sideslip_per_curvature_m': b-fr/cr,
            'front_force_per_curvature_nm': ff,
            'rear_force_per_curvature_nm': fr,
            'steer_speed_squared_coefficient_s2_per_m': m/length*(b/cf-a/cr)}


def constant_axle_tires(front_stiffness, rear_stiffness):
    """Use the existing table kernel with explicit load-independent linear curves.

    These manufactured curves have no bias, camber thrust or pressure dependence.
    Their finite source domains remain checked by evaluate_table.
    """
    base = table(camber_thrust=False)
    tables = tuple(replace(base, table_id='manufactured_constant_'+axle,
        curves=tuple(replace(curve, curve_id=curve.curve_id+'_'+axle,
            lateral_force_N=tuple(.5*stiffness*alpha for alpha in curve.slip_angle_rad))
            for curve in base.curves))
        for axle, stiffness in (('front', front_stiffness), ('rear', rear_stiffness)))

    def provider(query):
        axle = 0 if query.corner_id.startswith('front_') else 1
        state = SteadyStateLateralOperatingState(query.slip_angle_rad, query.normal_load_n,
            query.inclination_rad, query.pressure_pa, query.state_id,
            query.source_tire_id, query.convention_id)
        response = evaluate_table(tables[axle], state)
        return CorneringTireResponse(query, response.lateral_force_N,
            response.source_and_adapter_provenance,
            'manufactured_constant_axle_linear_'+str(axle))
    return provider


def analytic_geometry(c, q, rack):
    """Same manufactured geometry, with exact Ry(theta)Rx(phi) derivatives.

    Freeze each current upright material point exactly as the original fixture
    does. This avoids cancellation noise in tiny-curvature verification without
    changing the physical closure or scaled Newton acceptance criteria.
    """
    g = geometry(c, q, rack)
    matrix = rotation(q)
    transpose = tuple(tuple(matrix[j][i] for j in range(3)) for i in range(3))
    sp, cp, st, ct = math.sin(q[1]), math.cos(q[1]), math.sin(q[2]), math.cos(q[2])
    dphi = ((0.,st*cp,-st*sp),(0.,-sp,-cp),(0.,ct*cp,-ct*sp))
    dtheta = ((-st,ct*sp,ct*cp),(0.,0.,0.),(-ct,-st*sp,-st*cp))

    def exact(point, wheel_index=None):
        local = mv(transpose, tuple(v-(q[0] if i==2 else 0.)
                                    for i,v in enumerate(point.point.position_m)))
        dp, dt = mv(dphi,local), mv(dtheta,local)
        body = tuple((float(i==2),dp[i],dt[i]) for i in range(3))
        wheel = tuple(tuple(matrix[i][2] if j==wheel_index else 0.
                             for j in range(4)) for i in range(3))
        return replace(point,J_body=body,J_wheel=wheel)

    wheels = tuple(replace(w,center=exact(w.center,i),contact=exact(w.contact,i))
                   for i,w in enumerate(g.wheels))
    masses = (replace(g.masses[0],point=exact(g.masses[0].point)),
              *(replace(m,point=w.center) for m,w in zip(g.masses[1:],wheels)))
    coefficients = tuple(w.contact.J_wheel[2][i] for i,w in enumerate(wheels))
    jac = tuple(tuple(-value/coefficients[i] for value in w.contact.J_body[2])
                for i,w in enumerate(wheels))
    return replace(g,wheels=wheels,masses=masses,J_wb=jac,contact_coefficients=coefficients)


def solve_reference_case(*, speed, curvature, front_stiffness, rear_stiffness, guess=None):
    tire = constant_axle_tires(front_stiffness, rear_stiffness)
    c = case(curvature, speed_m_s=speed,
        state_id=f'manufactured_{speed}_{front_stiffness}_{rear_stiffness}_{curvature}',
        tire_revision=f'manufactured_cf_{front_stiffness}_cr_{rear_stiffness}')
    return solve_cornering(c, initial() if guess is None else guess,
        geometry_provider=analytic_geometry, tire_provider=tire, config=config())


def reference_inputs(speed, cf, cr):
    return dict(mass_kg=MASS_KG, front_distance_m=FRONT_DISTANCE_M,
        rear_distance_m=REAR_DISTANCE_M, front_stiffness_n_per_rad=cf,
        rear_stiffness_n_per_rad=cr, speed_m_s=speed)


def straight_reference(gravity):
    return {'heave_m': RADIUS-SPRUNG_MASS*gravity/(4*SPRING_K),
            'normal_load_n': MASS_KG*gravity/4}
