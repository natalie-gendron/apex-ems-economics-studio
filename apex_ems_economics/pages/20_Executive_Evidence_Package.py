"""Page 18: Executive Evidence Package - downloadable decision support."""
from datetime import date

import pandas as pd
import streamlit as st

from components.formatting import fmt_currency_compact
from components.tables import display_table
from components.state import (baseline_id, editable_table, get_data, get_result,
                              page_setup, set_table)
from core import integration_outputs, risk_engine
from core.economics_engine import compare_scenarios
from core.recommendation_engine import recommend
from core.validation_engine import data_quality_score
from services.ai_insight_service import detect_anomalies, narrative_insights
from services.export_service import evidence_package_sheets, to_csv_bytes, to_excel_bytes

page_setup("Executive Evidence Package",
           "The decision, the economics, the assumptions, and the evidence - exportable to Excel/CSV.")

data = get_data()
base_id = baseline_id()
scenarios = data["scenarios"]
names = dict(zip(scenarios["scenario_id"], scenarios["scenario_name"]))
results = {sid: get_result(sid) for sid in scenarios["scenario_id"]}
comparison = compare_scenarios(results, base_id)
dq = data_quality_score(data)
recs = recommend(data, results, base_id, dq)

# ----------------------------------------------------------- decision framing
st.subheader("Decision statement")
decision = st.text_area(
    "What decision is being made?",
    value="Select the EMS sourcing and contract strategy for FY27 for the analyzer and RF "
          "product families: current allocation vs volume shift, cash-focused renegotiation, "
          "and dual-sourcing the single-sourced RF module.")
recommended = st.selectbox("Recommended scenario", scenarios["scenario_id"].tolist(),
                           index=min(2, len(scenarios) - 1),
                           format_func=lambda s: names.get(s, s))
owner = st.text_input("Decision owner", value="VP Operations Finance")

col1, col2 = st.columns([1, 3])
if col1.button("Record this decision", type="secondary"):
    records = data["decision_records"].copy()
    existing = records["decision_statement"].astype(str) == decision
    row = {
        "decision_id": (f"DEC-{len(records) + 1:03d}" if not existing.any()
                        else records.loc[existing, "decision_id"].iloc[0]),
        "decision_statement": decision,
        "recommended_scenario_id": recommended,
        "decision_owner": owner,
        "decision_date": date.today().isoformat(),
        "status": "Recorded",
        "rationale": recs[0]["why"] if recs else "",
        "conditions": recs[0]["required_conditions"] if recs else "",
        "notes": f"Data-confidence {dq['overall_score']:.0f}/100; "
                 f"year-1 economic delta ${delta_total:,.0f}",
    }
    if existing.any():
        for k, v in row.items():
            records.loc[existing, k] = v
    else:
        records = pd.concat([records, pd.DataFrame([row])], ignore_index=True)
    set_table("decision_records", records)
    st.success("Decision recorded in the decision register below.")
    st.rerun()
col2.caption("Recording writes the decision, owner, recommended scenario, rationale, and "
             "data-confidence into the decision register - the audit trail for why this call "
             "was made with the numbers available at the time.")

st.subheader("Decision register")
editable_table("decision_records", column_config={
    "status": st.column_config.SelectboxColumn(
        "Status", options=["Draft", "Recorded", "Approved", "Superseded", "Rejected"]),
})

rec_result = results[recommended]
base_result = results[base_id]
delta_total = rec_result.totals["total_economic_cost"] - base_result.totals["total_economic_cost"]
delta_recurring = (rec_result.totals["recurring_economic_cost"]
                   - base_result.totals["recurring_economic_cost"])
delta_cogs = rec_result.totals["cogs_relevant_cost"] - base_result.totals["cogs_relevant_cost"]
delta_wc = rec_result.totals["oem_inventory_value"] - base_result.totals["oem_inventory_value"]
one_time = rec_result.totals["one_time_cost"] + rec_result.totals["transition_cost"]
cash_impact = (-delta_wc
               + rec_result.totals.get("payables_funding", 0)
               - base_result.totals.get("payables_funding", 0)
               - one_time)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Year-1 total economic Δ", fmt_currency_compact(delta_total), delta_color="inverse")
col2.metric("Recurring economic Δ/yr", fmt_currency_compact(delta_recurring))
col3.metric("Gross-margin impact (−ΔCOGS)", fmt_currency_compact(-delta_cogs))
col4.metric("Cash-flow impact (yr 1)", fmt_currency_compact(cash_impact))
st.caption(f"One-time + transition cost of the recommended scenario: {fmt_currency_compact(one_time)}. "
           f"Data-confidence score: {dq['overall_score']:.0f}/100.")

# ----------------------------------------------------------- narrative
insights = narrative_insights(data, results, base_id, comparison)
st.subheader("Executive narrative (deterministic template)")
for line in insights["summary"]:
    st.markdown(f"- {line}")
st.markdown("**Key drivers beyond the quote:** " + " · ".join(insights["key_drivers"]))

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Recommended actions**")
    for rec in recs[:6]:
        with st.expander(rec["action"]):
            st.markdown(f"**Why:** {rec['why']}")
            st.markdown(f"**Financial impact:** {rec['financial_impact']}")
            st.markdown(f"**Key risks:** {rec['key_risks']}")
            st.markdown(f"**Required conditions:** {rec['required_conditions']}")
            st.markdown(f"**Confidence:** {rec['confidence']} · **Next step:** {rec['next_step']}")
with col2:
    st.markdown("**Anomalies & watch items**")
    anomalies = detect_anomalies(data, base_result)
    for a in anomalies[:8]:
        st.markdown(f"- **{a['type']}** — {a['subject']}: {a['detail']}")
    st.markdown("**Questions to close before deciding**")
    for func in ("procurement", "quality", "engineering", "supplier"):
        for q in insights[f"questions_{func}"][:2]:
            st.markdown(f"- *{func.capitalize()}:* {q}")

# ----------------------------------------------------------- exports
st.divider()
st.subheader("Exports")

exec_summary = pd.DataFrame([
    {"Item": "Decision statement", "Value": decision},
    {"Item": "Recommended scenario", "Value": names.get(recommended, recommended)},
    {"Item": "Decision owner", "Value": owner},
    {"Item": "Baseline total economic cost", "Value": base_result.totals["total_economic_cost"]},
    {"Item": "Recommended total economic cost (yr 1)", "Value": rec_result.totals["total_economic_cost"]},
    {"Item": "Recurring delta per year", "Value": delta_recurring},
    {"Item": "One-time + transition cost", "Value": one_time},
    {"Item": "Gross-margin impact (-dCOGS)", "Value": -delta_cogs},
    {"Item": "Delta OEM inventory", "Value": delta_wc},
    {"Item": "Cash-flow impact year 1 (positive = cash freed)", "Value": cash_impact},
    {"Item": "Expected risk cost delta", "Value": rec_result.totals["risk_cost"] - base_result.totals["risk_cost"]},
    {"Item": "Data-confidence score", "Value": round(dq["overall_score"], 0)},
] + [{"Item": f"Action {i+1}", "Value": r["action"]} for i, r in enumerate(recs[:5])])

actions_df = pd.DataFrame(recs)
risks_df = risk_engine.risk_register_with_expected_cost(data)
sheets = evidence_package_sheets(
    comparison=comparison,
    supplier_summary=rec_result.supplier_summary,
    product_summary=rec_result.product_summary,
    line_items=rec_result.line_items,
    inventory=data["inventory_records"],
    quality=data["quality_metrics"],
    contract_terms=data["contract_terms"],
    risks=risks_df,
    assumptions=data["assumptions"],
    actions=actions_df,
    executive_summary=exec_summary,
)
col1, col2, col3 = st.columns(3)
with col1:
    st.download_button("⬇ Evidence package (Excel, multi-tab)",
                       to_excel_bytes(sheets), "apex_ems_evidence_package.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       type="primary")
with col2:
    st.download_button("⬇ Scenario comparison (CSV)", to_csv_bytes(comparison),
                       "scenario_comparison.csv", mime="text/csv")
with col3:
    st.download_button("⬇ Recommended-scenario cost detail (CSV)",
                       to_csv_bytes(rec_result.line_items), "cost_detail.csv", mime="text/csv")
st.caption("PDF export is a future enhancement; the Excel package is the v1 board-ready artifact.")

# ----------------------------------------------------------- integration outputs
st.divider()
st.subheader("Future-integration output tables (Apex platform interfaces)")
st.caption("Standardized frames for the Executive SIOP Decision Engine, Manufacturing Economics "
           "Studio, Margin Intelligence, Working Capital Optimizer, and Strategic Network Optimizer.")
tab1, tab2, tab3, tab4 = st.tabs(["Product cost", "Inventory", "Margin", "Supply"])
with tab1:
    df = integration_outputs.product_cost_output(rec_result)
    display_table(df)
    st.download_button("⬇ product_cost_output.csv", to_csv_bytes(df),
                       "product_cost_output.csv", mime="text/csv")
with tab2:
    df = integration_outputs.inventory_output(rec_result, data)
    display_table(df)
    st.download_button("⬇ inventory_output.csv", to_csv_bytes(df),
                       "inventory_output.csv", mime="text/csv")
with tab3:
    df = integration_outputs.margin_output(rec_result, base_result)
    display_table(df)
    st.download_button("⬇ margin_output.csv", to_csv_bytes(df),
                       "margin_output.csv", mime="text/csv")
with tab4:
    df = integration_outputs.supply_output(rec_result, data)
    display_table(df)
    st.download_button("⬇ supply_output.csv", to_csv_bytes(df),
                       "supply_output.csv", mime="text/csv")
