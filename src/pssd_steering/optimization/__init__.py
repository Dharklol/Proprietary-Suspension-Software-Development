"""Authorized steering inverse-design development interfaces.

The package composes the role resolver, parametric geometry generator, target
providers, analyzer-composed candidate evaluator, deterministic nominal
constrained-search baseline, constraint-provider screening, local sensitivity,
provider-neutral suspension poses, multi-state steering evaluation, and
machine-readable comparison reports. Tire, effort, manufacturing, robustness,
physical-correlation, and production-release models remain outside this implementation.
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
from .multistate import (
    MultiStateSteeringEvaluation,
    PoseStateEvaluation,
    evaluate_candidate_over_pose_set,
)
from .poses import (
    STEERING_DOF_RULE,
    PoseCoordinate,
    PoseDefinitionError,
    PosedSteeringGeometry,
    RigidTransform,
    SteeringPoseState,
    SuspensionPoseSet,
    apply_pose_state,
    load_pose_set,
    transform_wheel_plane,
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
    "MultiStateSteeringEvaluation",
    "ObjectiveContribution",
    "ParameterRole",
    "PoseCoordinate",
    "PoseDefinitionError",
    "PoseStateEvaluation",
    "PosedSteeringGeometry",
    "RankedCandidate",
    "RequirementSet",
    "ResolvedCandidate",
    "RigidTransform",
    "RoleResolutionError",
    "STEERING_DOF_RULE",
    "ScreenedCandidateEvaluation",
    "SearchConfigurationError",
    "SearchSettings",
    "SensitivityConfigurationError",
    "SensitivitySettings",
    "StartResult",
    "SteeringConstraintSet",
    "SteeringPoseState",
    "SteeringSearchResult",
    "SteeringTarget",
    "SupplementalConstraintResult",
    "SuspensionPoseSet",
    "SyntheticRecoveryFixture",
    "TargetDefinitionError",
    "VariableDefinition",
    "VariableSensitivity",
    "analyze_local_sensitivity",
    "apply_pose_state",
    "build_analyzer_incremental_target",
    "build_candidate_comparison",
    "candidate_comparison_report",
    "candidate_evaluation_report",
    "evaluate_candidate",
    "evaluate_candidate_over_pose_set",
    "evaluate_constraint_set",
    "generate_candidate_geometry",
    "load_constraint_set",
    "load_historical_fit_target",
    "load_pose_set",
    "load_requirement_set",
    "load_synthetic_recovery_fixture",
    "local_sensitivity_report",
    "reflect_lateral",
    "resolve_candidate",
    "run_nominal_inverse_design",
    "screen_candidate_evaluation",
    "screened_candidate_report",
    "steering_search_report",
    "transform_wheel_plane",
    "write_json_report",
]
