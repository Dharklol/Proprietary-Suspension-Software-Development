# Phase 0 Model Assurance and Migration Charter

**Status:** Draft for team review  
**Release target:** Phase 0 foundation  
**Authority:** Vehicle Dynamics / Suspension

## 1. Purpose

Phase 0 establishes a durable model-assurance system before the software begins relying on legacy calculators or new physical implementations. The objective is to ensure that every quantity and result used in the vehicle model has a known definition, derivation, assumptions, evidence, uncertainty, applicable operating range, numerical behavior, dependencies, and verification status.

## 2. Audit layers

Every model item is reviewed through five independent layers:

1. **Definition:** the quantity, sign, frame, reference point, and units are unambiguous.
2. **Physics:** the governing equations are suitable for the intended problem.
3. **Numerical implementation:** the software solves or evaluates those equations correctly and robustly.
4. **Evidence:** the active parameters and data sources are defensible and traceable.
5. **Application:** the model is used only inside its stated validity envelope.

Passing one layer does not compensate for failing another.

## 3. Authority hierarchy

### 3.1 Equation authority

1. Conservation laws, rigid-body mechanics, and exact geometric constraints.
2. Accepted textbooks and primary literature.
3. Specialized peer-reviewed models.
4. Documented external-software formulations.
5. Team derivations with complete review and verification.
6. Legacy calculators, heuristics, and rules of thumb.

### 3.2 Parameter authority

1. Calibrated measurement on the current vehicle or component.
2. Controlled rig, dyno, alignment, or bench measurement.
3. Verified CAD or FEA result.
4. Manufacturer data for the exact component and condition.
5. Previous-vehicle measurement with applicability justification.
6. Engineering estimate.
7. Placeholder.

The literature governs model form; current-vehicle evidence governs current-vehicle parameters.

## 4. Dispositions

Legacy and proposed items receive one disposition:

- `accepted`
- `accepted_with_restrictions`
- `rewrite`
- `benchmark_only`
- `research`
- `deprecated`
- `unknown`

Nothing is removed without a migration record explaining its replacement or retirement.

## 5. Maturity levels

- `M0 proposed`
- `M1 equations_reviewed`
- `M2 analytical_tests_passed`
- `M3 independent_benchmark_passed`
- `M4 cross_tool_comparison_passed`
- `M5 experimental_correlation_passed`
- `M6 approved_for_design_decisions`

Disposition and maturity are separate. A model can be correct but restricted, or promising but immature.

## 6. Circular-validation controls

Sensor calibration, installation calibration, parameter identification, model validation, and regression testing use explicitly classified datasets. Validation data must not be silently reused for calibration or tuning. Model disagreement is not by itself grounds for deleting or filtering measured data.

## 7. Phase 0 deliverables

- Frozen convention and definition specification.
- Canonical quantity dictionary.
- Literature concordance.
- Model and equation registry.
- Legacy calculator inventory and disposition records.
- Verification benchmark suite.
- Sensor, channel, and calibration registry.
- Risk, assumption, and FMEA linkage.
- Release and change-control process.

## 8. Completion gate

Phase 0 is complete when all MVP quantities are defined, all legacy calculator blocks have dispositions, all accepted equations have sources and tests, all active parameters have provenance, high-severity ambiguities are resolved or block dependent outputs, and Phase 2 implementation can begin without redesigning the Phase 0 data structures.

## 9. Prohibited dead ends

- No untyped parameter dictionaries in the canonical model.
- No hidden formulas in UI code.
- No spreadsheet cell address as an API.
- No silent unit conversion or extrapolation.
- No result without model and configuration revision.
- No active parameter without provenance.
- No optimizer that hides infeasible or failed evaluations.
- No calibration on the final validation dataset.
- No filtering that destroys raw data.
- No global high-fidelity switch; fidelity is selected per subsystem.
- No learned model without a deterministic fallback and benchmark.
- No numerical convergence mistaken for physical correctness.
