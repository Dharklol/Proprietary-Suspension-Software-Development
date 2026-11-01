"""Local conservative stiffness under an explicitly supplied compression map."""
from dataclasses import dataclass
import math
from .spring_force import SpringConstitutiveResult


@dataclass(frozen=True)
class CompressionMap:
    spring_id: str
    configuration_id: str
    coordinate_id: str
    derivative_source_id: str
    gradient: float
    curvature_per_m: float


@dataclass(frozen=True)
class LocalStiffness:
    generalized_force_N: float
    elastic_N_per_m: float
    geometric_N_per_m: float
    total_N_per_m: float
    compression_map: CompressionMap
    spring_source_id: str


def local_stiffness(spring: SpringConstitutiveResult, mapping: CompressionMap) -> LocalStiffness:
    """EQ-SUSP-0038: Q=-F dx/dq; K=k(dx/dq)^2+F d²x/dq².

    Negative total stiffness is retained. Curvature must be supplied explicitly.
    """
    if not spring.ok:
        raise ValueError("Successful spring evaluation required")
    if (spring.spring_id, spring.configuration_id) != (mapping.spring_id, mapping.configuration_id):
        raise ValueError("Spring/configuration mismatch")
    if not all((mapping.coordinate_id, mapping.derivative_source_id)):
        raise ValueError("Coordinate and derivative provenance required")
    values = (spring.force_N, spring.tangent_stiffness_N_per_m,
              mapping.gradient, mapping.curvature_per_m)
    if any(v is None or not math.isfinite(v) for v in values):
        raise ValueError("Finite force, tangent and map derivatives required")
    force, tangent, rho, eta = values
    elastic, geometric = tangent * rho**2, force * eta
    result = (-force * rho, elastic, geometric, elastic + geometric)
    if not all(math.isfinite(v) for v in result):
        raise ValueError("Nonfinite mapped stiffness")
    return LocalStiffness(*result, mapping, spring.source_id)
