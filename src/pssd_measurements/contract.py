"""Validation for nonredundant physical-measurement data packages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from ._csv import (
    is_finite,
    read_rows,
    validate_calibration_rows,
    validate_channel_rows,
    validate_raw_rows,
)


@dataclass(frozen=True)
class PackageIssue:
    path: Path
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def _load_toml(path: Path) -> dict:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _check_header(
    path: Path,
    actual: list[str],
    expected: list[str],
    issues: list[PackageIssue],
) -> None:
    if actual != expected:
        issues.append(
            PackageIssue(path, f"Header mismatch; expected {expected!r}, got {actual!r}")
        )


def _append_messages(path: Path, messages: list[str], issues: list[PackageIssue]) -> None:
    issues.extend(PackageIssue(path, message) for message in messages)


def validate_measurement_package(
    package_dir: Path,
    *,
    contract_path: Path | None = None,
) -> list[PackageIssue]:
    """Validate one session package without repeating sensor inventory in raw data."""

    package_dir = package_dir.resolve()
    if contract_path is None:
        contract_path = (
            Path(__file__).resolve().parents[2]
            / "schemas"
            / "measurement_data_contract.toml"
        )
    issues: list[PackageIssue] = []
    try:
        contract = _load_toml(contract_path)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [PackageIssue(contract_path, f"Cannot load contract: {exc}")]

    files = contract["files"]
    session_path = package_dir / files["session"]
    try:
        session = _load_toml(session_path).get("session")
    except (OSError, tomllib.TOMLDecodeError) as exc:
        issues.append(PackageIssue(session_path, f"Cannot load session: {exc}"))
        session = None
    if not isinstance(session, dict):
        issues.append(PackageIssue(session_path, "Missing [session] table"))
    else:
        for field in contract["session"]["required_fields"]:
            value = session.get(field)
            if not isinstance(value, str) or not value.strip():
                issues.append(PackageIssue(session_path, f"Missing session field: {field}"))
        if session.get("data_role") not in contract["enums"]["data_role"]:
            issues.append(PackageIssue(session_path, f"Invalid data_role: {session.get('data_role')!r}"))

    channels_path = package_dir / files["channels"]
    calibrations_path = package_dir / files["calibrations"]
    raw_path = package_dir / files["raw_samples"]
    points_path = package_dir / files["steering_points"]

    try:
        header, rows = read_rows(channels_path)
    except OSError as exc:
        issues.append(PackageIssue(channels_path, f"Cannot read channels: {exc}"))
        header, rows = [], []
    _check_header(channels_path, header, contract["channels"]["required_columns"], issues)
    channels, messages = validate_channel_rows(rows, contract["enums"]["channel_status"])
    _append_messages(channels_path, messages, issues)

    try:
        header, rows = read_rows(calibrations_path)
    except OSError as exc:
        issues.append(PackageIssue(calibrations_path, f"Cannot read calibrations: {exc}"))
        header, rows = [], []
    _check_header(
        calibrations_path,
        header,
        contract["calibrations"]["required_columns"],
        issues,
    )
    calibrations, messages = validate_calibration_rows(
        rows, contract["enums"]["calibration_status"]
    )
    _append_messages(calibrations_path, messages, issues)

    for channel_id, channel in channels.items():
        calibration = calibrations.get(channel.get("calibration_id", ""))
        if calibration is None:
            issues.append(PackageIssue(channels_path, f"Channel {channel_id} has no calibration row"))
            continue
        for field in ("sensor_id", "quantity_id"):
            if channel.get(field) != calibration.get(field):
                issues.append(
                    PackageIssue(
                        channels_path,
                        f"Channel {channel_id} {field} differs from calibration",
                    )
                )
        if channel.get("raw_unit") != calibration.get("input_unit"):
            issues.append(PackageIssue(channels_path, f"Channel {channel_id} raw_unit differs from calibration"))
        if channel.get("canonical_unit") != calibration.get("output_unit"):
            issues.append(
                PackageIssue(
                    channels_path,
                    f"Channel {channel_id} canonical_unit differs from calibration",
                )
            )

    try:
        header, rows = read_rows(raw_path)
    except OSError as exc:
        issues.append(PackageIssue(raw_path, f"Cannot read raw samples: {exc}"))
        header, rows = [], []
    _check_header(raw_path, header, contract["raw_samples"]["required_columns"], issues)
    _append_messages(
        raw_path,
        validate_raw_rows(rows, set(channels), contract["enums"]["quality_flag"]),
        issues,
    )

    if points_path.exists():
        try:
            header, rows = read_rows(points_path)
        except OSError as exc:
            issues.append(PackageIssue(points_path, f"Cannot read steering points: {exc}"))
            header, rows = [], []
        _check_header(
            points_path,
            header,
            contract["steering_points"]["required_columns"],
            issues,
        )
        seen: set[str] = set()
        required_numbers = (
            "repeat_index",
            "target_fraction",
            "measured_rack_m",
            "left_heading_rad",
            "right_heading_rad",
            "hold_start_s",
            "hold_end_s",
        )
        optional_numbers = (
            "primary_shaft_rad",
            "steering_wheel_rad",
            "steering_wheel_torque_nm",
        )
        for number, row in enumerate(rows, start=2):
            point_id = (row.get("point_id") or "").strip()
            if not point_id or point_id in seen:
                issues.append(
                    PackageIssue(points_path, f"Row {number}: point_id must be nonempty and unique")
                )
            seen.add(point_id)
            if row.get("approach_direction") not in contract["enums"]["approach_direction"]:
                issues.append(PackageIssue(points_path, f"Row {number}: invalid approach_direction"))
            for field in required_numbers:
                if not is_finite(row.get(field)):
                    issues.append(PackageIssue(points_path, f"Row {number}: invalid {field}"))
            for field in optional_numbers:
                value = (row.get(field) or "").strip()
                if value and not is_finite(value):
                    issues.append(PackageIssue(points_path, f"Row {number}: invalid {field}"))
            if row.get("quality_flag") not in contract["enums"]["quality_flag"]:
                issues.append(PackageIssue(points_path, f"Row {number}: invalid quality_flag"))
            if is_finite(row.get("hold_start_s")) and is_finite(row.get("hold_end_s")):
                if float(row["hold_end_s"]) < float(row["hold_start_s"]):
                    issues.append(PackageIssue(points_path, f"Row {number}: hold_end_s precedes hold_start_s"))
    return issues
