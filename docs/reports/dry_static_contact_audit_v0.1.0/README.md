# CAD dry mass, global static balance and contact checkpoint

Specification: `docs/models/vehicle/dry_static_contact_spec_v0.1.0.md`.
Reproduce: `PYTHONPATH=src python scripts/run_dry_static_contact_audit.py`.

All eleven audit checks pass. This does not mean full native suspension
equilibrium passes; that separate report field is explicitly false.

| Inventory category | CAD instances | Mass (kg) |
|---|---:|---:|
| Body inventory candidates | 1966 | 157.210126 |
| Outboard inventory | 202 | 32.236810 |
| Remaining mixed members | 292 | 6.282254 |
| Verified front tubes | 8 | 0.815559 |
| Additional electrical CG approximation | — | 7.185810 |
| Total | 2468 | 203.730559 |

All mass and first moments close without selecting an ownership fraction. These
categories are not a final sprung/unsprung decomposition. The dry CAD mass is
449.149 lb versus 477 lb in the separate scale session; the 27.851 lb discrepancy
remains unexplained and no scale factor or ballast is introduced.

Using nominal ideal-circle support locations, total weight is 1998.596788 N,
front axle reaction is 919.031296 N and rear is 1079.565492 N at g=9.81 m/s^2.
The four corner reactions remain a one-parameter family; no equal split or hidden
crossweight is imposed. Endpoint examples in results.json prove global wrench
closure, not suspension-equilibrium feasibility. Actual circle support positions
are used rather than nominal axle stations, changing front axle load by about
0.069 N compared with an axle-station approximation.

The existing steering-closed contact geometry is rebased explicitly to the dry CAD
CG. Twelve sampled corner states pass wheel-to-qL derivative refinement and
heave/pitch virtual-work checks. Driver-referenced body points returned by the
legacy provider are discarded; driver gravity/equilibrium is never invoked.
The geometry remains an ideal rigid-circle model, not measured tire compliance.

## Stopping point and next steps

The source mass ledger, global static balance and contact-coordinate bridge are
reconciled. A complete native static/ride composition is still blocked by compatible
member ownership/gravity and the wheel/body/tire model. The next highest-value work
is resolving that moving-mass decomposition and then solving the matching no-driver
spring/ARB/gravity equilibrium with independent wrench closure. More isolated
manufactured-force cases will not remove those source dependencies.

Existing BOM/drawings can support the next ownership work; no new owner input is
required merely to continue it. If those sources cannot resolve the remaining joint
mass allocations, report the specific part/assumption needed. Keep the unexplained
scale discrepancy and housing tensor signs explicit. This stays aligned with G3/
G5a analytical development ahead of UI/release or physical correlation.
