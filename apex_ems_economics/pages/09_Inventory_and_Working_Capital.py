"""Page 8: Inventory and Working Capital - ownership vs location modeled separately."""
import streamlit as st

from components.executive_cards import formula_expander, metric_row
from components.formatting import fmt_currency_compact, md
from components.tables import display_table
from components.state import editable_table, get_data, get_result, get_settings, page_setup, scenario_selector
from core import inventory_engine
from core.inventory_engine import carrying_cost_decomposition, exposure_summary, ownership_location_matrix
from models.schemas import InventoryStage, Ownership, PhysicalLocation

page_setup("Inventory & Working Capital",
           "Financial ownership and physical location are modeled separately: OEM-owned material "
           "can sit at an EMS site, and EMS-owned material can back OEM demand.")

data = get_data()
settings = get_settings()
scenario_id, scenario_name = scenario_selector()

# ------------------------------------------------------------- exposure
exp = exposure_summary(data, settings)
if exp:
    st.subheader("Inventory exposure (baseline records)")
    metric_row([
        ("OEM-owned @ OEM sites", fmt_currency_compact(exp["oem_owned_at_oem_sites"]), None),
        ("OEM-owned @ EMS sites", fmt_currency_compact(exp["oem_owned_at_ems_sites"]), None),
        ("OEM-owned in transit", fmt_currency_compact(exp["oem_owned_in_transit"]), None),
        ("EMS-owned @ EMS sites", fmt_currency_compact(exp["ems_owned_at_ems_sites"]), None),
    ])
    metric_row([
        ("Balance-sheet inventory (OEM)", fmt_currency_compact(exp["balance_sheet_inventory"]), None),
        ("Off-balance-sheet exposure", fmt_currency_compact(exp["off_balance_sheet_exposure"]), None),
        ("Excess + NCNR liability", fmt_currency_compact(exp["excess_value"] + exp["ncnr_liability_value"]), None),
        ("Annual carrying cost", fmt_currency_compact(exp["annual_carrying_cost"]), None),
    ])
    st.caption(
        "Off-balance-sheet exposure is EMS/supplier-owned inventory dedicated to OEM demand: "
        "not on the OEM balance sheet, but an economic commitment (liability windows, buyback "
        "provisions) if demand falls.")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Ownership × location matrix")
    matrix = ownership_location_matrix(data)
    st.dataframe(matrix.style.format("${:,.0f}"), width="stretch")
with col2:
    st.subheader("Carrying-cost decomposition")
    decomp = carrying_cost_decomposition(exp.get("oem_owned_total", 0.0), settings)
    display_table(decomp, overrides={
        "Rate %": st.column_config.NumberColumn(format="%.2f%%"),
        "Annual cost": st.column_config.NumberColumn(format="$%,.0f")})
    st.caption("Components are editable in global_settings.csv (cost of capital, storage, "
               "insurance, shrinkage, handling, obsolescence, administrative).")

formula_expander("Working-capital cost formulas", """
```
Inventory carrying cost   = average OEM-owned inventory value × annual carrying-cost %
Advance-payment cost      = advance % × annual spend × cost of capital
Payment-terms effect      = (reference days − payment days) ÷ 365 × annual spend × cost of capital
                            (negative = benefit when terms are longer than the reference)
Working-capital cost      = carrying + advances + terms effect
DIO                       = OEM inventory value ÷ (annual COGS ÷ 365)
```
For scenario analysis, each supplier's OEM-owned **inventory-days intensity** is derived from
the baseline records and scaled with allocated spend, so shifting volume to a supplier with
worse consignment terms correctly increases OEM-owned inventory.
""")

st.divider()

# ------------------------------------------------------------- scenario view
result = get_result(scenario_id)
li = result.line_items
if not li.empty:
    st.subheader(f"Scenario working-capital cost: {scenario_name}")
    view = li[["product_name", "supplier_name", "oem_inventory_value",
               "wc_carrying", "wc_advance", "wc_terms_effect", "wc_cost"]]
    display_table(view, overrides={
        c: st.column_config.NumberColumn(c, format="$%,.0f")
        for c in ["oem_inventory_value", "wc_carrying", "wc_advance", "wc_terms_effect", "wc_cost"]})
    dio = inventory_engine.days_inventory_outstanding(
        result.totals["oem_inventory_value"], result.totals["cogs_relevant_cost"])
    st.caption(md(f"Modeled OEM inventory {fmt_currency_compact(result.totals['oem_inventory_value'])} "
               f"≈ {dio:.0f} days inventory outstanding at scenario COGS. Note the payment-terms "
               "effect: Pacific (net 75) generates a financing benefit; Meridian (net 30 + 10% "
               "advance) a financing cost."))

st.divider()
st.subheader("Inventory records")
editable_table("inventory_records", column_config={
    "stage": st.column_config.SelectboxColumn("Stage", options=[s.value for s in InventoryStage]),
    "ownership": st.column_config.SelectboxColumn("Ownership", options=[o.value for o in Ownership]),
    "physical_location": st.column_config.SelectboxColumn(
        "Physical location", options=[p.value for p in PhysicalLocation]),
    "unit_cost": st.column_config.NumberColumn("Unit cost", format="$%,.2f"),
})
