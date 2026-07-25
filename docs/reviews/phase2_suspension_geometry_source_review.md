# Phase 2 suspension geometry/source review

## Review scope

PR #38 establishes the first suspension-side R&D boundary after steering Phase 1. It reviews:

- the WUFR-26 final OptimumK suspension source identity;
- the complete front/rear double-wishbone hardpoint snapshot exposed by the Box text representation;
- the source-to-canonical orientation transform;
- explicit front/rear lateral-link roles;
- actuation hardpoint preservation;
- WUFR-27 baseline inheritance;
- the provider-neutral Python geometry contract;
- the boundary to the existing steering pose contract.

No suspension-motion equation, optimization, load transfer, compliance, wheel-center construction, or production geometry decision is reviewed here.

## Source review

`WUFR-26 FINAL 8.21.2025.xlsx` was re-located in Box and its current identity agrees with the previously cataloged steering evidence:

- file ID: `2014803790843`;
- file-version ID: `2224178574043`;
- provider SHA-1: `15eadfb93369192038888da92ebaa6674db56cfa`;
- size: `18692` bytes;
- path: `WashURacing / 6. WUFR-26 / WUFR-26 CAD AND DRAWINGS / 7. SUSPENSION / Geometry`.

The Box content representation exposes the vehicle setup, front/rear Double A-Arm tables, Push/Pull tables, wheel/setup values, and attachment roles. The PR38 snapshot transcribes those values exactly at source display precision.

Raw XLSX bytes could not be captured through the available Box download action, so no new raw-byte SHA-256 is claimed. The provider identity remains sufficient to freeze the exact Box version while the missing project SHA-256 remains explicit.

## Coordinate review

The source coordinate matrix and the previously reviewed steering-frame reconciliation agree:

```text
[x_can, y_can, z_can]_m = 0.001 * [x_optk, -y_optk, z_optk]_mm
```

Representative check:

```text
front-left UPRI_LowPnt source = [0.000, -587.096, 157.117] mm
front-left UPRI_LowPnt canonical = [0.000000, +0.587096, 0.157117] m
```

The explicit right-side source row converts independently to negative canonical `y`; the loader does not synthesize the right side by mirroring the left.

## Accepted geometry roles

The following source roles are accepted for the PR38 contract:

1. Upper/lower chassis pickups and upright joints are nominal rigid double-wishbone geometry inputs.
2. Front `CHAS_TiePnt`/`UPRI_TiePnt` are retained as source evidence but the link is classified as `steering_tie_rod`; front suspension motion must not use those OptimumK points to supersede the later steering-FDR geometry.
3. Rear `CHAS_TiePnt`/`UPRI_TiePnt` are classified as a `chassis_locating_toe_link`, matching the source's chassis attachment note.
4. Push/Pull hardpoints are preserved for future actuation/motion-ratio work but have no active equations in PR38.
5. Front Push/Pull attaches to the upper arm; rear Push/Pull attaches to the lower arm.
6. Static camber/toe and wheel dimensions are setup metadata, not a wheel-center construction rule.

## Accepted origin boundary

The front and rear suspension point sets remain axle/suspension-reference-local after orientation conversion. `Reference Distance = 1562.400 mm` is stored separately.

PR38 does not translate rear coordinates into the front reference frame. This avoids silently assuming a whole-vehicle origin relationship that the extracted source text does not state explicitly enough for model authority.

## Steering integration boundary

The already merged steering pose contract requires:

`upright_reference_pose_excludes_tie_rod_steering_rotation`

The future front suspension model must therefore provide a zero-steer upright reference pose and leave the steering-axis rotational DOF unresolved for `MOD-STEER-0001` to close with the actual steering tie rod.

This review does not yet choose the mathematical transport rule for that zero-steer reference. That rule belongs in the next equation/benchmark authorization.

## Disposition

The geometry/source contract is suitable for development use and regression as nominal WUFR-26/27 design-source evidence.

`MOD-SUSP-0001` remains **proposed / M0**. The next PR may implement rigid kinematics only after its independent coordinate, equations, branch rules, numerical behavior, zero-steer reference definition, failure states, and benchmarks are reviewed and frozen.

## Explicit non-claims

PR38 does not establish:

- as-built WUFR-26 or WUFR-27 hardpoints;
- installed symmetry or tolerances;
- wheel-center coordinates;
- bump/camber/toe curves;
- roll-center or instant-center outputs;
- spring/damper motion ratio;
- compliant kinematics;
- tire/load response;
- vehicle equilibrium;
- optimized suspension geometry.
