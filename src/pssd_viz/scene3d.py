"""Provider-neutral 3D engineering-scene contracts.

The scene layer is downstream of solved physics.  It stores display primitives,
state-dependent point positions, standard symbols, and provenance, but it does not
solve steering, suspension, tire, or vehicle equations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Sequence

Vec3 = tuple[float, float, float]

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


class SceneContractError(ValueError):
    """Raised when a 3D engineering scene is internally inconsistent."""


def _vec3(value: Sequence[float], *, name: str) -> Vec3:
    if len(value) != 3:
        raise SceneContractError(f"{name} must contain exactly three coordinates")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise SceneContractError(f"{name} must contain finite coordinates")
    return result  # type: ignore[return-value]


def _nonblank(value: str, *, name: str) -> str:
    if not value.strip():
        raise SceneContractError(f"{name} must be non-empty")
    return value


def _valid_id(value: str, *, name: str) -> str:
    if not _ID_RE.fullmatch(value):
        raise SceneContractError(f"{name} contains unsupported characters: {value!r}")
    return value


@dataclass(frozen=True)
class SceneMetadata:
    scene_id: str
    title: str
    frame_id: str
    length_unit: str
    axis_convention: str
    configuration_id: str
    model_id: str
    authority: str
    source_ids: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _valid_id(self.scene_id, name="scene_id")
        for name in (
            "title",
            "frame_id",
            "length_unit",
            "axis_convention",
            "configuration_id",
            "model_id",
            "authority",
        ):
            _nonblank(getattr(self, name), name=name)
        if any(not item.strip() for item in (*self.source_ids, *self.notes)):
            raise SceneContractError("source_ids and notes may not contain blank values")


@dataclass(frozen=True)
class SceneLayer:
    layer_id: str
    label: str
    visible_by_default: bool = True

    def __post_init__(self) -> None:
        _valid_id(self.layer_id, name="layer_id")
        _nonblank(self.label, name="layer label")


@dataclass(frozen=True)
class ScenePoint:
    point_id: str
    label: str
    coordinates: Vec3
    layer_id: str
    symbol: str = ""
    source_role: str = "display_from_reviewed_geometry"

    def __post_init__(self) -> None:
        _valid_id(self.point_id, name="point_id")
        _nonblank(self.label, name="point label")
        _valid_id(self.layer_id, name="point layer_id")
        object.__setattr__(self, "coordinates", _vec3(self.coordinates, name=self.point_id))
        _nonblank(self.source_role, name="point source_role")


@dataclass(frozen=True)
class SceneSegment:
    segment_id: str
    label: str
    start_point_id: str
    end_point_id: str
    layer_id: str
    symbol: str = ""
    render_kind: str = "line"
    source_role: str = "display_from_reviewed_geometry"

    def __post_init__(self) -> None:
        _valid_id(self.segment_id, name="segment_id")
        _nonblank(self.label, name="segment label")
        _valid_id(self.start_point_id, name="start_point_id")
        _valid_id(self.end_point_id, name="end_point_id")
        _valid_id(self.layer_id, name="segment layer_id")
        if self.start_point_id == self.end_point_id:
            raise SceneContractError("segment endpoints must be distinct point IDs")
        if self.render_kind not in {"line", "arrow"}:
            raise SceneContractError("render_kind must be 'line' or 'arrow'")
        _nonblank(self.source_role, name="segment source_role")


@dataclass(frozen=True)
class SceneAxis:
    axis_id: str
    label: str
    point: Vec3
    direction: Vec3
    display_half_length: float
    layer_id: str
    symbol: str = ""
    source_role: str = "display_from_reviewed_geometry"

    def __post_init__(self) -> None:
        _valid_id(self.axis_id, name="axis_id")
        _nonblank(self.label, name="axis label")
        _valid_id(self.layer_id, name="axis layer_id")
        object.__setattr__(self, "point", _vec3(self.point, name=f"{self.axis_id}.point"))
        direction = _vec3(self.direction, name=f"{self.axis_id}.direction")
        magnitude = math.sqrt(sum(item * item for item in direction))
        if magnitude <= 1.0e-15:
            raise SceneContractError("axis direction must have nonzero magnitude")
        object.__setattr__(
            self, "direction", tuple(item / magnitude for item in direction)
        )
        if not math.isfinite(self.display_half_length) or self.display_half_length <= 0.0:
            raise SceneContractError("display_half_length must be finite and positive")
        _nonblank(self.source_role, name="axis source_role")


@dataclass(frozen=True)
class SceneScalar:
    label: str
    symbol: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        _nonblank(self.label, name="scalar label")
        _nonblank(self.symbol, name="scalar symbol")
        if not math.isfinite(self.value):
            raise SceneContractError("scalar value must be finite")


@dataclass(frozen=True)
class SceneState:
    state_id: str
    label: str
    parameter_label: str
    parameter_symbol: str
    parameter_value: float
    parameter_unit: str
    point_overrides: tuple[tuple[str, Vec3], ...] = field(default_factory=tuple)
    scalars: tuple[SceneScalar, ...] = field(default_factory=tuple)
    status: str = "valid"
    message: str = ""

    def __post_init__(self) -> None:
        _valid_id(self.state_id, name="state_id")
        for name in ("label", "parameter_label", "parameter_symbol", "parameter_unit", "status"):
            _nonblank(getattr(self, name), name=name)
        if not math.isfinite(self.parameter_value):
            raise SceneContractError("state parameter_value must be finite")
        ids: list[str] = []
        normalized: list[tuple[str, Vec3]] = []
        for point_id, coordinates in self.point_overrides:
            _valid_id(point_id, name="point override id")
            ids.append(point_id)
            normalized.append((point_id, _vec3(coordinates, name=f"override:{point_id}")))
        if len(ids) != len(set(ids)):
            raise SceneContractError("state point overrides contain duplicate point IDs")
        object.__setattr__(self, "point_overrides", tuple(normalized))


@dataclass(frozen=True)
class EngineeringScene:
    metadata: SceneMetadata
    layers: tuple[SceneLayer, ...]
    points: tuple[ScenePoint, ...]
    segments: tuple[SceneSegment, ...]
    axes: tuple[SceneAxis, ...] = field(default_factory=tuple)
    states: tuple[SceneState, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.layers:
            raise SceneContractError("engineering scene requires at least one layer")
        layer_ids = [item.layer_id for item in self.layers]
        if len(layer_ids) != len(set(layer_ids)):
            raise SceneContractError("scene contains duplicate layer IDs")
        layer_set = set(layer_ids)

        point_ids = [item.point_id for item in self.points]
        if len(point_ids) != len(set(point_ids)):
            raise SceneContractError("scene contains duplicate point IDs")
        point_set = set(point_ids)

        segment_ids = [item.segment_id for item in self.segments]
        axis_ids = [item.axis_id for item in self.axes]
        if len(segment_ids) != len(set(segment_ids)) or len(axis_ids) != len(set(axis_ids)):
            raise SceneContractError("scene contains duplicate segment or axis IDs")

        for item in self.points:
            if item.layer_id not in layer_set:
                raise SceneContractError(f"point {item.point_id} references unknown layer")
        for item in self.segments:
            if item.layer_id not in layer_set:
                raise SceneContractError(f"segment {item.segment_id} references unknown layer")
            if item.start_point_id not in point_set or item.end_point_id not in point_set:
                raise SceneContractError(f"segment {item.segment_id} references unknown point")
        for item in self.axes:
            if item.layer_id not in layer_set:
                raise SceneContractError(f"axis {item.axis_id} references unknown layer")

        state_ids = [item.state_id for item in self.states]
        if len(state_ids) != len(set(state_ids)):
            raise SceneContractError("scene contains duplicate state IDs")
        for state in self.states:
            for point_id, _ in state.point_overrides:
                if point_id not in point_set:
                    raise SceneContractError(
                        f"state {state.state_id} overrides unknown point {point_id}"
                    )

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema": "pssd.engineering_scene/v0.1.0",
            "metadata": {
                "scene_id": self.metadata.scene_id,
                "title": self.metadata.title,
                "frame_id": self.metadata.frame_id,
                "length_unit": self.metadata.length_unit,
                "axis_convention": self.metadata.axis_convention,
                "configuration_id": self.metadata.configuration_id,
                "model_id": self.metadata.model_id,
                "authority": self.metadata.authority,
                "source_ids": list(self.metadata.source_ids),
                "notes": list(self.metadata.notes),
            },
            "layers": [
                {
                    "layer_id": item.layer_id,
                    "label": item.label,
                    "visible_by_default": item.visible_by_default,
                }
                for item in self.layers
            ],
            "points": [
                {
                    "point_id": item.point_id,
                    "label": item.label,
                    "symbol": item.symbol,
                    "coordinates": list(item.coordinates),
                    "layer_id": item.layer_id,
                    "source_role": item.source_role,
                }
                for item in self.points
            ],
            "segments": [
                {
                    "segment_id": item.segment_id,
                    "label": item.label,
                    "symbol": item.symbol,
                    "start_point_id": item.start_point_id,
                    "end_point_id": item.end_point_id,
                    "layer_id": item.layer_id,
                    "render_kind": item.render_kind,
                    "source_role": item.source_role,
                }
                for item in self.segments
            ],
            "axes": [
                {
                    "axis_id": item.axis_id,
                    "label": item.label,
                    "symbol": item.symbol,
                    "point": list(item.point),
                    "direction": list(item.direction),
                    "display_half_length": item.display_half_length,
                    "layer_id": item.layer_id,
                    "source_role": item.source_role,
                }
                for item in self.axes
            ],
            "states": [
                {
                    "state_id": state.state_id,
                    "label": state.label,
                    "parameter_label": state.parameter_label,
                    "parameter_symbol": state.parameter_symbol,
                    "parameter_value": state.parameter_value,
                    "parameter_unit": state.parameter_unit,
                    "point_overrides": [
                        {"point_id": point_id, "coordinates": list(coordinates)}
                        for point_id, coordinates in state.point_overrides
                    ],
                    "scalars": [
                        {
                            "label": scalar.label,
                            "symbol": scalar.symbol,
                            "value": scalar.value,
                            "unit": scalar.unit,
                        }
                        for scalar in state.scalars
                    ],
                    "status": state.status,
                    "message": state.message,
                }
                for state in self.states
            ],
        }

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def write_scene_json(scene: EngineeringScene, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(scene.canonical_payload(), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    return output
