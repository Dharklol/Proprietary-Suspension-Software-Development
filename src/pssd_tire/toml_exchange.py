"""Deterministic TOML exchange writer for source-derived tire force branches.

The project deliberately keeps runtime dependencies small.  This writer only emits the narrow
``explicit_lateral_force_branches`` schema already consumed by
:func:`pssd_tire.force_demand.load_lateral_force_branch_set`; it is not a general TOML serializer.
"""

from __future__ import annotations

from pathlib import Path

from .force_demand import TireLateralForceBranchSet


def _q(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def format_lateral_force_branch_set_toml(branch_set: TireLateralForceBranchSet) -> str:
    """Render the generic force-demand branch-set schema in a stable order."""

    lines = [
        'source_type = "explicit_lateral_force_branches"',
        f"branch_set_id = {_q(branch_set.branch_set_id)}",
        f"version = {_q(branch_set.version)}",
        f"source_tire_id = {_q(branch_set.source_tire_id)}",
        f"intended_tire_id = {_q(branch_set.intended_tire_id)}",
        f"authority = {_q(branch_set.authority)}",
        f"source_path = {_q(branch_set.source_path)}",
        "",
    ]
    if branch_set.provenance:
        lines.append("[source]")
        lines.extend(f"{key} = {_q(value)}" for key, value in branch_set.provenance)
        lines.append("")

    for branch in branch_set.branches:
        lines.extend(
            [
                "[[branches]]",
                f"id = {_q(branch.branch_id)}",
                f"authority = {_q(branch.authority)}",
                f"source_branch_description = {_q(branch.source_branch_description)}",
                "",
                "[branches.operating_point]",
                f"normal_load_n = {branch.operating_point.normal_load_n:.17g}",
                f"inclination_deg = {branch.operating_point.inclination_deg:.17g}",
                f"pressure_kpa = {branch.operating_point.pressure_kpa:.17g}",
                "",
            ]
        )
        if branch.provenance:
            lines.append("[branches.provenance]")
            lines.extend(f"{key} = {_q(value)}" for key, value in branch.provenance)
            lines.append("")
        for sample in branch.samples:
            lines.extend(
                [
                    "[[branches.samples]]",
                    f"slip_angle_magnitude_deg = {sample.slip_angle_magnitude_deg:.17g}",
                    f"lateral_force_magnitude_n = {sample.lateral_force_magnitude_n:.17g}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_lateral_force_branch_set_toml(
    path: str | Path, branch_set: TireLateralForceBranchSet
) -> None:
    """Write a branch set in the exact schema consumed by the runtime loader."""

    Path(path).write_text(format_lateral_force_branch_set_toml(branch_set), encoding="utf-8")
