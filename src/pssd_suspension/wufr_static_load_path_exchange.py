"""Canonical WUFR static load-path screening exchange.

Implements AUTH-SUSP-0019 / MOD-SUSP-0011.  This module reads the four
accepted frozen static result records and packages their values without
rerunning physics, transforming frames, relocating points, repairing signs, or
completing missing loads.  The output is a deterministic screening exchange,
not an FEA boundary-condition set or structural release.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
import tomllib
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
CORNER_ORDER = ("front_left", "front_right", "rear_left", "rear_right")
RESULT_LABEL = "uncorrelated_design_intent_static_load_path_screening_exchange"
MODEL_ID = "MOD-SUSP-0011"
AUTHORIZATION_ID = "AUTH-SUSP-0019"
CONFIGURATION_ID = "WUFR27_SUSPENSION_BASELINE_V0"
STATIC_STATE_ID = "WUFR26_DRIVER_NO_FUEL_DESIGN_INTENT_REFERENCE"
SOURCE_RECORD_ID = "WUFR27_STATIC_LOAD_PATH_EXCHANGE_V0"
SCHEMA_VERSION = "0.1.0"
MISSING_FORCE_ID = "KW_V5_non_spring_static_force"

SOURCE_KEYS = (
    "vehicle_equilibrium",
    "carrier_wrench",
    "level1_interface",
    "rocker_included",
)


class WUFRStaticLoadPathExchangeFailureCode(str, Enum):
    SOURCE_RECORD_UNAVAILABLE = "source_record_unavailable"
    SOURCE_RECORD_FAILURE = "source_record_failure"
    SOURCE_HASH_MISMATCH = "source_hash_mismatch"
    CONFIGURATION_MISMATCH = "configuration_mismatch"
    STATIC_STATE_MISMATCH = "static_state_mismatch"
    CORNER_COUNT_OR_ORDER_MISMATCH = "corner_count_or_order_mismatch"
    SETTING_MISMATCH = "setting_mismatch"
    REQUIRED_SECTION_MISSING = "required_section_missing"
    SOURCE_FIELD_MISSING = "source_field_missing"
    FRAME_OR_POINT_IDENTITY_MISSING = "frame_or_point_identity_missing"
    NONFINITE_SOURCE_VALUE = "nonfinite_source_value"
    PROHIBITED_AUTHORITY_FLAG = "prohibited_authority_flag"
    MISSING_BOUNDARY_NOT_DECLARED = "missing_boundary_not_declared"
    PACKET_INCOMPLETE = "packet_incomplete"


class WUFRStaticLoadPathExchangeError(ValueError):
    def __init__(
        self,
        code: WUFRStaticLoadPathExchangeFailureCode,
        message: str,
        *,
        failed_source: str | None = None,
        failed_section: str | None = None,
        failed_field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.failed_source = failed_source
        self.failed_section = failed_section
        self.failed_field = failed_field


@dataclass(frozen=True)
class WUFRStaticLoadPathExchangeResult:
    ok: bool
    packet: dict[str, Any] | None = None
    failure_code: WUFRStaticLoadPathExchangeFailureCode | None = None
    failed_source: str | None = None
    failed_section: str | None = None
    failed_field: str | None = None
    message: str = ""


@dataclass(frozen=True)
class _Source:
    key: str
    path: str
    model_id: str
    authorization_id: str
    result_label: str
    data: dict[str, Any]
    raw_bytes: bytes
    sha256: str


def canonical_json_bytes(document: Mapping[str, Any]) -> bytes:
    """Return the canonical UTF-8 representation used by the frozen packet."""
    return (
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_json_text(document: Mapping[str, Any]) -> str:
    return canonical_json_bytes(document).decode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _finite_tree(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, Mapping):
        return all(_finite_tree(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return all(_finite_tree(item) for item in value)
    return False


def _require_mapping(parent: Mapping[str, Any], key: str, *, source: str, path: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.SOURCE_FIELD_MISSING,
            f"Required mapping {path}.{key} is unavailable",
            failed_source=source,
            failed_field=f"{path}.{key}",
        )
    return value


def _require_sequence(parent: Mapping[str, Any], key: str, *, source: str, path: str) -> Sequence[Any]:
    value = parent.get(key)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.SOURCE_FIELD_MISSING,
            f"Required sequence {path}.{key} is unavailable",
            failed_source=source,
            failed_field=f"{path}.{key}",
        )
    return value


def _require_point(value: Any, *, source: str, field: str) -> list[float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or len(value) != 3:
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.FRAME_OR_POINT_IDENTITY_MISSING,
            f"{field} must be a three-component source-owned Cartesian value",
            failed_source=source,
            failed_field=field,
        )
    result = [float(item) for item in value]
    if not all(math.isfinite(item) for item in result):
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.NONFINITE_SOURCE_VALUE,
            f"{field} contains a nonfinite value",
            failed_source=source,
            failed_field=field,
        )
    return result


def _source_contract(source_path: Path) -> dict[str, Any]:
    try:
        with source_path.open("rb") as stream:
            document = tomllib.load(stream)
    except OSError as exc:
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.SOURCE_RECORD_UNAVAILABLE,
            f"Unable to read exchange source contract: {exc}",
            failed_source=str(source_path),
        ) from exc
    if (
        document.get("record_id") != SOURCE_RECORD_ID
        or document.get("authorization_id") != AUTHORIZATION_ID
        or document.get("model_id") != MODEL_ID
        or document.get("result_label") != RESULT_LABEL
        or tuple(document.get("corner_order", ())) != CORNER_ORDER
    ):
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.SOURCE_RECORD_FAILURE,
            "Static load-path exchange source contract identity does not match AUTH-SUSP-0019",
            failed_source=str(source_path),
        )
    return document


def _load_sources(root: Path, contract: Mapping[str, Any]) -> dict[str, _Source]:
    source_table = _require_mapping(contract, "source", source="exchange_contract", path="root")
    sources: dict[str, _Source] = {}
    for key in SOURCE_KEYS:
        entry = _require_mapping(source_table, key, source="exchange_contract", path="source")
        relative = str(entry.get("result_record", ""))
        if not relative:
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.SOURCE_FIELD_MISSING,
                f"Source record path is missing for {key}",
                failed_source="exchange_contract",
                failed_field=f"source.{key}.result_record",
            )
        path = root / relative
        try:
            raw = path.read_bytes()
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.SOURCE_RECORD_UNAVAILABLE,
                f"Unable to load {key} record {relative}: {exc}",
                failed_source=key,
            ) from exc
        if not isinstance(data, dict):
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.SOURCE_RECORD_FAILURE,
                f"{key} record root must be an object",
                failed_source=key,
            )
        if not _finite_tree(data):
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.NONFINITE_SOURCE_VALUE,
                f"{key} record contains a nonfinite or unsupported value",
                failed_source=key,
            )
        sources[key] = _Source(
            key=key,
            path=relative,
            model_id=str(entry.get("model_id", "")),
            authorization_id=str(entry.get("authorization_id", "")),
            result_label=str(entry.get("result_label", "")),
            data=data,
            raw_bytes=raw,
            sha256=sha256_bytes(raw),
        )
    return sources


def _sources_from_documents(
    contract: Mapping[str, Any],
    documents: Mapping[str, Mapping[str, Any]],
) -> dict[str, _Source]:
    source_table = _require_mapping(contract, "source", source="exchange_contract", path="root")
    sources: dict[str, _Source] = {}
    for key in SOURCE_KEYS:
        entry = _require_mapping(source_table, key, source="exchange_contract", path="source")
        data = documents.get(key)
        if not isinstance(data, Mapping):
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.SOURCE_RECORD_UNAVAILABLE,
                f"Injected source document {key} is unavailable",
                failed_source=key,
            )
        copied = deepcopy(dict(data))
        if not _finite_tree(copied):
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.NONFINITE_SOURCE_VALUE,
                f"Injected {key} record contains a nonfinite or unsupported value",
                failed_source=key,
            )
        raw = canonical_json_bytes(copied)
        sources[key] = _Source(
            key=key,
            path=str(entry.get("result_record", "")),
            model_id=str(entry.get("model_id", "")),
            authorization_id=str(entry.get("authorization_id", "")),
            result_label=str(entry.get("result_label", "")),
            data=copied,
            raw_bytes=raw,
            sha256=sha256_bytes(raw),
        )
    return sources


def _metadata_value(data: Mapping[str, Any], key: str) -> Any:
    if key in data:
        return data[key]
    primary = data.get("primary")
    if isinstance(primary, Mapping) and key in primary:
        return primary[key]
    return None


def _corner_ids(data: Mapping[str, Any], *, source: str) -> tuple[str, ...]:
    corners = data.get("corners")
    if isinstance(corners, Sequence) and not isinstance(corners, (str, bytes, bytearray)):
        return tuple(str(item.get("corner_id", "")) if isinstance(item, Mapping) else "" for item in corners)
    primary = data.get("primary")
    if isinstance(primary, Mapping):
        solve = primary.get("solve")
        if isinstance(solve, Mapping):
            order = solve.get("wheel_coordinate_order")
            if isinstance(order, Sequence) and not isinstance(order, (str, bytes, bytearray)):
                return tuple(str(item) for item in order)
    raise WUFRStaticLoadPathExchangeError(
        WUFRStaticLoadPathExchangeFailureCode.CORNER_COUNT_OR_ORDER_MISMATCH,
        f"{source} does not carry a four-corner identity",
        failed_source=source,
        failed_field="corner_order",
    )


def _validate_sources(sources: Mapping[str, _Source]) -> tuple[int, int]:
    eq = sources["vehicle_equilibrium"].data
    carrier = sources["carrier_wrench"].data
    level1 = sources["level1_interface"].data
    rocker = sources["rocker_included"].data

    expected = {
        "vehicle_equilibrium": ("MOD-VEH-0007", "AUTH-VEH-0010", "uncorrelated_design_intent_static_gravity"),
        "carrier_wrench": ("MOD-VEH-0008", "AUTH-VEH-0011", "uncorrelated_design_intent_static_carrier_wrench"),
        "level1_interface": ("MOD-SUSP-0009", "AUTH-SUSP-0017", "uncorrelated_design_intent_static_level1_interface_loads"),
        "rocker_included": ("MOD-SUSP-0010", "AUTH-SUSP-0018", "uncorrelated_design_intent_static_rocker_included_loads"),
    }
    for key, (model_id, authorization_id, label) in expected.items():
        source = sources[key]
        data = source.data
        if (
            source.model_id != model_id
            or source.authorization_id != authorization_id
            or source.result_label != label
            or _metadata_value(data, "model_id") != model_id
            or _metadata_value(data, "authorization_id") != authorization_id
            or _metadata_value(data, "result_label") != label
        ):
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.SOURCE_RECORD_FAILURE,
                f"{key} source identity does not match the authorized record",
                failed_source=key,
            )
        if _metadata_value(data, "configuration_id") != CONFIGURATION_ID:
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.CONFIGURATION_MISMATCH,
                f"{key} configuration does not match {CONFIGURATION_ID}",
                failed_source=key,
                failed_field="configuration_id",
            )
        if _metadata_value(data, "static_state_id") != STATIC_STATE_ID:
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.STATIC_STATE_MISMATCH,
                f"{key} static state does not match {STATIC_STATE_ID}",
                failed_source=key,
                failed_field="static_state_id",
            )
        if _corner_ids(data, source=key) != CORNER_ORDER:
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.CORNER_COUNT_OR_ORDER_MISMATCH,
                f"{key} corner order is not the exact FL/FR/RL/RR contract",
                failed_source=key,
                failed_field="corner_order",
            )

    primary = _require_mapping(eq, "primary", source="vehicle_equilibrium", path="root")
    if eq.get("status") != "pass" or primary.get("ok") is not True:
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.SOURCE_RECORD_FAILURE,
            "Vehicle static-equilibrium record is not accepted/successful",
            failed_source="vehicle_equilibrium",
        )
    front_setting = int(primary.get("front_arb_setting", -1))
    rear_setting = int(primary.get("rear_arb_setting", -1))
    if (front_setting, rear_setting) != (1, 1):
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.SETTING_MISMATCH,
            "The exchange is authorized only for the accepted setting-1/1 fixture",
            failed_source="vehicle_equilibrium",
            failed_field="primary.front_arb_setting/rear_arb_setting",
        )

    if carrier.get("status") != "pass" or any(item.get("ok") is not True for item in carrier.get("corners", ())):
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.SOURCE_RECORD_FAILURE,
            "Carrier-wrench record is not successful for all corners",
            failed_source="carrier_wrench",
        )
    if level1.get("status") != "accepted" or any(item.get("solve", {}).get("ok") is not True for item in level1.get("corners", ())):
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.SOURCE_RECORD_FAILURE,
            "Level-1 interface-load record is not successful for all corners",
            failed_source="level1_interface",
        )
    if rocker.get("status") != "accepted":
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.SOURCE_RECORD_FAILURE,
            "Rocker included-load record is not accepted",
            failed_source="rocker_included",
        )

    carrier_boundaries = _require_mapping(carrier, "boundaries", source="carrier_wrench", path="root")
    level1_boundaries = _require_mapping(level1, "boundaries", source="level1_interface", path="root")
    rocker_boundaries = _require_mapping(rocker, "boundaries", source="rocker_included", path="root")
    prohibited_true = (
        ("carrier_wrench", "structural_load_case_authority", carrier_boundaries.get("structural_load_case_authority")),
        ("carrier_wrench", "installed_as_built_authority", carrier_boundaries.get("installed_as_built_authority")),
        ("level1_interface", "complete_physical_vehicle_load_case", level1_boundaries.get("complete_physical_vehicle_load_case")),
        ("level1_interface", "individual_a_arm_joint_split_authorized", level1_boundaries.get("individual_a_arm_joint_split_authorized")),
        ("level1_interface", "installed_as_built_authority", level1_boundaries.get("installed_as_built_authority")),
        ("rocker_included", "complete_hardware_reaction", rocker_boundaries.get("complete_hardware_reaction")),
        ("rocker_included", "complete_rocker_equilibrium", rocker_boundaries.get("complete_rocker_equilibrium")),
        ("rocker_included", "actual_damper_force_applied", rocker_boundaries.get("actual_damper_force_applied")),
        ("rocker_included", "structural_release_authority", rocker_boundaries.get("structural_release_authority")),
        ("rocker_included", "installed_as_built_authority", rocker_boundaries.get("installed_as_built_authority")),
    )
    for source, field, value in prohibited_true:
        if value is not False:
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.PROHIBITED_AUTHORITY_FLAG,
                f"Prohibited authority boundary {source}.{field} must remain false",
                failed_source=source,
                failed_field=f"boundaries.{field}",
            )

    for index, corner in enumerate(rocker.get("corners", ())):
        included = corner.get("included") if isinstance(corner, Mapping) else None
        missing = included.get("missing_load_ids") if isinstance(included, Mapping) else None
        if missing != [MISSING_FORCE_ID]:
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.MISSING_BOUNDARY_NOT_DECLARED,
                f"Rocker corner {CORNER_ORDER[index]} does not retain the KW V5 missing-force identity",
                failed_source="rocker_included",
                failed_field=f"corners[{index}].included.missing_load_ids",
            )
    return front_setting, rear_setting


def _record(
    *,
    record_id: str,
    corner_id: str,
    load_role: str,
    acting_on_body_id: str,
    counterparty_body_id: str,
    frame_id: str,
    point_or_reference_id: str,
    point_m: Sequence[float],
    force_N: Sequence[float],
    moment_Nm: Sequence[float],
    source_model_id: str,
    source_authorization_id: str,
    source_result_path: str,
    source_field_path: str,
    sign_convention: str,
    fidelity_label: str,
    complete_for_named_source_record: bool,
    **extra: Any,
) -> dict[str, Any]:
    record = {
        "record_id": record_id,
        "corner_id": corner_id,
        "load_role": load_role,
        "acting_on_body_id": acting_on_body_id,
        "counterparty_body_id": counterparty_body_id,
        "frame_id": frame_id,
        "point_or_reference_id": point_or_reference_id,
        "application_or_reference_point_m": _require_point(point_m, source=source_model_id, field=source_field_path + ".point"),
        "force_N": _require_point(force_N, source=source_model_id, field=source_field_path + ".force_N"),
        "moment_Nm": _require_point(moment_Nm, source=source_model_id, field=source_field_path + ".moment_Nm"),
        "source_model_id": source_model_id,
        "source_authorization_id": source_authorization_id,
        "source_result_path": source_result_path,
        "source_field_path": source_field_path,
        "sign_convention": sign_convention,
        "fidelity_label": fidelity_label,
        "complete_for_named_source_record": bool(complete_for_named_source_record),
    }
    record.update(extra)
    return record


def _carrier_records(source: _Source) -> dict[str, list[dict[str, Any]]]:
    result = {corner_id: [] for corner_id in CORNER_ORDER}
    for index, corner in enumerate(source.data["corners"]):
        corner_id = CORNER_ORDER[index]
        wrench = _require_mapping(corner, "level1_wrench", source=source.key, path=f"corners[{index}]")
        frame = str(wrench.get("frame_id", ""))
        if not frame:
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.FRAME_OR_POINT_IDENTITY_MISSING,
                "Carrier wrench frame identity is missing",
                failed_source=source.key,
                failed_field=f"corners[{index}].level1_wrench.frame_id",
            )
        result[corner_id].append(_record(
            record_id=f"{corner_id}:carrier_external_wrench",
            corner_id=corner_id,
            load_role="carrier_external_wrench",
            acting_on_body_id="outboard_carrier",
            counterparty_body_id="road_contact_and_unsprung_gravity_sources",
            frame_id=frame,
            point_or_reference_id=f"{corner_id}:current_carrier_reference",
            point_m=wrench["reference_point_m"],
            force_N=wrench["force_N"],
            moment_Nm=wrench["moment_Nm"],
            source_model_id=source.model_id,
            source_authorization_id=source.authorization_id,
            source_result_path=source.path,
            source_field_path=f"corners[{index}].level1_wrench",
            sign_convention="Signed Cartesian external wrench on the outboard carrier copied exactly from MOD-VEH-0008",
            fidelity_label="complete_external_carrier_wrench_for_authorized_static_gravity_case_only",
            complete_for_named_source_record=bool(wrench.get("complete")),
        ))
    return result


def _level1_records(source: _Source) -> dict[str, list[dict[str, Any]]]:
    result = {corner_id: [] for corner_id in CORNER_ORDER}
    zeros = (0.0, 0.0, 0.0)
    for index, corner in enumerate(source.data["corners"]):
        corner_id = CORNER_ORDER[index]
        geometry = _require_mapping(corner, "geometry", source=source.key, path=f"corners[{index}]")
        solve = _require_mapping(corner, "solve", source=source.key, path=f"corners[{index}]")
        frame = str(geometry.get("frame_id", ""))
        if not frame:
            raise WUFRStaticLoadPathExchangeError(
                WUFRStaticLoadPathExchangeFailureCode.FRAME_OR_POINT_IDENTITY_MISSING,
                "Level-1 geometry frame identity is missing",
                failed_source=source.key,
                failed_field=f"corners[{index}].geometry.frame_id",
            )
        for name in ("lateral", "actuation"):
            axial = _require_mapping(solve, name, source=source.key, path=f"corners[{index}].solve")
            element_id = str(axial.get("element_id", name))
            body_id = str(axial.get("body_id", ""))
            axial_scalar = float(axial["axial_force_N"])
            common = dict(
                corner_id=corner_id,
                frame_id=frame,
                source_model_id=source.model_id,
                source_authorization_id=source.authorization_id,
                source_result_path=source.path,
                fidelity_label="ideal_two_force_axial_interface_reaction",
                complete_for_named_source_record=True,
                source_axial_force_N=axial_scalar,
                source_element_id=element_id,
            )
            result[corner_id].append(_record(
                record_id=f"{corner_id}:{element_id}:on_body",
                load_role=f"{name}_force_on_body",
                acting_on_body_id=body_id,
                counterparty_body_id=f"{element_id}_remote",
                point_or_reference_id=f"{element_id}:body_point",
                point_m=axial["body_point_m"],
                force_N=axial["force_on_body_N"],
                moment_Nm=zeros,
                source_field_path=f"corners[{index}].solve.{name}.force_on_body_N",
                sign_convention="Signed Cartesian force copied exactly; positive source axial_force_N denotes tension",
                **common,
            ))
            result[corner_id].append(_record(
                record_id=f"{corner_id}:{element_id}:on_remote",
                load_role=f"{name}_force_on_remote",
                acting_on_body_id=f"{element_id}_remote",
                counterparty_body_id=body_id,
                point_or_reference_id=f"{element_id}:remote_point",
                point_m=axial["remote_point_m"],
                force_N=axial["force_on_remote_N"],
                moment_Nm=zeros,
                source_field_path=f"corners[{index}].solve.{name}.force_on_remote_N",
                sign_convention="Explicit equal/opposite remote-end Cartesian force copied exactly; positive source axial_force_N denotes tension",
                **common,
            ))

        for name, arm_id in (("upper_spherical", "upper_a_arm"), ("lower_spherical", "lower_a_arm")):
            spherical = _require_mapping(solve, name, source=source.key, path=f"corners[{index}].solve")
            interface_id = str(spherical.get("interface_id", name))
            for role, acting_on, counterparty, force_key in (
                ("force_on_carrier", "outboard_carrier", arm_id, "force_on_carrier_N"),
                ("force_on_arm", arm_id, "outboard_carrier", "force_on_arm_N"),
            ):
                result[corner_id].append(_record(
                    record_id=f"{corner_id}:{interface_id}:{role}",
                    corner_id=corner_id,
                    load_role=f"{name}_{role}",
                    acting_on_body_id=acting_on,
                    counterparty_body_id=counterparty,
                    frame_id=frame,
                    point_or_reference_id=interface_id,
                    point_m=spherical["point_m"],
                    force_N=spherical[force_key],
                    moment_Nm=zeros,
                    source_model_id=source.model_id,
                    source_authorization_id=source.authorization_id,
                    source_result_path=source.path,
                    source_field_path=f"corners[{index}].solve.{name}.{force_key}",
                    sign_convention="Explicit signed spherical-interface action/reaction vector copied exactly",
                    fidelity_label="ideal_spherical_interface_reaction",
                    complete_for_named_source_record=True,
                ))

        for name, body_id in (("upper_hinge", "upper_a_arm"), ("lower_hinge", "lower_a_arm")):
            hinge = _require_mapping(solve, name, source=source.key, path=f"corners[{index}].solve")
            result[corner_id].append(_record(
                record_id=f"{corner_id}:{name}:equivalent_support",
                corner_id=corner_id,
                load_role=f"{name}_equivalent_support_reaction",
                acting_on_body_id=body_id,
                counterparty_body_id="chassis_equivalent_ideal_revolute_support",
                frame_id=frame,
                point_or_reference_id=f"{name}:reference",
                point_m=hinge["point_m"],
                force_N=hinge["force_N"],
                moment_Nm=hinge["moment_Nm"],
                source_model_id=source.model_id,
                source_authorization_id=source.authorization_id,
                source_result_path=source.path,
                source_field_path=f"corners[{index}].solve.{name}",
                sign_convention="Signed equivalent ideal-revolute support resultant on the named A-arm copied exactly",
                fidelity_label="equivalent_hinge_resultant_no_forward_aft_joint_split",
                complete_for_named_source_record=True,
                hinge_axis_unit=deepcopy(hinge.get("axis_unit")),
                hinge_axis_moment_component_Nm=hinge.get("moment_axis_component_Nm"),
            ))
    return result


def _rocker_records(source: _Source) -> dict[str, list[dict[str, Any]]]:
    result = {corner_id: [] for corner_id in CORNER_ORDER}
    zeros = (0.0, 0.0, 0.0)
    counterparty = {
        "push_pull": "actuation_rod",
        "conservative_spring": "coil_spring",
        "physical_arb_link": "zbar_link",
    }
    for index, corner in enumerate(source.data["corners"]):
        corner_id = CORNER_ORDER[index]
        included = _require_mapping(corner, "included", source=source.key, path=f"corners[{index}]")
        point_loads = _require_sequence(included, "point_loads", source=source.key, path=f"corners[{index}].included")
        frame = ""
        for load_index, load in enumerate(point_loads):
            if not isinstance(load, Mapping):
                raise WUFRStaticLoadPathExchangeError(
                    WUFRStaticLoadPathExchangeFailureCode.SOURCE_FIELD_MISSING,
                    "Rocker point-load record is malformed",
                    failed_source=source.key,
                    failed_field=f"corners[{index}].included.point_loads[{load_index}]",
                )
            load_id = str(load.get("load_id", ""))
            frame = str(load.get("frame_id", frame))
            result[corner_id].append(_record(
                record_id=f"{corner_id}:rocker:{load_id}",
                corner_id=corner_id,
                load_role=f"rocker_point_load:{load_id}",
                acting_on_body_id="rocker",
                counterparty_body_id=counterparty.get(load_id, str(load.get("source_id", "source_interface"))),
                frame_id=frame,
                point_or_reference_id=f"{corner_id}:rocker:{load_id}:application",
                point_m=load["application_point_m"],
                force_N=load["force_N"],
                moment_Nm=zeros,
                source_model_id=source.model_id,
                source_authorization_id=source.authorization_id,
                source_result_path=source.path,
                source_field_path=f"corners[{index}].included.point_loads[{load_index}]",
                sign_convention="Signed Cartesian point load on the rocker copied exactly from MOD-SUSP-0010",
                fidelity_label="named_included_rocker_point_load_missing_kw_v5_non_spring_force",
                complete_for_named_source_record=True,
                upstream_source_id=load.get("source_id"),
                load_case_id=load.get("load_case_id"),
            ))
        spring = _require_mapping(corner, "spring", source=source.key, path=f"corners[{index}]")
        pivot = spring.get("rocker_pivot_m")
        result[corner_id].append(_record(
            record_id=f"{corner_id}:rocker:partial_pivot_support",
            corner_id=corner_id,
            load_role="rocker_included_load_ideal_revolute_support_contribution",
            acting_on_body_id="rocker",
            counterparty_body_id="chassis_ideal_revolute_support",
            frame_id=frame,
            point_or_reference_id=f"{corner_id}:rocker_pivot",
            point_m=pivot,
            force_N=included["pivot_force_contribution_N"],
            moment_Nm=included["pivot_moment_contribution_Nm"],
            source_model_id=source.model_id,
            source_authorization_id=source.authorization_id,
            source_result_path=source.path,
            source_field_path=f"corners[{index}].included.pivot_force_contribution_N/pivot_moment_contribution_Nm",
            sign_convention="Signed ideal-revolute support contribution for the named included load set only",
            fidelity_label="incomplete_rocker_support_contribution_kw_v5_force_missing",
            complete_for_named_source_record=True,
            complete_hardware_reaction=False,
            free_axis_moment_residual_Nm=included.get("free_axis_moment_residual_Nm"),
        ))
    return result


def _manifest_entry(source: _Source) -> dict[str, Any]:
    return {
        "source_key": source.key,
        "source_model_id": source.model_id,
        "source_authorization_id": source.authorization_id,
        "source_result_label": source.result_label,
        "source_result_path": source.path,
        "source_sha256": source.sha256,
        "source_byte_count": len(source.raw_bytes),
        "hash_algorithm": "sha256",
        "exact_source_record_copied": True,
    }


def _benchmark_blocks(data: Mapping[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(value) for key, value in data.items() if isinstance(key, str) and key.startswith("BENCH-")}


def _assemble_packet(
    contract: Mapping[str, Any],
    sources: Mapping[str, _Source],
    front_setting: int,
    rear_setting: int,
) -> dict[str, Any]:
    eq = sources["vehicle_equilibrium"].data
    carrier = sources["carrier_wrench"].data
    level1 = sources["level1_interface"].data
    rocker = sources["rocker_included"].data
    packet_contract = _require_mapping(contract, "packet", source="exchange_contract", path="root")
    fidelity = _require_mapping(packet_contract, "fidelity", source="exchange_contract", path="packet")
    missing = _require_mapping(packet_contract, "missing_and_deferred", source="exchange_contract", path="packet")
    permitted = _require_mapping(packet_contract, "permitted_use", source="exchange_contract", path="packet")
    prohibited = _require_mapping(packet_contract, "prohibited_use", source="exchange_contract", path="packet")

    carrier_records = _carrier_records(sources["carrier_wrench"])
    level1_records = _level1_records(sources["level1_interface"])
    rocker_records = _rocker_records(sources["rocker_included"])

    packet = {
        "packet_identity": {
            "version": "0.1.0",
            "schema_version": SCHEMA_VERSION,
            "record_id": SOURCE_RECORD_ID,
            "status": "accepted",
            "result_label": RESULT_LABEL,
            "model_id": MODEL_ID,
            "authorization_id": AUTHORIZATION_ID,
            "configuration_id": CONFIGURATION_ID,
            "static_state_id": STATIC_STATE_ID,
            "front_arb_setting": front_setting,
            "rear_arb_setting": rear_setting,
            "corner_order": list(CORNER_ORDER),
            "canonical_units": "SI",
            "canonical_format": "JSON",
        },
        "source_manifest": [_manifest_entry(sources[key]) for key in SOURCE_KEYS],
        "vehicle_static_state": {
            "source_result_path": sources["vehicle_equilibrium"].path,
            "source_field_path": "primary",
            "primary": deepcopy(eq["primary"]),
            "solver_configuration": deepcopy(eq.get("solver_configuration")),
            "authority_boundary": deepcopy(eq.get("authority_boundary")),
        },
        "carrier_external_wrenches": {
            "source_result_path": sources["carrier_wrench"].path,
            "source_field_path": "corners",
            "corners": deepcopy(carrier["corners"]),
            "records_by_corner": carrier_records,
            "four_corner_reconstruction": deepcopy(carrier.get("four_corner_reconstruction")),
            "boundaries": deepcopy(carrier["boundaries"]),
        },
        "level1_interface_loads": {
            "source_result_path": sources["level1_interface"].path,
            "source_field_path": "corners",
            "corners": deepcopy(level1["corners"]),
            "records_by_corner": level1_records,
            "collection": deepcopy(level1.get("collection")),
            "boundaries": deepcopy(level1["boundaries"]),
        },
        "rocker_included_loads": {
            "source_result_path": sources["rocker_included"].path,
            "source_field_path": "corners",
            "corners": deepcopy(rocker["corners"]),
            "records_by_corner": rocker_records,
            "collection": deepcopy(rocker.get("collection")),
            "boundaries": deepcopy(rocker["boundaries"]),
        },
        "missing_and_deferred_loads": {
            "items": deepcopy(list(missing.get("items", ()))),
            "required_missing_force_id": MISSING_FORCE_ID,
            "kw_v5_actual_force_available": False,
            "zero_damper_force_assumption_used": False,
            "unit_damper_influence_is_geometry_sensitivity_only": True,
            "unit_damper_influence": {
                corner_id: deepcopy(rocker["corners"][index]["damper_unit_influence"])
                for index, corner_id in enumerate(CORNER_ORDER)
            },
        },
        "diagnostics": {
            "source_benchmarks": {
                key: _benchmark_blocks(sources[key].data)
                for key in SOURCE_KEYS
            },
            "source_hashes": {key: sources[key].sha256 for key in SOURCE_KEYS},
            "load_record_counts": {
                "carrier_external_wrenches": sum(len(records) for records in carrier_records.values()),
                "level1_interface_loads": sum(len(records) for records in level1_records.values()),
                "rocker_included_loads": sum(len(records) for records in rocker_records.values()),
            },
            "copy_policy": "exact_source_values_no_physics_rerun_no_frame_transform_no_point_relocation_no_sign_repair",
        },
        "fidelity_and_use_boundaries": {
            "fidelity_label": fidelity.get("label"),
            "complete_for_named_upstream_record_exchange": True,
            "complete_physical_hardware_load_case": False,
            "complete_rocker_equilibrium": False,
            "complete_chassis_pickup_load_set": False,
            "structural_load_case_authority": False,
            "fea_boundary_condition_authority": False,
            "structural_release_authority": False,
            "installed_as_built_authority": False,
            "production_authority": False,
            "permitted_uses": deepcopy(list(permitted.get("items", ()))),
            "prohibited_uses": deepcopy(list(prohibited.get("items", ()))),
        },
    }
    required_sections = tuple(packet_contract.get("sections", {}).get("required", ())) if isinstance(packet_contract.get("sections"), Mapping) else ()
    if not required_sections:
        required_sections = (
            "packet_identity", "source_manifest", "vehicle_static_state", "carrier_external_wrenches",
            "level1_interface_loads", "rocker_included_loads", "missing_and_deferred_loads",
            "diagnostics", "fidelity_and_use_boundaries",
        )
    if tuple(packet.keys()) != required_sections:
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.REQUIRED_SECTION_MISSING,
            "Canonical packet section order/completeness does not match AUTH-SUSP-0019",
            failed_section="packet_root",
        )
    record_ids: list[str] = []
    for section in (carrier_records, level1_records, rocker_records):
        for corner_id in CORNER_ORDER:
            records = section[corner_id]
            if not records:
                raise WUFRStaticLoadPathExchangeError(
                    WUFRStaticLoadPathExchangeFailureCode.PACKET_INCOMPLETE,
                    f"No load records were published for {corner_id}",
                    failed_section="records_by_corner",
                )
            record_ids.extend(str(record["record_id"]) for record in records)
    if len(record_ids) != len(set(record_ids)):
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.PACKET_INCOMPLETE,
            "Canonical load-record identities are not unique",
            failed_section="records_by_corner",
        )
    if not _finite_tree(packet):
        raise WUFRStaticLoadPathExchangeError(
            WUFRStaticLoadPathExchangeFailureCode.NONFINITE_SOURCE_VALUE,
            "Assembled packet contains a nonfinite or unsupported value",
            failed_section="packet_root",
        )
    canonical_json_bytes(packet)
    return packet


def evaluate_wufr_static_load_path_exchange(
    *,
    root: str | Path = ROOT,
    source_contract_path: str | Path | None = None,
    source_documents: Mapping[str, Mapping[str, Any]] | None = None,
) -> WUFRStaticLoadPathExchangeResult:
    root_path = Path(root)
    contract_path = Path(source_contract_path) if source_contract_path is not None else root_path / "data_catalog/wufr27_static_load_path_exchange_v0.toml"
    try:
        contract = _source_contract(contract_path)
        sources = _load_sources(root_path, contract) if source_documents is None else _sources_from_documents(contract, source_documents)
        front_setting, rear_setting = _validate_sources(sources)
        packet = _assemble_packet(contract, sources, front_setting, rear_setting)
        return WUFRStaticLoadPathExchangeResult(ok=True, packet=packet)
    except WUFRStaticLoadPathExchangeError as exc:
        return WUFRStaticLoadPathExchangeResult(
            ok=False,
            packet=None,
            failure_code=exc.code,
            failed_source=exc.failed_source,
            failed_section=exc.failed_section,
            failed_field=exc.failed_field,
            message=str(exc),
        )
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return WUFRStaticLoadPathExchangeResult(
            ok=False,
            packet=None,
            failure_code=WUFRStaticLoadPathExchangeFailureCode.SOURCE_FIELD_MISSING,
            message=f"Source-preserving packet assembly failed closed: {exc}",
        )


def load_wufr_static_load_path_source_documents(*, root: str | Path = ROOT) -> dict[str, dict[str, Any]]:
    root_path = Path(root)
    contract = _source_contract(root_path / "data_catalog/wufr27_static_load_path_exchange_v0.toml")
    return {key: deepcopy(source.data) for key, source in _load_sources(root_path, contract).items()}
