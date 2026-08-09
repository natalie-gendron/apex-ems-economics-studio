"""Page 13: Risk-Adjusted Economics."""
import streamlit as st

from components.executive_cards import formula_expander, metric_row
from components.formatting import fmt_currency_compact
from components.tables import display_table
from components.state import editable_table, get_data, get_result, page_setup, scenario_selector
from core.risk_engine import risk_register_with_expected_cost
from core.scoring_engine import supplier_scores, weights_valid

page_setup("Risk-Adjusted Economics",
           "Expected risk cost by supplier and product, and the configurable weighted supplier score.")

data = get_data()
scenario_id, scenario_name = scenario_selector()
result = get_result(scenario_id)

st.subheader("Risk register")
st.caption("Categories: financial, country, natural disaster, geopolitical, cyber, quality, "
           "delivery, capacity, labor, component concentration, single-source, sub-tier, IP, "
           "transition, contract, data transparency.")
editable_table("risks", column_config={
    "probability_pct": st.column_config.NumberColumn("Probability %", min_value=0, max_value=100),
    "financial_impact_usd": st.column_config.NumberColumn("Financial impact", format="$%,.0f"),
    "operational_impact": st.column_config.SelectboxColumn(options=["Low", "Medium", "High", "Severe"]),
    "mitigation_status": st.column_config.SelectboxColumn(
        options=["Open", "Monitoring", "Partially mitigated", "Mitigated", "Accepted"]),
    "confidence": st.column_config.SelectboxColumn(options=["High", "Medium", "Low"]),
})

formula_expander("Risk formulas", """
```
Expected risk cost  = probability × estimated financial impact
Risk-adjusted cost  = base economic cost + Σ expected risk costs
```
**Expected risk cost is a decision-analysis measure, not an accounting expense.** It prices
risk onto the same axis as cost so alternatives can be compared; it is never booked.
Supplier-level risks are allocated to products by spend share; product-level risks by volume.
""")

st.divider()
register = risk_register_with_expected_cost(data)
st.subheader("Expected risk cost ranking")
display_table(register[["risk_id", "supplier_id", "product_id", "category", "description",
                        "probability_pct", "financial_impact_usd", "expected_cost",
                        "mitigation_status", "confidence"]],
              overrides={"probability_pct": st.column_config.NumberColumn(
                  "Probability", format="%.0f%%")})

li = result.line_items
if not li.empty:
    metric_row([
        (f"Scenario expected risk cost ({scenario_name})",
         fmt_currency_compact(result.totals["risk_cost"]), None),
        ("Recurring economic cost", fmt_currency_compact(result.totals["recurring_economic_cost"]), None),
        ("Risk share of economics",
         f"{result.totals['risk_cost'] / result.totals['recurring_economic_cost'] * 100:.1f}%", None),
    ], columns=3)

st.divider()
st.subheader("Risk-adjusted supplier score")
weights = data["scoring_weights"]
if not weights_valid(weights):
    st.error("Scoring weights must sum to 100%. Fix them below.")
st.caption("Weights are editable and must sum to 100%. The score is a decision-support summary "
           "only — it never replaces the detailed economics above.")
editable_table("scoring_weights")

risk_by_sup = li.groupby("supplier_id")["risk_cost"].sum() if not li.empty else None
scores = supplier_scores(data, result.supplier_summary, risk_by_sup)
if not scores.empty:
    score_cols = [c for c in scores.columns if c not in ("supplier_id", "supplier_name")]
    display_table(scores, overrides={
        c: st.column_config.NumberColumn(c, format="%.0f") for c in score_cols})
