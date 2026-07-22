# SOLIDWORKS metadata exporter

## Purpose

`tools/solidworks/WUFR26_SolidWorks_Metadata_Exporter.bas` exports a read-only JSON inventory of the active SOLIDWORKS part or assembly for the WUFR-26 steering source-freeze package.

The report is a derived metadata artifact. It does not replace the untouched native SOLIDWORKS file, its provider identity, or the raw-byte SHA-256 required by the source-hash contract.

## Recommended runs

Run the macro twice:

1. with the intended WUFR-26 parent steering assembly and configuration active;
2. with `GEOMETRY FINAL.SLDPRT` active.

The assembly run captures dependency, component-configuration, suppression, display-state, and lightweight-state context. The part run captures the native feature tree, equations, named dimensions, design-table state, and motion-study inventory.

## Installation

1. In SOLIDWORKS, choose `Tools > Macro > New` and save a temporary `.swp` macro.
2. Open the VBA editor.
3. Choose `File > Import File`.
4. Import `tools/solidworks/WUFR26_SolidWorks_Metadata_Exporter.bas`.
5. Run the public procedure `main`.

The first line is an exported-module `Attribute VB_Name` declaration. Importing the `.bas` file preserves it correctly. When copying the source manually into an existing module, omit the first line.

The macro uses late-bound objects. It does not require a manual VBA reference to the Motion Study type library. The SOLIDWORKS Motion add-in should still be loaded through `Tools > Add-Ins` before the run when motion-study information is required.

## Preparation

Before the assembly run:

- activate the exact WUFR-26 configuration being documented;
- set relevant steering components to **Resolved** where practical;
- expose the intended MotionManager study;
- do not rebuild or save merely for the extractor;
- note any existing dirty state before running.

The macro does not activate another configuration or study and does not resolve components itself.

## Output

For a saved document, the UTF-8 JSON report is written beside the active model:

```text
<model_name>_YYYYMMDD_HHMMSS_solidworks_metadata.json
```

For an unsaved document, it is written to the Windows Desktop.

The report contains:

- SOLIDWORKS revision and build information;
- active document path, type, configuration, units, and dirty flag before/after;
- document and configuration custom properties;
- configuration and display-state names;
- equations and design-table presence;
- feature/subfeature inventory and reachable display dimensions;
- feature error/warning information from `What's Wrong`;
- dependency pairs;
- model-level external-reference paths, statuses, entities, and configurations when the installed API exposes them;
- assembly component path, referenced configuration/display state, suppression code, lightweight state, envelope state, visibility, and fixed state;
- motion-study names, type codes, duration, time-bar location, frame rate when exposed, and motion-feature names;
- indexed matches for `Steer Input`, `Dimension2`, `Ackermann`, `rack`, `tie rod`, `wheel angle`, and related names;
- nonfatal extraction warnings.

## Safety boundary

The macro intentionally contains no calls to save, save-as, rebuild, configuration activation, motion-study activation, calculation, or component resolution methods.

It reads the document dirty flag before and after extraction. A changed flag is reported in the completion message and JSON.

Custom properties are requested with cached reads to avoid activating inactive configurations. Feature suppression is reported only for the active configuration.

## Known limitations

- Model-level `IModelDocExtension.ListExternalFileReferences2` is unavailable in older SOLIDWORKS releases. The report records that state rather than guessing. Preserve `Find References > Copy List` and External References screenshots alongside the JSON.
- Lightweight components can omit details from external-reference and component inspection. A warning is emitted when lightweight state is detected.
- Some Design Study bounds, plot definitions, sensor selections, driver/monitor details, and UI-only result definitions are not consistently exposed through the general VBA interfaces. Preserve screenshots of those dialogs.
- `GetFirstDisplayDimension` reports dimensions reachable from the feature API; it is not guaranteed to reproduce every annotation visible in the user interface.
- A successful report does not prove that the open file is the exact provider revision. Hash the untouched downloaded bytes separately.

## Package to return

Include the following in the CAD evidence package:

1. untouched native provider files;
2. parent-assembly Pack and Go ZIP;
3. parent-assembly metadata JSON;
4. `GEOMETRY FINAL.SLDPRT` metadata JSON;
5. `Find References > Copy List` text;
6. ConfigurationManager, equations, design-study/motion-study, driver/monitor, External References, and rebuild-status screenshots;
7. optional STEP or Parasolid geometry supplements.

Before sending the reports, check:

- `document.active_configuration`;
- `document.dirty_before` and `document.dirty_after`;
- `warnings`;
- `external_references`;
- `assembly_components` for `lightweight: true`;
- `motion_studies`;
- `target_name_matches`.
