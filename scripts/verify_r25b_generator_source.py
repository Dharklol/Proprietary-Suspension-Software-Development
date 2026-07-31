#!/usr/bin/env python3
"""Verify and audit the exact TTC Spline Fitter live-script generator.

The MATLAB live script is an OOXML ZIP package. This command reads only its
metadata and code XML, verifies the frozen binary identity, and checks the
cornering-generator profile that explains the processed R25B Trojan. It does
not execute MATLAB, alter source data, or authorize runtime tire behavior.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

EXPECTED_NAME = "TTC_Spline_Fitter.mlx"
EXPECTED_SIZE_BYTES = 286_864
EXPECTED_SHA1 = "c78a66751be956b60ff0f879cd0f733638a71ce3"
EXPECTED_SHA256 = "a4e8a0d079d9ba64fbba428885d9c1c2c0699ca80c12f7d5a3c05b88988aa248"
EXPECTED_MATLAB_RELEASE = "R2024b Update 3"
EXPECTED_FZ_N = (222.0, 445.0, 667.0, 890.0, 1112.0)
EXPECTED_PRESSURE_KPA_SOURCE_ORDER = (96.5, 82.7, 68.9, 55.2)
EXPECTED_INCLINATION_DEG = (0.0, 2.0, 4.0)
EXPECTED_TOTAL_ROWS = 9_630
EXPECTED_STATE_COUNT = 60
EXPECTED_ROWS_PER_STATE_HISTOGRAM = ((100, 2), (130, 13), (160, 27), (190, 18))

_REQUIRED_CODE_SNIPPETS = (
    "fz_targets = [222, 445, 667, 890, 1112];",
    "p_targets = [96.5, 82.7, 68.9, 55.2];",
    "ia_targets = [0 2 4];",
    "SA = zeros(9630, 1);",
    "ET = linspace(0.01, 96.3, 9630).';",
    "abs(fz_src + fz_current) < 100",
    "abs(p_src - p_current) < 5",
    "abs(ia_src - ia_current) < 1",
    "sl_src == 0",
    "norm_fy = fy_src(sweep_indices)./fz_src(sweep_indices);",
    "fy = norm_fy * -1*fz_current;",
    "smoothingParam = 0.5;",
    "n_points = 100;",
    "if fz_current >= 667",
    "if p_current >= 68.9",
    "if ia_current <= 2",
    "sim_sa = linspace(-12, 12, n_points);",
    "ft = fittype( 'smoothingspline' );",
    "opts.SmoothingParam = smoothingParam;",
)


@dataclass(frozen=True)
class R25bGeneratorAudit:
    name: str
    size_bytes: int
    sha1: str
    sha256: str
    matlab_release: str
    code_paragraph_count: int
    required_snippet_count: int
    all_required_snippets_present: bool
    missing_snippets: tuple[str, ...]
    normal_load_values_n: tuple[float, ...]
    pressure_values_kpa_source_order: tuple[float, ...]
    inclination_values_deg: tuple[float, ...]
    state_count: int
    total_rows: int
    rows_per_state_histogram: tuple[tuple[int, int], ...]
    exact_cornering_profile_confirmed: bool


def _digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm, usedforsecurity=False)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_rows_for_state(normal_load_n: float, pressure_kpa: float, inclination_deg: float) -> int:
    rows = 100
    if normal_load_n >= 667.0:
        rows += 30
    if pressure_kpa >= 68.9:
        rows += 30
    if inclination_deg <= 2.0:
        rows += 30
    return rows


def expected_cornering_profile() -> tuple[int, int, tuple[tuple[int, int], ...]]:
    histogram: dict[int, int] = {}
    total_rows = 0
    state_count = 0
    for normal_load_n in EXPECTED_FZ_N:
        for pressure_kpa in EXPECTED_PRESSURE_KPA_SOURCE_ORDER:
            for inclination_deg in EXPECTED_INCLINATION_DEG:
                rows = expected_rows_for_state(normal_load_n, pressure_kpa, inclination_deg)
                histogram[rows] = histogram.get(rows, 0) + 1
                total_rows += rows
                state_count += 1
    return total_rows, state_count, tuple(sorted(histogram.items()))


def extract_code_paragraphs(path: Path) -> tuple[str, ...]:
    if not zipfile.is_zipfile(path):
        raise ValueError("MATLAB live script is not a readable OOXML ZIP package")
    with zipfile.ZipFile(path) as archive:
        try:
            document_xml = archive.read("matlab/document.xml")
        except KeyError as exc:
            raise ValueError("MATLAB live script is missing matlab/document.xml") from exc
    root = ET.fromstring(document_xml)
    paragraphs: list[str] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "p":
            continue
        text = "".join(element.itertext())
        if "\n" in text and any(
            marker in text
            for marker in ("run_files", "fz_targets", "function [", "smoothingspline")
        ):
            paragraphs.append(text)
    return tuple(paragraphs)


def _extract_matlab_release(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        names = (
            "metadata/mwcorePropertiesReleaseInfo.xml",
            "metadata/mwcoreProperties.xml",
            "metadata/coreProperties.xml",
        )
        combined = "\n".join(
            archive.read(name).decode("utf-8", errors="replace")
            for name in names
            if name in archive.namelist()
        )
    if EXPECTED_MATLAB_RELEASE in combined:
        return EXPECTED_MATLAB_RELEASE
    return "unresolved"


def audit_generator(path: Path) -> R25bGeneratorAudit:
    if not path.is_file():
        raise SystemExit(f"generator file not found: {path}")
    if path.name != EXPECTED_NAME:
        raise SystemExit(f"unexpected generator filename: {path.name!r}")
    size = path.stat().st_size
    sha1 = _digest(path, "sha1")
    sha256 = _digest(path, "sha256")
    paragraphs = extract_code_paragraphs(path)
    code = "\n\n".join(paragraphs)
    missing = tuple(snippet for snippet in _REQUIRED_CODE_SNIPPETS if snippet not in code)
    total_rows, state_count, histogram = expected_cornering_profile()
    exact = (
        size == EXPECTED_SIZE_BYTES
        and sha1 == EXPECTED_SHA1
        and sha256 == EXPECTED_SHA256
        and not missing
        and total_rows == EXPECTED_TOTAL_ROWS
        and state_count == EXPECTED_STATE_COUNT
        and histogram == EXPECTED_ROWS_PER_STATE_HISTOGRAM
    )
    return R25bGeneratorAudit(
        name=path.name,
        size_bytes=size,
        sha1=sha1,
        sha256=sha256,
        matlab_release=_extract_matlab_release(path),
        code_paragraph_count=len(paragraphs),
        required_snippet_count=len(_REQUIRED_CODE_SNIPPETS),
        all_required_snippets_present=not missing,
        missing_snippets=missing,
        normal_load_values_n=EXPECTED_FZ_N,
        pressure_values_kpa_source_order=EXPECTED_PRESSURE_KPA_SOURCE_ORDER,
        inclination_values_deg=EXPECTED_INCLINATION_DEG,
        state_count=state_count,
        total_rows=total_rows,
        rows_per_state_histogram=histogram,
        exact_cornering_profile_confirmed=exact,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("generator", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    audit = audit_generator(args.generator)
    rendered = json.dumps(asdict(audit), indent=2, sort_keys=True) + "\n"
    if args.json_output is not None:
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if not audit.exact_cornering_profile_confirmed:
        print("R25B generator provenance check failed closed.")
        return 3
    print("R25B generator identity and exact 9,630-row cornering profile verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
