# Phase 3 provider-neutral linkage statics authorization review

## Decision

Authorize `MOD-SUSP-0006` as the first reusable suspension load-path statics kernel under `AUTH-SUSP-0010`.

The authorized problem is intentionally narrow:

`one rigid body + exactly six ideal two-force links + one prescribed external wrench -> six signed axial link forces`.

The implementation is not allowed to create a WUFR load case, move WUFR application points, infer a missing reaction, or report structural stress/factor of safety.

## Why this slice is useful now

PR #67 completed the rigid-road compatibility provider but further WUFR-specific prediction is increasingly limited by as-built evidence. Linkage statics is different: the mathematical kernel can be verified completely with analytical fixtures before WUFR-27 exists, and later adapters can supply geometry and load cases without changing the equilibrium contract.

This is also a direct step toward replacing the useful member-force portion of OptimumK Forces with a transparent source-preserving solver.

## Literature/source basis

Borg (2009), *An Approach to Using Finite Element Models to Predict Suspension Member Loads in a Formula SAE Vehicle*, Chapter 3 Section 3.3.1, constructs unit vectors for six suspension members and solves their six axial loads from three force and three moment equations by matrix algebra. That is the physical architecture adopted for this first generic kernel.

The same source is also a warning against overpromotion: its truss FE model reproduced the hand calculation, while converting to beam members introduced bending and changed axial load distribution; steering articulation also materially changed member loads in cornering cases. The first project model therefore freezes the truss/two-force assumption as `ASM-SUSP-0004` and explicitly excludes beam/stress release.

Guiggiani (2022), Section 3.10.7, provides the broader internal-equilibrium framing: tire/road loads are transmitted to the body through suspension linkage and elastic paths. The project continues to keep kinematics, constitutive spring/ARB force, vehicle equilibrium, and structural statics as separate providers.

## Numerical architecture

A raw 6x6 force/moment matrix mixes dimensionless force-direction rows with moment rows carrying length. `EQ-SUSP-0021` therefore scales moment rows by

`L_ref=max ||r_body-r_O||`

before evaluating conditioning.

The accepted solve must be finite, full-rank, and satisfy

`cond_inf(A_tilde) <= 1e10`.

No pseudoinverse, least-squares, minimum-norm, stiffness-weighted, clipped, or regularized force sharing is allowed. Those methods would answer a different physical problem and could hide a bad geometry/topology definition.

After solving, `EQ-SUSP-0022` reconstructs force and moment equilibrium in physical SI units from the original geometry. This catches scaling/assembly/sign mistakes independently of the linear solver's internal algebraic residual.

## WUFR topology hold

The first implementation remains provider-neutral on purpose.

The current reviewed actuation source says the front push/pull attachment is on the **upper A-arm** and the rear attachment is on the **lower A-arm**. Therefore a direct six-link upright adapter would not be source preserving unless a later audit proves an equivalent topology.

The next WUFR statics gate must identify:

- rigid bodies and/or massless joint nodes;
- upper/lower arm load-path representation;
- tie-rod versus rear toe-link role;
- front/rear arm-mounted actuation pickup;
- rocker/coilover/ARB force interfaces;
- brake torque reaction path;
- external wrench application point/frame;
- determinacy/rank of the resulting ideal network.

Only then should a WUFR adapter be authorized.

## Verification plan

`BENCH-SUSP-0018` is an exact analytical six-link fixture with known simultaneous force/moment loading and known signed forces.

`BENCH-SUSP-0019` proves reference-point and rigid-translation invariance.

`BENCH-SUSP-0020` proves fail-closed behavior for degenerate links, unsupported link counts, singular/ill-conditioned systems, and nonfinite inputs.

These gates verify the statics kernel, not the physical fidelity of `ASM-SUSP-0004` for a welded suspension assembly.

## Roadmap relationship

The broader ordering is frozen in `docs/roadmaps/post_rigid_contact_program_v0.1.0.md`:

1. bounded WUFR static-equilibrium closeout;
2. reusable linkage/load-path statics;
3. reusable steady-state tire model;
4. pre-build WUFR-27 physical correlation contract;
5. maneuver QSS after physical static correlation.

The linkage statics kernel may be developed in parallel with the first static-equilibrium composition because it consumes prescribed external wrenches and does not depend on WUFR-27 physical correlation.

## Merge gate

This authorization PR may merge when registry validation and the focused authorization tests are green.

The next PR is implementation only: deterministic `src/pssd_suspension/linkage_statics.py`, analytical/failure tests, benchmark reporter, and a frozen result record. It still must not publish WUFR member forces.
