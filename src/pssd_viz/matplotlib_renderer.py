"""Headless deterministic renderer for engineering figures.

Matplotlib is an optional dependency.  Importing :mod:`pssd_viz` never imports it;
this module resolves it only when rendering is explicitly requested.
"""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
import textwrap
from typing import Iterable

from .contracts import EngineeringFigureSpec, FigureAvailability


class VisualizationDependencyError(RuntimeError):
    """Raised when the optional plotting backend is not installed."""


_LINE_STYLES = ("-", "--", "-.", ":")

# Presentation aliases only. The underlying figure contract keeps the repository's
# canonical quantity wording; exported engineering graphics add conventional symbols
# where the quantity mapping is unambiguous.
_STANDARD_QUANTITY_LABELS = {
    "Steering input": ("Steering input angle", "δ_in"),
    "Centered projected road-wheel heading": ("Road-wheel steer angle", "δ"),
    "Evaluated minus target wheel heading": ("Steer-angle residual", "Δδ"),
    "Target road-wheel heading": ("Road-wheel steer-angle target", "δ_target"),
    "Alternate minus baseline target heading": ("Target steer-angle correction", "Δδ_target"),
    "Slip-angle magnitude": ("Slip-angle magnitude", "|α|"),
    "Lateral-force magnitude": ("Lateral tire-force magnitude", "|F_y|"),
    "Velocity-center longitudinal position S": ("Velocity-center longitudinal position", "S"),
    "Required incremental wheel heading": ("Required road-wheel steer angle", "δ_req"),
}

_STANDARD_SERIES_LABELS = {
    "left target": "Left target, δ_L,target",
    "right target": "Right target, δ_R,target",
    "left evaluated": "Left evaluated, δ_L",
    "right evaluated": "Right evaluated, δ_R",
    "left residual": "Left residual, Δδ_L",
    "right residual": "Right residual, Δδ_R",
    "baseline left": "Baseline left, δ_L,base",
    "baseline right": "Baseline right, δ_R,base",
    "alternate left": "Alternate left, δ_L,alt",
    "alternate right": "Alternate right, δ_R,alt",
    "left target correction": "Left target correction, Δδ_L,target",
    "right target correction": "Right target correction, Δδ_R,target",
    "left required heading": "Left required, δ_L,req",
    "right required heading": "Right required, δ_R,req",
}


def render_engineering_figure(
    spec: EngineeringFigureSpec,
    output_stem: str | Path,
    *,
    formats: Iterable[str] = ("svg", "png"),
) -> tuple[Path, ...]:
    """Render one figure to the requested static formats.

    The renderer consumes only an :class:`EngineeringFigureSpec`.  It performs no
    vehicle, tire, steering, or suspension calculations.  An unavailable figure
    is rendered as an explicit diagnostic page rather than as an empty plot.
    """

    matplotlib, plt = _load_matplotlib()
    output_stem = Path(output_stem)
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    normalized_formats = tuple(_normalize_format(item) for item in formats)
    if not normalized_formats:
        raise ValueError("at least one output format is required")

    rc = {
        "svg.hashsalt": "pssd-viz-v0.1.0",
        "svg.fonttype": "none",
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.5,
        "figure.dpi": 120,
        "savefig.dpi": 160,
    }
    context = matplotlib.rc_context(rc) if hasattr(matplotlib, "rc_context") else nullcontext()
    with context:
        fig, ax = plt.subplots(figsize=(8.0, 5.5), constrained_layout=False)
        try:
            if spec.availability is FigureAvailability.AVAILABLE:
                _render_available(ax, spec)
            else:
                _render_unavailable(ax, spec)

            fig.suptitle(spec.metadata.title)
            fig.subplots_adjust(left=0.11, right=0.97, top=0.88, bottom=0.28)
            fig.text(
                0.01,
                0.018,
                _wrap_block(spec.metadata.footer_text()),
                ha="left",
                va="bottom",
                fontsize=6.5,
            )
            if spec.metadata.notes:
                fig.text(
                    0.01,
                    0.115,
                    _wrap_block("Notes: " + " | ".join(spec.metadata.notes)),
                    ha="left",
                    va="bottom",
                    fontsize=6.5,
                )

            outputs: list[Path] = []
            for fmt in normalized_formats:
                path = output_stem.with_suffix(f".{fmt}")
                fig.savefig(
                    path,
                    format=fmt,
                    metadata=_metadata_for_format(spec, fmt),
                )
                outputs.append(path)
            return tuple(outputs)
        finally:
            plt.close(fig)


def _display_quantity_label(quantity: str, unit: str) -> str:
    term_symbol = _STANDARD_QUANTITY_LABELS.get(quantity)
    if term_symbol is None:
        base = quantity
    else:
        term, symbol = term_symbol
        base = f"{term}, {symbol}"
    normalized_unit = unit.strip()
    return base if not normalized_unit or normalized_unit == "-" else f"{base} [{normalized_unit}]"


def _display_series_label(label: str) -> str:
    return _STANDARD_SERIES_LABELS.get(label, label)


def _render_available(ax, spec: EngineeringFigureSpec) -> None:
    for index, series in enumerate(spec.series):
        ax.plot(
            series.x,
            series.y,
            label=_display_series_label(series.label),
            linestyle=_LINE_STYLES[index % len(_LINE_STYLES)],
        )
    ax.set_xlabel(_display_quantity_label(spec.metadata.x_quantity, spec.metadata.x_unit))
    ax.set_ylabel(_display_quantity_label(spec.metadata.y_quantity, spec.metadata.y_unit))
    if len(spec.series) > 1 or spec.series[0].label:
        ax.legend()


def _render_unavailable(ax, spec: EngineeringFigureSpec) -> None:
    ax.set_axis_off()
    ax.text(
        0.5,
        0.58,
        "FIGURE UNAVAILABLE",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
    )
    ax.text(
        0.5,
        0.42,
        _wrap_block(spec.unavailable_reason or "", width=92),
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=10,
        wrap=True,
    )


def _wrap_block(value: str, *, width: int = 118) -> str:
    """Wrap each logical line without changing the underlying metadata payload."""

    return "\n".join(
        textwrap.fill(line, width=width, break_long_words=False, break_on_hyphens=False)
        for line in value.splitlines()
    )


def _normalize_format(value: str) -> str:
    normalized = value.strip().lower().lstrip(".")
    if normalized not in {"svg", "png"}:
        raise ValueError(f"unsupported engineering figure format: {value!r}")
    return normalized


def _metadata_for_format(spec: EngineeringFigureSpec, fmt: str) -> dict[str, str]:
    description = spec.metadata.footer_text()
    if fmt == "svg":
        return {
            "Creator": "pssd_viz",
            "Date": "1970-01-01T00:00:00Z",
            "Title": spec.metadata.title,
            "Description": description,
        }
    return {
        "Software": "pssd_viz",
        "Title": spec.metadata.title,
        "Description": description,
    }


def _load_matplotlib():
    try:
        import matplotlib
    except ImportError as exc:  # pragma: no cover - exercised in dependency-missing installs
        raise VisualizationDependencyError(
            "Matplotlib is required for rendering. Install the optional dependency "
            "with `pip install -e '.[viz]'`."
        ) from exc

    matplotlib.use("Agg", force=True)
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover
        raise VisualizationDependencyError(
            "Matplotlib pyplot could not be imported after selecting the Agg backend."
        ) from exc
    return matplotlib, plt
