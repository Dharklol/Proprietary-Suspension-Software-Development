# Steady-cornering development authorization review packet

Status: owner accepted the three assumptions and uncorrelated development scope on
2026-10-10 ("that sounds good with me"). Implementation is authorized by
AUTH-VEH-0012; benchmark passes and predictive authority are not implied.

The owner selected the reviewed driver/no-fuel 306.17484975 kg configuration and
requested a focused specification/authorization change permitting an uncorrelated
steady-cornering development model without an external synchronized pose export.

The proposal is AUTH-VEH-0012 / MOD-VEH-0009. It composes existing providers with
newly documented maneuver equations and leaves static behavior unchanged. It
does not merely remove a correlation gate: it introduces three explicit assumptions
whose acceptance determines whether the bounded development model is useful.

| Review decision | Proposed treatment |
|---|---|
| Maneuver inertia | Uniform acceleration at the reviewed sprung and prototype wheel lumps; angular-momentum and gyroscopic terms omitted, not inferred |
| Constant speed with steered lateral forces | Explicit solved virtual tangential force at current total CG; not propulsion or combined-slip authority |
| Maneuver contact geometry | Explicit extension of fixed-radius rigid-circle geometry; no loaded-radius or compliance claim |
| Roadmap exception | Synthetic and uncorrelated development implementation may precede physical correlation after focused review; physical/predictive and setup promotion stays gated |
| Source-domain completeness | Four tires require valid signed slip/IA/load/pressure queries; any incomplete case fails |
| Native synchronization | Same state/configuration/revisions and fully steered contact geometry, with each steering DOF solved once |

Review the motion/force/frame definitions, ten-equation closure count, and direct
plus mapped virtual-work terms in the function specification. Physical wrench
closure remains an independent non-negotiable verification gate. In particular,
the virtual holder must be accepted as an experimental boundary; if rejected,
the first model needs an explicit longitudinal tire/drive provider instead.

The attached Guiggiani text was inspected at printed pp. 76-78, 81-82, 93-94,
102-104. It supports the motion and force/moment relationships and specifically
identifies angular-momentum/gyroscopic contributions; it does not validate the
proposed omitted terms for WUFR. Existing Box/Drive calculators are historical
comparison sources and do not supply missing inertial authority.

No concrete pressure or V/kappa schedule is selected by this proposal. Those are
required before publishing a WUFR sample. No implementation should invent them.
The next gate is synthetic implementation verification; concrete WUFR samples
still require the explicit pressure, maneuver and setup inputs above.
