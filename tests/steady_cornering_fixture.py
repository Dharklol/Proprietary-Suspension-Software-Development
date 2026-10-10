"""Manufactured four-wheel fixture. All numbers and tire curves are synthetic."""
from dataclasses import replace
import math

from pssd_tire.steady_state_lateral import (
    SteadyStateLateralCurve, SteadyStateLateralTable, SteadyStateLateralOperatingState, evaluate_table,
)
from pssd_vehicle.force_coordinates import PointReference, rotation_matrix_yaw_pitch_roll
from pssd_vehicle.steady_cornering import (
    ASSUMPTIONS, CORNERS, CorneringCase, CorneringGeometry, CorneringMass,
    CorneringSolverConfig, CorneringTireResponse, CorneringWheel, KinematicPoint,
)
from pssd_vehicle.wufr_road_contact import ideal_rigid_circle_contact

POSITIONS = ((.75,.5),(.75,-.5),(-.75,.5),(-.75,-.5))
RADIUS = .2
SPRING_K = 10000.
SPRUNG_MASS = 100.
WHEEL_MASS = 5.


def case(curvature=0., **changes):
    base = CorneringCase("synthetic_state", "SYNTHETIC", "geometry-v1", "spring-v1", "tire-v1",
        "synthetic_heading", "synthetic_origin", 8., curvature, (75000.,)*4, 9.81,
        1, 1, "synthetic_seated_spring", "synthetic_source", "synthetic_intended", "synthetic_signs",
        ASSUMPTIONS, "uniform_acceleration_current_mass_lumps",
        "virtual_tangential_force_at_current_total_cg", "fixed_radius_zero_width_rigid_circle",
        "evidence_only", 0.)
    return replace(base, **changes)


def config(**changes):
    base = CorneringSolverConfig(
        (.05,.1,.1,.1,.03,100.,300.,300.,300.,300.),
        (1000.,500.,500.,300.,300.,300.,300.,1000.,1000.,500.),
        (.08,-.2,-.2,-.3,-.045,-500.,10.,10.,10.,10.),
        (.25,.2,.2,.3,.045,500.,2000.,2000.,2000.,2000.),
        (2e-6,2e-6,2e-6,2e-6,2e-6,1e-3,1e-3,1e-3,1e-3,1e-3),
        1e-11, 1e-9, 30, 20)
    return replace(base, **changes)


def initial():
    return (.18, .002, -.002, .01, .002, 0., 300.,300.,300.,300.)


def mv(matrix, vector):
    return tuple(sum(a*b for a,b in zip(row,vector)) for row in matrix)


def rotation(q):
    return rotation_matrix_yaw_pitch_roll(phi_rad=q[1], theta_rad=q[2], psi_rad=0.)


def plane_and_forward(q, rack, index):
    delta = 10*rack if index < 2 else 0.
    matrix = rotation(q)
    return (mv(matrix, (-math.sin(delta),math.cos(delta),0.)),
            mv(matrix, (math.cos(delta),math.sin(delta),0.)))


def center_position(q, w, index):
    return tuple(v+(q[0] if i == 2 else 0.)
                 for i,v in enumerate(mv(rotation(q), (*POSITIONS[index],w[index]))))


def contact_position(q, w, rack, index):
    plane,_ = plane_and_forward(q,rack,index)
    return ideal_rigid_circle_contact(center_position(q,w,index),plane,(0.,0.,1.),RADIUS).contact_point_m


def sprung_position(q,w):
    return tuple(v+(q[0] if i == 2 else 0.)
                 for i,v in enumerate(mv(rotation(q),(0.,0.,.35))))


def compatible_wheels(q, rack):
    matrix = rotation(q)
    output = []
    for index,(x,y) in enumerate(POSITIONS):
        plane,_ = plane_and_forward(q,rack,index)
        # Exact fully-steered gap root in each vertical guide coordinate.
        output.append((RADIUS*math.sqrt(1-plane[2]**2)-q[0]-matrix[2][0]*x-matrix[2][1]*y)/matrix[2][2])
    return tuple(output)


def point(c,q,w,name,position_fn,step=5e-6):
    def derivative(values,index,body):
        minus = tuple(v-step if i==index else v for i,v in enumerate(values))
        plus = tuple(v+step if i==index else v for i,v in enumerate(values))
        a,b = (position_fn(minus,w),position_fn(plus,w)) if body else (position_fn(q,minus),position_fn(q,plus))
        return tuple((hi-lo)/(2*step) for lo,hi in zip(a,b))
    body_columns = tuple(derivative(q,i,True) for i in range(3))
    wheel_columns = tuple(derivative(w,i,False) for i in range(4))
    ref = PointReference(name,c.heading_frame_id,c.origin_id,position_fn(q,w),name,
                         "synthetic_geometry",c.configuration_id,"synthetic_verification",
                         fixed_role="current_kinematic_point")
    return KinematicPoint(ref,tuple(tuple(col[i] for col in body_columns) for i in range(3)),
                          tuple(tuple(col[i] for col in wheel_columns) for i in range(3)),
                          "material_application_point")


def geometry(c,q,rack):
    w = compatible_wheels(q,rack)
    step=5e-6
    columns = []
    for j in range(3):
        low=compatible_wheels(tuple(v-step if i==j else v for i,v in enumerate(q)),rack)
        high=compatible_wheels(tuple(v+step if i==j else v for i,v in enumerate(q)),rack)
        columns.append(tuple((b-a)/(2*step) for a,b in zip(low,high)))
    jac = tuple(tuple(col[i] for col in columns) for i in range(4))
    wheels=[]
    masses=[CorneringMass(SPRUNG_MASS,point(c,q,w,"sprung_cg",sprung_position))]
    for index,name in enumerate(CORNERS):
        center=point(c,q,w,"center_"+name,lambda qb,zw,i=index:center_position(qb,zw,i))
        # Freeze the instantaneous circle material point in the upright/body frame.
        # The lowest-point locus changes material identity as the plane rotates.
        radial=tuple(a-b for a,b in zip(contact_position(q,w,rack,index),center_position(q,w,index)))
        transpose=tuple(tuple(rotation(q)[j][i] for j in range(3)) for i in range(3))
        local_radial=mv(transpose,radial)
        def material_contact(qb,zw,i=index,local=local_radial):
            return tuple(a+b for a,b in zip(center_position(qb,zw,i),mv(rotation(qb),local)))
        contact=point(c,q,w,"contact_"+name,material_contact)
        plane,forward=plane_and_forward(q,rack,index)
        length=math.hypot(*forward[:2])
        wheels.append(CorneringWheel(name,center,contact,
            (forward[0]/length,forward[1]/length,0.),math.asin(plane[2]),
            "front_tie_rod_once" if index<2 else "rear_native_toe_link"))
        masses.append(CorneringMass(WHEEL_MASS,center))
    return CorneringGeometry(q,rack,c.state_id,c.configuration_id,c.geometry_revision,c.setup_revision,
        w,jac,(rotation(q)[2][2],)*4,tuple(p.contact.point.position_m[2] for p in wheels),
        tuple(-SPRING_K*v for v in w),tuple(masses),tuple(wheels),
        ("synthetic_geometry", "synthetic_springs"),"synthetic_geometry_branch")


def table(camber_thrust=True):
    curves=[]
    for load in (10.,2000.):
        for inclination in (-.3,.3):
            for pressure in (50000.,100000.):
                curves.append(SteadyStateLateralCurve(
                    f"synthetic_{load}_{inclination}_{pressure}",load,inclination,pressure,
                    (-.5,0.,.5),tuple(load*(6*a+(0.2*inclination if camber_thrust else 0.)) for a in (-.5,0.,.5)),
                    "synthetic_source","synthetic_intended","synthetic_fixture","synthetic_hash",
                    "synthetic_signs","synthetic_adapter","synthetic_verification",
                    segment_branch_ids=("synthetic_linear","synthetic_linear")))
    return SteadyStateLateralTable("synthetic_signed_table",tuple(curves))


TABLE = table()


def tire(query):
    state=SteadyStateLateralOperatingState(query.slip_angle_rad,query.normal_load_n,
        query.inclination_rad,query.pressure_pa,query.state_id,query.source_tire_id,query.convention_id)
    result=evaluate_table(TABLE,state)
    return CorneringTireResponse(query,result.lateral_force_N,
        result.source_and_adapter_provenance,"synthetic_linear")
