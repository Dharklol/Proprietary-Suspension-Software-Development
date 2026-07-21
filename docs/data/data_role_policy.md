# Measurement Data Role Policy

A measurement session declares one primary role: calibration, identification, validation, or diagnostic.

Calibration data establish sensor transformations. Identification data estimate parameters such as compliance. Validation data assess a previously frozen model or requirement. Diagnostic data troubleshoot a system without entering acceptance evidence.

One dataset may be referenced by another workflow, but it must not silently serve as both calibration and independent validation evidence. Every reuse records the upstream session ID, source hash, processing revision, and new evidence role.
