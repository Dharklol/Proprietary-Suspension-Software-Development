"""Authorized steering inverse-design development interfaces.

The package composes the role resolver, parametric geometry generator, target
providers, analyzer-composed candidate evaluator, deterministic nominal
constrained-search baseline, constraint-provider screening, local sensitivity,
and machine-readable comparison reports. Tire, effort, suspension-state,
manufacturing, robustness, and production-release models remain outside this
implementation.
"""

from .candidate_comparison import (
    CandidateComparisonError,
    CandidateComparisonResult,
    CandidateComparisonRow,
    CandidateComparisonSettings,
    ConstraintMarginSummary,
    build_candidate_comparison,
)
from .constraints import (
    ConstraintAvailability,
    ConstraintDefinition,
    ConstraintDefinitionError,
    ConstraintDisposition,
    ScreenedCandidateEvaluation,
    SteeringConstraintSet,
    SupplementalConstraintResult,
    evaluate_constraint_set,
    load_constraint_set,
    screen_candidate_evaluation,
)
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
from .reporting import (
    candidate_evaluation_report,
    steering_search_report,
    write_json_report,
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
from .sensitivity import (
    ConstraintMarginSensitivity,
    LocalSensitivityResult,
    SensitivityConfigurationError,
    SensitivitySettings,
    VariableSensitivity,
    analyze_local_sensitivity,
)
from .study_reporting import (
    candidate_comparison_report,
    local_sensitivity_report,
    screened_candidate_report,
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
    "CandidateComparisonError",
    "CandidateComparisonResult",
    "CandidateComparisonRow",
    "CandidateComparisonSettings",
    "CandidateEvaluation",
    "CandidateEvaluationStatus",
    "CandidateGeometryError",
    "ConstraintAvailability",
    "ConstraintDefinition",
    "ConstraintDefinitionError",
    "ConstraintDisposition",
    "ConstraintMarginSensitivity",
    "ConstraintMarginSummary",
    "ConstraintResult",
    "GeneratedSteeringGeometry",
    "LocalFrameDefinition",
    "LocalSensitivityResult",
    "ObjectiveContribution",
    "ParameterRole",
    "RankedCandidate",
    "RequirementSet",
    "ResolvedCandidate",
    "RoleResolutionError",
    "ScreenedCandidateEvaluation",
    "SearchConfigurationError",
    "SearchSettings",
    "SensitivityConfigurationError",
    "SensitivitySettings",
    "StartResult",
    "SteeringConstraintSet",
    "SteeringSearchResult",
    "SteeringTarget",
    "SupplementalConstraintResult",
    "SyntheticRecoveryFixture",
    "TargetDefinitionError",
    "VariableDefinition",
    "VariableSensitivity",
    "analyze_local_sensitivity",
    "build_analyzer_incremental_target",
    "build_candidate_comparison",
    "candidate_comparison_report",
    "candidate_evaluation_report",
    "evaluate_candidate",
    "evaluate_constraint_set",
    "generate_candidate_geometry",
    "load_constraint_set",
    "load_historical_fit_target",
    "load_requirement_set",
    "load_synthetic_recovery_fixture",
    "local_sensitivity_report",
    "reflect_lateral",
    "resolve_candidate",
    "run_nominal_inverse_design",
    "screen_candidate_evaluation",
    "screened_candidate_report",
    "steering_search_report",
    "write_json_report",
]
