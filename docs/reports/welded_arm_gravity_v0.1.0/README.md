# Welded-arm ownership resolution checkpoint

Specification: `docs/models/vehicle/welded_arm_gravity_spec_v0.1.0.md`.
Run `PYTHONPATH=src python scripts/run_welded_arm_gravity.py`.

Six welding-jig drawings resolve 36 component instances to eight moving arms,
including the previously uncertain front/rear tab/connector attachments. Their
combined source mass is 2.443048505 kg. Nine checks pass; all source masses/CGs
are unchanged and the remaining inventory subtraction closes exactly.
Analytic generalized gravity agrees with independent potential-energy derivatives
within 2e-7 N/Nm in the sampled states (acceptance 1e-5). Rear source-frame placement
is explicit. Housing tensor ambiguity does not block mass/CG gravity mapping.

The earlier front ownership report is regenerated: ten source-supported parts,
eighteen candidates, sixteen joint components and seventy-two unresolved hardware
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

Rigid ownership is resolved for the listed 36 parts, not for the complete car.
Remaining source facts needed are arm-endcap attachment, rod-endcap attachment,
rod-end endpoint ownership and clamping stacks. Bearing/rod-end intrinsic rotation
splits matter for dynamics; a declared joint-centered-ball approximation may be
sufficient for static gravity. No such approximation is introduced silently.

Full native static equilibrium remains open. Next use the attachment confirmations
or readable assembly callouts to map the remaining masses, then compose their
gravity and solve the no-driver spring/ARB/road-compatible static state. This
continues the G3/G5a analytical path. Housing signs and the 27.851 lb scale gap
remain separate; UI/release and physical correlation are downstream.
