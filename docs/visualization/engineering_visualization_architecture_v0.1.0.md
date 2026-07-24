# Engineering Visualization Architecture v0.1.0

## Purpose

The visualization layer exists to make model outputs easier to verify, review, and communicate without creating a second implementation of the physics.

The architectural rule is:

`physics/result provider -> visualization data contract -> static report or interactive viewer`

The visualization package may format, label, compare, and render values already supplied by an upstream result. It may not solve steering closure, calculate suspension motion, interpolate a tire, generate vehicle equilibrium, infer missing state values, or silently repair unavailable data.

## Package boundary

`pssd_viz` is provider-neutral and downstream of the engineering packages. Importing the base package has no third-party plotting dependency. Static rendering is optional through the `viz` project extra and the Matplotlib-backed renderer.

The first contract is `EngineeringFigureSpec`:

- `FigureMetadata` carries figure identity, quantity names/units, model/configuration identity, state IDs, source IDs, authority, and notes;
- `SeriesSpec` carries already-computed finite x/y values;
- `FigureAvailability` distinguishes a renderable result from an explicitly unavailable result;
- `EngineeringFigureSpec.fingerprint()` hashes the complete canonical render request.

The renderer accepts this contract only. Model-specific adapters belong in later subsystem figure suites rather than in the renderer.

## Authoritative static format

SVG is the preferred engineering-review format because labels and line work remain vector-readable in PDR/FDR documents. PNG is generated as a convenience format for systems that do not handle SVG well.

Static artifacts carry a sidecar JSON manifest containing:

- the canonical figure contract;
- its SHA-256 fingerprint;
- rendered artifact paths, sizes, formats, and SHA-256 digests.

Report manifests group figure manifests without copying model values into another hand-maintained document.

## Missing-data behavior

A requested figure must never become a blank image merely because the required result is absent. When a source result is unavailable, the caller constructs an `UNAVAILABLE` figure with an explicit reason. The renderer produces a visible `FIGURE UNAVAILABLE` diagnostic page with the same model/configuration/source metadata footer.

Examples include:

- no reviewed planar-motion schedule supplied;
- requested tire point outside the source-supported domain;
- no canonical zero-steer suspension pose available;
- benchmark report missing the requested result field.

The visualization layer does not infer replacement values.

## Determinism

The Matplotlib renderer uses the headless Agg backend, fixed SVG hash salt, fixed static image metadata, fixed figure dimensions, and no wall-clock timestamps in generated files. The figure contract fingerprint and artifact hashes allow CI to identify exactly what was rendered.

No project-specific color meaning is frozen in this foundation. Multiple series are distinguished using labels and line styles while allowing the plotting backend's default color cycle. Semantic color policy can be added later if the team establishes one.

## Optional dependency rule

Matplotlib is intentionally not a core runtime dependency. Core registry, steering, tire, and vehicle calculations continue to install with `pip install -e .`. Rendering uses:

`pip install -e '.[viz]'`

CI has a separate visualization workflow that installs this extra, runs visualization tests, renders both a valid figure and an unavailable-data diagnostic, and uploads the generated SVG/PNG/manifest package.

## Relationship to the future 3D viewer

Static reporting and the future 3D viewer share the same boundary: both consume explicit visualization contracts downstream of solved physics.

The planned 3D layer will use a separate scene contract containing engineering primitives such as named points, segments, planes, reference frames, polylines, state transforms, and source metadata. It should not consume internal solver objects directly. A browser viewer can then render the scene JSON without introducing Three.js or other web dependencies into the numerical packages.

The static plot layer remains the engineering-evidence path even after the interactive viewer exists. The viewer is for exploration and debugging; review-critical results must remain reproducible as static artifacts.

## PR 35 scope

PR 35 establishes only the visualization foundation:

1. provider-neutral figure contracts and validation;
2. deterministic spec fingerprinting;
3. optional headless Matplotlib rendering;
4. SVG/PNG artifact generation;
5. explicit unavailable-data rendering;
6. artifact and report manifests with SHA-256 hashes;
7. isolated visualization CI with a synthetic smoke report.

No steering-specific PDR figure suite, subsystem result adapter, 3D scene schema, Three.js viewer, GUI, or new engineering physics is included. Those are intentionally separate follow-on increments.
