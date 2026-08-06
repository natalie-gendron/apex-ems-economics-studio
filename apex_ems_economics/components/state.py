"""Shared Streamlit session state: data loading, scenario context, editors.

All pages call ``get_data()`` which loads the CSV repository once into
session state; edits made in data editors update the in-memory frames and
can be persisted back to CSV with the sidebar save button. Engine results
are cached per scenario and invalidated whenever any table is edited.
"""
from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd
import streamlit as st

from core import scenario_engine
from core.config import load_settings
from core.economics_engine import ScenarioResult, compute_scenario
from repositories.csv_repository import CsvRepository

_DATA_KEY = "apex_data"
_REPO_KEY = "apex_repo"
_RESULT_CACHE_KEY = "apex_results"
_DIRTY_KEY = "apex_dirty"


def get_repo() -> CsvRepository:
    if _REPO_KEY not in st.session_state:
        st.session_state[_REPO_KEY] = CsvRepository()
    return st.session_state[_REPO_KEY]


def get_data() -> Dict[str, pd.DataFrame]:
    if _DATA_KEY not in st.session_state:
        st.session_state[_DATA_KEY] = get_repo().load_all()
        st.session_state[_RESULT_CACHE_KEY] = {}
        st.session_state[_DIRTY_KEY] = False
    return st.session_state[_DATA_KEY]


def set_table(name: str, df: pd.DataFrame) -> None:
    st.session_state[_DATA_KEY][name] = df
    st.session_state[_RESULT_CACHE_KEY] = {}  # invalidate engine cache
    st.session_state.pop("mc_result", None)   # simulated results are stale too
    st.session_state[_DIRTY_KEY] = True


def reload_from_disk() -> None:
    st.session_state[_DATA_KEY] = get_repo().load_all()
    st.session_state[_RESULT_CACHE_KEY] = {}
    st.session_state[_DIRTY_KEY] = False


def save_to_disk() -> None:
    get_repo().save_all(get_data())
    st.session_state[_DIRTY_KEY] = False


def get_settings() -> Dict[str, float]:
    return load_settings(get_data())


def get_result(scenario_id: str) -> ScenarioResult:
    cache = st.session_state.setdefault(_RESULT_CACHE_KEY, {})
    if scenario_id not in cache:
        cache[scenario_id] = compute_scenario(get_data(), scenario_id, get_settings())
    return cache[scenario_id]


def baseline_id() -> str:
    return scenario_engine.baseline_scenario_id(get_data())


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------

def page_setup(title: str, caption: str = "") -> None:
    st.set_page_config(page_title=f"{title} - Apex EMS Economics Studio",
                       layout="wide", initial_sidebar_state="expanded")
    st.title(title)
    if caption:
        st.caption(caption)
    _sidebar_common()


def _sidebar_common() -> None:
    with st.sidebar:
        st.markdown("**Apex EMS Economics Studio**")
        data = get_data()
        if st.session_state.get(_DIRTY_KEY):
            st.warning("Unsaved edits (session only).")
            col1, col2 = st.columns(2)
            if col1.button("Save to CSV", width="stretch"):
                save_to_disk()
                st.success("Saved.")
                st.rerun()
            if col2.button("Discard", width="stretch"):
                reload_from_disk()
                st.rerun()
        st.caption(
            f"{len(data['suppliers'])} suppliers · {len(data['products'])} products · "
            f"{len(data['scenarios'])} scenarios")


def scenario_selector(key: str = "scenario_select", label: str = "Scenario") -> Tuple[str, str]:
    """Sidebar scenario picker shared across pages. Returns (id, name)."""
    data = get_data()
    scenarios = data["scenarios"]
    options = scenarios["scenario_id"].tolist()
    names = dict(zip(scenarios["scenario_id"], scenarios["scenario_name"]))
    default = st.session_state.get("active_scenario", baseline_id())
    index = options.index(default) if default in options else 0
    with st.sidebar:
        chosen = st.selectbox(label, options, index=index,
                              format_func=lambda s: names.get(s, s), key=key)
    st.session_state["active_scenario"] = chosen
    return chosen, names.get(chosen, chosen)


def editable_table(
    entity: str, help_text: str = "", column_config: dict | None = None,
    disabled: bool = False, key: str | None = None,
) -> pd.DataFrame:
    """Standard editable data grid bound to a repository entity."""
    data = get_data()
    df = data.get(entity, pd.DataFrame())
    if help_text:
        st.caption(help_text)
    edited = st.data_editor(
        df, num_rows="dynamic", width="stretch", key=key or f"editor_{entity}",
        column_config=column_config, disabled=disabled)
    if not disabled and not edited.equals(df):
        set_table(entity, edited)
        # Recompute the whole page immediately so metrics, charts, and engine
        # results rendered ABOVE this editor also reflect the edit right away.
        # No loop risk: next run stores == editor value, so equals() is True.
        st.rerun()
    return edited
