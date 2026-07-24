"""Downstream steering-to-scene adapter for the engineering 3D viewer.

This module calls the reviewed rigid steering evaluator and converts its solved point
positions into :mod:`pssd_viz.scene3d` primitives.  It does not implement a second
steering mechanism model.
"""

from __future__ import annotations

import math
from typing import Iterable

from pssd_steering.core import SteeringGeometry, solve_sweep

from .scene3d import (
    EngineeringScene,
    SceneAxis,
    SceneLayer,
    SceneMetadata,
    ScenePoint,
    SceneScalar,
    SceneSegment,
    SceneState,
)


def _add(a: tuple[float, float, float], b: tuple[float, float, float]):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a: tuple[float, float, float], scalar: float):
    return (a[0] * scalar, a[1] * scalar, a[2] * scalar)


def _state_id(displacement_m: float) -> str:
    millimetres = displacement_m * 1000.0
    if abs(millimetres) < 1.0e-12:
        return "rack_center"
    sign = "p" if millimetres > 0.0 else "m"
    magnitude = f"{abs(millimetres):.3f}".rstrip("0").rstrip(".").replace(".", "p")
    return f"rack_{sign}{magnitude}mm"


def build_steering_engineering_scene(
    geometry: SteeringGeometry,
    *,
    rack_displacements_m: Iterable[float] = (
        -0.0254,
        -0.01905,
        -0.0127,
        -0.00635,
        0.0,
        0.00635,
        0.0127,
        0.01905,
        0.0254,
    ),
    scene_id: str = "SCENE-STEER-WUFR27-V0",
) -> EngineeringScene:
    """Build a state-aware steering mechanism scene from ``MOD-STEER-0001`` results.

    ``x_r`` is the signed rack displacement along the declared rack axis.  Viewer
    geometry is limited to source-backed steering primitives available in the current
    steering configuration: rack joints, tie-rod joints, tie rods, rack axis, steering
    axes, and a body-axis orientation glyph.  Wheel centres and wheel planes are not
    invented here; they enter later through the suspension pose provider.
    """

    displacements = tuple(float(value) for value in rack_displacements_m)
    if not displacements:
        raise ValueError("rack_displacements_m cannot be empty")
    if 0.0 not in displacements:
        raise ValueError("steering scene requires the centered x_r = 0 state")
    if any(not math.isfinite(value) for value in displacements):
        raise ValueError("rack_displacements_m must be finite")
    if any(upper <= lower for lower, upper in zip(displacements, displacements[1:])):
        raise ValueError("rack_displacements_m must be strictly increasing")

    solved = solve_sweep(geometry, displacements)
    center_index = displacements.index(0.0)
    left_center = solved["left"][center_index]
    right_center = solved["right"][center_index]
    if not left_center.ok or not right_center.ok:
        raise RuntimeError("centered steering state is infeasible and cannot seed the viewer")
    assert left_center.rack_inner_joint is not None
    assert right_center.rack_inner_joint is not None
    assert left_center.rotated_outer_joint is not None
    assert right_center.rotated_outer_joint is not None

    source_path = geometry.metadata.get("source_path", "unknown")
    inherited_source = geometry.metadata.get("inherited_source_path")
    source_ids = tuple(
        item for item in (source_path, inherited_source) if item is not None and item != "unknown"
    )

    layers = (
        SceneLayer("body_frame", "Body-frame orientation", True),
        SceneLayer("rack", "Rack and inboard joints", True),
        SceneLayer("tie_rods", "Tie rods and outboard joints", True),
        SceneLayer("steering_axes", "Steering axes", True),
    )

    frame_origin = geometry.rack.axis.point
    frame_scale = 0.12
    frame_x = _add(frame_origin, (frame_scale, 0.0, 0.0))
    frame_y = _add(frame_origin, (0.0, frame_scale, 0.0))
    frame_z = _add(frame_origin, (0.0, 0.0, frame_scale))

    points = (
        ScenePoint(
            "BODY_AXIS_ORIGIN",
            "Body-axis display origin",
            frame_origin,
            "body_frame",
            symbol="O_B*",
            source_role="display_anchor_only_at_rack_axis_origin",
        ),
        ScenePoint("BODY_X_TIP", "+x body-axis glyph", frame_x, "body_frame", symbol="x_B"),
        ScenePoint("BODY_Y_TIP", "+y body-axis glyph", frame_y, "body_frame", symbol="y_B"),
        ScenePoint("BODY_Z_TIP", "+z body-axis glyph", frame_z, "body_frame", symbol="z_B"),
        ScenePoint(
            "RACK_IN_L",
            "Left rack inner joint",
            left_center.rack_inner_joint,
            "rack",
            symbol="P_r,L",
            source_role=geometry.left.source_role,
        ),
        ScenePoint(
            "RACK_IN_R",
            "Right rack inner joint",
            right_center.rack_inner_joint,
            "rack",
            symbol="P_r,R",
            source_role=geometry.right.source_role,
        ),
        ScenePoint(
            "TIEROD_OUT_L",
            "Left outer tie-rod joint",
            left_center.rotated_outer_joint,
            "tie_rods",
            symbol="P_t,L",
            source_role=geometry.left.source_role,
        ),
        ScenePoint(
            "TIEROD_OUT_R",
            "Right outer tie-rod joint",
            right_center.rotated_outer_joint,
            "tie_rods",
            symbol="P_t,R",
            source_role=geometry.right.source_role,
        ),
    )

    segments = (
        SceneSegment(
            "BODY_X",
            "+x body axis",
            "BODY_AXIS_ORIGIN",
            "BODY_X_TIP",
            "body_frame",
            symbol="x_B",
            render_kind="arrow",
            source_role="canonical_axis_orientation_glyph",
        ),
        SceneSegment(
            "BODY_Y",
            "+y body axis",
            "BODY_AXIS_ORIGIN",
            "BODY_Y_TIP",
            "body_frame",
            symbol="y_B",
            render_kind="arrow",
            source_role="canonical_axis_orientation_glyph",
        ),
        SceneSegment(
            "BODY_Z",
            "+z body axis",
            "BODY_AXIS_ORIGIN",
            "BODY_Z_TIP",
            "body_frame",
            symbol="z_B",
            render_kind="arrow",
            source_role="canonical_axis_orientation_glyph",
        ),
        SceneSegment(
            "RACK_SPAN",
            "Rack inner-joint span",
            "RACK_IN_R",
            "RACK_IN_L",
            "rack",
            symbol="rack",
        ),
        SceneSegment(
            "TIEROD_L",
            "Left tie rod",
            "RACK_IN_L",
            "TIEROD_OUT_L",
            "tie_rods",
            symbol="L_tr,L",
        ),
        SceneSegment(
            "TIEROD_R",
            "Right tie rod",
            "RACK_IN_R",
            "TIEROD_OUT_R",
            "tie_rods",
            symbol="L_tr,R",
        ),
    )

    axes = (
        SceneAxis(
            "RACK_AXIS",
            "Rack translation axis",
            geometry.rack.axis.point,
            geometry.rack.axis.direction,
            0.38,
            "rack",
            symbol="e_r",
            source_role="reviewed_rack_axis",
        ),
        SceneAxis(
            "STEERING_AXIS_L",
            "Left steering axis",
            geometry.left.steering_axis.point,
            geometry.left.steering_axis.direction,
            0.19,
            "steering_axes",
            symbol="k_s,L",
            source_role=geometry.left.source_role,
        ),
        SceneAxis(
            "STEERING_AXIS_R",
            "Right steering axis",
            geometry.right.steering_axis.point,
            geometry.right.steering_axis.direction,
            0.19,
            "steering_axes",
            symbol="k_s,R",
            source_role=geometry.right.source_role,
        ),
    )

    states: list[SceneState] = []
    for index, displacement in enumerate(displacements):
        left = solved["left"][index]
        right = solved["right"][index]
        valid = left.ok and right.ok
        message = ""
        overrides: list[tuple[str, tuple[float, float, float]]] = []
        scalars: list[SceneScalar] = []
        if valid:
            assert left.rack_inner_joint is not None
            assert right.rack_inner_joint is not None
            assert left.rotated_outer_joint is not None
            assert right.rotated_outer_joint is not None
            assert left.upright_rotation is not None
            assert right.upright_rotation is not None
            overrides.extend(
                (
                    ("RACK_IN_L", left.rack_inner_joint),
                    ("RACK_IN_R", right.rack_inner_joint),
                    ("TIEROD_OUT_L", left.rotated_outer_joint),
                    ("TIEROD_OUT_R", right.rotated_outer_joint),
                )
            )
            scalars.extend(
                (
                    SceneScalar(
                        "Left upright rotation",
                        "θ_u,L",
                        math.degrees(left.upright_rotation),
                        "deg",
                    ),
                    SceneScalar(
                        "Right upright rotation",
                        "θ_u,R",
                        math.degrees(right.upright_rotation),
                        "deg",
                    ),
                    SceneScalar(
                        "Left tie-rod closure residual",
                        "ΔL_tr,L",
                        (left.closure_length_residual or 0.0) * 1.0e6,
                        "µm",
                    ),
                    SceneScalar(
                        "Right tie-rod closure residual",
                        "ΔL_tr,R",
                        (right.closure_length_residual or 0.0) * 1.0e6,
                        "µm",
                    ),
                )
            )
        else:
            failures = []
            for result in (left, right):
                if not result.ok:
                    code = result.failure_code.value if result.failure_code is not None else "failure"
                    failures.append(f"{result.side}: {code}: {result.message}")
            message = " | ".join(failures)

        states.append(
            SceneState(
                state_id=_state_id(displacement),
                label=f"x_r = {displacement * 1000.0:+.2f} mm",
                parameter_label="Rack displacement",
                parameter_symbol="x_r",
                parameter_value=displacement * 1000.0,
                parameter_unit="mm",
                point_overrides=tuple(overrides),
                scalars=tuple(scalars),
                status="valid" if valid else "infeasible",
                message=message,
            )
        )

    return EngineeringScene(
        metadata=SceneMetadata(
            scene_id=scene_id,
            title="WUFR-27 Rigid Steering Mechanism Viewer",
            frame_id="CANONICAL_ISO8855_BODY",
            length_unit="m",
            axis_convention="+x forward, +y vehicle left, +z upward; right-handed",
            configuration_id=geometry.geometry_id,
            model_id="MOD-STEER-0001",
            authority=(
                "nominal design-source rigid steering visualization; not installed/as-built authority"
            ),
            source_ids=source_ids,
            notes=(
                "The body-axis glyph is anchored at the rack-axis origin for display only; it does not redefine the body-frame origin.",
                "Wheel centres and wheel planes are intentionally omitted because the current steering configuration does not carry a reviewed point source for them.",
                "Tie-rod and joint motion comes directly from MOD-STEER-0001 solved states; the viewer performs no closure calculation.",
            ),
        ),
        layers=layers,
        points=points,
        segments=segments,
        axes=axes,
        states=tuple(states),
    )
