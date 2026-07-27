# Phase 3 WUFR physical ARB linkage-force authorization review

## Decision

Authorize a narrow extension of `MOD-SUSP-0005` that converts the already-reviewed Z-bar transverse blade action into the **physical signed axial force in each rocker-to-blade linkage**.

This is the missing force-vector interface needed before a later rocker free-body solve. It does not itself solve the rocker.

## Source basis

The existing Z-bar model already provides the exact ingredients required by virtual work:

- source-defined rigid linkage center length and current link closure;
- current blade tip and current rocker pickup for each side;
- free housing angle and signed blade transverse coordinate `d_i`;
- signed conjugate transverse elastic action `f_i = k_b d_i`;
- current rocker pivot and rocker axis;
- independently verified conservative generalized rocker torque.

The physical assembly drawings close the remaining topology question. Both front and rear assemblies contain two dedicated ARB linkages with one RH/LH rod-end pair per linkage. With the reviewer-confirmed WUFR27 hardware carryover, a first-order ideal axial two-force-member representation is mechanically consistent with the hardware and with the rigid-link constraint already used by the mechanism solver.

## Force derivation

For one side, let

- `B` be the current blade tip;
- `P` be the current rocker pickup;
- `u = (P-B)/||P-B||` point from blade tip to rocker;
- `n` be the exact signed blade transverse unit direction used by the existing deformation coordinate `d`;
- `f = k_b d` be the already-authorized transverse elastic coordinate action;
- `T>0` mean linkage tension.

A positive tensile link force acts on the blade tip as `T u`. For a virtual transverse blade displacement `delta B = n delta d`, equilibrium/virtual work gives

`T (u dot n) = k_b d`.

Therefore

`T = (k_b d)/(u dot n)`.

The physical force on the rocker is the exact opposite:

`F_rocker = -T u`.

The denominator is geometry, not a motion ratio. It is evaluated from the current solved mechanism state and must not be replaced by its nominal value.

## Independent verification oracle

This recovery has a particularly strong independent check already available in the codebase. The moment of the physical linkage force about the rocker axis must equal the existing conservative generalized rocker torque:

`tau = rocker_axis dot ((P-R) cross F_rocker)`

and

`tau = Q_rocker`.

Because the housing angle is an ideal free coordinate selected at the elastic-energy minimum, the envelope/virtual-work derivative with respect to prescribed rocker angle is exactly carried by the physical linkage force at the moving rocker pickup. This lets the physical-force mapping be checked against the previously verified energy-gradient result rather than against another new force formula.

## Failure boundary

The physical force is not published when:

- the upstream mechanism or constitutive result failed;
- source/configuration identity does not match;
- the link is degenerate;
- `|u dot n| <= 1e-6`;
- link closure residual exceeds the existing mechanism tolerance;
- the projected-force equation does not reconstruct `k_b d`;
- the physical rocker torque disagrees with existing `Q_rocker`.

No generalized force, motion ratio, nominal angle, absolute value, clipping, or regularization is accepted as a substitute.

## Downstream boundary

A later rocker-equilibrium model may consume:

- this physical ARB-link force at the rocker pickup;
- the solved push/pull-rod force from `MOD-SUSP-0007`;
- a separately reviewed physical spring force vector at the current rocker coilover pickup.

Only then is the ideal rocker-pivot reaction mechanically defined. This authorization stops before that composition.
