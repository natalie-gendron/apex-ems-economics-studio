"""Apex EMS Economics Studio - home page."""
import streamlit as st

from components.state import get_data, page_setup
from components.tables import display_table
from core.validation_engine import data_quality_score, validate

page_setup(
    "Apex EMS Economics Studio",
    "A standalone module of the Apex Operations Finance Studio - turning EMS contracts, "
    "quotes, and operational assumptions into an auditable economic decision model.")

data = get_data()

st.markdown("""
**Finance should not merely report supplier cost after the fact.** This studio connects
contracts, operations, supply chain, quality, inventory, risk, and economics so leadership
can make better outsourcing decisions *before* outcomes are locked in.

**How to use it**

1. Review or edit inputs: *Supplier & Site Profiles, Product Setup, BOM, Contract Economics,
   Conversion Cost, Inventory, Quality, Logistics, Service Levels, Capacity, Risks.*
2. Build scenarios in the *Scenario Builder* (allocations, overrides, one-time costs).
3. Read the results: *Executive Overview, Scenario Comparison, Should-Cost, Contract
   Opportunities.*
4. Check what the model rests on: *Data Quality & Assumptions.*
5. Export the *Executive Evidence Package.*

Every output distinguishes **quoted cost from true economic cost**, **ownership from
physical location**, **booked cost from expected (decision-analysis) cost**, and
**known facts from estimates**. Calculations are deterministic and auditable; the
optional Monte Carlo and AI insight layers never replace them.
""")

st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("Model health")
    issues = validate(data)
    errors = issues[issues["severity"] == "Error"]
    warnings = issues[issues["severity"] == "Warning"]
    dq = issues[issues["severity"] == "Data-quality issue"]
    a, b, c = st.columns(3)
    a.metric("Errors", len(errors))
    b.metric("Warnings", len(warnings))
    c.metric("Data-quality flags", len(dq))
    if not errors.empty:
        st.error("Errors present - affected calculations may be unreliable:")
        display_table(errors)
    with st.expander("All validation findings"):
        display_table(issues)

with col2:
    st.subheader("Data confidence")
    score = data_quality_score(data)
    st.metric("Overall data-quality score", f"{score['overall_score']:.0f} / 100")
    st.caption(
        f"Completeness {score['completeness']:.0f} · Source status {score['source_status']:.0f} · "
        f"Confidence {score['confidence']:.0f} · Recency {score['recency']:.0f} · "
        f"Driver coverage {score['driver_coverage']:.0f}")
    st.markdown(
        "The score summarizes how much of the model rests on confirmed facts versus "
        "estimates and inferences. Details and priorities: **Data Quality & Assumptions**.")

st.divider()
st.caption(
    "Sample data describes a fictional advanced test-equipment manufacturer (Novatron Test "
    "Systems) and three fictional EMS suppliers. No real supplier or customer data is included.")
