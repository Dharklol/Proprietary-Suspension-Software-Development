# Joint allocation checkpoint

The front and rear corner COM snapshots contain these distinct CAD instances:

| Family | Front count | Front kg | Rear count | Rear kg |
|---|---:|---:|---:|---:|
| Rod ends | 12 | 0.266712 | 16 | 0.355616 |
| HAB-4TG bearings | 4 | 0.067132 | 4 | 0.067132 |
| Washers | 16 | 0.043545 | 20 | 0.036287 |
| Top-hat spacers | 16 | 0.036287 | 20 | 0.045359 |
| 1/4-inch hex screws | 16 | 0.182344 | 20 | 0.231332 |

Counts are from matching the part names in the frozen front/rear corner
inventories; masses are summed once per source row using 0.45359237 kg/lb.
This is a selected inventory, not all outstanding hardware (nuts are excluded).
No row is added to the existing arm/rod ledger.

For gravity, an inner ball whose center of mass is at the joint center follows
that center irrespective of its spin. If that assumption holds, a complete
rod-end CG can follow the shank's pose: the centered ball contributes its mass
at the same joint point under either rotation. This does not authorize the
complete tensor to follow the shank, nor does it establish which joint each
source row belongs to. For washers, screws and spacers, identify the clamped
body before assigning motion; a nearby arm CG or an assembly name is not proof.

Next evidence needed: endpoint matches for each rod-end instance, which body
clamps each hardware stack, and whether a centered-ball gravity approximation
is justified. Then reconcile mass and first moments and solve the matching dry
static state before any native bump case. The 477 lb scale session is separate.
