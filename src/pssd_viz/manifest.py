"""Deterministic manifest helpers for engineering-figure artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable

from .contracts import EngineeringFigureSpec


@dataclass(frozen=True)
class FigureArtifact:
    """One rendered file attached to a figure specification."""

    format: str
    path: str
    sha256: str
    size_bytes: int


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_record(path: str | Path, *, root: str | Path | None = None) -> FigureArtifact:
    artifact_path = Path(path)
    display_path = artifact_path
    if root is not None:
        try:
            display_path = artifact_path.relative_to(Path(root))
        except ValueError:
            display_path = artifact_path
    return FigureArtifact(
        format=artifact_path.suffix.lstrip(".").lower(),
        path=display_path.as_posix(),
        sha256=sha256_file(artifact_path),
        size_bytes=artifact_path.stat().st_size,
    )


def write_figure_manifest(
    spec: EngineeringFigureSpec,
    artifacts: Iterable[FigureArtifact],
    output_path: str | Path,
) -> Path:
    """Write a deterministic sidecar manifest for one engineering figure."""

    payload = {
        "schema": "pssd.engineering_figure_manifest/v0.1.0",
        "figure_fingerprint_sha256": spec.fingerprint(),
        "figure": spec.canonical_payload(),
        "artifacts": [
            {
                "format": item.format,
                "path": item.path,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
            }
            for item in artifacts
        ],
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_report_manifest(
    *,
    report_id: str,
    figure_manifests: Iterable[str | Path],
    output_path: str | Path,
) -> Path:
    """Write a small deterministic manifest that groups figure-sidecar manifests."""

    if not report_id.strip():
        raise ValueError("report_id must be non-empty")
    paths = [Path(item) for item in figure_manifests]
    payload = {
        "schema": "pssd.engineering_report_manifest/v0.1.0",
        "report_id": report_id,
        "figure_manifests": [
            {
                "path": path.name,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in paths
        ],
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return path
