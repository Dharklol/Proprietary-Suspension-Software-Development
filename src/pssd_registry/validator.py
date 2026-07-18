"""Minimal, dependency-free validation for Phase 0 TOML registry records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tomllib


_ID_PATTERN = re.compile(r"^[A-Z]+-[A-Z0-9]+-[0-9]{4}$")


@dataclass(frozen=True)
class ValidationIssue:
    path: Path
    message: str


def _load_toml(path: Path) -> dict:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def validate_repository(root: Path) -> list[ValidationIssue]:
    """Validate registry files against the repository contract.

    The validator intentionally covers only structural requirements in Phase 0.
    Physics, uncertainty, and source review remain engineering review tasks.
    """

    root = root.resolve()
    contract_path = root / "schemas" / "registry_contract.toml"
    issues: list[ValidationIssue] = []

    try:
        contract = _load_toml(contract_path)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [ValidationIssue(contract_path, f"Cannot load registry contract: {exc}")]

    prefixes: dict[str, str] = contract.get("id_prefixes", {})
    required: dict[str, list[str]] = contract.get("required_fields", {})
    enums: dict[str, list[str]] = contract.get("enums", {})

    records_root = root / "registry" / "records"
    seen_ids: dict[str, Path] = {}

    for path in sorted(records_root.rglob("*.toml")):
        try:
            document = _load_toml(path)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            issues.append(ValidationIssue(path, f"Invalid TOML: {exc}"))
            continue

        record = document.get("record")
        if not isinstance(record, dict):
            issues.append(ValidationIssue(path, "Missing [record] table"))
            continue

        record_type = record.get("type")
        if record_type not in prefixes:
            issues.append(ValidationIssue(path, f"Unknown record type: {record_type!r}"))
            continue

        for field in required.get(record_type, []):
            if field not in record:
                issues.append(ValidationIssue(path, f"Missing required field: {field}"))

        record_id = record.get("id")
        if isinstance(record_id, str):
            expected_prefix = prefixes[record_type] + "-"
            if not record_id.startswith(expected_prefix):
                issues.append(
                    ValidationIssue(
                        path,
                        f"ID {record_id!r} does not match type prefix {expected_prefix!r}",
                    )
                )
            if not _ID_PATTERN.match(record_id):
                issues.append(ValidationIssue(path, f"ID format is invalid: {record_id!r}"))
            if path.stem != record_id:
                issues.append(
                    ValidationIssue(path, f"File name must match record ID {record_id!r}")
                )
            if record_id in seen_ids:
                issues.append(
                    ValidationIssue(path, f"Duplicate ID also used by {seen_ids[record_id]}")
                )
            else:
                seen_ids[record_id] = path
        else:
            issues.append(ValidationIssue(path, "Record id must be a string"))

        for field in ("status", "disposition", "maturity", "severity", "verification_level"):
            if field in record and record[field] not in enums.get(field, []):
                issues.append(
                    ValidationIssue(
                        path,
                        f"Invalid {field} value {record[field]!r}; allowed: {enums.get(field, [])}",
                    )
                )

    return issues
