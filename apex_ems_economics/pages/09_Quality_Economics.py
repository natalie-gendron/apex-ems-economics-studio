"""Page 9: Quality Economics."""
import pandas as pd
import streamlit as st

from components.executive_cards import formula_expander
from components.state import editable_table, get_data, get_result, get_settings, page_setup, scenario_selector
from core.quality_engine import copq, get_quality_row

page_setup("Quality Economics",
           "Cost of poor quality by supplier and product, split into total and OEM-borne shares.")

data = get_data()
settings = get_settings()
scenario_id, scenario_name = scenario_selector()

st.subheader("Quality metrics")
st.caption("Responsibility columns (OEM / Shared / EMS) determine the OEM-borne share of each "
           "cost per the configurable shares in global settings (OEM 100% / Shared 50% / EMS 20% "
           "residual).")
editable_table("quality_metrics", column_config={
    "scrap_responsibility": st.column_config.SelectboxColumn(options=["OEM", "Shared", "EMS", "Unknown"]),
    "rework_responsibility": st.column_config.SelectboxColumn(options=["OEM", "Shared", "EMS", "Unknown"]),
    "warranty_responsibility": st.column_config.SelectboxColumn(options=["OEM", "Shared", "EMS", "Unknown"]),
    "confidence": st.column_config.SelectboxColumn(options=["High", "Medium", "Low"]),
})

formula_expander("Cost-of-poor-quality formulas", """
```
Scrap             = volume × scrap rate × unit price
Rework            = volume × rework rate × rework hours × rework labor rate
Retest            = volume × rework rate × retest cost/unit
Returns           = volume × return rate × unit price × 0.5
Warranty          = volume × warranty rate × unit price
Field failures    = volume × field-failure rate × unit price × repair multiplier
Downtime          = downtime hours/year × cost/hour × volume share
Premium freight   = quality events/year × cost/event × volume share
Expected recall   = recall probability × recall impact × volume share   ← decision measure
Quality-adjusted unit cost = (quoted cost + OEM-borne COPQ) ÷ good units
```
**Expected recall cost is an expected value, not a booked accounting cost.** Good units =
volume × final yield.
""")

st.divider()
st.subheader(f"COPQ by allocation line — scenario: {scenario_name}")

result = get_result(scenario_id)
rows = []
for _, line in result.line_items.iterrows():
    q = get_quality_row(data, line["supplier_id"], line["product_id"])
    detail = copq(q, line["volume"], line["unit_price"], settings,
                  volume_share=line["allocation_pct"] / 100.0)
    rows.append({
        "Product": line["product_name"], "Supplier": line["supplier_name"],
        "Scrap": detail["scrap_cost"], "Rework": detail["rework_cost"],
        "Retest": detail["retest_cost"], "Returns": detail["return_cost"],
        "Warranty": detail["warranty_cost"], "Field failures": detail["field_failure_cost"],
        "Downtime": detail["downtime_cost"], "Premium freight": detail["premium_freight_cost"],
        "Expected recall*": detail["expected_recall_cost"],
        "Total COPQ (all parties)": detail["total_copq"],
        "OEM-borne COPQ": detail["oem_copq"],
        "COPQ $/unit": detail["copq_per_unit"],
        "Final yield %": detail["final_yield_pct"],
    })
df = pd.DataFrame(rows)
money = [c for c in df.columns if c not in ("Product", "Supplier", "Final yield %")]
st.dataframe(df, hide_index=True, width="stretch", column_config={
    **{c: st.column_config.NumberColumn(c, format="$%,.0f") for c in money},
    "COPQ $/unit": st.column_config.NumberColumn("COPQ $/unit", format="$%,.2f"),
    "Final yield %": st.column_config.NumberColumn("Final yield %", format="%.1f%%")})
st.caption(
    "*Expected recall cost is a probability-weighted decision measure. "
    "The OEM-borne column is what enters the economic model; the all-parties column shows the "
    "full quality burden including what the EMS absorbs. In the sample data, Meridian's weaker "
    "yields AND weaker contractual recovery (OEM warranty responsibility) both raise the OEM-borne share.")
