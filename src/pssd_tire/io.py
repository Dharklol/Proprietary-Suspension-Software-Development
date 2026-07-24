"""Optional source readers for common tire-data file formats.

The core tire response layer has no third-party runtime dependency. ``.tir`` files are
parsed as metadata using the Python standard library. MATLAB ``.mat`` TTC channels can
be read when SciPy is already installed, but SciPy is intentionally not a required
project dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import math
from pathlib import Path
import re
from typing import Iterable

from .lateral import TireDataError


class TireOptionalDependencyError(TireDataError):
    """Raised when an optional source-file reader dependency is unavailable."""


@dataclass(frozen=True)
class TirDocument:
    """Raw section/key representation of a TIR file; not a Magic Formula evaluator."""

    source_path: str
    sections: tuple[tuple[str, tuple[tuple[str, str], ...]], ...]

    @property
    def section_map(self) -> dict[str, dict[str, str]]:
        return {name: dict(values) for name, values in self.sections}

    def value(self, section: str, key: str) -> str:
        try:
            return self.section_map[section][key]
        except KeyError as exc:
            raise TireDataError(f"TIR value [{section}] {key} is unavailable") from exc


_TIR_ASSIGNMENT = re.compile(r"^([A-Za-z0-9_]+)\s*=\s*(.*?)\s*$")


def parse_tir_text(text: str, *, source_path: str = "") -> TirDocument:
    """Parse TIR sections and assignments without evaluating tire equations."""

    sections: dict[str, list[tuple[str, str]]] = {}
    current = "ROOT"
    sections[current] = []
    for raw_line in text.splitlines():
        line = raw_line.split("$", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            if not current:
                raise TireDataError("TIR file contains an empty section name")
            sections.setdefault(current, [])
            continue
        match = _TIR_ASSIGNMENT.match(line)
        if match is None:
            continue
        key, value = match.groups()
        sections[current].append((key, value.strip().strip("'\"")))
    return TirDocument(
        source_path=source_path,
        sections=tuple((name, tuple(values)) for name, values in sections.items()),
    )


def load_tir_metadata(path: str | Path) -> TirDocument:
    source_path = Path(path)
    return parse_tir_text(
        source_path.read_text(encoding="utf-8", errors="replace"),
        source_path=str(source_path),
    )


DEFAULT_TTC_CHANNELS = (
    "FZ",
    "SL",
    "SA",
    "P",
    "IA",
    "FX",
    "FY",
    "MX",
    "MZ",
    "N",
    "V",
    "TSTC",
)


def load_mat_ttc_channels(
    path: str | Path,
    *,
    channels: Iterable[str] = DEFAULT_TTC_CHANNELS,
) -> dict[str, tuple[float, ...]]:
    """Read selected numeric TTC channels from a MATLAB file using optional SciPy.

    This is an ingestion utility only. It performs no filtering, smoothing, sign
    conversion, curve fitting, or tire-force evaluation.
    """

    if importlib.util.find_spec("scipy.io") is None:
        raise TireOptionalDependencyError(
            "Reading MATLAB .mat files requires optional scipy; the core tire/steering package "
            "does not depend on scipy"
        )
    from scipy.io import loadmat  # type: ignore[import-not-found]

    source_path = Path(path)
    try:
        document = loadmat(source_path, squeeze_me=True)
    except NotImplementedError as exc:
        raise TireOptionalDependencyError(
            "This MATLAB file appears to require an HDF5/v7.3 reader; no HDF5 dependency is "
            "required by the core package"
        ) from exc

    result: dict[str, tuple[float, ...]] = {}
    for channel in channels:
        if channel not in document:
            continue
        values = document[channel]
        try:
            flattened = values.reshape(-1).tolist()
        except AttributeError as exc:
            raise TireDataError(f"MAT channel {channel!r} is not a numeric array") from exc
        numeric = tuple(float(value) for value in flattened)
        if not all(math.isfinite(value) for value in numeric):
            raise TireDataError(f"MAT channel {channel!r} contains nonfinite values")
        result[str(channel)] = numeric
    return result
