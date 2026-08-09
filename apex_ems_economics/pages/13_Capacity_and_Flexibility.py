"""Page 12: Capacity and Flexibility."""
import streamlit as st

from components.executive_cards import formula_expander
from components.tables import display_table
from components.state import editable_table, get_data, get_result, page_setup, scenario_selector
from core.capacity_engine import capacity_analysis, volume_shift_feasibility

page_setup("Capacity & Flexibility",
           "Headroom, feasibility of scenario allocations, and volume-shift analysis.")

data = get_data()
scenario_id, scenario_name = scenario_selector()
result = get_result(scenario_id)

st.subheader("Capacity records")
editable_table("capacity_records")

formula_expander("Capacity formulas", """
```
Usable capacity      = available × max utilization %
Headroom             = usable − committed
Incremental feasible = headroom + overtime − volume already allocated by this scenario
Volume feasible      = allocated ≤ headroom + overtime
Reservation $/unit   = annual reservation fee ÷ allocated volume
```
Ramp, transfer, qualification, and tooling lead times bound **how fast** a shift can happen
even when capacity exists.
""")

st.divider()
st.subheader(f"Capacity vs scenario allocation — {scenario_name}")
cap = capacity_analysis(data, result.line_items)
if cap.empty:
    st.info("No capacity records.")
else:
    view = cap[["site_id", "supplier_id", "usable_capacity", "committed_capacity", "headroom",
                "overtime_capacity", "allocated_volume_model", "incremental_feasible",
                "volume_feasible", "utilization_pct", "reservation_fee_annual",
                "constraint_notes"]]
    display_table(view, overrides={
        "volume_feasible": st.column_config.CheckboxColumn("Feasible?"),
        "utilization_pct": st.column_config.NumberColumn("Utilization", format="%.0f%%"),
    })
    infeasible = cap[~cap["volume_feasible"]]
    if not infeasible.empty:
        st.error("Allocated volume exceeds feasible capacity at: "
                 + ", ".join(infeasible["site_id"]))
    tight = cap[(cap["utilization_pct"] > cap["max_utilization_pct"] - 8) & cap["volume_feasible"]]
    if not tight.empty:
        st.warning("Sites running close to their utilization ceiling: "
                   + ", ".join(tight["site_id"]) + " — upside flexibility is limited.")

st.divider()
st.subheader("Volume-shift feasibility check")
col1, col2 = st.columns(2)
target = col1.selectbox("Target site", cap["site_id"].tolist() if not cap.empty else [])
volume = col2.number_input("Additional annual volume (units)", min_value=0, value=3000, step=500)
if target:
    check = volume_shift_feasibility(cap, target, float(volume))
    if check["feasible"]:
        st.success(f"Feasible — {check['reason']}. Incremental capacity available: "
                   f"{check['incremental_feasible']:,.0f} units/yr.")
    else:
        st.error(f"Not feasible — {check['reason']}.")
    if "qualification_weeks" in check:
        st.caption(f"Timeline: qualification ~{check['qualification_weeks']:.0f} wks, "
                   f"transfer ~{check['transfer_weeks']:.0f} wks, then ramp at the site's "
                   f"monthly ramp rate. Ramp risk rises when these overlap demand peaks.")
