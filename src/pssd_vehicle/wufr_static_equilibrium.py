"""Public AUTH-VEH-0010 WUFR static-equilibrium API.

Source contracts and force composition live in ``wufr_static_equilibrium_core``.
The public solve entry point uses the equation-preserving cached runtime plus the
explicit physical-provider numerical settings declared in
``wufr_static_equilibrium_settings``.
"""

from .wufr_static_equilibrium_core import (
    BODY_ORDER,
    BODY_UNITS,
    CORNER_ORDER,
    RESULT_LABEL,
    WHEEL_UNITS,
    WUFRPhysicalClosureResult,
    WUFRStaticEquilibriumConfig,
    WUFRStaticEquilibriumError,
    WUFRStaticEquilibriumFailureCode,
    WUFRStaticEquilibriumProvider,
    WUFRStaticEquilibriumResult,
    WUFRStaticEquilibriumSource,
    WUFRStaticEquilibriumStatus,
    WUFRSuspensionCompositionResult,
    WUFRUnsprungGravityReductionResult,
    evaluate_wufr_unsprung_gravity_reduction,
    evaluate_wufr_physical_closure,
    evaluate_wufr_suspension_composition,
    load_wufr_static_equilibrium_source,
)
from .wufr_static_equilibrium_settings import (
    default_wufr_quasi_static_config,
    load_wufr_static_equilibrium_provider,
    solve_wufr_static_equilibrium,
)

__all__ = [
    "BODY_ORDER",
    "BODY_UNITS",
    "CORNER_ORDER",
    "RESULT_LABEL",
    "WHEEL_UNITS",
    "WUFRPhysicalClosureResult",
    "WUFRStaticEquilibriumConfig",
    "WUFRStaticEquilibriumError",
    "WUFRStaticEquilibriumFailureCode",
    "WUFRStaticEquilibriumProvider",
    "WUFRStaticEquilibriumResult",
    "WUFRStaticEquilibriumSource",
    "WUFRStaticEquilibriumStatus",
    "WUFRSuspensionCompositionResult",
    "WUFRUnsprungGravityReductionResult",
    "default_wufr_quasi_static_config",
    "evaluate_wufr_physical_closure",
    "evaluate_wufr_suspension_composition",
    "evaluate_wufr_unsprung_gravity_reduction",
    "load_wufr_static_equilibrium_provider",
    "load_wufr_static_equilibrium_source",
    "solve_wufr_static_equilibrium",
]
