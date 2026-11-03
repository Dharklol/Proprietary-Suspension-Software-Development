"""Front design-intent spring binding for generalized force ports (BENCH-SUSP-0045)."""
from dataclasses import dataclass
import math
from .actuation import ActuationStateResult, solve_actuation_q_L_state
from .geometry import ActuationAttachment
from .kinematics import KinematicsSolverConfig
from .generalized_forces import DeformationPort
from .spring_force import SpringLawKind, SpringStateResult, evaluate_spring_from_actuation


def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def axis(a,b):
    v=sub(b,a);length=math.sqrt(dot(v,v))
    if length<1e-12: raise ValueError('Degenerate hinge axis')
    return tuple(x/length for x in v)


@dataclass(frozen=True)
class NativeFrontSpringPort:
    port: DeformationPort
    configuration_id: str
    geometry_id: str
    spring_source_id: str
    assumption_ids: tuple[str,...]
    installed_as_built_authority: bool
    q_L_rad: float
    rocker_derivative: float
    coil_point_derivative_m_per_rad: tuple[float,...]
    actuation_state: ActuationStateResult
    spring_state: SpringStateResult


def bind_front_spring_port(corner,nominal_wheel_reference,package,q_L_rad,*,geometry_id,source_authority):
    """Exact implicit-closure derivative in [heave,pitch,left qL,right qL].

Both spring eyes share chassis rigid motion, so heave/pitch deformation columns
are zero even at finite pitch. This binds the reviewed front linear law only;
it does not provide damping, installed limits or vehicle equilibrium.
"""
    if corner.axle.value!='front' or package.front.kind is not SpringLawKind.LINEAR:
        raise ValueError('Front linear design-intent package required')
    if not geometry_id or not source_authority or not math.isfinite(q_L_rad):
        raise ValueError('Geometry/source identity and finite coordinate required')
    state=solve_actuation_q_L_state(corner,nominal_wheel_reference,q_L_rad,
        geometry_id=geometry_id,configuration_id=package.configuration_id,source_authority=source_authority,
        kinematics_config=KinematicsSolverConfig(root_angle_tolerance_rad=1e-13,length_residual_tolerance_m=1e-13,squared_residual_zero_tolerance_m2=1e-20))
    if not state.ok: raise ValueError('Native actuation unavailable: '+state.message)
    if state.owning_arm!=ActuationAttachment.UPPER_ARM.value: raise ValueError('Expected source front upper-arm actuation')
    w=corner.wishbone;upstream=state.wheel_state.upstream_state
    uL=axis(w.lower_fore_inboard.position_m,w.lower_aft_inboard.position_m)
    uU=axis(w.upper_fore_inboard.position_m,w.upper_aft_inboard.position_m)
    d=sub(upstream.upper_upright_m,upstream.lower_upright_m)
    lower=cross(uL,sub(upstream.lower_upright_m,w.lower_fore_inboard.position_m))
    upper=cross(uU,sub(upstream.upper_upright_m,w.upper_fore_inboard.position_m))
    denominator=dot(d,upper)
    if abs(denominator)<1e-10: raise ValueError('Near-singular upper-arm closure')
    ratio=dot(d,lower)/denominator
    attachment_derivative=tuple(ratio*x for x in cross(uU,sub(state.arm_attachment_m,w.upper_fore_inboard.position_m)))
    a=corner.actuation;pivot=a.rocker_pivot.position_m
    rocker_axis=axis(pivot,a.rocker_axis_reference.position_m)
    rod_derivative=cross(rocker_axis,sub(state.rocker_rod_point_m,pivot))
    rod=sub(state.rocker_rod_point_m,state.arm_attachment_m)
    denominator=dot(rod,rod_derivative)
    if abs(denominator)<1e-10: raise ValueError('Near-singular rocker closure')
    theta_prime=dot(rod,attachment_derivative)/denominator
    coil_derivative=tuple(theta_prime*x for x in cross(rocker_axis,sub(state.rocker_coilover_point_m,pivot)))
    coil_vector=sub(state.rocker_coilover_point_m,a.chassis_attachment.position_m)
    length=math.sqrt(dot(coil_vector,coil_vector))
    dL=dot(coil_vector,coil_derivative)/length
    active=2 if corner.side.value=='left' else 3
    length_gradient=tuple(dL if i==active else 0. for i in range(4))
    spring=evaluate_spring_from_actuation(package.front,package.reference,state,dL_dq=length_gradient,
        coordinate_order=('heave','pitch_front_up','left_qL','right_qL'),coordinate_units=('m','rad','rad','rad'),
        use_local_rho_dw_when_available=False)
    if not spring.ok or not spring.generalized_force_available:
        raise ValueError('Native spring unavailable: '+spring.message)
    port=DeformationPort('native-front-spring-'+corner.side.value,spring.x_s_m,tuple(-x for x in length_gradient),0.,package.front.linear_rate_N_per_m,0.)
    return NativeFrontSpringPort(port,package.configuration_id,geometry_id,package.source_record_id,
        spring.assumption_ids,spring.installed_as_built_authority,q_L_rad,theta_prime,coil_derivative,state,spring)
