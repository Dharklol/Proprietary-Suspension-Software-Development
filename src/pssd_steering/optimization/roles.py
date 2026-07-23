"""Role resolution for the authorized steering inverse-design development layer.

This module contains no steering physics. It resolves a named requirement set into
an immutable candidate parameter record before the geometry generator composes the
existing ``MOD-STEER-0001`` analyzer contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Mapping


class RoleResolutionError(ValueError):
    """Raised when a requirement set or candidate role assignment is invalid."""


class ParameterRole(str, Enum):
    EVIDENCE_ONLY = "evidence_only"
    FIXED_PARAMETER = "fixed_parameter"
    BOUNDED_DESIGN_VARIABLE = "bounded_design_variable"
    DISCRETE_OPTION = "discrete_option"
    HARD_EQUALITY = "hard_equality"
    HARD_LOWER_BOUND = "hard_lower_bound"
    HARD_UPPER_BOUND = "hard_upper_bound"
    ACCEPTABLE_BAND = "acceptable_band"
    TARGET_VALUE = "target_value"
    TARGET_CURVE = "target_curve"
    DERIVED_OUTPUT = "derived_output"
    REPORT_ONLY = "report_only"


@dataclass(frozen=True)
class VariableDefinition:
    """One role-selectable scalar supported by the first geometry generator."""

    id: str
    role: ParameterRole
    unit: str
    reference: float
    minimum: float | None = None
    maximum: float | None = None
    coordinate_definition: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise RoleResolutionError("Variable id is required")
        if not self.unit:
            raise RoleResolutionError(f"Variable {self.id!r} requires an explicit unit")
        if not math.isfinite(self.reference):
            raise RoleResolutionError(f"Variable {self.id!r} reference must be finite")
        if self.role is ParameterRole.BOUNDED_DESIGN_VARIABLE:
            if self.minimum is None or self.maximum is None:
                raise RoleResolutionError(
                    f"Bounded variable {self.id!r} requires minimum and maximum"
                )
            if not math.isfinite(self.minimum) or not math.isfinite(self.maximum):
                raise RoleResolutionError(f"Variable {self.id!r} bounds must be finite")
            if self.minimum >= self.maximum:
                raise RoleResolutionError(f"Variable {self.id!r} has invalid bounds")
            if not self.minimum <= self.reference <= self.maximum:
                raise RoleResolutionError(
                    f"Variable {self.id!r} reference is outside its bounds"
                )
        elif self.role is ParameterRole.FIXED_PARAMETER:
            if self.minimum is not None and self.maximum is not None:
                if not self.minimum <= self.reference <= self.maximum:
                    raise RoleResolutionError(
                        f"Fixed variable {self.id!r} reference is outside documented bounds"
                    )
        else:
            raise RoleResolutionError(
                f"Variable {self.id!r} uses unsupported first-generator role {self.role.value!r}"
            )

    def validate_value(self, value: float, *, supplied: bool) -> float:
        value = float(value)
        if not math.isfinite(value):
            raise RoleResolutionError(f"Variable {self.id!r} must be finite")
        if self.role is ParameterRole.FIXED_PARAMETER:
            if supplied and not math.isclose(value, self.reference, rel_tol=0.0, abs_tol=1.0e-15):
                raise RoleResolutionError(
                    f"Variable {self.id!r} is fixed at {self.reference} {self.unit}"
                )
            return self.reference
        if self.minimum is None or self.maximum is None:
            raise RoleResolutionError(f"Variable {self.id!r} is missing bounds")
        if not self.minimum <= value <= self.maximum:
            raise RoleResolutionError(
                f"Variable {self.id!r}={value} {self.unit} lies outside "
                f"[{self.minimum}, {self.maximum}] {self.unit}"
            )
        return value


@dataclass(frozen=True)
class LocalFrameDefinition:
    """Explicit left-upright local directions for steering-arm pickup offsets."""

    u_direction: tuple[float, float, float]
    v_direction: tuple[float, float, float]
    depth_direction: tuple[float, float, float]
    authority: str
    origin_rule: str
    orthonormal_tolerance: float = 1.0e-12

    def __post_init__(self) -> None:
        vectors = {
            "u_direction": self.u_direction,
            "v_direction": self.v_direction,
            "depth_direction": self.depth_direction,
        }
        for name, vector in vectors.items():
            if len(vector) != 3 or not all(math.isfinite(component) for component in vector):
                raise RoleResolutionError(f"{name} must contain three finite values")
            magnitude = math.sqrt(sum(component * component for component in vector))
            if abs(magnitude - 1.0) > self.orthonormal_tolerance:
                raise RoleResolutionError(f"{name} must be a unit vector")
        u, v, depth = self.u_direction, self.v_direction, self.depth_direction
        dot_uv = sum(a * b for a, b in zip(u, v))
        dot_ud = sum(a * b for a, b in zip(u, depth))
        dot_vd = sum(a * b for a, b in zip(v, depth))
        if max(abs(dot_uv), abs(dot_ud), abs(dot_vd)) > self.orthonormal_tolerance:
            raise RoleResolutionError("Outer-pickup local-frame directions must be orthogonal")
        cross_uv = (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        )
        handedness = sum(a * b for a, b in zip(cross_uv, depth))
        if handedness < 1.0 - self.orthonormal_tolerance:
            raise RoleResolutionError(
                "Outer-pickup local frame must be right-handed with u cross v = depth"
            )


@dataclass(frozen=True)
class RequirementSet:
    """Parsed steering inverse-design requirement set."""

    id: str
    version: str
    baseline_configuration_id: str
    evaluator_model_id: str
    optimizer_model_id: str
    symmetry_mode: str
    independent_sides_enabled: bool
    variables: tuple[VariableDefinition, ...]
    item_roles: tuple[tuple[str, ParameterRole], ...]
    outer_pickup_frame: LocalFrameDefinition
    source_path: str

    @property
    def variable_map(self) -> dict[str, VariableDefinition]:
        return {variable.id: variable for variable in self.variables}

    @property
    def role_map(self) -> dict[str, ParameterRole]:
        roles = {variable.id: variable.role for variable in self.variables}
        roles.update(self.item_roles)
        return roles

    def variable(self, variable_id: str) -> VariableDefinition:
        try:
            return self.variable_map[variable_id]
        except KeyError as exc:
            raise RoleResolutionError(f"Unknown design variable {variable_id!r}") from exc


@dataclass(frozen=True)
class ResolvedCandidate:
    """Immutable, unit-explicit candidate values after role and bound checks."""

    candidate_id: str
    requirement_set_id: str
    values: tuple[tuple[str, float], ...]
    roles: tuple[tuple[str, ParameterRole], ...]
    units: tuple[tuple[str, str], ...]
    supplied_overrides: tuple[str, ...]

    @property
    def value_map(self) -> dict[str, float]:
        return dict(self.values)

    def value(self, variable_id: str) -> float:
        try:
            return self.value_map[variable_id]
        except KeyError as exc:
            raise RoleResolutionError(
                f"Resolved candidate does not contain variable {variable_id!r}"
            ) from exc


def _tuple3(value: object, *, name: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise RoleResolutionError(f"{name} must be a three-value TOML array")
    result = tuple(float(component) for component in value)
    if not all(math.isfinite(component) for component in result):
        raise RoleResolutionError(f"{name} must contain finite values")
    return result  # type: ignore[return-value]


def _parse_role(value: object, *, context: str) -> ParameterRole:
    try:
        return ParameterRole(str(value))
    except ValueError as exc:
        raise RoleResolutionError(f"{context} has unknown role {value!r}") from exc


def load_requirement_set(path: str | Path) -> RequirementSet:
    """Load and structurally validate the first inverse-design requirement set."""

    source_path = Path(path)
    with source_path.open("rb") as stream:
        document = tomllib.load(stream)

    requirement_set_id = str(document.get("requirement_set_id", ""))
    if not requirement_set_id:
        raise RoleResolutionError("requirement_set_id is required")
    vocabulary = document.get("role_vocabulary", {})
    allowed_values = set(vocabulary.get("allowed", []))
    known_values = {role.value for role in ParameterRole}
    unknown_allowed = allowed_values - known_values
    if unknown_allowed:
        raise RoleResolutionError(
            f"Requirement set declares unknown roles: {sorted(unknown_allowed)}"
        )

    variables: list[VariableDefinition] = []
    seen_ids: set[str] = set()
    for table in document.get("variables", []):
        variable_id = str(table.get("id", ""))
        if variable_id in seen_ids:
            raise RoleResolutionError(f"Duplicate variable id {variable_id!r}")
        seen_ids.add(variable_id)
        role = _parse_role(table.get("role"), context=f"Variable {variable_id!r}")
        if role.value not in allowed_values:
            raise RoleResolutionError(
                f"Variable {variable_id!r} role {role.value!r} is not allowed by the requirement set"
            )
        variables.append(
            VariableDefinition(
                id=variable_id,
                role=role,
                unit=str(table.get("unit", "")),
                reference=float(table.get("reference")),
                minimum=(float(table["minimum"]) if "minimum" in table else None),
                maximum=(float(table["maximum"]) if "maximum" in table else None),
                coordinate_definition=str(table.get("coordinate_definition", "")),
            )
        )

    item_roles: list[tuple[str, ParameterRole]] = []
    all_role_ids = set(seen_ids)
    for collection_name in ("items", "constraints"):
        for table in document.get(collection_name, []):
            item_id = str(table.get("id", ""))
            if not item_id:
                raise RoleResolutionError(f"{collection_name} entry requires an id")
            if item_id in all_role_ids:
                raise RoleResolutionError(f"Duplicate requirement item id {item_id!r}")
            all_role_ids.add(item_id)
            role = _parse_role(table.get("role"), context=f"Item {item_id!r}")
            item_roles.append((item_id, role))

    symmetry = document.get("symmetry", {})
    if str(symmetry.get("mode")) != "exact_reflection":
        raise RoleResolutionError("The first geometry generator requires exact_reflection symmetry")
    if bool(symmetry.get("independent_sides_enabled", False)):
        raise RoleResolutionError("Independent left/right variables are not authorized in this release")

    frame = document.get("outer_pickup_local_frame")
    if not isinstance(frame, dict):
        raise RoleResolutionError("[outer_pickup_local_frame] is required")
    local_frame = LocalFrameDefinition(
        u_direction=_tuple3(frame.get("u_direction"), name="u_direction"),
        v_direction=_tuple3(frame.get("v_direction"), name="v_direction"),
        depth_direction=_tuple3(frame.get("depth_direction"), name="depth_direction"),
        authority=str(frame.get("authority", "")),
        origin_rule=str(frame.get("origin_rule", "")),
        orthonormal_tolerance=float(frame.get("orthonormal_tolerance", 1.0e-12)),
    )

    return RequirementSet(
        id=requirement_set_id,
        version=str(document.get("version", "0")),
        baseline_configuration_id=str(document.get("baseline_configuration_id", "")),
        evaluator_model_id=str(document.get("evaluator_model_id", "")),
        optimizer_model_id=str(document.get("optimizer_model_id", "")),
        symmetry_mode="exact_reflection",
        independent_sides_enabled=False,
        variables=tuple(variables),
        item_roles=tuple(item_roles),
        outer_pickup_frame=local_frame,
        source_path=str(source_path),
    )


def resolve_candidate(
    requirement_set: RequirementSet,
    overrides: Mapping[str, float] | None = None,
    *,
    candidate_id: str = "REFERENCE",
) -> ResolvedCandidate:
    """Resolve candidate values without inferring or silently changing roles."""

    supplied = dict(overrides or {})
    variable_map = requirement_set.variable_map
    role_map = requirement_set.role_map
    unknown = set(supplied) - set(variable_map)
    if unknown:
        first = sorted(unknown)[0]
        known_role = role_map.get(first)
        if known_role is ParameterRole.DERIVED_OUTPUT:
            raise RoleResolutionError(
                f"{first!r} is a derived output and cannot be supplied independently"
            )
        if known_role is not None:
            raise RoleResolutionError(
                f"{first!r} has role {known_role.value!r} and is not a candidate scalar"
            )
        raise RoleResolutionError(f"Unknown candidate override {first!r}")

    resolved_values: list[tuple[str, float]] = []
    roles: list[tuple[str, ParameterRole]] = []
    units: list[tuple[str, str]] = []
    for variable in requirement_set.variables:
        was_supplied = variable.id in supplied
        proposed = supplied.get(variable.id, variable.reference)
        value = variable.validate_value(proposed, supplied=was_supplied)
        resolved_values.append((variable.id, value))
        roles.append((variable.id, variable.role))
        units.append((variable.id, variable.unit))

    return ResolvedCandidate(
        candidate_id=candidate_id,
        requirement_set_id=requirement_set.id,
        values=tuple(resolved_values),
        roles=tuple(roles),
        units=tuple(units),
        supplied_overrides=tuple(sorted(supplied)),
    )
