# Phase 3 rocker included-load authorization review

## Decision

Accept `AUTH-SUSP-0016` for implementation after review and merge.

The physical push/pull, spring, and ARB-link interfaces now exist with exact current application points and signed force vectors. Their contribution to an ideal rigid-rocker support can be assembled without introducing any missing constitutive law.

The reviewed support is an ideal revolute joint. It can cancel the included resultant force and the moment perpendicular to the rocker axis, but it cannot supply a reaction couple about that free axis. The signed axis moment is therefore retained as a residual diagnostic rather than repaired.

## WUFR boundary

The WUFR adapter is authorized to consume exactly:

- the Level-1 actuation force on the remote rocker endpoint;
- the conservative spring force on the rocker eye;
- the physical ARB-link force on the current mechanism rocker pickup.

Under `AUTH-SUSP-0015`, the KW V5 non-spring static contribution remains unavailable and may not be assumed zero. Every WUFR v0.1 result must therefore identify that missing contribution and set `complete_hardware_reaction=false`.

## Authorized outputs

- included force and moment resultants;
- ideal support force contribution;
- ideal support moment contribution perpendicular to the axis;
- signed free-axis moment residual;
- exact algebraic residual diagnostics;
- included/missing load identities and source provenance.

## Not authorized

- complete rocker equilibrium or total pivot/bearing reaction;
- damper gas/static-friction force;
- hidden balancing terms;
- vehicle operating-load generation;
- individual bearing split or structural analysis;
- installed/as-built claims.

## Next gate

Implement `MOD-SUSP-0008` and `BENCH-SUSP-0026` through `BENCH-SUSP-0028`. Complete rocker hardware reactions remain blocked until the KW V5 static contribution and a source-complete physically consistent load state are separately reviewed.
