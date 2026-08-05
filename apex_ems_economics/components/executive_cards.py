"""Executive summary cards and callouts."""
from __future__ import annotations

from typing import List, Optional, Tuple

import streamlit as st

from components.formatting import fmt_currency_compact


def metric_row(metrics: List[Tuple[str, str, Optional[str]]], columns: int = 4) -> None:
    """Render metrics in rows: [(label, value, delta_or_None), ...]."""
    for start in range(0, len(metrics), columns):
        cols = st.columns(columns)
        for col, (label, value, delta) in zip(cols, metrics[start:start + columns]):
            with col:
                if delta is not None:
                    st.metric(label, value, delta, delta_color="inverse")
                else:
                    st.metric(label, value)


def callout_grid(callouts: List[Tuple[str, str, str]], columns: int = 3) -> None:
    """Render titled callout cards: [(title, headline, detail), ...]."""
    for start in range(0, len(callouts), columns):
        cols = st.columns(columns)
        for col, (title, headline, detail) in zip(cols, callouts[start:start + columns]):
            with col:
                with st.container(border=True):
                    st.caption(title)
                    st.markdown(f"**{headline}**")
                    st.caption(detail)


def top_list(title: str, items: List[Tuple[str, float]], money: bool = True) -> None:
    """Ranked top-N list inside a bordered container."""
    with st.container(border=True):
        st.markdown(f"**{title}**")
        for i, (label, value) in enumerate(items, start=1):
            value_str = fmt_currency_compact(value) if money else f"{value:,.0f}"
            st.markdown(f"{i}. {label} — `{value_str}`")


def formula_expander(title: str, formula_md: str) -> None:
    """Standard 'how is this calculated' expander."""
    with st.expander(f"ⓘ {title}"):
        st.markdown(formula_md)
