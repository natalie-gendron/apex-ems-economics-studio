"""Page 19: Model Settings - every global assumption, editable and explained."""
import pandas as pd
import streamlit as st

from components.executive_cards import metric_row
from components.formatting import fmt_pct
from components.state import get_data, get_settings, page_setup, set_table
from core.config import CARRYING_COST_COMPONENTS, SETTING_GROUPS, carrying_cost_pct

page_setup("Model Settings",
           "Every global assumption the engines use — grouped, described, and editable here "
           "rather than buried in code or a CSV.")

data = get_data()
settings = get_settings()
gs = data.get("global_settings", pd.DataFrame())
if gs is None or gs.empty:
    st.error("global_settings table is empty; engines are running on built-in defaults.")
    st.stop()

# ------------------------------------------------------------------ headline
metric_row([
    ("Total inventory carrying cost", fmt_pct(carrying_cost_pct(settings)), None),
    ("Cost of capital", fmt_pct(settings["cost_of_capital_pct"]), None),
    ("In-house assembly & test", fmt_pct(settings["inhouse_conversion_pct_of_revenue"]) + " of revenue", None),
    ("Payment-terms reference", f"{settings['payment_terms_reference_days']:.0f} days", None),
], columns=4)
st.caption("These four drive more of the model's output than any other inputs: carrying cost "
           "prices every day of inventory, the reference days decide whether payment terms read "
           "as a benefit or a cost, and the in-house percentage closes per-system margin.")

# ------------------------------------------------------------------ grouped editors
grouped_keys = {k for keys in SETTING_GROUPS.values() for k in keys}
tabs = st.tabs(list(SETTING_GROUPS.keys()) + ["Other"])

def _editor(keys, tab_key: str) -> None:
    subset = gs[gs["key"].isin(keys)].copy()
    if subset.empty:
        st.caption("No settings in this group.")
        return
    edited = st.data_editor(
        subset, width="stretch", hide_index=True, key=f"settings_{tab_key}",
        disabled=["key", "unit"], num_rows="fixed",
        column_config={
            "key": st.column_config.TextColumn("Setting", width="medium"),
            "value": st.column_config.NumberColumn("Value", required=True),
            "unit": st.column_config.TextColumn("Unit", width="small"),
            "description": st.column_config.TextColumn("What it means", width="large"),
        })
    if not edited.equals(subset):
        merged = gs.copy()
        merged.loc[edited.index, :] = edited
        set_table("global_settings", merged)
        st.rerun()

for tab, (group, keys) in zip(tabs, SETTING_GROUPS.items()):
    with tab:
        _editor(keys, group)
        if group == "Working capital & carrying cost":
            comp_rate = carrying_cost_pct(settings)
            st.info(f"The carrying-cost components sum to **{comp_rate:.2f}%** per year. "
                    "That total is applied to average OEM-owned inventory everywhere in the "
                    "model — inventory, service (safety stock), and working capital.",
                    icon=":material/percent:")
            st.dataframe(pd.DataFrame(
                [{"Component": label, "Rate %": settings.get(key, 0.0)}
                 for key, label in CARRYING_COST_COMPONENTS]
                + [{"Component": "Total", "Rate %": comp_rate}],
            ), hide_index=True, width="stretch",
                column_config={"Rate %": st.column_config.NumberColumn(format="%.2f%%")})
        if group == "Quality responsibility & cost":
            st.caption("Responsibility shares decide how much of each quality cost lands on the "
                       "OEM. The EMS-responsible share is deliberately above zero: even with full "
                       "contractual recovery the OEM absorbs disruption, engineering time, and "
                       "imperfect recovery.")
        if group == "Should-cost":
            bench = sum(settings.get(f"benchmark_{k}_pct", 0.0)
                        for k in ("material", "labor", "overhead", "margin", "other"))
            if abs(bench - 100) > 0.01:
                st.warning(f"Level 1 benchmark structure sums to {bench:.1f}% (expected 100%).")
            else:
                st.success(f"Level 1 benchmark structure sums to {bench:.0f}%.")

with tabs[-1]:
    _editor([k for k in gs["key"] if k not in grouped_keys], "other")

# ------------------------------------------------------------------ guidance
st.divider()
with st.expander("What is deliberately NOT editable here"):
    st.markdown("""
Some values stay in code on purpose, because they are **model structure rather than business
assumptions** — changing them via a form would break the model with no meaningful guardrail:

| Not exposed | Why |
|---|---|
| Entity/table mappings, override target list | Structural wiring; a bad edit silently disables scenario overrides |
| Carrying-cost component *list* | The components are structural; their **rates** are editable above |
| Monte Carlo distribution *types* | Chosen per driver in the engine; the **ranges** live in the Assumption Register |
| Supplier-score rating scales (e.g. "Bundled pricing" → 30 points) | A normalization scale, not a business assumption. It affects only the advisory composite score — never the economics — and the **weights**, which decide what actually matters, are editable on the Risk-Adjusted Economics page. Exposing ten more knobs here would bury the ~20 that move money. |

Everything that changes a dollar figure is either on this page, in the **Assumption Register**,
or in the entity tables themselves.
""")
st.caption("Edits apply immediately across every page and scenario. Use **Save to CSV** in the "
           "sidebar to persist them; **Discard** reverts to the stored values.")
