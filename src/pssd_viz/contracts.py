"""Provider-neutral engineering-figure contracts.

The visualization layer is deliberately downstream of the physics packages.  These
objects describe what to draw and the provenance that must accompany the figure;
they do not calculate vehicle, tire, suspension, or steering quantities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
import re
from typing import Any, Iterable


_FIGURE_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]*$")


class FigureAvailability(str, Enum):
    """Whether the requested engineering figure has renderable source data."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class FigureContractError(ValueError):
    """Raised when a figure contract is internally inconsistent."""


@dataclass(frozen=True)
class FigureMetadata:
    """Identity, labels, authority, and provenance attached to one figure."""

    figure_id: str
    title: str
    x_quantity: str
    x_unit: str
    y_quantity: str
    y_unit: str
    model_id: str
    configuration_id: str
    authority: str
    state_ids: tuple[str, ...] = field(default_factory=tuple)
    source_ids: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not _FIGURE_ID_RE.fullmatch(self.figure_id):
            raise FigureContractError(
                "figure_id must use uppercase letters, digits, '.', '_' or '-'"
            )
        for field_name in (
            "title",
            "x_quantity",
            "y_quantity",
            "model_id",
            "configuration_id",
            "authority",
        ):
            if not getattr(self, field_name).strip():
                raise FigureContractError(f"{field_name} must be non-empty")
        for collection_name in ("state_ids", "source_ids", "notes"):
            values = getattr(self, collection_name)
            if any(not value.strip() for value in values):
                raise FigureContractError(f"{collection_name} may not contain blank values")

    @property
    def x_axis_label(self) -> str:
        return _quantity_label(self.x_quantity, self.x_unit)

    @property
    def y_axis_label(self) -> str:
        return _quantity_label(self.y_quantity, self.y_unit)

    def footer_text(self) -> str:
        state_text = ", ".join(self.state_ids) if self.state_ids else "none"
        source_text = ", ".join(self.source_ids) if self.source_ids else "none"
        return (
            f"{self.figure_id} | model={self.model_id} | config={self.configuration_id} | "
            f"authority={self.authority} | states={state_text} | sources={source_text}"
        )


@dataclass(frozen=True)
class SeriesSpec:
    """One already-computed x/y series to be rendered."""

    label: str
    x: tuple[float, ...]
    y: tuple[float, ...]
    style_key: str = "default"

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise FigureContractError("series label must be non-empty")
        if len(self.x) != len(self.y):
            raise FigureContractError("series x/y lengths must match")
        if not self.x:
            raise FigureContractError("series must contain at least one sample")
        for value in (*self.x, *self.y):
            if not math.isfinite(value):
                raise FigureContractError("series values must be finite")
        if not self.style_key.strip():
            raise FigureContractError("style_key must be non-empty")

    @classmethod
    def from_iterables(
        cls,
        *,
        label: str,
        x: Iterable[float],
        y: Iterable[float],
        style_key: str = "default",
    ) -> "SeriesSpec":
        return cls(
            label=label,
            x=tuple(float(value) for value in x),
            y=tuple(float(value) for value in y),
            style_key=style_key,
        )


@dataclass(frozen=True)
class EngineeringFigureSpec:
    """Complete render request for an engineering line figure or explicit unavailable figure."""

    metadata: FigureMetadata
    series: tuple[SeriesSpec, ...] = field(default_factory=tuple)
    availability: FigureAvailability = FigureAvailability.AVAILABLE
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if self.availability is FigureAvailability.AVAILABLE:
            if not self.series:
                raise FigureContractError("available figures require at least one series")
            if self.unavailable_reason is not None:
                raise FigureContractError(
                    "available figures may not carry an unavailable_reason"
                )
        else:
            if self.series:
                raise FigureContractError("unavailable figures may not carry data series")
            if self.unavailable_reason is None or not self.unavailable_reason.strip():
                raise FigureContractError(
                    "unavailable figures require a non-empty unavailable_reason"
                )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible deterministic description of the requested figure."""

        return {
            "schema": "pssd.engineering_figure/v0.1.0",
            "metadata": {
                "figure_id": self.metadata.figure_id,
                "title": self.metadata.title,
                "x_quantity": self.metadata.x_quantity,
                "x_unit": self.metadata.x_unit,
                "y_quantity": self.metadata.y_quantity,
                "y_unit": self.metadata.y_unit,
                "model_id": self.metadata.model_id,
                "configuration_id": self.metadata.configuration_id,
                "authority": self.metadata.authority,
                "state_ids": list(self.metadata.state_ids),
                "source_ids": list(self.metadata.source_ids),
                "notes": list(self.metadata.notes),
            },
            "availability": self.availability.value,
            "unavailable_reason": self.unavailable_reason,
            "series": [
                {
                    "label": item.label,
                    "x": list(item.x),
                    "y": list(item.y),
                    "style_key": item.style_key,
                }
                for item in self.series
            ],
        }

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _quantity_label(quantity: str, unit: str) -> str:
    unit = unit.strip()
    return quantity if not unit or unit == "-" else f"{quantity} [{unit}]"
