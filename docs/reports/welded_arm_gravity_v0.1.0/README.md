# Welded-arm ownership resolution checkpoint

Specification: `docs/models/vehicle/welded_arm_gravity_spec_v0.1.0.md`.
Run `PYTHONPATH=src python scripts/run_welded_arm_gravity.py`.

Six welding-jig drawings resolve the initial 36 component instances, including
front/rear tabs and connectors. Owner-confirmed fixed endcaps extend the gravity
manifest to 52 arm-attached instances with source mass 2.617227975 kg. Eight
turnbuckle endcaps have separately confirmed rod ownership; their rod pose/gravity
binding remains open. Ten checks pass; all source masses/CGs
are unchanged and the remaining inventory subtraction closes exactly.
Analytic generalized gravity agrees with independent potential-energy derivatives
within 2e-7 N/Nm in the sampled states (acceptance 1e-5). Rear source-frame placement
is explicit. Housing tensor ambiguity does not block mass/CG gravity mapping.

The earlier front ownership report is regenerated: twenty-two source-supported parts,
six candidates, sixteen joint components and seventy-two unresolved hardware
instances, plus eight existing nominally verified tubes. Dynamic tensor authority
is unchanged. New rear source names are retained in a read-only COM snapshot.

## Reviewed sources

- [Front upper arm jig](https://account.box.com/file/2212894192309)
- [Front lower arm jig](https://account.box.com/file/2212884754818)
- [Rear upper arm jig](https://account.box.com/file/2212897983602)
- [Rear lower arm jig](https://account.box.com/file/2212895802675)
- [Front tab/connector jig](https://account.box.com/file/2212895915302)
- [Rear tab/connector jig](https://account.box.com/file/2212894105772)

The rear upper jig contact-note tube numbers conflict with its own BOM; the BOM
is corroborated by the rear-corner assembly. Jig/tooling weights are excluded.
Raw PDF download tools were unavailable; source findings use extracted text and
do not claim visual callout inspection. Drive and Box files are unchanged.

## Solid stopping point

Rigid ownership is resolved for the 52 arm-attached parts and eight rod endcaps,
not for the complete car. Endcap attachment is confirmed and no longer a source
question. Remaining source facts are rod-end endpoint ownership and clamping
stacks. Rod/endcap pose mapping remains an implementation task. Bearing/rod-end intrinsic rotation
splits matter for dynamics; a declared joint-centered-ball approximation may be
sufficient for static gravity. No such approximation is introduced silently.

Full native static equilibrium remains open. Next implement the confirmed rod/endcap pose mapping and use readable assembly
callouts to map the remaining joint hardware, then compose their
gravity and solve the no-driver spring/ARB/road-compatible static state. This
continues the G3/G5a analytical path. Housing signs and the 27.851 lb scale gap
remain separate; UI/release and physical correlation are downstream.
