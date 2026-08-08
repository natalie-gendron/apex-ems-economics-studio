"""Page 16: Contract Opportunity Analysis."""
import pandas as pd
import streamlit as st

from components.formatting import fmt_currency_compact
from components.state import editable_table, get_data, get_settings, page_setup
from core.config import carrying_cost_pct

page_setup("Contract Opportunity Analysis",
           "Negotiation levers with quantified annual savings, cash impact, and difficulty.")

data = get_data()
settings = get_settings()
levers = data["negotiation_levers"]

st.subheader("Negotiation lever register")
st.caption("annual_savings = recurring P&L impact (negative = a cost/give). "
           "working_capital_impact = one-time cash released. Each lever names an owner and next action.")
editable_table("negotiation_levers", column_config={
    "annual_savings": st.column_config.NumberColumn("Annual savings", format="$%,.0f"),
    "working_capital_impact": st.column_config.NumberColumn("WC impact (cash)", format="$%,.0f"),
    "risk_impact": st.column_config.SelectboxColumn(
        options=["Reduces", "Neutral", "Slightly increases", "Increases"]),
    "implementation_difficulty": st.column_config.SelectboxColumn(options=["Low", "Medium", "High"]),
    "negotiation_difficulty": st.column_config.SelectboxColumn(options=["Low", "Medium", "High"]),
    "confidence": st.column_config.SelectboxColumn(options=["High", "Medium", "Low"]),
})

st.divider()
st.subheader("Prioritized opportunities")
if not levers.empty:
    rate = carrying_cost_pct(settings) / 100.0
    ranked = levers.copy()
    ranked["annual_savings"] = pd.to_numeric(ranked["annual_savings"], errors="coerce").fillna(0)
    ranked["working_capital_impact"] = pd.to_numeric(
        ranked["working_capital_impact"], errors="coerce").fillna(0)
    # Total annualized value: P&L savings + carrying-cost value of released cash.
    ranked["total_annual_value"] = (ranked["annual_savings"]
                                    + ranked["working_capital_impact"] * rate)
    difficulty_rank = {"Low": 1, "Medium": 2, "High": 3}
    ranked["difficulty_score"] = (
        ranked["implementation_difficulty"].map(difficulty_rank).fillna(2)
        + ranked["negotiation_difficulty"].map(difficulty_rank).fillna(2))
    ranked = ranked.sort_values(["total_annual_value"], ascending=False)

    view = ranked[["lever_id", "supplier_id", "lever", "proposed_change", "annual_savings",
                   "working_capital_impact", "total_annual_value", "difficulty_score",
                   "risk_impact", "confidence", "owner", "next_action"]]
    st.dataframe(view, hide_index=True, width="stretch", column_config={
        "annual_savings": st.column_config.NumberColumn("P&L $/yr", format="$%,.0f"),
        "working_capital_impact": st.column_config.NumberColumn("Cash", format="$%,.0f"),
        "total_annual_value": st.column_config.NumberColumn("Total annual value*", format="$%,.0f"),
        "difficulty_score": st.column_config.NumberColumn("Difficulty (2=easy, 6=hard)"),
    })
    st.caption(f"*Total annual value = P&L savings + released cash × carrying-cost rate "
               f"({carrying_cost_pct(settings):.1f}%). Quick wins: high value, low difficulty "
               "(e.g. the P-100 volume-tier reset is already earned at current volumes).")

    total_pnl = ranked["annual_savings"].clip(lower=0).sum()
    total_cash = ranked["working_capital_impact"].clip(lower=0).sum()
    col1, col2 = st.columns(2)
    col1.metric("Total P&L opportunity (gross)", fmt_currency_compact(total_pnl))
    col2.metric("Total cash-release opportunity (gross)", fmt_currency_compact(total_cash))
    st.caption("Gross of concessions and not additive across mutually exclusive levers; "
               "model chosen combinations as scenarios for a net figure.")
