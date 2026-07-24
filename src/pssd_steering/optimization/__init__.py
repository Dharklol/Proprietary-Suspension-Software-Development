"""Authorized steering inverse-design development interfaces.

The package composes the role resolver, parametric geometry generator, target
providers, analyzer-composed candidate evaluator, deterministic nominal
constrained-search baseline, constraint-provider screening, local sensitivity,
provider-neutral suspension poses, external pose-table ingestion, multi-state
steering evaluation, explicit operating-state target aggregation, explicit
dynamic-toe and state-dependent steering-gain objectives, bounded tire-informed
differential target generation, and machine-readable reports. Tire source parsing
and lateral response surfaces live in the reusable ``pssd_tire`` package; effort,
manufacturing, robustness, physical-correlation, and production-release models
remain outside this implementation.
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
from .external_poses import (
    ROTATION_CONVENTION,
    ExternalCoordinateColumn,
    ExternalPoseAdapterError,
    ExternalPoseImport,
    load_external_pose_table,
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
from .operating_evaluation import (
    OperatingStateCandidateEvaluation,
    evaluate_operating_state_candidate,
)
from .operating_reporting import (
    operating_state_candidate_report,
    operating_state_search_report,
)
from .operating_search import (
    OperatingStateRankedCandidate,
    OperatingStateSearchResult,
    run_operating_state_inverse_design,
)
from .operating_targets import (
    OperatingStateTarget,
    OperatingStateTargetSet,
    OperatingTargetRole,
    SyntheticOperatingTargetFixture,
    build_analyzer_operating_state_target_set,
    load_explicit_operating_state_target_set,
    load_synthetic_operating_target_fixture,
)
from .pose_reporting import multi_state_steering_report
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
from .state_metrics import (
    StateMetricCandidateEvaluation,
    StateMetricId,
    StateMetricRankedCandidate,
    StateMetricSearchResult,
    StateMetricTarget,
    StateMetricTargetSet,
    build_analyzer_state_metric_target_set,
    evaluate_state_metric_candidate,
    load_explicit_state_metric_target_set,
    run_state_metric_inverse_design,
    state_metric_pair,
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
from .tire_targets import (
    TireDifferentialStateDefinition,
    TireSlipDifferential,
    build_tire_informed_operating_target_set,
    peak_grip_slip_angle_differential,
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
    "ExternalCoordinateColumn",
    "ExternalPoseAdapterError",
    "ExternalPoseImport",
    "GeneratedSteeringGeometry",
    "LocalFrameDefinition",
    "LocalSensitivityResult",
    "MultiStateSteeringEvaluation",
    "ObjectiveContribution",
    "OperatingStateCandidateEvaluation",
    "OperatingStateRankedCandidate",
    "OperatingStateSearchResult",
    "OperatingStateTarget",
    "OperatingStateTargetSet",
    "OperatingTargetRole",
    "ParameterRole",
    "PoseCoordinate",
    "PoseDefinitionError",
    "PoseStateEvaluation",
    "PosedSteeringGeometry",
    "ROTATION_CONVENTION",
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
    "StateMetricCandidateEvaluation",
    "StateMetricId",
    "StateMetricRankedCandidate",
    "StateMetricSearchResult",
    "StateMetricTarget",
    "StateMetricTargetSet",
    "SteeringConstraintSet",
    "SteeringPoseState",
    "SteeringSearchResult",
    "SteeringTarget",
    "SupplementalConstraintResult",
    "SuspensionPoseSet",
    "SyntheticOperatingTargetFixture",
    "SyntheticRecoveryFixture",
    "TargetDefinitionError",
    "TireDifferentialStateDefinition",
    "TireSlipDifferential",
    "VariableDefinition",
    "VariableSensitivity",
    "analyze_local_sensitivity",
    "apply_pose_state",
    "build_analyzer_incremental_target",
    "build_analyzer_operating_state_target_set",
    "build_analyzer_state_metric_target_set",
    "build_candidate_comparison",
    "build_tire_informed_operating_target_set",
    "candidate_comparison_report",
    "candidate_evaluation_report",
    "evaluate_candidate",
    "evaluate_candidate_over_pose_set",
    "evaluate_constraint_set",
    "evaluate_operating_state_candidate",
    "evaluate_state_metric_candidate",
    "generate_candidate_geometry",
    "load_constraint_set",
    "load_explicit_operating_state_target_set",
    "load_explicit_state_metric_target_set",
    "load_external_pose_table",
    "load_historical_fit_target",
    "load_pose_set",
    "load_requirement_set",
    "load_synthetic_operating_target_fixture",
    "load_synthetic_recovery_fixture",
    "local_sensitivity_report",
    "multi_state_steering_report",
    "operating_state_candidate_report",
    "operating_state_search_report",
    "peak_grip_slip_angle_differential",
    "reflect_lateral",
    "resolve_candidate",
    "run_nominal_inverse_design",
    "run_operating_state_inverse_design",
    "run_state_metric_inverse_design",
    "screen_candidate_evaluation",
    "screened_candidate_report",
    "state_metric_pair",
    "steering_search_report",
    "transform_wheel_plane",
    "write_json_report",
]
