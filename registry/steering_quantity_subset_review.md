# Steering Quantity Subset Review Index

**Status:** Proposed records created; no quantity is frozen  
**Task:** `P0-STR-001`

## Formal proposed records

| Quantity ID | Review focus |
|---|---|
| `QTY-GEO-0001` | Axle-center construction and active vehicle configuration |
| `QTY-GEO-0004` | Steering-axis road-plane intersections versus wheel-center track |
| `QTY-STEER-0001` | Steering-wheel zero, sign, and unwrap |
| `QTY-STEER-0002` | Primary-shaft section and sensor/model relation |
| `QTY-STEER-0003` | Pinion zero and relation to column |
| `QTY-STEER-0004` | Rack axis, measured point, center, and sign |
| `QTY-STEER-0005` | Exact C-factor meaning and constant/variable ratio |
| `QTY-STEER-0006` | Left road-wheel plane and sign |
| `QTY-STEER-0007` | Right road-wheel plane and sign |
| `QTY-STEER-0010` | Local ratio numerator, denominator, and derivative convention |
| `QTY-STEER-0011` | Secant interval and zero behavior |
| `QTY-STEER-0012` | Joint-center tie-rod length versus physical assembly dimensions |
| `QTY-STEER-0013` | Ideal Ackermann construction and steering-axis track |
| `QTY-STEER-0014` | Error sign, independent variable, and turn direction |
| `QTY-STEER-0015` | Turning-path reference point and low-speed assumptions |
| `QTY-ALIGN-0001` | Left static toe sign and rack-center state |
| `QTY-ALIGN-0002` | Right static toe sign and rack-center state |

## Deliberately deferred records

- `QTY-STEER-0008`, mean road-wheel angle: arithmetic and curvature-equivalent means remain unresolved.
- `QTY-STEER-0009`, equivalent single-track steer angle: curvature/path construction remains to be selected.
- normalized Ackermann percentage/coefficient: no unique definition has been approved.
- rack width, rack axis, hardpoints, steering-axis lines, and reference configuration: these are structured geometry/configuration objects rather than simple scalar quantities and require schema design.
- physical tie-rod body length, thread engagement, and adjustment state: component/setup records rather than aliases of `QTY-STEER-0012`.

## Review order

1. Freeze body and road frames plus angle polarity.
2. Define the reference configuration and geometry-object schema.
3. Review left/right road-wheel and static-toe definitions.
4. Resolve steering-wheel, shaft, pinion, and rack zeros.
5. Recover or reject the legacy C-factor definition.
6. Approve tie-rod joint-center length and physical component separation.
7. Approve Ackermann reference/error definitions.
8. Split and approve turning-path variants.
9. Approve local and secant ratio definitions.
10. Promote accepted records from `proposed/M0` only after benchmark expectations are frozen.

## Freeze rule

Freezing a quantity definition does not freeze a vehicle parameter value. Definitions are project-wide; parameter observations remain configuration-, revision-, and evidence-specific.
