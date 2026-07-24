"""Engineering visualization contracts and optional static rendering."""

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

__all__ = [
    "EngineeringFigureSpec",
    "FigureArtifact",
    "FigureAvailability",
    "FigureContractError",
    "FigureMetadata",
    "SeriesSpec",
    "artifact_record",
    "sha256_file",
    "write_figure_manifest",
    "write_report_manifest",
]
