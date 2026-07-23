"""Authorized steering inverse-design development interfaces.

The current package boundary includes role resolution and parametric geometry
generation only. Search, ranking, tire, load, compliance, and robustness models
remain outside this implementation.
"""

from .geometry import (
    CandidateGeometryError,
    GeneratedSteeringGeometry,
    generate_candidate_geometry,
    reflect_lateral,
)
from .roles import (
    LocalFrameDefinition,
    ParameterRole,
    RequirementSet,
    ResolvedCandidate,
    RoleResolutionError,
    VariableDefinition,
    load_requirement_set,
    resolve_candidate,
)

__all__ = [
    "CandidateGeometryError",
    "GeneratedSteeringGeometry",
    "LocalFrameDefinition",
    "ParameterRole",
    "RequirementSet",
    "ResolvedCandidate",
    "RoleResolutionError",
    "VariableDefinition",
    "generate_candidate_geometry",
    "load_requirement_set",
    "reflect_lateral",
    "resolve_candidate",
]
