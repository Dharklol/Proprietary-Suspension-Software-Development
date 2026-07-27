from __future__ import annotations

import unittest

from pssd_vehicle.quasi_static import (
    CompatibilityState,
    QuasiStaticFailureCode,
    QuasiStaticStatus,
    solve_quasi_static_equilibrium,
)

from tests.test_vehicle_quasi_static import (
    BODY_ORDER,
    BODY_UNITS,
    body_external,
    compatibility,
    config,
    suspension,
)


class VehicleQuasiStaticTangentBoundaryTests(unittest.TestCase):
    def test_provider_failure_is_not_reinterpreted_as_one_sided_bound_derivative(self) -> None:
        """One-sided tangent fallback is legal only when a declared bound blocks a side."""

        def plus_side_fails(q: tuple[float, ...]) -> CompatibilityState:
            if q[0] > 0.0:
                return CompatibilityState(
                    QuasiStaticStatus.FAILURE,
                    source_id="synthetic-provider-failure",
                    failure_code=QuasiStaticFailureCode.COMPATIBILITY_PROVIDER_FAILURE,
                    message="intentional positive-side provider failure",
                )
            return compatibility(q)

        result = solve_quasi_static_equilibrium(
            (0.0, 0.0, 0.0),
            body_coordinate_order=BODY_ORDER,
            body_coordinate_units=BODY_UNITS,
            compatibility_provider=plus_side_fails,
            suspension_provider=suspension,
            body_external_provider=body_external,
            config=config(),
        )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.failure_code,
            QuasiStaticFailureCode.COMPATIBILITY_PROVIDER_FAILURE,
        )
        self.assertIn("positive-side provider failure", result.message)


if __name__ == "__main__":
    unittest.main()
