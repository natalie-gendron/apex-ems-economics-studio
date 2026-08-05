"""Plotly chart components with a restrained, validated palette.

Palette notes (dataviz method):
  * Categorical slots are assigned in FIXED order and keyed to the entity
    (supplier), never to rank - filtering does not repaint survivors.
  * Sequential = one hue (blue); diverging = blue vs red with gray midpoint.
  * One axis per chart; thin marks; recessive gridlines; selective labels.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go

# Validated categorical palette (fixed slot order).
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
               "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING_NEG = "#2a78d6"   # favorable / decrease
DIVERGING_POS = "#d03b3b"   # unfavorable / increase
NEUTRAL = "#898781"
GRID = "#e1e0d9"
INK = "#0b0b0b"

_LAYOUT = dict(
    template="plotly_white",
    font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=INK, size=13),
    margin=dict(l=10, r=10, t=40, b=10),
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(gridcolor=GRID, zerolinecolor="#c3c2b7"),
    yaxis=dict(gridcolor=GRID, zerolinecolor="#c3c2b7"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)


def supplier_color_map(supplier_ids: List[str]) -> Dict[str, str]:
    """Stable entity->color assignment: sorted ids take fixed slots."""
    return {sid: CATEGORICAL[i % len(CATEGORICAL)]
            for i, sid in enumerate(sorted(set(supplier_ids)))}


def waterfall(bridge: pd.DataFrame, title: str, value_col: str = "value") -> go.Figure:
    """Cost bridge waterfall: first bar absolute, adders relative, total at end."""
    if bridge.empty:
        return go.Figure()
    measures = ["absolute"] + ["relative"] * (len(bridge) - 1) + ["total"]
    x = bridge["step"].tolist() + ["True economic cost"]
    y = bridge[value_col].tolist() + [0]
    fig = go.Figure(go.Waterfall(
        x=x, y=y, measure=measures,
        text=[f"${v:,.0f}" for v in bridge[value_col]] + [f"${bridge[value_col].sum():,.0f}"],
        textposition="outside",
        connector=dict(line=dict(color=GRID, width=1)),
        increasing=dict(marker=dict(color=DIVERGING_POS)),
        decreasing=dict(marker=dict(color=DIVERGING_NEG)),
        totals=dict(marker=dict(color=SEQ_BLUE[4])),
    ))
    fig.update_layout(title=title, showlegend=False, **_LAYOUT)
    return fig


def stacked_cost_bars(
    df: pd.DataFrame, x_col: str, buckets: List[tuple], title: str,
) -> go.Figure:
    """Stacked annual cost buckets (buckets = [(column, label), ...]).

    Buckets take sequential-blue steps (they are parts of one magnitude, not
    independent identities), keeping supplier hues free for supplier identity.
    """
    fig = go.Figure()
    n = len(buckets)
    for i, (col, label) in enumerate(buckets):
        fig.add_trace(go.Bar(
            x=df[x_col], y=df[col], name=label,
            marker=dict(color=SEQ_BLUE[min(i, len(SEQ_BLUE) - 1)],
                        line=dict(color="#fcfcfb", width=2)),
        ))
    fig.update_layout(barmode="stack", title=title, **_LAYOUT)
    return fig


def grouped_bar(
    df: pd.DataFrame, x_col: str, series: List[tuple], title: str,
    y_title: str = "", colors: Optional[List[str]] = None,
) -> go.Figure:
    fig = go.Figure()
    palette = colors or CATEGORICAL
    for i, (col, label) in enumerate(series):
        fig.add_trace(go.Bar(
            x=df[x_col], y=df[col], name=label,
            marker=dict(color=palette[i % len(palette)], line=dict(color="#fcfcfb", width=2)),
        ))
    layout = dict(_LAYOUT)
    layout["yaxis"] = {**layout["yaxis"], "title": y_title}
    fig.update_layout(barmode="group", title=title, **layout)
    return fig


def per_unit_comparison(
    df: pd.DataFrame, name_col: str, quoted_col: str, econ_col: str, title: str,
) -> go.Figure:
    """Quoted vs true economic cost per unit, per supplier/scenario."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[name_col], y=df[quoted_col], name="Quoted per unit",
        marker=dict(color=SEQ_BLUE[1], line=dict(color="#fcfcfb", width=2)),
        text=[f"${v:,.0f}" for v in df[quoted_col]], textposition="outside"))
    fig.add_trace(go.Bar(
        x=df[name_col], y=df[econ_col], name="True economic per unit",
        marker=dict(color=SEQ_BLUE[4], line=dict(color="#fcfcfb", width=2)),
        text=[f"${v:,.0f}" for v in df[econ_col]], textposition="outside"))
    fig.update_layout(barmode="group", title=title, **_LAYOUT)
    return fig


def tornado(sensitivities: pd.Series, title: str) -> go.Figure:
    """Driver sensitivity chart (correlation with outcome)."""
    if sensitivities.empty:
        return go.Figure()
    s = sensitivities.sort_values(key=abs)
    colors = [DIVERGING_POS if v > 0 else DIVERGING_NEG for v in s.values]
    fig = go.Figure(go.Bar(
        x=s.values, y=s.index, orientation="h",
        marker=dict(color=colors), text=[f"{v:+.2f}" for v in s.values],
        textposition="outside"))
    layout = dict(_LAYOUT)
    layout["xaxis"] = {**layout["xaxis"], "title": "Correlation with total economic cost",
                       "range": [-1.15, 1.15]}
    fig.update_layout(title=title, showlegend=False, **layout)
    return fig


def histogram(values: pd.Series, title: str, x_title: str = "") -> go.Figure:
    fig = go.Figure(go.Histogram(
        x=values, nbinsx=40,
        marker=dict(color=SEQ_BLUE[3], line=dict(color="#fcfcfb", width=1))))
    p10, p50, p90 = values.quantile(0.1), values.quantile(0.5), values.quantile(0.9)
    for v, label in [(p10, "P10"), (p50, "P50"), (p90, "P90")]:
        fig.add_vline(x=v, line=dict(color=NEUTRAL, dash="dot", width=1),
                      annotation_text=label, annotation_position="top")
    layout = dict(_LAYOUT)
    layout["xaxis"] = {**layout["xaxis"], "title": x_title}
    fig.update_layout(title=title, showlegend=False, **layout)
    return fig


def scenario_delta_bars(comparison: pd.DataFrame, baseline_id: str, title: str) -> go.Figure:
    """Delta vs baseline per scenario (favorable = blue/down)."""
    df = comparison[comparison["scenario_id"] != baseline_id]
    if df.empty or "delta_total_vs_baseline" not in df.columns:
        return go.Figure()
    colors = [DIVERGING_NEG if v < 0 else DIVERGING_POS for v in df["delta_total_vs_baseline"]]
    fig = go.Figure(go.Bar(
        x=df["scenario_name"], y=df["delta_total_vs_baseline"],
        marker=dict(color=colors),
        text=[f"${v:,.0f}" for v in df["delta_total_vs_baseline"]],
        textposition="outside"))
    layout = dict(_LAYOUT)
    layout["yaxis"] = {**layout["yaxis"], "title": "Δ total economic cost vs baseline ($/yr)"}
    fig.update_layout(title=title, showlegend=False, **layout)
    return fig
