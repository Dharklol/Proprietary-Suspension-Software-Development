# Calibration Records

A `CAL-*` record identifies one calibration method and lifecycle state for one sensor-to-quantity mapping. Planned or blocked records may define the required method without coefficients. Performed calibrations store their immutable coefficients, residuals, uncertainty, validity interval, and source hash in the measurement package; stable registry records may reference that evidence without duplicating every session row.

Never overwrite a performed calibration when the sensor is remounted, adjusted, repaired, or recalibrated. Issue a new calibration ID and preserve the superseded record.
