# WUFR V5 damper static-force source audit

## Purpose

This audit resolves the next source boundary exposed after the physical spring and ARB linkage forces were implemented. The rocker free body now has reviewed push/pull, spring, and ARB interfaces, but the KW V5 piggyback damper can also exert nonzero force at zero shaft velocity. That contribution must not be hidden inside a spring result or silently set to zero.

The decision is frozen in `AUTH-SUSP-0015`.

## 1. Hardware identity now frozen

Two project sources identify the current hardware:

- KW correspondence dated 2023-10-16 describes the V5 FSAE as a four-way adjustable solid-piston damper that replaced the earlier 3-way Formula SAE damper.
- The 2024-04-10 invoice records four `V5 FSAE DAMPER-PIGGY BACK` units under item/part `3980599103`.

The reviewed KW Formula Student attachment separately provides:

- `185.7 mm` full-extension eye-to-eye length;
- `57 mm` travel;
- `36 mm` spring inner-diameter compatibility.

These sources are sufficient to freeze the hardware family and exact purchased item identity. They are not sufficient to calculate a static damper force.

## 2. Why a zero-speed damper force cannot be assumed zero

Dixon, *The Shock Absorber Handbook*, 2nd ed., Section 7.4, separates three very-low-speed effects in a pressurized damper:

1. a pressure-area force;
2. a gas-spring stiffness as pressure rises with rod insertion;
3. a Coulomb-like friction contribution.

For a slow bidirectional creep loop, the generic relations are

```text
F_in  = F_G + F_F,in
F_out = F_G - F_F,out
```

and, when the friction magnitudes are sufficiently symmetric for the stated reduction,

```text
F_G = 0.5 * (F_in + F_out)
F_F = 0.5 * (F_in - F_out)
```

The textbook also gives the generic pressure-area basis for `F_G`. Applying that relation to the KW V5 still requires the source-specific effective displacement area and pressure reference. Position dependence further requires gas volume/geometry and a thermodynamic assumption. None of those numerical inputs are present in the reviewed project package.

## 3. Available sources and what they do not contain

### KW email

The email establishes architecture and product lineage only. It does not provide:

- charge pressure;
- effective rod/displacement area;
- reservoir gas volume;
- separator geometry;
- static force;
- seal friction;
- force-versus-position data.

### Invoice

The invoice establishes the purchased item identity `3980599103` and quantity four. It contains no performance parameters.

### KW Formula Student attachment

The attachment provides packaging and travel dimensions used by the spring package. It does not provide a quasi-static force loop or enough internal geometry to derive one.

### WUFR shock assembly/BOM

The assembly source corroborates the KW V5 hardware family. It does not expose the internal gas-force parameters or installed service state.

### Existing spring provider

`MOD-SUSP-0004` and the physical bridge implemented under `AUTH-SUSP-0014` provide the conservative coil-spring contribution only. Their explicit exclusion of gas force is a scope boundary, not evidence that the gas contribution is zero.

## 4. Exact missing authority

A source-based analytic model needs, at minimum:

- effective rod/displacement area or sufficient internal dimensions;
- nitrogen charge pressure and its position/temperature reference;
- gas volume and separator/reservoir geometry;
- pressure-versus-position law or thermodynamic model;
- static friction/breakaway treatment.

A direct test can replace most of that internal detail. The preferred evidence is a slow bidirectional force-versus-position test of a representative damper with documented:

- item/serial and service history;
- charge/service state;
- body/reservoir temperature;
- adjuster settings;
- position/zero/sign convention;
- creep speed and dwell protocol;
- fixture tare and load-cell uncertainty;
- repeatability after conditioning.

The test should report both travel directions at common positions so that gas bias and friction can be separated without fitting a hidden offset.

## 5. Rocker-reaction consequence

The currently reviewed physical inputs can support a separately labeled **included-load contribution** from:

- the solved push/pull force;
- the conservative spring force;
- the physical ARB linkage force.

That result may be useful for sign checks, force-path diagnostics, and later superposition. It is not the complete hardware pivot reaction because the non-spring damper contribution remains unavailable.

A later rocker model must therefore expose, at minimum:

```text
included_force_set
missing_force_set
complete_hardware_reaction = false
rocker_axis_moment_residual
```

It must not add a balancing torque or force to conceal an inconsistent load state.

## 6. Decision

`AUTH-SUSP-0015`:

- freezes the KW V5 FSAE hardware identity and generic static-force mechanics;
- blocks a WUFR numerical gas-force, static-friction, or gas-stiffness provider;
- blocks complete rocker equilibrium/pivot-reaction claims;
- permits a later separately authorized included-load contribution with explicit incompleteness;
- defines the exact manufacturer-data or test packet needed to remove the hold.

This is the current source stopping point for complete rocker hardware loads.
