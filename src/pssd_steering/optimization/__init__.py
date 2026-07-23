"""Authorized steering inverse-design development interfaces.

The package composes the role resolver, parametric geometry generator, target
providers, analyzer-composed candidate evaluator, and deterministic nominal
constrained-search baseline. Tire, effort, suspension-state, packaging,
manufacturing, robustness, and production-release models remain outside this
implementation.
"""

from .evaluation import (
    CandidateEvaluation,
    CandidateEvaluationStatus,
    ConstraintResult,
    ObjectiveContribution,
    evaluate_candidate,
)
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
from .search import (
    RankedCandidate,
    SearchConfigurationError,
    SearchSettings,
    StartResult,
    SteeringSearchResult,
    run_nominal_inverse_design,
)
from .targets import (
    SteeringTarget,
    SyntheticRecoveryFixture,
    TargetDefinitionError,
    build_analyzer_incremental_target,
    load_historical_fit_target,
    load_synthetic_recovery_fixture,
)

__all__ = [
    "CandidateEvaluation",
    "CandidateEvaluationStatus",
    "CandidateGeometryError",
    "ConstraintResult",
    "GeneratedSteeringGeometry",
    "LocalFrameDefinition",
    "ObjectiveContribution",
    "ParameterRole",
    "RankedCandidate",
    "RequirementSet",
    "ResolvedCandidate",
    "RoleResolutionError",
    "SearchConfigurationError",
    "SearchSettings",
    "StartResult",
    "SteeringSearchResult",
    "SteeringTarget",
    "SyntheticRecoveryFixture",
    "TargetDefinitionError",
    "VariableDefinition",
    "build_analyzer_incremental_target",
    "evaluate_candidate",
    "generate_candidate_geometry",
    "load_historical_fit_target",
    "load_requirement_set",
    "load_synthetic_recovery_fixture",
    "reflect_lateral",
    "resolve_candidate",
    "run_nominal_inverse_design",
]
