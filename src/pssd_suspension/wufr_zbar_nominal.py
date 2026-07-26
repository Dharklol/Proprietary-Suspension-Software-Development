"""Reviewed nominal-continuation entrypoint for the WUFR Z-bar solver.

The raw mechanism equations have repeated geometric branches over a full housing
revolution.  This wrapper deliberately searches only a numerical trust region
around the predecessor housing angle so source-continuation cannot jump to a
remote assembly branch.  The trust region is a numerical branch-control rule,
not an installed articulation limit.
"""
from __future__ import annotations

from .wufr_zbar import (
    ZBarAxleFixture,
    ZBarMechanismResult,
    ZBarSolverConfig,
    solve_zbar_mechanism,
)

NOMINAL_BRANCH_SEARCH_HALF_WIDTH_RAD = 0.5


def solve_nominal_zbar_mechanism(
    fixture: ZBarAxleFixture,
    theta_left_rad: float,
    theta_right_rad: float,
    *,
    with_jacobian: bool = True,
) -> ZBarMechanismResult:
    """Solve only the branch continuously connected to the nominal fixture."""
    config = ZBarSolverConfig(housing_search_half_width_rad=NOMINAL_BRANCH_SEARCH_HALF_WIDTH_RAD)
    return solve_zbar_mechanism(
        fixture,
        theta_left_rad,
        theta_right_rad,
        config=config,
        with_jacobian=with_jacobian,
    )
