# Steering Geometry Generator Implementation v0.1.0

**Model:** `MOD-STEER-0002`  
**Authorization:** `AUTH-STEER-0002`  
**Task:** `P1-STR-002`  
**Status:** Implemented for review in PR #21

## 1. Purpose and boundary

This release implements the role resolver and parametric geometry generator that sit immediately upstream of the existing rigid steering analyzer. It does not implement optimization search, objective scoring, candidate ranking, tire or effort models, suspension-state evaluation, tolerance propagation, or production design selection.

`MOD-STEER-0001` remains the sole authority for rigid steering closure, branch identity, singularity diagnostics, wheel-plane projection, steering gains and ratios, Ackermann quantities, and turning-path quantities. The generator only resolves configuration roles, applies declared coordinate transforms, derives reference tie-rod lengths, constructs the existing `SteeringGeometry` contract, and asks the analyzer to verify the centered state.

## 2. Implementation structure

| File | Responsibility |
|---|---|
| `src/pssd_steering/optimization/roles.py` | Parse the named requirement set, validate role vocabulary, validate variable references and bounds, and resolve immutable candidate values. |
| `src/pssd_steering/optimization/geometry.py` | Apply the authorized symmetric geometry transforms, derive tie-rod lengths, construct `SteeringGeometry`, and preflight the reference state through `solve_corner_position`. |
| `src/pssd_steering/config.py` | Load direct steering geometry or exact source-preserving inherited baseline configurations. |
| `configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml` | Define development variables, roles, broad non-authoritative bounds, exact symmetry, and the explicit outer-pickup local frame. |
| `tests/test_steering_geometry_generator.py` | Freeze zero-offset reconstruction, role switching, reflection, depth bounds, derived-length behavior, invalid-candidate rejection, and analyzer composition. |

## 3. Role resolution

Each scalar supported by the first generator is represented by a `VariableDefinition`. The role comes from the requirement set rather than from the Python field location. The current implementation accepts:

- `bounded_design_variable`, with finite minimum, reference, and maximum values;
- `fixed_parameter`, which returns its reference and rejects a different supplied value.

Other roles remain valid in the requirement schema but are not silently interpreted as candidate scalars. Derived outputs, constraints, targets, report-only values, and evidence cannot be supplied through the candidate override map. A later requirement set may therefore change outer-pickup depth or another supported scalar from variable to fixed without changing the geometry generator.

All current candidate values use the explicit units declared by the requirement set. No implicit unit conversion is performed in this release.

## 4. Baseline inheritance

`WUFR27_STEERING_BASELINE_V0` inherits the complete numerical geometry from `WUFR26_DESIGN_NOMINAL_V0`. The loader follows the declared source path, loads the source geometry once, and changes only the named configuration identity, version, and provenance metadata. It does not copy or override hardpoints.

The zero-offset generator benchmark therefore tests two separate requirements:

1. the WUFR-27 baseline is numerically identical to the frozen WUFR-26 source geometry;
2. a reference candidate generated from the WUFR-27 baseline is numerically identical to that baseline.

This keeps current-car grounding data separate from future generated candidates while preventing duplicated baseline coordinates from drifting.

## 5. Parametric geometry

For the first symmetric nominal-height release, the resolved candidate is

```text
q = [
    rack_longitudinal_offset,
    rack_vertical_offset,
    rack_inner_joint_half_spacing,
    outer_pickup_local_u_offset,
    outer_pickup_local_v_offset,
    outer_pickup_local_depth_offset
]
```

The steering axes, wheel centers, upright poses, suspension hardpoints, rack-axis direction, wheelbase, steering-axis track definition, rack travel, and static alignment remain fixed.

### 5.1 Rack transform

The rack-axis origin is translated only in body `x` and `z`:

```text
a_r,new = a_r,baseline + [dx_r, 0, dz_r]
```

The first release requires the reviewed lateral `+y` rack-axis direction. The generated reference inner joints are

```text
p_in,L = a_r,new + h e_r
p_in,R = reflect_y(p_in,L)
```

where `h` is the positive inner-joint half-spacing and `reflect_y([x,y,z]) = [x,-y,z]`.

### 5.2 Outer-pickup transform

The development requirement set declares an explicit nominal left-upright local frame. Its current basis is

```text
u = body +x
v = body +z
depth = body -y on the left side
```

with `u cross v = depth`. This is a workflow-development frame, not a measured steering-arm surface or packaging authority. The left pickup is

```text
p_out,L = p_out,L,baseline + du u + dv v + dd depth
```

and the right pickup is generated by exact center-plane reflection. The depth variable remains restricted to `+/-5 mm`; a requirement set may make it fixed without modifying this implementation.

A later reviewed upright or CAD adapter may supply a different explicit local frame through the same contract.

### 5.3 Derived tie-rod length

For each side, reference tie-rod joint-center length is derived as

```text
L_j = norm(p_out,j - p_in,j)
```

The role resolver rejects a separately supplied left or right tie-rod length. This prevents arbitrary joint coordinates and an inconsistent independent length from entering the analyzer together.

## 6. Symmetry and preflight

Before generation, the baseline is checked for the exact design-model reflection required by the authorization. The checks cover:

- rack-axis location and direction;
- steering-axis points and directions;
- rack inner joints;
- outer tie-rod joints;
- wheel-forward basis availability and reflection where present;
- side-local static-toe equality;
- reflected source-role declaration.

After construction, the reference closure length residual is checked for each side. The generator then calls the existing `solve_corner_position` analyzer function at centered rack displacement. A missing branch, branch ambiguity, near-singular centered state, or other analyzer failure is returned as `CandidateGeometryError` before any later sweep or search can begin.

The generator contains no copy of the tie-rod closure equation, root solver, branch rule, or singularity calculation.

## 7. Verification

`tests/test_steering_geometry_generator.py` covers:

| Test family | Acceptance behavior |
|---|---|
| Baseline inheritance | WUFR-27 and WUFR-26 numerical steering geometry are identical. |
| Zero-offset reconstruction | Generated reference geometry matches the WUFR-27 baseline to numerical precision. |
| Coordinate transforms | Rack and outer-pickup changes follow the declared body and local frames. |
| Reflection | Right geometry is the exact body-`y` reflection of the generated left geometry. |
| Tie-rod derivation | Reported length equals joint-center distance on each side and is equal under reflection. |
| Role switching | Outer-pickup depth can change from bounded variable to fixed without generator changes. |
| Bounds | A depth value outside the explicit `+/-5 mm` development range is rejected. |
| Double specification | Supplying a derived tie-rod length is rejected. |
| Invalid geometry | An asymmetric baseline is rejected before an analyzer sweep. |
| Analyzer composition | Centered preflight calls the existing analyzer once per side. |

The repository registry validation, full unit-test suite, and existing WUFR-26 Level E report generation passed on the implementation branch before review.

## 8. Authority and limitations

The broad rack and in-plane pickup bounds are mathematical and workflow-development bounds only. Passing this generator means that a candidate is structurally representable and has a valid centered rigid mechanism state under the current analyzer. It does not establish:

- closure over the full rack range;
- monotonic response over the full sweep;
- articulation or thread engagement;
- wheel, brake, upright, chassis, or rack clearance;
- physical steering-arm feasibility;
- manufacturing feasibility;
- tire-informed quality;
- steering effort;
- robustness or as-built performance.

Those checks enter through the constrained-search and constraint-report stages authorized later in `AUTH-STEER-0002` or through separate higher-fidelity authorizations.

## 9. Literature continuity

No new steering-physics equation is introduced here. Generated candidates use the exact rigid analyzer whose equation records retain the steering-geometry basis from Guiggiani Chapter 3 and Gillespie Chapter 8. The generator/analyzer separation also follows the staged model-comparison and validation logic documented from Romano. The explicit distinction between target achievement and physical feasibility follows the Huang et al. development lesson recorded in the literature concordance.

The next implementation must preserve this separation while adding deterministic target recovery and constrained search around the same analyzer and generated-geometry contracts.
