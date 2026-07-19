#!/usr/bin/env python3
"""Validate all machine-readable Phase 0 registry records."""

from pathlib import Path
import sys

from pssd_registry import validate_repository


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    issues = validate_repository(root)
    if not issues:
        print("Registry validation passed.")
        return 0

    print(f"Registry validation failed with {len(issues)} issue(s):")
    for issue in issues:
        print(f"- {issue.path.relative_to(root)}: {issue.message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
