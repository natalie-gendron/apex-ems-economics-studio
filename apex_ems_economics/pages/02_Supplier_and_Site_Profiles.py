"""Page 2: Supplier and Site Profiles."""
import streamlit as st

from components.state import editable_table, get_data, page_setup

page_setup("Supplier & Site Profiles",
           "Create and edit EMS supplier and site records. Ratings are 1 (weak) to 5 (strong).")

data = get_data()

st.subheader("Suppliers")
editable_table("suppliers", column_config={
    "financial_health": st.column_config.NumberColumn("Financial health (1-5)", min_value=1, max_value=5),
    "capacity_rating": st.column_config.NumberColumn("Capacity (1-5)", min_value=1, max_value=5),
    "quality_rating": st.column_config.NumberColumn("Quality (1-5)", min_value=1, max_value=5),
    "delivery_rating": st.column_config.NumberColumn("Delivery (1-5)", min_value=1, max_value=5),
    "responsiveness_rating": st.column_config.NumberColumn("Responsiveness (1-5)", min_value=1, max_value=5),
    "status": st.column_config.SelectboxColumn("Status", options=[
        "Approved", "Conditional", "Under qualification", "Phase-out", "Exited"]),
    "strategic_importance": st.column_config.SelectboxColumn(
        "Strategic importance", options=["High", "Medium", "Low"]),
    "single_source_risk": st.column_config.SelectboxColumn(
        "Single-source risk", options=["High", "Medium", "Low"]),
    "data_transparency": st.column_config.SelectboxColumn("Data transparency", options=[
        "Full open-book", "Partial open-book", "Bundled pricing", "No cost transparency"]),
    "strategic_fit": st.column_config.SelectboxColumn("Strategic fit", options=["High", "Medium", "Low"]),
})

st.subheader("Sites")
st.caption("Geographic, political, and natural-disaster risk feed the risk register qualitatively; "
           "quantified risks belong on the Risk-Adjusted Economics page.")
editable_table("sites", column_config={
    "geographic_risk": st.column_config.SelectboxColumn("Geographic risk", options=["Low", "Medium", "High"]),
    "political_risk": st.column_config.SelectboxColumn("Political risk", options=["Low", "Medium", "High"]),
    "natural_disaster_risk": st.column_config.SelectboxColumn(
        "Natural-disaster risk", options=["Low", "Medium", "High"]),
})

st.info("Supplier IDs are referenced by quotes, contracts, quality metrics, logistics lanes, "
        "service levels, capacity records, risks, and allocations - edit IDs with care.")
