# Suspension linkage statics function specification

## Scope

`MOD-SUSP-0006` is the first provider-neutral structural/load-path statics kernel. It solves one rigid body supported by exactly six ideal pin-ended two-force links under one prescribed external wrench.

The model intentionally answers only:

> Given this geometry and this external wrench, what signed axial forces are required in these six ideal links for rigid-body equilibrium?

It does **not** decide whether the external wrench is a real WUFR load case, whether the six-link topology accurately represents a particular WUFR assembly, or whether a real member survives the resulting force.

## Inputs

### Body/reference record

Required:

- `body_id`;
- `frame_id`;
- explicit equilibrium reference point `r_O_m=[x,y,z]`.

### Link record

Exactly six records, each containing:

- stable `link_id`;
- `frame_id` matching the body;
- body application point `r_body_m`;
- remote endpoint `r_remote_m`;
- source/configuration provenance.

The kernel derives

`l = r_remote - r_body`

`L = ||l||`

`u = l/L`.

`N > 0` is tension. Therefore the force exerted by the link on the rigid body is

`F_body = N*u`.

The remote-end action is `-N*u`.

### External wrench record

Required:

- force `F_ext_N=[Fx,Fy,Fz]`;
- couple `M_ext_Nm=[Mx,My,Mz]` about exactly `r_O_m`;
- `frame_id`;
- source/load-case provenance.

The kernel does not translate an ambiguously referenced moment. A caller may use the existing `MOD-VEH-0003` wrench tools before this interface.

## Equilibrium assembly

For link `j`, define the body-end moment arm

`r_j = r_body,j - r_O`.

The unit-axial-force wrench column is

`a_j = [u_j ; r_j x u_j]`.

With the caller's stable six-link order,

`A = [a_1 ... a_6]`.

The equilibrium equation is

`A*N = -[F_ext ; M_ext,O]`.

The row order is fixed:

`[Fx, Fy, Fz, Mx, My, Mz]`.

## Numerical scaling and solve

Force rows are dimensionless while moment rows contain a length. Conditioning therefore must not be interpreted on the unscaled matrix.

Use

`L_ref = max_j ||r_body,j-r_O||`.

Require finite `L_ref > 1e-12 m`.

Then

`S = diag(1,1,1,1/L_ref,1/L_ref,1/L_ref)`

`A_tilde = S*A`

`b_tilde = S*b`.

The implementation must:

1. validate finite inputs and exactly six unique link IDs;
2. construct all six link axes and reject degenerate links;
3. assemble `A`, `b`, `L_ref`, `A_tilde`, and `b_tilde`;
4. determine singularity/conditioning before accepting a force vector;
5. require `cond_inf(A_tilde) <= 1e10`;
6. solve deterministically without least squares, pseudoinverse, regularization, stiffness weighting, or force clipping;
7. reconstruct physical equilibrium using the original unscaled geometry;
8. reject a result whose physical residual exceeds the frozen benchmark tolerance.

A dependency-light partial-pivot 6x6 solver is preferred so the core package does not need a numerical stack solely for this model. The implementation may compute `cond_inf` by reusing deterministic solves for the inverse columns.

## Result contract

Successful output must contain at least:

- model/authorization/assumption IDs;
- body/frame/reference point identity;
- external wrench and provenance;
- ordered link IDs;
- body/remote endpoints and current unit axes;
- signed axial force per link;
- body-end and remote-end force vectors;
- characteristic length;
- condition number and pivot diagnostics;
- reconstructed total link force/moment;
- physical force residual vector/norm;
- physical moment residual vector/norm;
- explicit fidelity statement: ideal rigid-body/two-force-link statics only.

Failed output retains all valid upstream provenance plus one structured failure code.

## Synthetic analytical benchmark

`BENCH-SUSP-0018` freezes a deliberately simple simultaneous force/moment fixture.

Reference:

`O=[0,0,0] m`.

Unit-wrench columns are created from:

| link | body point r [m] | unit axis u |
|---|---|---|
| L1 | `[0,0,0]` | `[1,0,0]` |
| L2 | `[0,0,0]` | `[0,1,0]` |
| L3 | `[0,0,0]` | `[0,0,1]` |
| L4 | `[0,1,0]` | `[0,0,1]` |
| L5 | `[0,0,1]` | `[1,0,0]` |
| L6 | `[1,0,0]` | `[0,1,0]` |

Remote endpoints are one meter farther along each unit axis.

For

`N=[100,200,300,40,50,60] N`,

the link wrench is

`F=[150,260,340] N`

`M=[40,50,60] N*m`.

Therefore the prescribed external wrench is

`F_ext=[-150,-260,-340] N`

`M_ext=[-40,-50,-60] N*m`.

The implementation must recover the signed target force vector without a magnitude convention or load-sharing rule.

## Reference-point invariance benchmark

`BENCH-SUSP-0019` moves the equilibrium reference point to

`O2=[0.31,-0.17,0.23] m`.

The external couple is translated exactly as

`M_ext,O2 = M_ext,O + (O-O2) x F_ext`.

With all link moments evaluated about `O2`, the solved axial forces must be unchanged.

The benchmark also rigidly translates the entire physical geometry to prove that an arbitrary global origin is not embedded in the solver.

## Failure benchmark

`BENCH-SUSP-0020` requires explicit failures for:

- coincident link endpoints;
- nonfinite geometry/wrench;
- five-link or seven-link topology;
- linearly dependent six-link wrench columns;
- near-dependent geometry above the condition limit.

Approximate force-sharing is deliberately outside this model.

## WUFR adapter boundary

No WUFR member-load calculation is authorized in the first implementation PR.

This matters because the reviewed actuation source explicitly states:

- front push/pull attachment is on the **upper A-arm**;
- rear push/pull attachment is on the **lower A-arm**.

Therefore a convenient six-links-directly-to-upright representation could move a real application point and change the load path. The next WUFR statics source audit must identify the actual rigid bodies, ideal axial links, pin/massless nodes, actuation pickups, tie-rod/toe-link role, brake reaction path, and any topology that is not statically determinate under ASM-SUSP-0004.

## Literature boundary

Borg (2009), Chapter 3 Section 3.3.1, is the primary published Formula SAE example for the six-member vector/matrix statics formulation used here. Its later truss/beam comparison is equally important: reproducing the axial truss solution does not validate the assumption that real welded members carry no bending. The same thesis reports material load changes when steering geometry is included.

Accordingly, `MOD-SUSP-0006` is a canonical **ideal load-path baseline**, not a final structural model.

Guiggiani (2022), Section 3.10.7, provides the broader vehicle-dynamics framing that internal suspension equilibrium determines how road/tire loads are transmitted through linkage and elastic paths. The constitutive spring/ARB providers remain separate from this statics kernel.
