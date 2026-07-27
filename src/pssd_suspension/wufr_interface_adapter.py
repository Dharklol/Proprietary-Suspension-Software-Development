"""Source-preserving adapter from reviewed WUFR kinematic states to Level-1 statics geometry.

The adapter deliberately does not solve steering. Front lateral-link endpoints
must be supplied by the current MOD-STEER-0001 closure. Rear toe-link endpoints
may be reconstructed from the already-reviewed rear upright/toe closure because
that closure is owned by MOD-SUSP-0001.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .actuation import ActuationStateResult
from .geometry import Axle, Point3, SuspensionCornerGeometry, ToeLinkRole
from .kinematics import SuspensionCornerStateResult
from .wufr_interface_statics import Level1CornerGeometry


class WufrInterfaceAdapterError(ValueError):
    pass


@dataclass(frozen=True)
class CurrentLateralLinkState:
    """Explicit current lateral-link geometry and source ownership."""

    body_point_m: Point3
    remote_point_m: Point3
    source_id: str

    def __post_init__(self) -> None:
        if not self.source_id:
            raise WufrInterfaceAdapterError("Current lateral-link state requires source_id")
        if not _finite3(self.body_point_m) or not _finite3(self.remote_point_m):
            raise WufrInterfaceAdapterError("Current lateral-link endpoints must be finite")
        if math.dist(self.body_point_m, self.remote_point_m) <= 1.0e-12:
            raise WufrInterfaceAdapterError("Current lateral-link endpoints are coincident")


def _finite3(point: Point3) -> bool:
    return len(point) == 3 and all(math.isfinite(float(value)) for value in point)


def _midpoint(a: Point3, b: Point3) -> Point3:
    return ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5, (a[2] + b[2]) * 0.5)


def _sub(a: Point3, b: Point3) -> Point3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _unit(vector: Point3) -> Point3:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if not math.isfinite(magnitude) or magnitude <= 1.0e-12:
        raise WufrInterfaceAdapterError("A-arm fore/aft pickups define a degenerate hinge axis")
    return tuple(value / magnitude for value in vector)  # type: ignore[return-value]


def _normalize_owner(owner: str) -> str:
    if owner in ("upper", "upper_arm", "upper_a_arm"):
        return "upper_a_arm"
    if owner in ("lower", "lower_arm", "lower_a_arm"):
        return "lower_a_arm"
    raise WufrInterfaceAdapterError("Actuation state does not declare a recognized owning arm")


def build_level1_geometry_from_current_states(
    corner: SuspensionCornerGeometry,
    suspension_state: SuspensionCornerStateResult,
    actuation_state: ActuationStateResult,
    *,
    front_lateral_state: CurrentLateralLinkState | None = None,
    geometry_source_id: str = "WUFR27_LEVEL1_LINKAGE_TOPOLOGY_V0",
) -> Level1CornerGeometry:
    """Build one source-bounded current Level-1 statics geometry record.

    Front steering remains owned by MOD-STEER-0001, so a front corner requires an
    explicit ``CurrentLateralLinkState`` carrying tie-rod points from that closure.
    Rear toe geometry is already closed by MOD-SUSP-0001 and is reconstructed
    from ``suspension_state.upright_transform``.
    """

    if corner.axle is not suspension_state.axle or corner.side is not suspension_state.side:
        raise WufrInterfaceAdapterError("Corner and suspension state identities do not match")
    if corner.axle.value != actuation_state.axle.value or corner.side.value != actuation_state.side:
        raise WufrInterfaceAdapterError("Corner and actuation state identities do not match")
    if not suspension_state.ok:
        raise WufrInterfaceAdapterError(suspension_state.message or "Suspension state is unavailable")
    if not actuation_state.ok:
        raise WufrInterfaceAdapterError(actuation_state.message or "Actuation state is unavailable")
    if not geometry_source_id:
        raise WufrInterfaceAdapterError("geometry_source_id is required")
    if not suspension_state.configuration_id or not actuation_state.configuration_id:
        raise WufrInterfaceAdapterError("Suspension and actuation states require configuration provenance")
    if suspension_state.configuration_id != actuation_state.configuration_id:
        raise WufrInterfaceAdapterError("Suspension and actuation state configuration IDs do not match")
    if suspension_state.upper_upright_m is None or suspension_state.lower_upright_m is None:
        raise WufrInterfaceAdapterError("Current upper/lower upright joint centers are unavailable")
    if actuation_state.arm_attachment_m is None or actuation_state.rocker_rod_point_m is None:
        raise WufrInterfaceAdapterError("Current arm/rocker push-pull endpoints are unavailable")

    wishbone = corner.wishbone
    upper_fore = wishbone.upper_fore_inboard.position_m
    upper_aft = wishbone.upper_aft_inboard.position_m
    lower_fore = wishbone.lower_fore_inboard.position_m
    lower_aft = wishbone.lower_aft_inboard.position_m
    upper_hinge_point = _midpoint(upper_fore, upper_aft)
    lower_hinge_point = _midpoint(lower_fore, lower_aft)
    upper_hinge_axis = _unit(_sub(upper_aft, upper_fore))
    lower_hinge_axis = _unit(_sub(lower_aft, lower_fore))

    upper_joint = suspension_state.upper_upright_m
    lower_joint = suspension_state.lower_upright_m
    carrier_reference = _midpoint(upper_joint, lower_joint)

    if corner.axle is Axle.FRONT:
        if corner.toe_link.role is not ToeLinkRole.STEERING_TIE_ROD:
            raise WufrInterfaceAdapterError("Front corner does not carry the reviewed steering tie-rod role")
        if front_lateral_state is None:
            raise WufrInterfaceAdapterError(
                "Front Level-1 geometry requires current MOD-STEER-0001 tie-rod endpoints; nominal suspension toe points are not substituted"
            )
        lateral = front_lateral_state
        if "steer" not in lateral.source_id.lower() and "mod-steer-0001" not in lateral.source_id.lower():
            raise WufrInterfaceAdapterError("Front lateral-link source must identify the current steering closure")
    else:
        if corner.toe_link.role is not ToeLinkRole.CHASSIS_LOCATING_TOE_LINK:
            raise WufrInterfaceAdapterError("Rear corner does not carry the reviewed chassis-locating toe-link role")
        if front_lateral_state is not None:
            raise WufrInterfaceAdapterError("Rear toe-link geometry is owned by MOD-SUSP-0001; do not inject a front steering state")
        if suspension_state.upright_transform is None:
            raise WufrInterfaceAdapterError("Rear current upright/toe transform is unavailable")
        lateral = CurrentLateralLinkState(
            body_point_m=suspension_state.upright_transform.apply_point(corner.toe_link.outboard.position_m),
            remote_point_m=corner.toe_link.inboard.position_m,
            source_id="MOD-SUSP-0001:rear_toe_link_current",
        )

    expected_owner = "upper_a_arm" if corner.axle is Axle.FRONT else "lower_a_arm"
    normalized_owner = _normalize_owner(actuation_state.owning_arm)
    if normalized_owner != expected_owner:
        raise WufrInterfaceAdapterError(
            f"{corner.axle.value} actuation ownership must remain {expected_owner}; got {normalized_owner}"
        )

    return Level1CornerGeometry(
        axle=corner.axle.value,
        side=corner.side.value,
        frame_id="WUFR26_OPTIMUMK_SUSPENSION_CANONICAL_AXLE_LOCAL",
        configuration_id=suspension_state.configuration_id,
        geometry_source_id=geometry_source_id,
        carrier_reference_m=carrier_reference,
        upper_arm_reference_m=upper_hinge_point,
        lower_arm_reference_m=lower_hinge_point,
        upper_hinge_point_m=upper_hinge_point,
        upper_hinge_axis_unit=upper_hinge_axis,
        lower_hinge_point_m=lower_hinge_point,
        lower_hinge_axis_unit=lower_hinge_axis,
        upper_spherical_point_m=upper_joint,
        lower_spherical_point_m=lower_joint,
        lateral_body_point_m=lateral.body_point_m,
        lateral_remote_point_m=lateral.remote_point_m,
        lateral_source_id=lateral.source_id,
        actuation_body_point_m=actuation_state.arm_attachment_m,
        actuation_remote_point_m=actuation_state.rocker_rod_point_m,
        actuation_owner=expected_owner,
        actuation_source_id="MOD-SUSP-0003:current_push_pull_geometry",
    )
