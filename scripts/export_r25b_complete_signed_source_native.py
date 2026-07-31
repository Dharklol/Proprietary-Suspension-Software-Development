#!/usr/bin/env python3
"""Freeze the complete signed source-native R25B SA/FY exchange.

The output preserves all 60 exact operating-state curves and all 9,630 source
samples from the hashed processed Trojan in a deterministic gzip-compressed
little-endian binary64 payload. It performs no canonical sign conversion,
branch classification, smoothing, symmetry completion, clipping,
extrapolation, or track scaling.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import struct

from scripts.verify_r25b_generator_source import audit_generator
from scripts.verify_r25b_runtime_source import verify_source

SOURCE_TIRE_ID = "HOOSIER_43105_18X7.5-10_R25B"
INTENDED_TIRE_ID = "HOOSIER_43104_18X7.5-10_R20"
EXCHANGE_ID = "WUFR26_H43105_R25B_COMPLETE_SIGNED_SOURCE_NATIVE_V0"
SOURCE_SHA1 = "475338b18b6cba21b967c7e75bdd12d9a0e3437a"
GENERATOR_SHA1 = "c78a66751be956b60ff0f879cd0f733638a71ce3"
GENERATOR_SHA256 = "a4e8a0d079d9ba64fbba428885d9c1c2c0699ca80c12f7d5a3c05b88988aa248"
FORMAT_ID = "R25B_SOURCE_NATIVE_F64_LE_V0"
CHANNEL_ORDER = ("SA", "FY", "FZ", "IA", "P", "V", "SL")
_MAGIC = b"R25BEX0\0"


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _load(path: Path) -> dict[str, "numpy.ndarray"]:
    try:
        import numpy
        from scipy.io import loadmat
    except ImportError as exc:
        raise SystemExit("NumPy and SciPy are required for source exchange export") from exc
    source = loadmat(path, squeeze_me=True)
    channels: dict[str, numpy.ndarray] = {}
    for name in CHANNEL_ORDER:
        if name not in source:
            raise SystemExit(f"source channel {name} is unavailable")
        values = numpy.asarray(source[name], dtype=float).reshape(-1)
        if len(values) != 9630 or not numpy.all(numpy.isfinite(values)):
            raise SystemExit(f"source channel {name} is not a finite 9,630-row vector")
        channels[name] = values
    return channels


def _validate_state_structure(channels: dict[str, "numpy.ndarray"]) -> None:
    keys = tuple(
        (float(channels["FZ"][index]), float(channels["P"][index]), float(channels["IA"][index]))
        for index in range(9630)
    )
    blocks: list[tuple[int, int, tuple[float, float, float]]] = []
    start = 0
    for index in range(1, len(keys) + 1):
        if index == len(keys) or keys[index] != keys[start]:
            blocks.append((start, index, keys[start]))
            start = index
    if len(blocks) != 60:
        raise SystemExit(f"expected 60 contiguous states, received {len(blocks)}")
    histogram: dict[int, int] = {}
    for start, end, _ in blocks:
        count = end - start
        histogram[count] = histogram.get(count, 0) + 1
        slip = channels["SA"][start:end]
        if any(right <= left for left, right in zip(slip, slip[1:])):
            raise SystemExit("source slip grid is not strictly increasing")
        if abs(float(slip[0]) + 12.0) > 1.0e-12 or abs(float(slip[-1]) - 12.0) > 1.0e-12:
            raise SystemExit("source slip grid does not span -12 to +12 degrees")
    if tuple(sorted(histogram.items())) != ((100, 2), (130, 13), (160, 27), (190, 18)):
        raise SystemExit("source rows/state histogram mismatch")


def _encode_payload(channels: dict[str, "numpy.ndarray"]) -> tuple[bytes, bytes]:
    import numpy

    header = {
        "channel_order": list(CHANNEL_ORDER),
        "format": FORMAT_ID,
        "generator_sha1": GENERATOR_SHA1,
        "intended_tire_id": INTENDED_TIRE_ID,
        "row_count": 9630,
        "source_sha1": SOURCE_SHA1,
        "source_tire_id": SOURCE_TIRE_ID,
    }
    header_bytes = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    raw = _MAGIC + struct.pack("<I", len(header_bytes)) + header_bytes
    for name in CHANNEL_ORDER:
        raw += numpy.asarray(channels[name], dtype="<f8").tobytes(order="C")
    return raw, gzip.compress(raw, compresslevel=9, mtime=0)


def export_exchange(source: Path, generator: Path, output_directory: Path) -> Path:
    verify_source(source)
    generator_audit = audit_generator(generator)
    if not generator_audit.exact_cornering_profile_confirmed:
        raise SystemExit("generator profile is not the frozen exact R25B profile")
    channels = _load(source)
    _validate_state_structure(channels)
    raw, compressed = _encode_payload(channels)
    output_directory.mkdir(parents=True, exist_ok=True)
    encoded = base64.b64encode(compressed).decode("ascii")
    chunk_size = 12000
    chunk_directory_name = "payload_base64"
    chunk_directory = output_directory / chunk_directory_name
    chunk_directory.mkdir(parents=True, exist_ok=True)
    chunk_names: list[str] = []
    for index, start in enumerate(range(0, len(encoded), chunk_size)):
        name = f"part-{index:03d}.txt"
        (chunk_directory / name).write_text(
            encoded[start:start + chunk_size], encoding="ascii"
        )
        chunk_names.append(name)
    chunk_names_toml = ", ".join(json.dumps(name) for name in chunk_names)

    manifest = f'''version = "0.1.0"
exchange_id = "{EXCHANGE_ID}"
status = "complete_signed_source_native_exchange_frozen_canonical_adapter_blocked"
source_tire_id = "{SOURCE_TIRE_ID}"
intended_tire_id = "{INTENDED_TIRE_ID}"
authority = "Exact source-native signed SA/FY curves from the hashed processed R25B Trojan. No canonical sign, pressure-basis, branch, track, or runtime authority is implied."
runtime_authorized = false
canonical_adapter_reviewed = false
curve_count = 60
sample_count = 9630
normal_load_values_n = [222.0, 445.0, 667.0, 890.0, 1112.0]
inclination_values_deg = [0.0, 2.0, 4.0]
pressure_values_kpa = [55.2, 68.9, 82.7, 96.5]
speed_values_kph = [40.2]
slip_ratio_values = [0.0]
source_slip_angle_min_deg = -12.0
source_slip_angle_max_deg = 12.0
rows_per_state_100_count = 2
rows_per_state_130_count = 13
rows_per_state_160_count = 27
rows_per_state_190_count = 18

[source_binary]
provider = "Box"
file_id = "1890914118742"
file_version_id = "2085674725942"
name = "Hoosier 43105 R25B Cornering Trojan.mat"
size_bytes = 333286
sha1 = "{SOURCE_SHA1}"

[generator]
provider = "Box"
file_id = "1890916633802"
file_version_id = "2085677125802"
name = "TTC_Spline_Fitter.mlx"
size_bytes = 286864
sha1 = "{GENERATOR_SHA1}"
sha256 = "{GENERATOR_SHA256}"
matlab_release = "R2024b Update 3"

[payload]
storage = "base64-chunks"
chunk_directory = "{chunk_directory_name}"
chunk_names = [{chunk_names_toml}]
format = "{FORMAT_ID}"
compression = "gzip-mtime-0"
channel_order = ["SA", "FY", "FZ", "IA", "P", "V", "SL"]
float_format = "IEEE-754 binary64 little-endian"
size_bytes = {len(compressed)}
sha256 = "{_sha256(compressed)}"
encoded_size_bytes = {len(encoded)}
base64_sha256 = "{_sha256(encoded.encode('ascii'))}"
uncompressed_sha256 = "{_sha256(raw)}"
header_and_payload_are_deterministic = true

[source_native_convention]
frame = "SAE J670 tire axis system: +x wheel heading, +z downward, +y completes the right-handed road-plane basis"
force_role = "road_on_tire"
slip_angle = "SAE J670 positive when the wheel slips to the right"
lateral_force = "FY resolved along source +y"
inclination = "source IA in degrees under the SAE tire-axis convention"
pressure = "source P channel in kPa; absolute-versus-gauge basis is not explicitly stated by the supplied TTC documents"

[curve_contract]
ordering = "FZ ascending, source P target order 96.5/82.7/68.9/55.2 kPa, IA ascending"
slip_samples = "exact source-native Trojan SA values, strictly increasing within every curve"
force_samples = "exact source-native Trojan FY values; nonmonotonic and post-peak behavior retained"
branch_policy = "unclassified; no pre-peak or post-peak selector is authorized by this exchange"
no_repair = true
no_smoothing_beyond_source_generator = true
no_symmetry_completion = true
no_extrapolation = true
no_track_scale = true

[activation_boundary]
full_signed_source_native_exchange_frozen = true
generator_provenance_reconciled = true
raw_input_reproduction_cross_check_complete = true
source_to_canonical_pressure_basis_resolved = false
source_specific_runtime_authorization_present = false
'''
    manifest_path = output_directory / "manifest.toml"
    manifest_path.write_text(manifest, encoding="utf-8")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("generator", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    manifest = export_exchange(args.source, args.generator, args.output_directory)
    print(f"Wrote {manifest}")
    print(f"Manifest SHA-256: {_sha256(manifest.read_bytes())}")
    print("Runtime activation remains disabled; this export is source-native evidence only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
