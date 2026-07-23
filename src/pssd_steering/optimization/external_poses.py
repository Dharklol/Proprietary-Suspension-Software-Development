"""External suspension-model pose ingestion for steering studies.

This adapter contains no suspension kinematics.  It converts a reviewed, explicit
rigid-transform exchange table into the canonical :mod:`poses` contract used by
``MOD-STEER-0002``.  Source-specific tools such as SolidWorks, OptimumK, or a
future native suspension solver remain responsible for generating the zero-steer
upright transforms.
"""

from __future__ import annotations

from dataclasses import dataclass
import csv
import math
from pathlib import Path
import tomllib

from .poses import (
    STEERING_DOF_RULE,
    PoseCoordinate,
    PoseDefinitionError,
    RigidTransform,
    SteeringPoseState,
    SuspensionPoseSet,
)


ROTATION_CONVENTION = "active_nominal_upright_to_state_body_frame"


class ExternalPoseAdapterError(PoseDefinitionError):
    """Raised when an external pose manifest or table violates the exchange contract."""


@dataclass(frozen=True)
class ExternalCoordinateColumn:
    id: str
    column: str
    unit: str

    def __post_init__(self) -> None:
        if not self.id or not self.column or not self.unit:
            raise ExternalPoseAdapterError("External coordinate definitions require id, column, and unit")


@dataclass(frozen=True)
class ExternalPoseImport:
    """Canonical pose set plus the source/adaptation provenance used to construct it."""

    adapter_id: str
    adapter_version: str
    manifest_path: str
    data_path: str
    source_type: str
    source_path: str
    source_revision: str
    authority: str
    frame_id: str
    frame_definition: str
    rotation_convention: str
    pose_set: SuspensionPoseSet


_REQUIRED_TRANSFORM_COLUMNS = (
    "left_tx_m",
    "left_ty_m",
    "left_tz_m",
    "left_r11",
    "left_r12",
    "left_r13",
    "left_r21",
    "left_r22",
    "left_r23",
    "left_r31",
    "left_r32",
    "left_r33",
    "right_tx_m",
    "right_ty_m",
    "right_tz_m",
    "right_r11",
    "right_r12",
    "right_r13",
    "right_r21",
    "right_r22",
    "right_r23",
    "right_r31",
    "right_r32",
    "right_r33",
)


def _nonempty(document: dict, key: str) -> str:
    value = str(document.get(key, "")).strip()
    if not value:
        raise ExternalPoseAdapterError(f"External pose manifest requires {key}")
    return value


def _float_cell(row: dict[str, str], column: str, *, state_id: str) -> float:
    try:
        value = float(row[column])
    except (KeyError, TypeError, ValueError) as exc:
        raise ExternalPoseAdapterError(
            f"State {state_id!r} has invalid or missing numeric column {column!r}"
        ) from exc
    if not math.isfinite(value):
        raise ExternalPoseAdapterError(
            f"State {state_id!r} column {column!r} must be finite"
        )
    return value


def _transform(row: dict[str, str], prefix: str, *, state_id: str, source_role: str) -> RigidTransform:
    rotation = (
        (
            _float_cell(row, f"{prefix}_r11", state_id=state_id),
            _float_cell(row, f"{prefix}_r12", state_id=state_id),
            _float_cell(row, f"{prefix}_r13", state_id=state_id),
        ),
        (
            _float_cell(row, f"{prefix}_r21", state_id=state_id),
            _float_cell(row, f"{prefix}_r22", state_id=state_id),
            _float_cell(row, f"{prefix}_r23", state_id=state_id),
        ),
        (
            _float_cell(row, f"{prefix}_r31", state_id=state_id),
            _float_cell(row, f"{prefix}_r32", state_id=state_id),
            _float_cell(row, f"{prefix}_r33", state_id=state_id),
        ),
    )
    translation = (
        _float_cell(row, f"{prefix}_tx_m", state_id=state_id),
        _float_cell(row, f"{prefix}_ty_m", state_id=state_id),
        _float_cell(row, f"{prefix}_tz_m", state_id=state_id),
    )
    return RigidTransform(rotation=rotation, translation_m=translation, source_role=source_role)


def load_external_pose_table(manifest_path: str | Path) -> ExternalPoseImport:
    """Load a canonical external rigid-upright pose exchange table.

    Version 0.1 intentionally accepts only body-frame metre translations and a full
    active 3x3 rotation matrix.  Source-specific coordinate conversion must happen
    before this boundary and remain documented by the manifest.  This keeps steering
    independent of vendor-specific export formats and prevents silent frame/sign
    assumptions.
    """

    manifest_file = Path(manifest_path)
    with manifest_file.open("rb") as stream:
        document = tomllib.load(stream)

    adapter_id = _nonempty(document, "adapter_id")
    adapter_version = _nonempty(document, "version")
    pose_set_id = _nonempty(document, "pose_set_id")
    nominal_state_id = _nonempty(document, "nominal_state_id")
    source_type = _nonempty(document, "source_type")
    source_path = _nonempty(document, "source_path")
    source_revision = _nonempty(document, "source_revision")
    authority = _nonempty(document, "authority")
    frame_id = _nonempty(document, "frame_id")
    frame_definition = _nonempty(document, "frame_definition")
    rotation_convention = _nonempty(document, "rotation_convention")
    translation_unit = _nonempty(document, "translation_unit")
    steering_dof_rule = _nonempty(document, "steering_dof_rule")
    data_file_name = _nonempty(document, "data_file")

    if steering_dof_rule != STEERING_DOF_RULE:
        raise ExternalPoseAdapterError(
            f"External source must declare steering_dof_rule={STEERING_DOF_RULE!r}"
        )
    if bool(document.get("tie_rod_steering_response_included", True)):
        raise ExternalPoseAdapterError(
            "External pose table must explicitly declare tie_rod_steering_response_included=false"
        )
    if translation_unit != "m":
        raise ExternalPoseAdapterError("External pose exchange v0.1 requires translation_unit='m'")
    if rotation_convention != ROTATION_CONVENTION:
        raise ExternalPoseAdapterError(
            f"External pose exchange v0.1 requires rotation_convention={ROTATION_CONVENTION!r}"
        )

    coordinate_tables = document.get("coordinates", [])
    coordinates = tuple(
        ExternalCoordinateColumn(
            id=str(item.get("id", "")),
            column=str(item.get("column", "")),
            unit=str(item.get("unit", "")),
        )
        for item in coordinate_tables
    )
    coordinate_ids = [item.id for item in coordinates]
    coordinate_columns = [item.column for item in coordinates]
    if len(coordinate_ids) != len(set(coordinate_ids)):
        raise ExternalPoseAdapterError("External pose manifest contains duplicate coordinate ids")
    if len(coordinate_columns) != len(set(coordinate_columns)):
        raise ExternalPoseAdapterError("External pose manifest contains duplicate coordinate columns")

    data_path = (manifest_file.parent / data_file_name).resolve()
    if not data_path.is_file():
        raise ExternalPoseAdapterError(f"External pose data file does not exist: {data_path}")

    with data_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = tuple(reader.fieldnames or ())
        required = {"state_id", *_REQUIRED_TRANSFORM_COLUMNS, *coordinate_columns}
        missing = sorted(required.difference(fieldnames))
        if missing:
            raise ExternalPoseAdapterError(
                "External pose table is missing required columns: " + ", ".join(missing)
            )

        states: list[SteeringPoseState] = []
        seen: set[str] = set()
        for row_index, row in enumerate(reader, start=2):
            state_id = str(row.get("state_id", "")).strip()
            if not state_id:
                raise ExternalPoseAdapterError(f"External pose row {row_index} has no state_id")
            if state_id in seen:
                raise ExternalPoseAdapterError(f"External pose table contains duplicate state {state_id!r}")
            seen.add(state_id)

            state_coordinates = tuple(
                PoseCoordinate(
                    id=item.id,
                    value=_float_cell(row, item.column, state_id=state_id),
                    unit=item.unit,
                )
                for item in coordinates
            )
            states.append(
                SteeringPoseState(
                    state_id=state_id,
                    left_transform=_transform(
                        row,
                        "left",
                        state_id=state_id,
                        source_role=f"external_pose:{adapter_id}:{state_id}:left",
                    ),
                    right_transform=_transform(
                        row,
                        "right",
                        state_id=state_id,
                        source_role=f"external_pose:{adapter_id}:{state_id}:right",
                    ),
                    coordinates=state_coordinates,
                    source_type=source_type,
                    source_path=source_path,
                    authority=authority,
                    steering_dof_rule=steering_dof_rule,
                )
            )

    pose_set = SuspensionPoseSet(
        pose_set_id=pose_set_id,
        version=adapter_version,
        nominal_state_id=nominal_state_id,
        states=tuple(states),
        source_path=source_path,
        authority=authority,
    )
    return ExternalPoseImport(
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        manifest_path=str(manifest_file),
        data_path=str(data_path),
        source_type=source_type,
        source_path=source_path,
        source_revision=source_revision,
        authority=authority,
        frame_id=frame_id,
        frame_definition=frame_definition,
        rotation_convention=rotation_convention,
        pose_set=pose_set,
    )
