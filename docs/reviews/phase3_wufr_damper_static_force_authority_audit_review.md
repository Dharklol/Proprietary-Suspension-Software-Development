# Phase 3 WUFR damper static-force authority audit review

## Review decision

Accept `AUTH-SUSP-0015` as a source-boundary hold.

The reviewed project sources establish that WUFR purchased four KW V5 FSAE piggyback dampers, item `3980599103`, and that the V5 is a four-way adjustable solid-piston Formula Student damper. The same source chain provides packaging dimensions used elsewhere by the spring model. It does not provide a governing static gas-force or friction dataset.

Generic damper mechanics establish that a pressurized damper can exert a nonzero zero-speed pressure-area force, position-dependent gas stiffness, and very-low-speed friction. Therefore the absence of a WUFR numerical source cannot be repaired by setting those terms to zero.

## Authorized outcome

This review freezes:

- the exact current hardware/item identity;
- the generic static-force and slow-loop decomposition needed to define a test;
- the missing source fields;
- the prohibition on complete rocker pivot-reaction claims;
- permission for a future separately reviewed included-load contribution that is explicitly marked incomplete.

No numerical WUFR damper force, gas stiffness, friction, complete rocker equilibrium, stress, or structural release is authorized.

## Promotion evidence

The hold can be removed by either:

1. a reviewed slow bidirectional force-versus-position test of a representative KW V5 FSAE damper at documented temperature, adjuster settings, charge/service state, and installed-position domain; or
2. manufacturer data sufficient to reconstruct the static force, including effective displacement area, pressure reference, gas volume/geometry, position law, and a defensible friction treatment.

Installed/as-built promotion still requires actual damper identity/condition, installed position, temperature, and service state.
