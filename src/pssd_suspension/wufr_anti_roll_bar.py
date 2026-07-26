"""WUFR-27 anti-roll-bar blade-stiffness adapter.

The governing WUFR constitutive authority is the discrete SolidWorks FEA blade-tip
stiffness data in the Google Sheet ``ARB FEA vs Simulink``.  These are linear
force/deflection slopes in N/mm, converted explicitly to SI N/m.

This module intentionally does not implement the WUFR Z-bar mechanism map from
left/right suspension coordinates to blade-tip deformation.  Consumers must supply
an independently reviewed ``delta_b`` and Jacobian before requesting vehicle-level
generalized forces.  Settings are discrete; interpolation is prohibited.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import tomllib

from .anti_roll_bar import (
    AntiRollBarDefinition,
    AntiRollBarReference,
    SuspensionAntiRollBarError,
)


@dataclass(frozen=True)
class WufrBladeSetting:
    setting: int
    stiffness_N_per_mm: float
    definition: AntiRollBarDefinition


@dataclass(frozen=True)
class WufrAntiRollBarBladePackage:
    configuration_id: str
    source_record_id: str
    source_url: str
    source_sheet: str
    settings: tuple[WufrBladeSetting, ...]
    reference: AntiRollBarReference
    solidworks_fea_stiffness_N_per_mm: tuple[float, ...]
    simulink_comparison_N_per_mm: tuple[float, ...]
    instron_comparison_N_per_mm: tuple[float, ...]
    matlab_reduced_axle_comparison_Nm_per_deg: tuple[float, float]
    geometry_map_authorized: bool = False
    interpolation_authorized: bool = False
    installed_as_built_authority: bool = False

    def definition_for_setting(self, setting: int) -> AntiRollBarDefinition:
        if isinstance(setting, bool) or not isinstance(setting, int):
            raise SuspensionAntiRollBarError("WUFR ARB blade setting must be an integer 1..5; interpolation is not authorized")
        for item in self.settings:
            if item.setting == setting:
                return item.definition
        raise SuspensionAntiRollBarError("WUFR ARB blade setting must be one of the discrete settings 1..5")


def _finite_positive_tuple(values: object, name: str, expected_len: int) -> tuple[float, ...]:
    if not isinstance(values, list) or len(values) != expected_len:
        raise SuspensionAntiRollBarError(f"{name} must contain exactly {expected_len} values")
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) and value > 0.0 for value in result):
        raise SuspensionAntiRollBarError(f"{name} values must be finite and positive")
    return result


def load_wufr27_blade_anti_roll_bar_package(path: str | Path) -> WufrAntiRollBarBladePackage:
    """Load the governing discrete WUFR blade-tip stiffness package.

    The returned definitions use ``delta_b`` [m] as their elastic coordinate and
    blade-tip force [N] as conjugate action.  No vehicle/suspension-to-blade map is
    manufactured here.
    """
    source_path = Path(path)
    with source_path.open("rb") as stream:
        data = tomllib.load(stream)

    configuration_id = str(data["configuration_id"])
    source_record_id = str(data["record_id"])
    authority = data["governing_solidworks_fea"]
    source_values = _finite_positive_tuple(authority["stiffness_N_per_mm"], "SolidWorks FEA stiffness", 5)
    expected = (280.0, 300.0, 400.0, 700.0, 2300.0)
    if source_values != expected:
        raise SuspensionAntiRollBarError("Governing SolidWorks FEA blade stiffness values no longer match the frozen 1..5 settings")

    settings: list[WufrBladeSetting] = []
    assumptions = ("ASM-SUSP-0003",)
    for index, stiffness_N_per_mm in enumerate(source_values, start=1):
        definition = AntiRollBarDefinition(
            arb_id=f"WUFR27_ARB_BLADE_SETTING_{index}_V0",
            axle="wufr_blade",
            stiffness_action_per_coordinate=stiffness_N_per_mm * 1000.0,
            elastic_coordinate_unit="m",
            elastic_action_unit="N",
            source_id=source_record_id,
            configuration_id=configuration_id,
            assumption_ids=assumptions,
            installed_as_built_authority=False,
            reduced_axle_level=False,
        )
        settings.append(WufrBladeSetting(index, stiffness_N_per_mm, definition))

    comparison = data["comparison_only"]
    simulink = _finite_positive_tuple(comparison["simulink_stiffness_N_per_mm"], "Simulink comparison", 5)
    instron = _finite_positive_tuple(comparison["instron_stiffness_N_per_mm"], "Instron comparison", 5)
    matlab = _finite_positive_tuple(comparison["matlab_reduced_axle_Nm_per_deg"], "MATLAB reduced axle comparison", 2)

    reference = AntiRollBarReference(
        reference_id="WUFR27_ARB_BLADE_ZERO_DEFLECTION_REFERENCE_V0",
        configuration_id=configuration_id,
        elastic_coordinate_unit="m",
        zero_energy_coordinate=0.0,
        assumption_ids=assumptions,
        installed_as_built_authority=False,
    )

    boundaries = data["authority_boundaries"]
    if bool(boundaries["interpolation_authorized"]):
        raise SuspensionAntiRollBarError("WUFR ARB setting interpolation must remain disabled until separately authorized")
    if bool(boundaries["z_bar_geometry_map_authorized"]):
        raise SuspensionAntiRollBarError("WUFR Z-bar geometry map is not authorized in this package")

    return WufrAntiRollBarBladePackage(
        configuration_id=configuration_id,
        source_record_id=source_record_id,
        source_url=str(authority["spreadsheet_url"]),
        source_sheet=str(authority["sheet_name"]),
        settings=tuple(settings),
        reference=reference,
        solidworks_fea_stiffness_N_per_mm=source_values,
        simulink_comparison_N_per_mm=simulink,
        instron_comparison_N_per_mm=instron,
        matlab_reduced_axle_comparison_Nm_per_deg=(matlab[0], matlab[1]),
        geometry_map_authorized=False,
        interpolation_authorized=False,
        installed_as_built_authority=False,
    )
