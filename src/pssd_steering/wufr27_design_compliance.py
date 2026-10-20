"""WUFR-27 *nominal design-source* steering compliance and projected wheel headings.

Composes the reviewed WUFR-26 SolidWorks rack-input relation, WUFR-27's exact
inherited nominal geometry, the existing opt-in prescribed-torque compliance
bridge, and the canonical Level E wheel-plane projection. Never promotes the
design study to installed/as-built transmission or torque authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import tomllib
from typing import Sequence

from .compliance import CircularSpan, ComplianceDefinitionError
from .compliance_bridge import (
    PrescribedTorqueInput, SteeringComplianceComparison, SteeringTransmission,
    evaluate_prescribed_torque_sweep,
)
from .config import load_geometry
from .core import GeometryError, SolverSettings, SteeringGeometry
from .projection import (
    WheelPlaneReference, projected_wheel_heading, reference_from_static_alignment,
)


@dataclass(frozen=True)
class Wufr27DesignSource:
    """Frozen nominal-design data with source role, not installed calibration."""

    geometry: SteeringGeometry
    transmission: SteeringTransmission
    left_reference: WheelPlaneReference
    right_reference: WheelPlaneReference
    evidence_role: str
    source_parameter_id: str


@dataclass(frozen=True)
class DesignSourceHeading:
    """Projected global-heading radians at the source-derived centred wheel plane."""

    rigid_total_rad: float | None
    loaded_total_rad: float | None
    rigid_incremental_rad: float | None
    loaded_incremental_rad: float | None
    unavailable_reason: str | None

    @property
    def delta_incremental_rad(self) -> float | None:
        if self.rigid_incremental_rad is None or self.loaded_incremental_rad is None:
            return None
        return self.loaded_incremental_rad - self.rigid_incremental_rad


@dataclass(frozen=True)
class Wufr27DesignSourceResponse:
    comparison: SteeringComplianceComparison
    left: DesignSourceHeading
    right: DesignSourceHeading


def load_wufr27_design_source(root: Path) -> Wufr27DesignSource:
    """Load and validate the *specific* source lineage, never arbitrary ratios.

    PAR-STEER-0001 is approved for the recovered WUFR-26 Design Study signal
    mapping only. WUFR-27 inherits its nominal geometry for development.
    Both statements are intentionally weaker than an as-built claim.
    """
    root = Path(root)
    source_path = root / "configurations/steering/WUFR26_DESIGN_NOMINAL_V0.toml"
    child_path = root / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
    with source_path.open("rb") as stream:
        source = tomllib.load(stream)
    with child_path.open("rb") as stream:
        child = tomllib.load(stream)
    if (source.get("configuration_id") != "WUFR26_DESIGN_NOMINAL_V0"
            or child.get("configuration_id") != "WUFR27_STEERING_BASELINE_V0"
            or child.get("inheritance", {}).get("source_path")
               != "configurations/steering/WUFR26_DESIGN_NOMINAL_V0.toml"
            or child.get("vehicle_revision") != "WUFR-27"):
        raise ComplianceDefinitionError("unexpected nominal steering-source identity")
    geo = load_geometry(child_path)
    if geo.geometry_id != "WUFR27_STEERING_BASELINE_V0":
        raise ComplianceDefinitionError("unexpected inherited steering geometry")
    if tuple(geo.rack.axis.direction) != (0.0, 1.0, 0.0):
        raise ComplianceDefinitionError("source-positive +y rack direction changed")
    native = source["input_transmission"]
    rack_per_rev = float(native["rack_travel_per_revolution_m"])
    rack_per_rad = float(native["rack_travel_per_input_radian_m"])
    # Exact dimensional consistency, not an authorization to infer pinion
    # conversion from an arbitrary, unreviewed design study.
    if (not math.isclose(rack_per_rev, .0889, abs_tol=1e-12)
            or not math.isclose(rack_per_rad, rack_per_rev / (2 * math.pi),
                                abs_tol=1e-12)
            or "+y" not in native["positive_sign"]
            or "1:1" not in native["source_signal_role"]):
        raise ComplianceDefinitionError("design-study transmission lineage changed")
    tr = SteeringTransmission(
        pinion_angle_per_input_rad=1.0,
        rack_m_per_pinion_rad=rack_per_rad,
        authority=(
            "PAR-STEER-0001 / WUFR26_DESIGN_NOMINAL_V0 "
            "SolidWorks Design Study 1, +input => canonical +y rack, "
            "nominal 1:1; inherited for WUFR-27 design-source only"
        ),
    )

    def reference(side: str) -> WheelPlaneReference:
        state = source[side]
        if state.get("wheel_plane_reference") != (
                "derive with reference_from_static_alignment and rotate the "
                "plane normal about the steering axis"):
            raise ComplianceDefinitionError("source wheel-plane projection contract changed")
        return reference_from_static_alignment(
            side,
            toe_out=float(state["static_toe"]),
            camber=float(state["static_camber"]),
            source_role=(
                "WUFR-26 nominal OptimumK alignment, inherited unchanged for "
                "WUFR-27 design-source; not physically installed"
            ),
        )

    return Wufr27DesignSource(
        geometry=geo,
        transmission=tr,
        left_reference=reference("left"),
        right_reference=reference("right"),
        evidence_role="nominal_design_source_not_installed_or_as_built",
        source_parameter_id="PAR-STEER-0001",
    )


def _project_side(
    source: Wufr27DesignSource,
    comparison: SteeringComplianceComparison,
    side: str,
) -> DesignSourceHeading:
    state = comparison.left if side == "left" else comparison.right
    if (not state.rigid_position.ok or not state.elastic_position.ok
            or state.rigid_position.upright_rotation is None
            or state.elastic_position.upright_rotation is None):
        return DesignSourceHeading(
            None, None, None, None,
            "rigid solver failed for at least one load state: "
            f"rigid={state.rigid_position.failure_code}; "
            f"loaded={state.elastic_position.failure_code}",
        )
    corner = source.geometry.left if side == "left" else source.geometry.right
    ref = source.left_reference if side == "left" else source.right_reference
    try:
        rt, ri = projected_wheel_heading(
            corner, ref, state.rigid_position.upright_rotation
        )
        lt, li = projected_wheel_heading(
            corner, ref, state.elastic_position.upright_rotation
        )
    except (GeometryError, ValueError) as exc:
        return DesignSourceHeading(None, None, None, None, str(exc))
    return DesignSourceHeading(rt, lt, ri, li, None)


def evaluate_wufr27_design_source_sweep(
    source: Wufr27DesignSource,
    cases: Sequence[PrescribedTorqueInput],
    *,
    spans: tuple[CircularSpan, ...],
    settings: SolverSettings | None = None,
) -> tuple[Wufr27DesignSourceResponse, ...]:
    """Compose real nominal WUFR design geometry and aligned plane projection.

    Input torques remain *prescribed* in the driver-angle frame. No tire moment
    or installation/calibration identity is supplied or implied.
    """
    if source.evidence_role != "nominal_design_source_not_installed_or_as_built":
        raise ComplianceDefinitionError("design-source evidence role must be explicit")
    comparisons = evaluate_prescribed_torque_sweep(
        source.geometry, cases, source.transmission, spans=spans, settings=settings
    )
    return tuple(
        Wufr27DesignSourceResponse(
            comparison=state,
            left=_project_side(source, state, "left"),
            right=_project_side(source, state, "right"),
        )
        for state in comparisons
    )
