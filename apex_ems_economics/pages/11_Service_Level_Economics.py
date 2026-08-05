"""Page 11: Service-Level Economics."""
import pandas as pd
import streamlit as st

from components.executive_cards import formula_expander
from components.state import editable_table, get_data, get_result, get_settings, page_setup, scenario_selector
from core.logistics_engine import get_lane
from core.service_engine import get_service_row, service_cost

page_setup("Service-Level Economics",
           "The cost of service performance: safety stock, expedites, expected stockouts, penalties.")

data = get_data()
settings = get_settings()
scenario_id, scenario_name = scenario_selector()

st.subheader("Service levels by supplier")
editable_table("service_levels", column_config={
    "confidence": st.column_config.SelectboxColumn(options=["High", "Medium", "Low"]),
})

formula_expander("Service cost formulas", """
```
Safety-stock cost   = safety-stock days ÷ 365 × annual spend × carrying %
Buffer-stock cost   = buffer-stock days ÷ 365 × annual spend × carrying %
Expedite cost       = expedite rate % × volume × (expedite freight − standard freight)/unit
Expected stockout   = stockout probability × revenue-at-risk % × revenue × margin %  ← decision measure
Penalties           = contractual customer penalties × volume share
Service cost        = sum of the above
Service-adjusted cost/unit = (quoted + service cost) ÷ good units
```
A supplier with a **higher unit price can be economically superior** through shorter lead
times (less safety stock), better OTD (fewer expedites and stockouts), and more flexibility.
""")

st.divider()
st.subheader(f"Service cost by allocation line — scenario: {scenario_name}")

result = get_result(scenario_id)
rows = []
for _, line in result.line_items.iterrows():
    svc = get_service_row(data, line["supplier_id"])
    lane = get_lane(data, line["supplier_id"], line["site_id"])
    sc = service_cost(svc, lane, line["volume"], line["quoted_cost"], line["revenue"],
                      settings, volume_share=line["allocation_pct"] / 100.0)
    rows.append({
        "Product": line["product_name"], "Supplier": line["supplier_name"],
        "Safety stock": sc["safety_stock_cost"], "Buffer stock": sc["buffer_stock_cost"],
        "Expedites": sc["expedite_cost"], "Expected stockout*": sc["stockout_expected_cost"],
        "Penalties": sc["penalty_cost"], "Service cost": sc["service_cost"],
        "Revenue at risk": sc["revenue_at_risk"],
        "Service $/unit": sc["service_cost"] / line["volume"] if line["volume"] else 0,
    })
df = pd.DataFrame(rows)
money = [c for c in df.columns if c not in ("Product", "Supplier")]
st.dataframe(df, hide_index=True, width="stretch", column_config={
    **{c: st.column_config.NumberColumn(c, format="$%,.0f") for c in money},
    "Service $/unit": st.column_config.NumberColumn("Service $/unit", format="$%,.2f")})
st.caption("*Expected stockout cost is a probability-weighted lost-margin estimate (decision "
           "measure), not a booked cost. Sample data: Meridian's 45-day safety stock and 9% "
           "expedite rate cost far more than Atlas's 15-day / 2% profile — service performance "
           "priced in dollars.")

st.subheader("Performance vs commitment")
sl = data["service_levels"]
perf = sl[["supplier_id", "target_otd_pct", "actual_otd_pct",
           "target_lead_time_days", "actual_lead_time_days",
           "upside_flex_pct", "recovery_time_weeks"]].copy()
perf["otd_gap_pts"] = perf["actual_otd_pct"] - perf["target_otd_pct"]
st.dataframe(perf, hide_index=True, width="stretch")
