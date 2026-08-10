"""Page 15: Scenario Comparison (deterministic + optional Monte Carlo)."""
import pandas as pd
import streamlit as st

from components import charts
from components.formatting import fmt_currency_compact, md
from components.state import baseline_id, get_data, get_result, get_settings, page_setup
from components.tables import money_table
from core.capacity_engine import capacity_analysis
from core.economics_engine import compare_scenarios, cost_bridge
from core.monte_carlo_engine import (
    probability_cheaper, probability_savings_exceed, run_simulation)
from core.validation_engine import data_quality_score

page_setup("Scenario Comparison",
           "Compare up to five scenarios: cost buckets, per-unit economics, COGS/margin/cash impact.")

data = get_data()
settings = get_settings()
base_id = baseline_id()
scenarios = data["scenarios"]
names = dict(zip(scenarios["scenario_id"], scenarios["scenario_name"]))

selected = st.multiselect(
    "Scenarios to compare (max 5)", scenarios["scenario_id"].tolist(),
    default=scenarios["scenario_id"].tolist()[:4],
    format_func=lambda s: names.get(s, s), max_selections=5)
if not selected:
    st.stop()
if base_id not in selected:
    st.caption(f"Baseline ({names[base_id]}) is always included for deltas.")

results = {sid: get_result(sid) for sid in dict.fromkeys([base_id] + selected)}
comparison = compare_scenarios(results, base_id)
comparison = comparison[comparison["scenario_id"].isin(selected)]

# ----------------------------------------------------------- headline table
dq = data_quality_score(data)
table = comparison.copy()
table["gross_margin_impact"] = table.get("gross_margin_impact", 0)
money_cols = ["quoted_cost", "consigned_material_cost", "logistics_cost", "duty_cost",
              "quality_cost", "wc_cost", "service_cost", "risk_cost", "one_time_cost",
              "total_economic_cost", "cogs_relevant_cost", "oem_inventory_value",
              "delta_total_vs_baseline", "delta_cogs_vs_baseline", "gross_margin_impact",
              "delta_wc_inventory", "cash_flow_impact"]
money_table(
    table.drop(columns=["scenario_id"]),
    money_cols=[c for c in money_cols if c in table.columns],
    rename={"scenario_name": "Scenario", "annual_volume": "Volume", "good_units": "Good units",
            "quoted_cost": "Quoted", "consigned_material_cost": "Consigned mat.",
            "logistics_cost": "Logistics", "duty_cost": "Duties", "quality_cost": "Quality",
            "wc_cost": "Working cap.", "service_cost": "Service", "risk_cost": "Risk (exp.)",
            "one_time_cost": "One-time + transition", "total_economic_cost": "Total economic",
            "econ_cost_per_unit": "Econ $/unit", "cogs_relevant_cost": "COGS-relevant",
            "oem_inventory_value": "OEM inventory", "delta_total_vs_baseline": "Δ total",
            "delta_cogs_vs_baseline": "Δ COGS", "gross_margin_impact": "GM impact",
            "delta_wc_inventory": "Δ OEM inventory",
            "cash_flow_impact": "Cash-flow impact (yr 1)"},
    download_name="scenario_comparison")
st.caption(f"Data-confidence score {dq['overall_score']:.0f}/100 applies to all scenarios. "
           "GM impact = −Δ COGS (revenue held constant in v1). Cash-flow impact (positive = "
           "cash freed) = inventory released + incremental payables funding − one-time costs; "
           "cost and cash are deliberately separate: a change can improve cash without touching COGS.")

# ----------------------------------------------------------- charts
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(charts.scenario_delta_bars(
        comparison, base_id, "Δ total economic cost vs baseline"), width="stretch")
with col2:
    buckets = [("quoted_cost", "Quoted"), ("consigned_material_cost", "Consigned mat."),
               ("logistics_cost", "Logistics"), ("duty_cost", "Duties"),
               ("quality_cost", "Quality"), ("wc_cost", "Working capital"),
               ("service_cost", "Service"), ("risk_cost", "Risk")]
    st.plotly_chart(charts.stacked_cost_bars(
        comparison, "scenario_name", buckets, "Annual cost composition"), width="stretch")

# ----------------------------------------------------------- bridge per scenario
st.subheader("Cost bridge")
bridge_scenario = st.selectbox("Scenario", selected, format_func=lambda s: names.get(s, s))
bridge = cost_bridge(results[bridge_scenario])
st.plotly_chart(charts.waterfall(
    bridge, f"Quote → true economic cost per good unit — {names.get(bridge_scenario)}"),
    width="stretch")

# ----------------------------------------------------------- ranking & tradeoffs
st.subheader("Scenario ranking and tradeoff matrix")
rank = comparison[["scenario_name", "total_economic_cost"]].copy()
rank["Rank (lower cost = better)"] = rank["total_economic_cost"].rank().astype(int)
tradeoff_rows = []
for sid in selected:
    res = results[sid]
    cap = capacity_analysis(data, res.line_items)
    feasible = bool(cap["volume_feasible"].all()) if not cap.empty else True
    li = res.line_items
    tradeoff_rows.append({
        "Scenario": names.get(sid, sid),
        "Total economic cost": res.totals["total_economic_cost"],
        "Expected risk cost": res.totals["risk_cost"],
        "OEM inventory (cash)": res.totals["oem_inventory_value"],
        "Quality cost": res.totals["quality_cost"],
        "Service cost": res.totals["service_cost"],
        "Capacity feasible": "Yes" if feasible else "NO",
        "Quote-missing lines": int(li["quote_missing"].sum()) if not li.empty else 0,
    })
tradeoff = pd.DataFrame(tradeoff_rows)
money_table(tradeoff, money_cols=["Total economic cost", "Expected risk cost",
                                  "OEM inventory (cash)", "Quality cost", "Service cost"],
            download_name="tradeoff_matrix")
st.caption("No scenario dominates on every axis — e.g. dual-sourcing costs more but cuts "
           "expected risk; the renegotiation frees cash with minor P&L give. That tension is "
           "the executive decision.")

# ----------------------------------------------------------- Monte Carlo (optional)
st.divider()
st.subheader("Monte Carlo simulation (optional)")
st.caption("Simulated outputs — clearly distinguished from the deterministic results above. "
           "Drivers: demand, material prices, freight, expedite frequency, yield, tariff shock; "
           "ranges come from the assumption register.")
enable_mc = st.toggle("Enable Monte Carlo", value=False)
if enable_mc:
    col1, col2, col3 = st.columns(3)
    iterations = int(col1.number_input("Iterations", 100, 5000,
                                       int(settings["mc_default_iterations"]), step=100))
    seed = int(col2.number_input("Random seed", 0, 10_000, int(settings["mc_default_seed"])))
    mc_scenarios = col3.multiselect("Scenarios", selected, default=selected[:2],
                                    format_func=lambda s: names.get(s, s))
    if st.button("Run simulation", type="primary") and mc_scenarios:
        with st.spinner(f"Running {iterations} iterations across {len(mc_scenarios)} scenarios..."):
            sim = run_simulation(data, mc_scenarios, iterations, seed)
        st.session_state["mc_result"] = sim
        st.session_state["mc_scenarios"] = mc_scenarios
    sim = st.session_state.get("mc_result")
    if sim:
        mc_scenarios = st.session_state["mc_scenarios"]
        stats = pd.DataFrame(sim["summary"]).T
        stats.index = [names.get(s, s) for s in stats.index]
        money_table(stats.reset_index(names="Scenario"),
                    money_cols=["mean", "median", "p10", "p50", "p90", "min", "max", "std"],
                    download_name="mc_summary")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(charts.histogram(
                sim["totals"][mc_scenarios[0]],
                f"Simulated total economic cost — {names.get(mc_scenarios[0])}",
                "Total economic cost ($/yr)"), width="stretch")
        with col2:
            st.plotly_chart(charts.tornado(
                sim["sensitivities"], "Drivers of outcome variability"), width="stretch")
        if len(mc_scenarios) >= 2:
            a, b = mc_scenarios[0], mc_scenarios[1]
            p = probability_cheaper(sim["totals"], a, b)
            st.markdown(f"**P({names.get(a)} cheaper than {names.get(b)})** = {p:.0%}")
            target = st.number_input("Savings target vs baseline ($)", value=500_000, step=100_000)
            if base_id in sim["totals"].columns:
                for sid in mc_scenarios:
                    if sid != base_id:
                        ps = probability_savings_exceed(sim["totals"], sid, base_id, target)
                        st.markdown(md(f"P(savings of {names.get(sid)} > {fmt_currency_compact(target)}) = {ps:.0%}"))
            else:
                st.caption("Include the baseline scenario in the simulation to compute savings probabilities.")
        st.caption(f"Seed {sim['seed']}, {sim['iterations']} iterations — reproducible.")
