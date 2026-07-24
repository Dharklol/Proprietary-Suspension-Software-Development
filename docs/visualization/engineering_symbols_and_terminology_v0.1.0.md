# Engineering visualization terminology and symbols v0.1.0

## Purpose

Exported figures, images, and interactive viewer labels should use standard vehicle-dynamics terminology and conventional engineering symbols wherever the model quantity supports them. A symbol supplements the repository quantity definition; it never replaces source identity or silently changes a signal's meaning.

Preferred label form:

`Engineering quantity, symbol [unit]`

Examples:

- `Rack displacement, x_r [mm]`
- `Road-wheel steer angle, δ_L [deg]`
- `Slip angle, α [deg]`
- `Lateral tire force, F_y [N]`

## Canonical symbols

| Quantity | Preferred symbol | Visualization rule |
| --- | --- | --- |
| canonical body axes | `x_B`, `y_B`, `z_B` | retain `+x` forward, `+y` vehicle left, `+z` upward |
| rack displacement | `x_r` | signed translation along the declared rack axis |
| left/right road-wheel steer angle | `δ_L`, `δ_R` | use for the canonical road-wheel heading/steer quantity only with the configuration/reference state stated |
| generic road-wheel steer angle | `δ` | use when side does not need to be distinguished |
| design-study steering/pinion input angle | `δ_in` | do **not** relabel as steering-wheel angle unless the source is physically the steering wheel |
| steering-wheel angle | `δ_SW` | reserved for a source/measurement explicitly defined at the steering wheel |
| tire slip angle | `α` | preserve the source sign convention in metadata |
| lateral tire force | `F_y` | use `|F_y|` when a magnitude branch is intentionally plotted |
| tire normal load | `F_z` | use positive-normal-load convention only when the underlying provider does |
| camber / inclination angle | `γ` | retain source wording such as `IA` in provenance when applicable |
| tire inflation pressure | `p` | include absolute/gauge convention if it matters to the source |
| aligning moment | `M_z` | preserve source sign convention |
| longitudinal/lateral body velocity | `u`, `v` | body-frame components |
| yaw rate | `r` | positive by the declared body-frame right-hand convention |
| upright rotation used by the rigid mechanism solver | `θ_u,L`, `θ_u,R` | internal mechanism state; do not automatically call this road-wheel steer angle |
| tie-rod joint-centre length | `L_tr,L`, `L_tr,R` | rigid joint-centre distance |
| tie-rod closure length residual | `ΔL_tr,L`, `ΔL_tr,R` | report with an appropriately small length unit |
| longitudinal velocity-centre position | `S` | retain the explicit reference/coordinate convention |

## Naming rules

1. Prefer `steer angle`, `slip angle`, `normal load`, `lateral tire force`, `aligning moment`, `rack displacement`, and similarly standard terms over internal software names in titles and axes.
2. Preserve repository-specific definitions in notes/metadata when a common term is only an approximation to the software quantity. For example, the steering evaluator's canonical output remains the centered projected road-wheel heading defined by the steering contract.
3. Never call the design-study `Steer Input` signal `δ_SW` merely because an old source described a 1:1 steering-wheel relation. Installed transmission remains unverified.
4. Use left/right subscripts when the distinction matters. Use inside/outside only after turn direction has been assigned for that state.
5. Use magnitude notation explicitly (`|α|`, `|F_y|`) for the magnitude-only pre-peak tire branch contract.
6. Do not publish an unlabeled `Ackermann %`. Prefer inside/outside steer-angle split or the explicitly defined Ackermann reference/error quantities unless a normalized coefficient receives its own reviewed definition.
7. Units remain explicit on axes and scalar readouts even when a symbol is standard.
8. Source or authority labels may retain the source's own names (`IA`, `Steer Input`, etc.) so the engineering display remains traceable.

## Static and interactive consistency

Static SVG/PNG reports and the interactive 3D viewer should share the same terminology. The viewer may use compact symbols in state panels and element legends, but the corresponding full engineering term must remain visible nearby.

This convention is a presentation standard. It does not change any model equations, source signs, quantity IDs, or authorization boundaries.
