"""Engineering visualization contracts and optional static/3D rendering."""

from .contracts import (
    EngineeringFigureSpec,
    FigureAvailability,
    FigureContractError,
    FigureMetadata,
    SeriesSpec,
)
from .manifest import (
    FigureArtifact,
    artifact_record,
    sha256_file,
    write_figure_manifest,
    write_report_manifest,
)
from .scene3d import (
    EngineeringScene,
    SceneAxis,
    SceneContractError,
    SceneLayer,
    SceneMetadata,
    ScenePoint,
    SceneScalar,
    SceneSegment,
    SceneState,
    write_scene_json,
)

__all__ = [
    "EngineeringFigureSpec",
    "EngineeringScene",
    "FigureArtifact",
    "FigureAvailability",
    "FigureContractError",
    "FigureMetadata",
    "SceneAxis",
    "SceneContractError",
    "SceneLayer",
    "SceneMetadata",
    "ScenePoint",
    "SceneScalar",
    "SceneSegment",
    "SceneState",
    "SeriesSpec",
    "artifact_record",
    "sha256_file",
    "write_figure_manifest",
    "write_report_manifest",
    "write_scene_json",
]
