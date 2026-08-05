"""Page 14: Scenario Builder."""
import pandas as pd
import streamlit as st

from components.state import editable_table, get_data, page_setup, set_table

page_setup("Scenario Builder",
           "Create, duplicate, and edit scenarios: demand, allocations, overrides, one-time costs.")

data = get_data()

st.subheader("Scenarios")
st.caption("demand_multiplier scales every product's volume (e.g. 0.8 = demand down 20%). "
           "one_time_cost and transition_cost are year-1 scenario-level costs (qualification, "
           "tooling, dual-ramp, severance, write-offs).")
editable_table("scenarios")

# ----------------------------------------------------------- duplicate helper
with st.expander("Duplicate a scenario"):
    scenarios = data["scenarios"]
    src = st.selectbox("Scenario to duplicate", scenarios["scenario_id"].tolist(),
                       format_func=lambda s: f"{s} — "
                       f"{scenarios.set_index('scenario_id').loc[s, 'scenario_name']}")
    new_id = st.text_input("New scenario id", value="SCN-005")
    new_name = st.text_input("New scenario name", value="Copy of scenario")
    if st.button("Duplicate"):
        if new_id in scenarios["scenario_id"].values:
            st.error(f"Scenario id {new_id} already exists.")
        else:
            row = scenarios[scenarios["scenario_id"] == src].iloc[0].copy()
            row["scenario_id"], row["scenario_name"] = new_id, new_name
            row["is_baseline"], row["status"] = False, "Draft"
            set_table("scenarios", pd.concat([scenarios, row.to_frame().T], ignore_index=True))

            alloc = data["allocations"]
            copied = alloc[alloc["scenario_id"] == src].copy()
            copied["scenario_id"] = new_id
            set_table("allocations", pd.concat([alloc, copied], ignore_index=True))

            ovr = data["scenario_overrides"]
            covr = ovr[ovr["scenario_id"] == src].copy()
            if not covr.empty:
                covr["scenario_id"] = new_id
                covr["override_id"] = covr["override_id"] + "-C"
                set_table("scenario_overrides", pd.concat([ovr, covr], ignore_index=True))
            st.success(f"Duplicated {src} → {new_id} (allocations and overrides copied).")
            st.rerun()

st.divider()
st.subheader("Allocations (product → supplier/site, % of volume)")
st.caption("Per scenario and product, allocation percentages must sum to 100. "
           "Validation flags violations on the home page.")
editable_table("allocations", column_config={
    "allocation_pct": st.column_config.NumberColumn("Allocation %", min_value=0, max_value=100),
})

st.divider()
st.subheader("Scenario overrides (absolute values or changes from baseline)")
st.caption("""
Each override patches one field on one row for that scenario. change_type: **absolute**
(replace), **multiplier** (scale), **delta** (add). Special fields: quotes accept
`price_multiplier` (scales base + all tiers); inventory accepts `ownership_to_ems_share`
(converts % of an OEM-owned record to EMS ownership — consignment renegotiations).
Entities: product, quote, contract_term, inventory, risk, quality, logistics, service, capacity.
""")
editable_table("scenario_overrides", column_config={
    "entity": st.column_config.SelectboxColumn(options=[
        "product", "quote", "contract_term", "inventory", "risk",
        "quality", "logistics", "service", "capacity"]),
    "change_type": st.column_config.SelectboxColumn(options=["absolute", "multiplier", "delta"]),
})

with st.expander("Scenario recipe examples"):
    st.markdown("""
| Goal | How |
|---|---|
| Demand −20% | scenarios.demand_multiplier = 0.8 |
| Shift 25% of P-100 to Meridian | allocations: P-100 → SUP-ATL 75 / SUP-MER 25 |
| Supplier price +5% | override: quote / price_multiplier / multiplier / 1.05 |
| Tariff increase to 15% | override: logistics / LANE-MER-PEN / tariff_rate_pct / absolute / 15 |
| Quality deteriorates | override: quality / SUP-MER / scrap_rate_pct / delta / +1.5 |
| Payment terms renegotiated | override: contract_term / CT-ATL-PAY / value / absolute / 75 |
| Consignment → EMS-owned | override: inventory / INV-001 / ownership_to_ems_share / absolute / 60 |
| Dual-source risk reduction | override: risk / RSK-006 / probability_pct / absolute / 3 |
| Lower safety stock | override: service / SUP-MER / safety_stock_days / absolute / 30 |
| FX / freight shock | override: logistics / lane / freight_cost_per_unit / multiplier / 1.3 |
""")
