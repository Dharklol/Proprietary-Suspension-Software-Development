# Engineering 3D scene contract v0.1.0

## Purpose

The 3D layer is an engineering visualization and debugging interface downstream of solved model states. It is not a second kinematics engine.

Architecture:

`reviewed physics -> EngineeringScene -> scene.json -> browser viewer`

The authoritative model remains the source of point positions and state diagnostics. The viewer can change camera, layer visibility, and selected state only.

## Scene schema

`pssd.engineering_scene/v0.1.0` contains:

- scene metadata and authority;
- named visualization layers;
- source-backed or explicitly display-only points;
- segments connecting named points;
- infinite-axis display primitives represented by a point, unit direction, and finite display half-length;
- ordered states containing point-coordinate overrides and scalar diagnostics.

Every primitive retains a full engineering label and may carry a compact standard symbol.

## State contract

A state includes a named independent display parameter such as rack displacement `x_r`, explicit point overrides produced by the upstream solver, and optional scalar readouts such as upright rotation `θ_u` and tie-rod closure residual `ΔL_tr`.

The viewer never interpolates engineering states or solves intermediate linkage positions. The slider selects one explicitly supplied state. Animation/interpolation may be added later only as a visually marked display operation between already-solved states and may not be used as engineering evidence by itself.

An infeasible state remains explicit. The viewer must display a failure warning rather than silently retaining a previous valid state as though it were solved.

## Steering proof-of-concept

The PR #37 steering scene contains only geometry that the current steering configuration can support without inventing an upstream suspension source:

- rack translation axis `e_r`;
- left/right rack inner joints `P_r,L`, `P_r,R`;
- left/right outer tie-rod joints `P_t,L`, `P_t,R`;
- tie-rod joint-centre segments `L_tr,L`, `L_tr,R`;
- left/right steering axes `k_s,L`, `k_s,R`;
- canonical body-axis orientation glyphs `x_B`, `y_B`, `z_B`;
- explicit rack states `x_r` through the reviewed nominal development range.

The outer-joint and rack-joint positions at each state come directly from `MOD-STEER-0001` solution results.

### Deliberate omissions

The prototype does **not** invent wheel centres, tire envelopes, wheel planes, suspension links, or chassis surfaces. The current steering configuration identifies wheel-centre and upright information conceptually but does not expose a reviewed point source suitable for this scene. Those objects should enter after `MOD-SUSP-0001` and the zero-steer suspension-pose provider exist.

The body-axis glyph is anchored at the rack-axis origin only to make the orientation visible. This anchor does not redefine the canonical body-frame origin.

## Browser viewer

`viewer.html` embeds `scene.json` data and uses a pinned Three.js module for rendering. Initial controls are intentionally small:

- named solved-state slider;
- top, front, side, and isometric camera presets;
- mouse orbit and zoom;
- layer visibility toggles;
- state scalar diagnostics;
- element legend using engineering terminology and symbols;
- explicit infeasible-state warning.

The browser viewer contains no tie-rod closure, tire, suspension, load-transfer, or vehicle-equilibrium equations.

## Dependency policy

The Python numerical packages remain independent of Three.js. Three.js is a browser dependency only; no JavaScript or WebGL dependency is introduced into the core Python runtime.

The prototype HTML pins Three.js `0.185.1` from jsDelivr. The scene data itself is embedded so no local server is required, but opening the HTML requires network access to that pinned JavaScript module. A later team-facing workbench may vendor frontend dependencies during a proper web build if offline use becomes a requirement.

## Evidence boundary

The scene JSON is reproducible machine-readable visualization evidence. The interactive camera view is an interpretation/debugging tool. Important design claims must still be backed by model reports and static figures rather than by a manually positioned screenshot alone.

The steering proof-of-concept remains nominal design-source evidence. It does not claim installed geometry, compliance, backlash, physical steering stops, wheel-centre location, or suspension motion.
