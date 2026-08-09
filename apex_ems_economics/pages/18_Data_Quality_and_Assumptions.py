"""Page 17: Data Quality and Assumption Register."""
import pandas as pd
import streamlit as st

from components.executive_cards import metric_row
from components.tables import display_table
from components.state import editable_table, get_data, page_setup
from core.validation_engine import data_quality_score, validate
from services.ai_insight_service import challenge_assumptions

page_setup("Data Quality & Assumption Register",
           "What the model rests on: every assumption with status, source, confidence, and ranges.")

data = get_data()

# ----------------------------------------------------------- score
score = data_quality_score(data)
st.subheader("Data-quality score")
metric_row([
    ("Overall", f"{score['overall_score']:.0f} / 100", None),
    ("Completeness", f"{score['completeness']:.0f}", None),
    ("Source status", f"{score['source_status']:.0f}", None),
    ("Confidence", f"{score['confidence']:.0f}", None),
    ("Recency", f"{score['recency']:.0f}", None),
], columns=5)
st.caption("Weights: completeness 25% · source status 20% · confidence 25% · recency 15% · "
           "high-value driver coverage 15%. Driver coverage measures material-content "
           f"visibility on quotes (currently {score['driver_coverage']:.0f}).")

st.divider()
st.subheader("Assumption register")
st.caption("Statuses: Confirmed / Estimated / Benchmarked / Inferred / Missing / Stale / "
           "Under review. Min / most-likely / max ranges feed the Monte Carlo module.")
editable_table("assumptions", column_config={
    "status": st.column_config.SelectboxColumn(options=[
        "Confirmed", "Estimated", "Benchmarked", "Inferred", "Missing", "Stale", "Under review"]),
    "confidence": st.column_config.SelectboxColumn(options=["High", "Medium", "Low"]),
    "financial_impact_rank": st.column_config.SelectboxColumn(options=["High", "Medium", "Low"]),
    "distribution": st.column_config.SelectboxColumn(options=[
        "Triangular", "Normal", "Uniform", "Lognormal", "Bernoulli", "Discrete", ""]),
})

st.divider()
col1, col2 = st.columns(2)
with col1:
    st.subheader("Assumptions needing validation")
    st.caption("Ranked by low confidence × high financial impact (the 'assumption challenge').")
    challenged = challenge_assumptions(data)
    display_table(challenged)
with col2:
    st.subheader("Validation findings")
    issues = validate(data)
    severity_filter = st.multiselect(
        "Severity", ["Error", "Warning", "Information", "Data-quality issue"],
        default=["Error", "Warning", "Data-quality issue"])
    display_table(issues[issues["severity"].isin(severity_filter)])

st.divider()
st.subheader("Recommended data-collection priorities")
priorities = []
terms = data["contract_terms"]
for _, row in terms[terms["status"] == "Missing"].iterrows():
    priorities.append({
        "Priority": "High", "Item": f"Contract term: {row['term_name']} ({row['supplier_id']})",
        "Why": "Missing contract terms create unpriced liability and weaken negotiation.",
        "Suggested owner": "Procurement"})
for _, row in terms[terms["status"] == "Inferred"].iterrows():
    priorities.append({
        "Priority": "High", "Item": f"Confirm inferred term: {row['term_name']} ({row['supplier_id']})",
        "Why": "The model treats this as fact based on practice, not contract language.",
        "Suggested owner": "Procurement / Legal"})
challenged = challenge_assumptions(data)
for _, row in challenged.head(5).iterrows():
    priorities.append({
        "Priority": "High" if row["challenge_score"] >= 6 else "Medium",
        "Item": f"Validate assumption: {row['name']}",
        "Why": f"{row['confidence']} confidence × {row['financial_impact_rank']} financial impact.",
        "Suggested owner": row.get("owner", "") or "Ops Finance"})
bom = data["bom_items"]
low_bom = bom[bom["confidence"] == "Low"]["product_id"].unique()
if len(low_bom):
    priorities.append({
        "Priority": "Medium", "Item": f"Improve BOM pricing confidence for: {', '.join(low_bom)}",
        "Why": "Should-cost and residual analysis are benchmark-grade for these products.",
        "Suggested owner": "Engineering / Procurement"})
display_table(pd.DataFrame(priorities))
