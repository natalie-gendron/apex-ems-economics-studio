"""Page 4: BOM and Material Economics."""
import pandas as pd
import streamlit as st

from components.executive_cards import formula_expander
from components.formatting import fmt_currency
from components.tables import display_table
from components.state import editable_table, get_data, page_setup
from core.economics_engine import material_cost_per_unit
from core.should_cost_engine import unexplained_residual
from models.schemas import OwnershipModel, PurchaseResponsibility

page_setup("BOM & Material Economics",
           "Component-level material modeling where data exists; bundled estimates where it does not.")

data = get_data()

st.subheader("BOM items")
editable_table("bom_items", column_config={
    "ownership_model": st.column_config.SelectboxColumn(
        "Ownership model", options=[m.value for m in OwnershipModel]),
    "purchase_responsibility": st.column_config.SelectboxColumn(
        "Purchase responsibility", options=[p.value for p in PurchaseResponsibility]),
    "physical_location": st.column_config.SelectboxColumn(
        "Physical location", options=["OEM site", "EMS site", "In transit",
                                      "Third-party warehouse", "Unknown"]),
    "confidence": st.column_config.SelectboxColumn("Confidence", options=["High", "Medium", "Low"]),
    "unit_price": st.column_config.NumberColumn("Unit price", format="$%,.2f"),
})

formula_expander("Material cost formula", """
```
Component cost = qty × unit price × (1 + scrap%) ÷ yield% × (1 + freight%) × (1 + duty%)
Material cost per assembly = Σ component costs
```
Components with an OEM-owned ownership model count as **consigned material**: their cost is
excluded from the EMS quote and added separately in the economic model (never double counted).
""")

st.divider()
st.subheader("Material cost rollup by product")

rows = []
for pid in data["products"]["product_id"]:
    mc = material_cost_per_unit(data, pid)
    if mc["bom_lines"] == 0:
        continue
    rows.append({
        "product_id": pid, "BOM lines": mc["bom_lines"],
        "Material $/unit": mc["material_total"],
        "EMS-procured $/unit": mc["ems_material"],
        "OEM-consigned $/unit": mc["consigned_material"],
    })
rollup = pd.DataFrame(rows)
display_table(rollup, overrides={
    col: st.column_config.NumberColumn(col, format="$%,.0f")
    for col in ["Material $/unit", "EMS-procured $/unit", "OEM-consigned $/unit"]})

st.divider()
st.subheader("Bundled pricing: unexplained residual")
st.caption(
    "Quotes cover the EMS scope only (OEM-consigned material is excluded), so the residual is "
    "quote minus identified EMS-scope material minus estimated conversion. **It is an analytical "
    "estimate - NOT proof of supplier overcharging.** It may reflect missing BOM lines, benchmark "
    "error, spec differences, or genuine commercial opportunity.")

quotes = data["supplier_quotes"]
res_rows = []
for _, q in quotes.iterrows():
    r = unexplained_residual(data, q["product_id"], q["supplier_id"])
    if r.get("quote_missing"):
        continue
    res_rows.append({
        "quote_id": q["quote_id"], "product_id": q["product_id"], "supplier_id": q["supplier_id"],
        "Quoted price": r["quoted_price"],
        "Identified EMS material": r["identified_material"],
        "Consigned (excluded)": r.get("consigned_material_excluded", 0.0),
        "Estimated conversion": r["estimated_conversion"],
        "Residual": r["residual"],
        "Residual %": r["residual_pct"],
        "Bundled quote": pd.isna(q.get("quoted_material_content")),
    })
residuals = pd.DataFrame(res_rows)
display_table(residuals, overrides={
    "Quoted price": st.column_config.NumberColumn(format="$%,.0f"),
    "Identified EMS material": st.column_config.NumberColumn(format="$%,.0f"),
    "Consigned (excluded)": st.column_config.NumberColumn(format="$%,.0f"),
    "Estimated conversion": st.column_config.NumberColumn(format="$%,.0f"),
    "Residual": st.column_config.NumberColumn(format="$%,.0f"),
    "Residual %": st.column_config.NumberColumn(format="%.1f%%"),
})
st.caption(
    "Large positive residuals on bundled quotes (e.g. Meridian) indicate where cost "
    "transparency or should-cost review would be most valuable. Negative residuals suggest "
    "the estimate is too high or the supplier is pricing below modeled cost.")
