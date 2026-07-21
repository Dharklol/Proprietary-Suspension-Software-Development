"""CSV helpers for physical-measurement packages."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import re


ID_PATTERNS = {
    "channel_id": re.compile(r"^CH-[A-Z0-9]+-[0-9]{4}$"),
    "sensor_id": re.compile(r"^SNS-[A-Z0-9]+-[0-9]{4}$"),
    "quantity_id": re.compile(r"^QTY-[A-Z0-9]+-[0-9]{4}$"),
    "calibration_id": re.compile(r"^CAL-[A-Z0-9]+-[0-9]{4}$"),
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def is_finite(value: str | None) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def validate_ids(row: dict[str, str], fields: tuple[str, ...]) -> list[str]:
    issues: list[str] = []
    for field in fields:
        value = (row.get(field) or "").strip()
        if not ID_PATTERNS[field].fullmatch(value):
            issues.append(f"invalid {field} {value!r}")
    return issues


def validate_channel_rows(
    rows: list[dict[str, str]], allowed_status: list[str]
) -> tuple[dict[str, dict[str, str]], list[str]]:
    channels: dict[str, dict[str, str]] = {}
    issues: list[str] = []
    for number, row in enumerate(rows, start=2):
        issues.extend(f"row {number}: {item}" for item in validate_ids(
            row, ("channel_id", "sensor_id", "quantity_id", "calibration_id")
        ))
        channel_id = row.get("channel_id", "")
        if channel_id in channels:
            issues.append(f"row {number}: duplicate channel_id {channel_id!r}")
        channels[channel_id] = row
        if not is_finite(row.get("sample_rate_hz")) or float(row["sample_rate_hz"]) <= 0:
            issues.append(f"row {number}: sample_rate_hz must be positive")
        if row.get("status") not in allowed_status:
            issues.append(f"row {number}: invalid channel status {row.get('status')!r}")
    return channels, issues


def validate_calibration_rows(
    rows: list[dict[str, str]], allowed_status: list[str]
) -> tuple[dict[str, dict[str, str]], list[str]]:
    calibrations: dict[str, dict[str, str]] = {}
    issues: list[str] = []
    for number, row in enumerate(rows, start=2):
        issues.extend(f"row {number}: {item}" for item in validate_ids(
            row, ("calibration_id", "sensor_id", "quantity_id")
        ))
        calibration_id = row.get("calibration_id", "")
        if calibration_id in calibrations:
            issues.append(f"row {number}: duplicate calibration_id {calibration_id!r}")
        calibrations[calibration_id] = row
        if row.get("status") not in allowed_status:
            issues.append(f"row {number}: invalid calibration status {row.get('status')!r}")
        try:
            if not isinstance(json.loads(row.get("coefficients_json", "")), (dict, list)):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            issues.append(f"row {number}: invalid coefficients_json")
        digest = (row.get("source_sha256") or "").strip()
        if digest and not SHA256_PATTERN.fullmatch(digest):
            issues.append(f"row {number}: invalid source_sha256")
    return calibrations, issues


def validate_raw_rows(
    rows: list[dict[str, str]], channel_ids: set[str], quality_flags: list[str]
) -> list[str]:
    issues: list[str] = []
    last_time = -math.inf
    last_sequence = -1
    for number, row in enumerate(rows, start=2):
        if row.get("channel_id") not in channel_ids:
            issues.append(f"row {number}: unknown channel_id {row.get('channel_id')!r}")
        if not is_finite(row.get("time_s")) or float(row["time_s"]) < last_time:
            issues.append(f"row {number}: invalid or decreasing time_s")
        else:
            last_time = float(row["time_s"])
        try:
            sequence = int(row.get("sequence", ""))
            if sequence < 0 or sequence <= last_sequence:
                raise ValueError
            last_sequence = sequence
        except ValueError:
            issues.append(f"row {number}: sequence must strictly increase")
        if not is_finite(row.get("raw_value")):
            issues.append(f"row {number}: invalid raw_value")
        if row.get("quality_flag") not in quality_flags:
            issues.append(f"row {number}: invalid quality_flag")
    return issues
