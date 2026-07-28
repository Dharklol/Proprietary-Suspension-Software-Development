# Phase 3 rocker included-load implementation review

## Decision

Accept the v0.1 implementation subject to the automated benchmark and workflow gates.

The provider-neutral kernel implements the authorized ideal-revolute projection exactly and preserves the signed free-axis moment residual. The WUFR adapter consumes the physical force vectors at their source-owned current application points and performs source/configuration/geometry checks before composition.

## Verified behavior

- exact force and moment summation;
- exact ideal support force and perpendicular-moment contribution;
- no support-axis couple;
- translation invariance and homogeneous force scaling;
- nonzero free-axis residual retained without repair;
- failed/mismatched upstream sources fail closed;
- explicit missing KW V5 static contribution and `complete_hardware_reaction=false`.

## Remaining boundary

This implementation is not complete rocker equilibrium. A complete hardware reaction still requires the damper static contribution under `AUTH-SUSP-0015` and a source-complete physically consistent operating load state. Individual bearing loads and structural release remain later models.
