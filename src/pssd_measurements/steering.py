"""Small, transparent reductions for settled steering Level F points."""

from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path
from statistics import fmean, pstdev


@dataclass(frozen=True)
class SteeringPoint:
    point_id: str
    repeat_index: int
    approach_direction: str
    target_fraction: float
    measured_rack_m: float
    primary_shaft_rad: float | None
    steering_wheel_rad: float | None
    steering_wheel_torque_nm: float | None
    left_heading_rad: float
    right_heading_rad: float
    hold_start_s: float
    hold_end_s: float
    quality_flag: str


@dataclass(frozen=True)
class IncrementalSteeringPoint:
    point: SteeringPoint
    rack_from_center_m: float
    left_incremental_rad: float
    right_incremental_rad: float


@dataclass(frozen=True)
class GroupSummary:
    target_fraction: float
    approach_direction: str
    count: int
    rack_mean_m: float
    rack_std_m: float
    left_mean_rad: float
    left_std_rad: float
    right_mean_rad: float
    right_std_rad: float


def _optional_float(value: str) -> float | None:
    stripped = value.strip()
    return None if not stripped else float(stripped)


def load_steering_points(path: Path) -> list[SteeringPoint]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(stream)
        return [
            SteeringPoint(
                point_id=row["point_id"],
                repeat_index=int(row["repeat_index"]),
                approach_direction=row["approach_direction"],
                target_fraction=float(row["target_fraction"]),
                measured_rack_m=float(row["measured_rack_m"]),
                primary_shaft_rad=_optional_float(row["primary_shaft_rad"]),
                steering_wheel_rad=_optional_float(row["steering_wheel_rad"]),
                steering_wheel_torque_nm=_optional_float(row["steering_wheel_torque_nm"]),
                left_heading_rad=float(row["left_heading_rad"]),
                right_heading_rad=float(row["right_heading_rad"]),
                hold_start_s=float(row["hold_start_s"]),
                hold_end_s=float(row["hold_end_s"]),
                quality_flag=row["quality_flag"],
            )
            for row in rows
        ]


def incrementalize_points(
    points: list[SteeringPoint],
    *,
    center_tolerance: float = 1e-12,
) -> list[IncrementalSteeringPoint]:
    """Subtract an independent center for every repeat and approach direction."""

    usable = [point for point in points if point.quality_flag == "ok"]
    centers: dict[tuple[int, str], SteeringPoint] = {}
    for point in usable:
        if abs(point.target_fraction) <= center_tolerance:
            key = (point.repeat_index, point.approach_direction)
            if key in centers:
                raise ValueError(f"Multiple center points for repeat/approach {key}")
            centers[key] = point

    required = {(point.repeat_index, point.approach_direction) for point in usable}
    missing = sorted(required.difference(centers))
    if missing:
        raise ValueError(f"Missing center point for repeat/approach groups: {missing}")

    return [
        IncrementalSteeringPoint(
            point=point,
            rack_from_center_m=(
                point.measured_rack_m
                - centers[(point.repeat_index, point.approach_direction)].measured_rack_m
            ),
            left_incremental_rad=(
                point.left_heading_rad
                - centers[(point.repeat_index, point.approach_direction)].left_heading_rad
            ),
            right_incremental_rad=(
                point.right_heading_rad
                - centers[(point.repeat_index, point.approach_direction)].right_heading_rad
            ),
        )
        for point in usable
    ]


def summarize_repeatability(
    points: list[IncrementalSteeringPoint],
    *,
    target_round_digits: int = 9,
) -> list[GroupSummary]:
    groups: dict[tuple[float, str], list[IncrementalSteeringPoint]] = {}
    for point in points:
        key = (
            round(point.point.target_fraction, target_round_digits),
            point.point.approach_direction,
        )
        groups.setdefault(key, []).append(point)

    summaries: list[GroupSummary] = []
    for (target, direction), group in sorted(groups.items()):
        rack = [item.rack_from_center_m for item in group]
        left = [item.left_incremental_rad for item in group]
        right = [item.right_incremental_rad for item in group]
        summaries.append(
            GroupSummary(
                target_fraction=target,
                approach_direction=direction,
                count=len(group),
                rack_mean_m=fmean(rack),
                rack_std_m=pstdev(rack),
                left_mean_rad=fmean(left),
                left_std_rad=pstdev(left),
                right_mean_rad=fmean(right),
                right_std_rad=pstdev(right),
            )
        )
    return summaries
