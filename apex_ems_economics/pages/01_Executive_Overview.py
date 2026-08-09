"""Page 1: Executive Overview."""
import pandas as pd
import streamlit as st

from components import charts
from components.executive_cards import callout_grid, formula_expander, metric_row, top_list
from components.formatting import fmt_currency_compact, fmt_pct
from components.tables import display_table
from components.state import baseline_id, get_data, get_result, page_setup, scenario_selector
from core import risk_engine
from core.economics_engine import compare_scenarios, cost_bridge
from core.recommendation_engine import recommend
from core.scoring_engine import supplier_scores
from core.should_cost_engine import comparison_table
from core.validation_engine import data_quality_score

page_setup("Executive Overview",
           "Quoted cost vs true economic cost for the selected scenario, with drivers, risks, and actions.")

data = get_data()
scenario_id, scenario_name = scenario_selector()
result = get_result(scenario_id)
base_id = baseline_id()
base = get_result(base_id)
t = result.totals

if result.line_items.empty:
    st.warning("No allocations found for this scenario. Configure them in the Scenario Builder.")
    st.stop()

# ---------------------------------------------------------------- headline
dq = data_quality_score(data)
quoted = t["quoted_cost"]
econ = t["total_economic_cost"]
premium_pct = (econ / quoted - 1) * 100 if quoted else 0

# Should-cost gap across products with quotes.
sc_gap = 0.0
for pid in result.line_items["product_id"].unique():
    comp = comparison_table(data, pid)
    if not comp.empty:
        li = result.line_items[result.line_items["product_id"] == pid]
        for _, row in li.iterrows():
            m = comp[comp["supplier_id"] == row["supplier_id"]]
            if not m.empty and m.iloc[0]["variance_usd"] > 0:
                sc_gap += m.iloc[0]["variance_usd"] * row["volume"]

delta_vs_base = econ - base.totals["total_economic_cost"] if scenario_id != base_id else None

st.subheader(f"Scenario: {scenario_name}")
metric_row([
    ("Annual EMS spend (quoted)", fmt_currency_compact(quoted), None),
    ("True economic cost", fmt_currency_compact(econ),
     fmt_currency_compact(delta_vs_base) if delta_vs_base is not None else None),
    ("Economic premium over quote", fmt_pct(premium_pct), None),
    ("Data confidence", f"{dq['overall_score']:.0f} / 100", None),
])
metric_row([
    ("Quality cost (OEM-borne)", fmt_currency_compact(t["quality_cost"]), None),
    ("Logistics + duties", fmt_currency_compact(t["logistics_cost"] + t["duty_cost"]), None),
    ("Working-capital cost", fmt_currency_compact(t["wc_cost"]), None),
    ("Expected risk cost*", fmt_currency_compact(t["risk_cost"]), None),
])
metric_row([
    ("Estimated savings opportunity (quote vs should-cost)†", fmt_currency_compact(sc_gap), None),
    ("OEM inventory (modeled)", fmt_currency_compact(t["oem_inventory_value"]), None),
    ("Consigned material (OEM-purchased)", fmt_currency_compact(t["consigned_material_cost"]), None),
    ("One-time + transition", fmt_currency_compact(t["one_time_cost"] + t["transition_cost"]), None),
], columns=4)
st.caption("*Expected risk cost is a decision-analysis measure (probability × impact), not a booked "
           "expense. †Sum of positive quote-vs-should-cost variances across allocated volume — an "
           "analytical ceiling, not a committed saving; see the Should-Cost page for interpretation.")

formula_expander("How true economic cost is calculated", """
```
Total economic cost =
    Quoted purchase cost                (price × volume, tier-adjusted)
  + Consigned material cost             (OEM-purchased material excluded from quote)
  + Logistics                           (freight, insurance, brokerage, packaging, handling, warehousing)
  + Duties & tariffs
  + OEM-borne cost of poor quality      (scrap, rework, returns, warranty, downtime, expected recall)
  + Working-capital cost                (carrying cost on OEM-owned inventory ± payment-terms effect, advances)
  + Service cost                        (safety/buffer stock, expedites, expected stockouts, penalties)
  + Expected risk cost                  (Σ probability × impact — decision measure)
  + One-time & transition costs         (scenario level)

Economic cost per unit = total annual economic cost ÷ annual good units
Good units = volume × final yield
```
Costs already inside the supplier quote (material, conversion, and freight/duties when the
quote includes them) are **never added twice** — see the Should-Cost page for the quote's
internal composition.
""")

st.divider()

# ---------------------------------------------------------------- bridge + supplier ranking
col1, col2 = st.columns([3, 2])
with col1:
    bridge = cost_bridge(result)
    st.plotly_chart(charts.waterfall(bridge, "Quote → true economic cost (per good unit)"),
                    width="stretch")
with col2:
    ss = result.supplier_summary
    st.plotly_chart(charts.per_unit_comparison(
        ss, "supplier_name", "quoted_per_unit", "econ_cost_per_unit",
        "Supplier economic ranking (per unit)"), width="stretch")

# ---------------------------------------------------------------- callouts
st.subheader("Executive callouts")
ss = result.supplier_summary
callouts = []
if len(ss) > 0:
    by_quote = ss.sort_values("quoted_per_unit").iloc[0]
    by_econ = ss.sort_values("econ_cost_per_unit").iloc[0]
    callouts.append(("Lowest quoted supplier", by_quote["supplier_name"],
                     f"{fmt_currency_compact(by_quote['quoted_per_unit'])}/unit quoted"))
    callouts.append(("Lowest true economic-cost supplier", by_econ["supplier_name"],
                     f"{fmt_currency_compact(by_econ['econ_cost_per_unit'])}/unit all-in"))
    risk_by_sup = result.line_items.groupby("supplier_id")["risk_cost"].sum()
    scores = supplier_scores(data, ss, risk_by_sup)
    if not scores.empty:
        callouts.append(("Lowest risk-adjusted supplier (weighted score)",
                         scores.iloc[0]["supplier_name"],
                         f"Score {scores.iloc[0]['Weighted score']:.0f}/100 — details on Risk page"))
    by_quality = ss.assign(q=ss["quality_cost"] / ss["quoted_cost"]).sort_values("q").iloc[0]
    callouts.append(("Best quality-adjusted supplier", by_quality["supplier_name"],
                     f"OEM-borne COPQ {fmt_pct(by_quality['quality_cost'] / by_quality['quoted_cost'] * 100)} of spend"))
    by_wc = ss.assign(w=ss["wc_cost"] / ss["quoted_cost"]).sort_values("w").iloc[0]
    callouts.append(("Best working-capital supplier", by_wc["supplier_name"],
                     f"WC cost {fmt_pct(by_wc['wc_cost'] / by_wc['quoted_cost'] * 100)} of spend"))

levers = data.get("negotiation_levers", pd.DataFrame())
if levers is not None and not levers.empty:
    lv = levers.assign(total=levers["annual_savings"].fillna(0)
                       + levers["working_capital_impact"].fillna(0) * 0.19)
    top_lever = lv.sort_values("total", ascending=False).iloc[0]
    callouts.append(("Top contract renegotiation opportunity", str(top_lever["lever"]),
                     f"{top_lever['supplier_id']}: {fmt_currency_compact(top_lever['annual_savings'])}/yr "
                     f"+ {fmt_currency_compact(top_lever['working_capital_impact'])} cash"))

terms = data.get("contract_terms", pd.DataFrame())
missing_terms = terms[terms["status"] == "Missing"] if terms is not None and not terms.empty else pd.DataFrame()
if not missing_terms.empty:
    callouts.append(("Largest unknown / data gap",
                     f"{len(missing_terms)} missing contract terms",
                     "e.g. " + "; ".join(missing_terms["term_name"].head(2))
                     + " — see Data Quality page"))
callout_grid(callouts)

st.divider()

# ---------------------------------------------------------------- top 5s
col1, col2, col3 = st.columns(3)
li = result.line_items
with col1:
    driver_items = []
    for bucket, label in [("quality_cost", "Quality (COPQ)"), ("wc_cost", "Working capital"),
                          ("service_cost", "Service"), ("risk_cost", "Expected risk"),
                          ("logistics_cost", "Logistics"), ("duty_cost", "Duties & tariffs"),
                          ("consigned_material_cost", "Consigned material")]:
        driver_items.append((label, float(li[bucket].sum())))
    driver_items.sort(key=lambda x: -x[1])
    top_list("Top 5 economic drivers beyond the quote", driver_items[:5])
with col2:
    risks_df = risk_engine.risk_register_with_expected_cost(data)
    risk_items = [(f"{r['category']} ({r.get('supplier_id') or r.get('product_id') or 'portfolio'})",
                   r["expected_cost"]) for _, r in risks_df.head(5).iterrows()]
    top_list("Top 5 risks (expected cost)", risk_items)
with col3:
    recs = recommend(data, {base_id: base, scenario_id: result}, base_id, dq)
    with st.container(border=True):
        st.markdown("**Top 5 actions**")
        for i, rec in enumerate(recs[:5], start=1):
            st.markdown(f"{i}. {rec['action']}")
        if not recs:
            st.caption("No actions triggered.")

st.divider()

# ---------------------------------------------------------------- allocation + comparison
col1, col2 = st.columns(2)
with col1:
    st.subheader("Product allocation")
    alloc = li[["product_name", "supplier_name", "allocation_pct", "volume",
                "econ_cost_per_unit"]].copy()
    display_table(alloc, overrides={
        "allocation_pct": st.column_config.NumberColumn("Allocation", format="%.0f%%"),
    })
with col2:
    st.subheader("Scenario comparison summary")
    all_results = {sid: get_result(sid) for sid in data["scenarios"]["scenario_id"]}
    comparison = compare_scenarios(all_results, base_id)
    st.plotly_chart(charts.scenario_delta_bars(
        comparison, base_id, "Δ total economic cost vs baseline"), width="stretch")
    st.caption("Full detail on the Scenario Comparison page.")
