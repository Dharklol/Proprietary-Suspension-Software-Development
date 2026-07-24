"""Headless deterministic renderer for engineering figures.

Matplotlib is an optional dependency.  Importing :mod:`pssd_viz` never imports it;
this module resolves it only when rendering is explicitly requested.
"""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from typing import Iterable

from .contracts import EngineeringFigureSpec, FigureAvailability


class VisualizationDependencyError(RuntimeError):
    """Raised when the optional plotting backend is not installed."""


_LINE_STYLES = ("-", "--", "-.", ":")


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
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.5,
        "figure.dpi": 120,
        "savefig.dpi": 160,
    }
    context = matplotlib.rc_context(rc) if hasattr(matplotlib, "rc_context") else nullcontext()
    with context:
        fig, ax = plt.subplots(figsize=(8.0, 5.0), constrained_layout=False)
        try:
            if spec.availability is FigureAvailability.AVAILABLE:
                _render_available(ax, spec)
            else:
                _render_unavailable(ax, spec)

            fig.suptitle(spec.metadata.title)
            fig.subplots_adjust(left=0.11, right=0.97, top=0.88, bottom=0.22)
            fig.text(
                0.01,
                0.02,
                spec.metadata.footer_text(),
                ha="left",
                va="bottom",
                fontsize=6.5,
                wrap=True,
            )
            if spec.metadata.notes:
                fig.text(
                    0.01,
                    0.075,
                    "Notes: " + " | ".join(spec.metadata.notes),
                    ha="left",
                    va="bottom",
                    fontsize=6.5,
                    wrap=True,
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


def _render_available(ax, spec: EngineeringFigureSpec) -> None:
    for index, series in enumerate(spec.series):
        ax.plot(
            series.x,
            series.y,
            label=series.label,
            linestyle=_LINE_STYLES[index % len(_LINE_STYLES)],
        )
    ax.set_xlabel(spec.metadata.x_axis_label)
    ax.set_ylabel(spec.metadata.y_axis_label)
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
        spec.unavailable_reason,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=10,
        wrap=True,
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
