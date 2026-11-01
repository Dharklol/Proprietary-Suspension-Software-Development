"""Scalar deformation ports; EQ-SUSP-0040 / BENCH-SUSP-0044.

Positive deformation stores energy. Its explicit time derivative represents
support motion; the gradient maps generalized velocity to deformation rate.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class DeformationPort:
    port_id: str
    deformation_m: float
    gradient: tuple[float, ...]
    explicit_rate_m_s: float
    stiffness_N_m: float
    damping_N_s_m: float
    compression_only: bool = False


@dataclass(frozen=True)
class PortForces:
    generalized_force: tuple[float, ...]
    potential_J: float
    dissipation_W: float
    support_power_W: float


def evaluate_ports(ports, coordinate_rates):
    """Return force and energy terms; stop at contact loss, never clip force.

Q=-gradient*(k*e+c*edot), edot=gradient*qdot+explicit_rate.
For this sign convention support power=(k*e+c*edot)*explicit_rate.
Compression-only ports require both positive deformation and positive effort.
This is a guarded contact-valid branch, not a unilateral event integrator.
"""
    ports=tuple(ports);rates=tuple(coordinate_rates)
    if not rates or not all(math.isfinite(v) for v in rates):
        raise ValueError('Finite nonempty coordinate rates required')
    if len({p.port_id for p in ports})!=len(ports):
        raise ValueError('Duplicate deformation port')
    force=[0.]*len(rates);potential=dissipation=support=0.
    for p in ports:
        values=(p.deformation_m,p.explicit_rate_m_s,p.stiffness_N_m,p.damping_N_s_m,*p.gradient)
        if not p.port_id or len(p.gradient)!=len(rates) or not all(math.isfinite(v) for v in values):
            raise ValueError('Port identity, dimension and finite values required')
        if p.stiffness_N_m<0 or p.damping_N_s_m<0:
            raise ValueError('Nonnegative stiffness and damping required')
        rate=sum(g*v for g,v in zip(p.gradient,rates))+p.explicit_rate_m_s
        effort=p.stiffness_N_m*p.deformation_m+p.damping_N_s_m*rate
        if p.compression_only and (p.deformation_m<=0 or effort<=0):
            raise ValueError('Contact-valid branch ended: '+p.port_id)
        for i,g in enumerate(p.gradient): force[i]-=g*effort
        potential+=.5*p.stiffness_N_m*p.deformation_m**2
        dissipation+=p.damping_N_s_m*rate**2
        support+=effort*p.explicit_rate_m_s
    result=PortForces(tuple(force),potential,dissipation,support)
    if not all(math.isfinite(v) for v in (*result.generalized_force,potential,dissipation,support)):
        raise ValueError('Nonfinite force/energy result')
    return result
