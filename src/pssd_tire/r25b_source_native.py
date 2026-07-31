"""Validated loader for the frozen R25B source-native signed exchange.

The payload preserves the exact processed-Trojan channels as deterministic,
gzip-compressed little-endian binary64 arrays. This module validates identity,
payload hashes, channel structure, state uniqueness, exact row coverage, and
source-native SA/FY curves. It intentionally stops before canonical conversion
because the pressure basis and source-specific authorization remain unresolved.
"""

from __future__ import annotations

from array import array
import base64
from dataclasses import dataclass
import gzip
import hashlib
import json
from math import isfinite
from pathlib import Path
import struct
import sys
import tomllib

EXPECTED_EXCHANGE_ID = "WUFR26_H43105_R25B_COMPLETE_SIGNED_SOURCE_NATIVE_V0"
EXPECTED_SOURCE_TIRE_ID = "HOOSIER_43105_18X7.5-10_R25B"
EXPECTED_INTENDED_TIRE_ID = "HOOSIER_43104_18X7.5-10_R20"
EXPECTED_SOURCE_SHA1 = "475338b18b6cba21b967c7e75bdd12d9a0e3437a"
EXPECTED_GENERATOR_SHA1 = "c78a66751be956b60ff0f879cd0f733638a71ce3"
EXPECTED_FORMAT = "R25B_SOURCE_NATIVE_F64_LE_V0"
EXPECTED_CHANNELS = ("SA", "FY", "FZ", "IA", "P", "V", "SL")
_MAGIC = b"R25BEX0\0"


class R25bSourceNativeExchangeError(ValueError):
    """Fail-closed source-native exchange validation error."""


@dataclass(frozen=True, slots=True)
class R25bSourceNativeCurve:
    curve_id: str
    source_row_start_1_based: int
    source_row_end_1_based: int
    normal_load_n: float
    inclination_deg: float
    pressure_kpa: float
    speed_kph: float
    slip_ratio: float
    source_slip_angle_deg: tuple[float, ...]
    source_lateral_force_n: tuple[float, ...]
    segment_branch_role: str

    @property
    def state_key(self) -> tuple[float, float, float]:
        return self.normal_load_n, self.inclination_deg, self.pressure_kpa


@dataclass(frozen=True, slots=True)
class R25bSourceNativeExchange:
    exchange_id: str
    source_tire_id: str
    intended_tire_id: str
    source_binary_sha1: str
    generator_sha1: str
    runtime_authorized: bool
    canonical_adapter_reviewed: bool
    curves: tuple[R25bSourceNativeCurve, ...]
    manifest_path: str
    payload_path: str
    payload_sha256: str

    @property
    def sample_count(self) -> int:
        return sum(len(curve.source_slip_angle_deg) for curve in self.curves)


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _required_string(record: dict[str, object], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise R25bSourceNativeExchangeError(f"required string {key!r} is missing")
    return value


def _decode_payload(
    compressed: bytes,
    *,
    expected_uncompressed_sha256: str,
) -> tuple[dict[str, object], dict[str, tuple[float, ...]]]:
    try:
        raw = gzip.decompress(compressed)
    except OSError as exc:
        raise R25bSourceNativeExchangeError("payload is not valid gzip data") from exc
    if _sha256_bytes(raw) != expected_uncompressed_sha256:
        raise R25bSourceNativeExchangeError("uncompressed payload SHA-256 mismatch")
    if not raw.startswith(_MAGIC):
        raise R25bSourceNativeExchangeError("payload magic is invalid")
    if len(raw) < len(_MAGIC) + 4:
        raise R25bSourceNativeExchangeError("payload header is truncated")
    header_length = struct.unpack_from("<I", raw, len(_MAGIC))[0]
    header_start = len(_MAGIC) + 4
    header_end = header_start + header_length
    try:
        header = json.loads(raw[header_start:header_end].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R25bSourceNativeExchangeError("payload JSON header is invalid") from exc
    if not isinstance(header, dict):
        raise R25bSourceNativeExchangeError("payload header must be an object")
    if header.get("format") != EXPECTED_FORMAT:
        raise R25bSourceNativeExchangeError("payload format identity mismatch")
    if tuple(header.get("channel_order", ())) != EXPECTED_CHANNELS:
        raise R25bSourceNativeExchangeError("payload channel order mismatch")
    row_count = int(header.get("row_count", -1))
    if row_count != 9630:
        raise R25bSourceNativeExchangeError("payload row count mismatch")
    if header.get("source_sha1") != EXPECTED_SOURCE_SHA1:
        raise R25bSourceNativeExchangeError("payload source identity mismatch")
    if header.get("generator_sha1") != EXPECTED_GENERATOR_SHA1:
        raise R25bSourceNativeExchangeError("payload generator identity mismatch")
    if header.get("source_tire_id") != EXPECTED_SOURCE_TIRE_ID:
        raise R25bSourceNativeExchangeError("payload source tire identity mismatch")
    if header.get("intended_tire_id") != EXPECTED_INTENDED_TIRE_ID:
        raise R25bSourceNativeExchangeError("payload intended tire identity mismatch")

    expected_bytes = row_count * 8 * len(EXPECTED_CHANNELS)
    payload = raw[header_end:]
    if len(payload) != expected_bytes:
        raise R25bSourceNativeExchangeError("payload binary array size mismatch")
    channels: dict[str, tuple[float, ...]] = {}
    offset = 0
    for name in EXPECTED_CHANNELS:
        channel_bytes = payload[offset:offset + row_count * 8]
        values = array("d")
        values.frombytes(channel_bytes)
        if sys.byteorder != "little":
            values.byteswap()
        channel = tuple(float(value) for value in values)
        if len(channel) != row_count or not all(isfinite(value) for value in channel):
            raise R25bSourceNativeExchangeError(f"payload channel {name} is invalid")
        channels[name] = channel
        offset += row_count * 8
    return header, channels


def _curve_id(fz: float, ia: float, pressure: float) -> str:
    return (
        f"R25B_FZ_{int(fz):04d}_IA_{int(ia):02d}_P_{pressure:04.1f}"
        .replace(".", "p")
    )


def _build_curves(channels: dict[str, tuple[float, ...]]) -> tuple[R25bSourceNativeCurve, ...]:
    keys = tuple(
        (channels["FZ"][index], channels["P"][index], channels["IA"][index])
        for index in range(9630)
    )
    blocks: list[tuple[int, int, tuple[float, float, float]]] = []
    start = 0
    for index in range(1, len(keys) + 1):
        if index == len(keys) or keys[index] != keys[start]:
            blocks.append((start, index, keys[start]))
            start = index
    if len(blocks) != 60:
        raise R25bSourceNativeExchangeError("payload must contain exactly 60 contiguous states")

    curves: list[R25bSourceNativeCurve] = []
    for start, end, (fz, pressure, ia) in blocks:
        slip = channels["SA"][start:end]
        force = channels["FY"][start:end]
        speed = channels["V"][start:end]
        slip_ratio = channels["SL"][start:end]
        if any(right <= left for left, right in zip(slip, slip[1:])):
            raise R25bSourceNativeExchangeError("source slip samples are not strictly increasing")
        if abs(slip[0] + 12.0) > 1.0e-12 or abs(slip[-1] - 12.0) > 1.0e-12:
            raise R25bSourceNativeExchangeError("source curve does not span -12 to +12 degrees")
        if len(set(speed)) != 1 or len(set(slip_ratio)) != 1:
            raise R25bSourceNativeExchangeError("speed or slip ratio varies within a source state")
        curves.append(
            R25bSourceNativeCurve(
                curve_id=_curve_id(fz, ia, pressure),
                source_row_start_1_based=start + 1,
                source_row_end_1_based=end,
                normal_load_n=fz,
                inclination_deg=ia,
                pressure_kpa=pressure,
                speed_kph=speed[0],
                slip_ratio=slip_ratio[0],
                source_slip_angle_deg=slip,
                source_lateral_force_n=force,
                segment_branch_role="unclassified_complete_signed_source_curve",
            )
        )
    states = [curve.state_key for curve in curves]
    if len(states) != len(set(states)):
        raise R25bSourceNativeExchangeError("duplicate source operating state")
    if sum(len(curve.source_slip_angle_deg) for curve in curves) != 9630:
        raise R25bSourceNativeExchangeError("source curve row coverage is incomplete")
    histogram: dict[int, int] = {}
    for curve in curves:
        count = len(curve.source_slip_angle_deg)
        histogram[count] = histogram.get(count, 0) + 1
    if tuple(sorted(histogram.items())) != ((100, 2), (130, 13), (160, 27), (190, 18)):
        raise R25bSourceNativeExchangeError("source rows/state histogram mismatch")
    return tuple(curves)


def load_r25b_source_native_exchange(manifest_path: Path) -> R25bSourceNativeExchange:
    """Load and validate the exact source-native exchange manifest and payload."""

    with manifest_path.open("rb") as stream:
        manifest = tomllib.load(stream)
    if manifest.get("exchange_id") != EXPECTED_EXCHANGE_ID:
        raise R25bSourceNativeExchangeError("unexpected exchange identity")
    if manifest.get("source_tire_id") != EXPECTED_SOURCE_TIRE_ID:
        raise R25bSourceNativeExchangeError("unexpected source tire identity")
    if manifest.get("intended_tire_id") != EXPECTED_INTENDED_TIRE_ID:
        raise R25bSourceNativeExchangeError("unexpected intended tire identity")
    if manifest.get("runtime_authorized") is not False:
        raise R25bSourceNativeExchangeError("source-native exchange may not be runtime authorized")
    if manifest.get("canonical_adapter_reviewed") is not False:
        raise R25bSourceNativeExchangeError("manifest unexpectedly claims canonical adapter review")

    source = manifest.get("source_binary")
    generator = manifest.get("generator")
    if not isinstance(source, dict) or source.get("sha1") != EXPECTED_SOURCE_SHA1:
        raise R25bSourceNativeExchangeError("source binary identity mismatch")
    if not isinstance(generator, dict) or generator.get("sha1") != EXPECTED_GENERATOR_SHA1:
        raise R25bSourceNativeExchangeError("generator identity mismatch")
    payload_record = manifest.get("payload")
    if not isinstance(payload_record, dict):
        raise R25bSourceNativeExchangeError("payload record is missing")
    if payload_record.get("format") != EXPECTED_FORMAT:
        raise R25bSourceNativeExchangeError("manifest payload format mismatch")
    if tuple(payload_record.get("channel_order", ())) != EXPECTED_CHANNELS:
        raise R25bSourceNativeExchangeError("manifest payload channel order mismatch")

    storage = payload_record.get("storage")
    if storage != "base64-chunks":
        raise R25bSourceNativeExchangeError("unsupported payload storage")
    chunk_directory_name = _required_string(payload_record, "chunk_directory")
    chunk_names = payload_record.get("chunk_names")
    if not isinstance(chunk_names, list) or not chunk_names or not all(
        isinstance(name, str) and name for name in chunk_names
    ):
        raise R25bSourceNativeExchangeError("payload chunk list is invalid")
    chunk_directory = manifest_path.parent / chunk_directory_name
    encoded_parts: list[str] = []
    for name in chunk_names:
        chunk_path = chunk_directory / name
        if not chunk_path.is_file():
            raise R25bSourceNativeExchangeError(
                f"source-native payload chunk is unavailable: {name}"
            )
        encoded_parts.append(chunk_path.read_text(encoding="ascii"))
    encoded = "".join(encoded_parts)
    if len(encoded) != int(payload_record.get("encoded_size_bytes", -1)):
        raise R25bSourceNativeExchangeError("payload base64 size mismatch")
    if _sha256_bytes(encoded.encode("ascii")) != _required_string(
        payload_record, "base64_sha256"
    ):
        raise R25bSourceNativeExchangeError("payload base64 SHA-256 mismatch")
    try:
        compressed = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise R25bSourceNativeExchangeError("payload base64 encoding is invalid") from exc
    payload_path = chunk_directory
    expected_payload_hash = _required_string(payload_record, "sha256")
    if _sha256_bytes(compressed) != expected_payload_hash:
        raise R25bSourceNativeExchangeError("compressed payload SHA-256 mismatch")
    if len(compressed) != int(payload_record.get("size_bytes", -1)):
        raise R25bSourceNativeExchangeError("compressed payload size mismatch")
    _, channels = _decode_payload(
        compressed,
        expected_uncompressed_sha256=_required_string(
            payload_record, "uncompressed_sha256"
        ),
    )
    curves = _build_curves(channels)
    return R25bSourceNativeExchange(
        exchange_id=EXPECTED_EXCHANGE_ID,
        source_tire_id=EXPECTED_SOURCE_TIRE_ID,
        intended_tire_id=EXPECTED_INTENDED_TIRE_ID,
        source_binary_sha1=EXPECTED_SOURCE_SHA1,
        generator_sha1=EXPECTED_GENERATOR_SHA1,
        runtime_authorized=False,
        canonical_adapter_reviewed=False,
        curves=curves,
        manifest_path=str(manifest_path),
        payload_path=str(payload_path),
        payload_sha256=expected_payload_hash,
    )
