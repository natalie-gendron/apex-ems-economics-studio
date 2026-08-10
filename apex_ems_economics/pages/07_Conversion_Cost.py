"""Page 6: Conversion and Manufacturing Cost."""
import pandas as pd
import streamlit as st

from components.executive_cards import formula_expander
from components.tables import display_table
from components.formatting import md
from components.state import editable_table, get_data, page_setup
from core.economics_engine import conversion_cost_per_unit, material_cost_per_unit

page_setup("Conversion & Manufacturing Cost",
           "EMS conversion economics per product-supplier: labor, equipment, test, overhead, fees, margin.")

data = get_data()

st.subheader("Conversion cost inputs")
st.caption("Rates in USD. Percentages apply as documented in the formula expander. "
           "Where the supplier provides no breakdown (e.g. bundled pricing), enter benchmark "
           "estimates and mark confidence Low.")
editable_table("conversion_costs", column_config={
    "confidence": st.column_config.SelectboxColumn("Confidence", options=["High", "Medium", "Low"]),
})

formula_expander("Conversion cost formulas", """
```
Direct labor      = labor hours/unit × labor rate
Burdened labor    = direct labor × (1 + labor burden %)
Equipment         = machine hours/unit × machine rate
Test              = test hours × test rate
Setup allocation  = setup hours × burdened rate ÷ batch size
Indirect labor    = burdened labor × indirect %
Factory overhead  = (burdened labor + equipment) × overhead %
Program mgmt fee  = subtotal × program mgmt %
Procurement fee   = material base × procurement %
Material handling = material base × handling %
Supplier margin   = (subtotal + fees) × margin %
Total conversion  = subtotal + fees + margin
```
The conversion estimate is a **transparency layer inside the quote** — it feeds should-cost
and residual analysis and is never added on top of the quoted price.
""")

st.divider()
st.subheader("Calculated conversion cost per unit")

rows = []
for _, cc in data["conversion_costs"].iterrows():
    pid, sid = cc["product_id"], cc["supplier_id"]
    material = material_cost_per_unit(data, pid)
    conv = conversion_cost_per_unit(data, pid, sid, material["material_total"])
    rows.append({
        "product_id": pid, "supplier_id": sid,
        "Direct labor": conv["direct_labor"], "Burdened labor": conv["burdened_labor"],
        "Equipment": conv["equipment"], "Test": conv["test"], "Setup": conv["setup"],
        "Indirect": conv["indirect"], "Factory OH": conv["factory_overhead"],
        "PM fee": conv["program_mgmt"], "Procurement fee": conv["procurement_fee"],
        "Mat. handling": conv["material_handling"], "Supplier margin": conv["supplier_margin"],
        "Total conversion": conv["conversion_total"],
        "confidence": cc.get("confidence", ""),
    })
df = pd.DataFrame(rows)
money_cols = [c for c in df.columns if c not in ("product_id", "supplier_id", "confidence")]
display_table(df, overrides={
    c: st.column_config.NumberColumn(c, format="$%,.2f") for c in money_cols})
st.caption(md("Labor-rate contrast in the sample data: Guadalajara $9.50/hr vs Penang $4.10/hr vs "
           "Kaohsiung $6.80/hr — cheap labor does not decide total economics on its own.")
)