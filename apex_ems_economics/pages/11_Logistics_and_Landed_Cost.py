"""Page 10: Logistics, Duties, and Landed Cost."""
import pandas as pd
import streamlit as st

from components.executive_cards import formula_expander
from components.tables import display_table
from components.formatting import md
from components.state import editable_table, get_data, get_result, page_setup, scenario_selector
from core.logistics_engine import get_lane, landed_cost_per_unit

page_setup("Logistics, Duties & Landed Cost",
           "Per-lane freight, duties, tariffs, and handling; landed cost per unit and per scenario.")

data = get_data()
scenario_id, scenario_name = scenario_selector()

st.subheader("Logistics lanes")
st.caption("Routine logistics only: service-driven expedites are priced on the Service page, "
           "quality-driven premium freight on the Quality page — no double counting. "
           "freight_paid_by reflects incoterms: under FOB/FCA the OEM pays main freight.")
editable_table("logistics_assumptions", column_config={
    "freight_paid_by": st.column_config.SelectboxColumn(options=["OEM", "EMS", "Shared"]),
    "confidence": st.column_config.SelectboxColumn(options=["High", "Medium", "Low"]),
})

formula_expander("Landed-cost formulas", """
```
Freight/unit     = lane freight cost per unit (0 if EMS pays or quote includes freight)
Insurance/unit   = unit price × insurance %
Brokerage/unit   = brokerage per shipment ÷ units per shipment
Duties/unit      = unit price × duty %
Tariffs/unit     = unit price × tariff %
Logistics/unit   = freight + insurance + brokerage + packaging + handling + warehousing
Total landed cost/unit = quoted price + logistics/unit + duties/unit + tariffs/unit
```
Transit days also feed working capital (OEM owns in-transit goods under FOB/FCA terms).
""")

st.divider()
st.subheader(f"Landed cost by allocation line — scenario: {scenario_name}")

result = get_result(scenario_id)
rows = []
for _, line in result.line_items.iterrows():
    lane = get_lane(data, line["supplier_id"], line["site_id"])
    lc = landed_cost_per_unit(lane, line["unit_price"])
    rows.append({
        "Product": line["product_name"], "Supplier": line["supplier_name"],
        "Quoted $/unit": line["unit_price"],
        "Freight": lc["freight"], "Insurance": lc["insurance"], "Brokerage": lc["brokerage"],
        "Packaging": lc["packaging"], "Handling": lc["handling"], "Warehousing": lc["warehousing"],
        "Duties": lc["duties"], "Tariffs": lc["tariffs"],
        "Logistics $/unit": lc["logistics_per_unit"],
        "Landed $/unit": line["unit_price"] + lc["logistics_per_unit"] + lc["duty_per_unit"],
        "Annual logistics + duties": (lc["logistics_per_unit"] + lc["duty_per_unit"]) * line["volume"],
    })
df = pd.DataFrame(rows)
money = [c for c in df.columns if c not in ("Product", "Supplier")]
display_table(df, overrides={
    **{c: st.column_config.NumberColumn(c, format="$%,.2f") for c in money},
    "Annual logistics + duties": st.column_config.NumberColumn(
        "Annual logistics + duties", format="$%,.0f")})
st.caption(md("In the sample data the Penang lane carries ~$118/unit ocean freight plus a 4.5% "
           "tariff — on a >$10K channel card the tariff alone is ~$450/unit, a major reason "
           "Meridian's low quote does not survive landed-cost scrutiny. Carbon/sustainability "
           "cost is a future enhancement."))
