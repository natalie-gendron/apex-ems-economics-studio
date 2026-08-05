"""Styled read-only table helpers."""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

from services.export_service import to_csv_bytes


def money_table(
    df: pd.DataFrame,
    money_cols: List[str],
    pct_cols: Optional[List[str]] = None,
    rename: Optional[Dict[str, str]] = None,
    download_name: Optional[str] = None,
    key: Optional[str] = None,
) -> None:
    """Display a dataframe with currency/percent formatting and CSV download."""
    if df.empty:
        st.info("No data to display.")
        return
    show = df.copy()
    if rename:
        show = show.rename(columns=rename)
        money_cols = [rename.get(c, c) for c in money_cols]
        pct_cols = [rename.get(c, c) for c in (pct_cols or [])]
    config: Dict[str, object] = {}
    for col in money_cols:
        if col in show.columns:
            config[col] = st.column_config.NumberColumn(col, format="$%,.0f")
    for col in pct_cols or []:
        if col in show.columns:
            config[col] = st.column_config.NumberColumn(col, format="%.1f%%")
    st.dataframe(show, width="stretch", column_config=config, hide_index=True)
    if download_name:
        st.download_button(
            f"Download {download_name}.csv", to_csv_bytes(df),
            file_name=f"{download_name}.csv", mime="text/csv",
            key=key or f"dl_{download_name}")
