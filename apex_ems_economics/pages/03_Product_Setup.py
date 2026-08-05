"""Page 3: Product and Subassembly Setup."""
import streamlit as st

from components.state import editable_table, get_data, page_setup

page_setup("Product & Subassembly Setup",
           "Define products and subassemblies, volumes, pricing, and sourcing context.")

data = get_data()

st.caption(
    "Material models supported: EMS turnkey (EMS procures all material), fully or partially "
    "consigned (customer-owned material), and hybrid. The material model interacts with BOM "
    "ownership models and contract inventory terms.")

editable_table("products", column_config={
    "product_type": st.column_config.SelectboxColumn("Type", options=["Product", "Subassembly"]),
    "annual_volume": st.column_config.NumberColumn("Annual volume", min_value=0, format="%,.0f"),
    "unit_selling_price": st.column_config.NumberColumn("Selling price", format="$%,.0f"),
    "current_standard_cost": st.column_config.NumberColumn("Std cost", format="$%,.2f"),
    "lifecycle_stage": st.column_config.SelectboxColumn(
        "Lifecycle", options=["NPI", "Growth", "Mature", "Decline", "End-of-life"]),
    "technical_complexity": st.column_config.SelectboxColumn(
        "Complexity", options=["Low", "Medium", "High", "Very High"]),
    "demand_variability": st.column_config.SelectboxColumn(
        "Demand variability", options=["Low", "Medium", "High"]),
    "product_priority": st.column_config.SelectboxColumn(
        "Priority", options=["Critical", "Standard", "Low"]),
    "transfer_complexity": st.column_config.SelectboxColumn(
        "Transfer complexity", options=["Low", "Medium", "High", "Very High"]),
    "material_model": st.column_config.SelectboxColumn("Material model", options=[
        "EMS turnkey", "Fully consigned", "Hybrid consigned RF components",
        "Partially consigned", "Hybrid"]),
    "target_gross_margin_pct": st.column_config.NumberColumn("Target GM %", format="%.0f%%"),
    "target_service_level_pct": st.column_config.NumberColumn("Target service %", format="%.0f%%"),
})

st.info(
    "Subassemblies reference their parent via parent_product_id and can carry their own "
    "quotes, BOMs, and allocations (e.g. SA-210 is built by Pacific and consigned to Atlas). "
    "Monthly volume is modeled as annual volume ÷ 12; volume seasonality is a future enhancement.")
