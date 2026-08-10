"""Page 7: Should-Cost Model."""
import streamlit as st

from components.executive_cards import formula_expander
from components.tables import display_table
from components.formatting import md
from components.state import get_data, get_settings, page_setup, set_table
from core.config import benchmark_structure
from core.should_cost_engine import (
    DEFAULT_BENCHMARK_STRUCTURE, benchmark_should_cost, comparison_table,
    level1_benchmark, variance_analysis)

page_setup("Should-Cost Model",
           "Three levels of should-cost detail, compared with quotes, standard cost, and peers.")

data = get_data()
settings = get_settings()
products = data["products"]
product_id = st.selectbox(
    "Product", products["product_id"].tolist(),
    format_func=lambda p: f"{p} — {products.set_index('product_id').loc[p, 'product_name']}")
volume = float(products.set_index("product_id").loc[product_id, "annual_volume"])

method = st.radio("Should-cost method", [
    "Level 1 — High-level benchmark",
    "Level 2 — Process-based estimate",
    "Level 3 — Detailed bottom-up"], horizontal=True, index=1)
st.caption({
    "Level 1 — High-level benchmark": "Top-down: estimated EMS-scope material ÷ benchmark "
                                      "material share. Supplier-independent sanity check; "
                                      "confidence is always Low.",
    "Level 2 — Process-based estimate": "Bottom-up: BOM material + modeled conversion. "
                                        "Confidence follows BOM and conversion data quality.",
    "Level 3 — Detailed bottom-up": "Same engine as Level 2 at full BOM/routing depth — only "
                                    "meaningful when the underlying data is high-confidence "
                                    "(gate below).",
}[method])

# ------------------------------------------------------------- method setup
structure = None
if method.startswith("Level 1"):
    st.subheader("Benchmark cost structure (EMS quote scope)")
    cols = st.columns(5)
    stored = benchmark_structure(settings)
    structure = {}
    for col, (key, default) in zip(cols, stored.items()):
        structure[key] = col.number_input(key.replace("_pct", " %"), value=float(default),
                                          min_value=0.0, max_value=100.0, key=f"bench_{key}")
    total_pct = sum(structure.values())
    if abs(total_pct - 100) > 0.01:
        st.warning(f"Structure sums to {total_pct:.0f}% (expected 100%).")
    if structure != stored:
        if st.button("Save this structure as the model default"):
            gs = data["global_settings"].copy()
            for key, val in structure.items():
                gs.loc[gs["key"] == f"benchmark_{key}", "value"] = val
            set_table("global_settings", gs)
            st.rerun()
        st.caption("Unsaved: these percentages apply to this view only until saved as the "
                   "model default (then they persist and appear on **Model Settings**).")
    bench = benchmark_should_cost(data, product_id, structure)
    if bench["should_cost"] == bench["should_cost"]:  # not NaN
        st.caption(md(f"Benchmark should-cost = EMS material ${bench['ems_material']:,.0f} "
                   f"({bench['material_source']}) ÷ {bench['material_share_pct']:.0f}% material share "
                   f"= **${bench['should_cost']:,.0f}** — anchored on material so it stays "
                   "independent of the quote (percent-of-quote would be circular)."))
    else:
        st.warning("No material estimate available (no BOM and no quoted material content) — "
                   "the benchmark should-cost cannot be computed for this product.")

engine_key = "benchmark" if method.startswith("Level 1") else "process"
comp = comparison_table(data, product_id, method=engine_key, structure=structure)

# Level 3 gate: detailed bottom-up requires high-confidence data coverage.
LEVEL3_COVERAGE_THRESHOLD = settings.get("level3_bom_coverage_threshold_pct", 70.0) / 100.0
if method.startswith("Level 3") and not comp.empty:
    coverage = float(comp.iloc[0]["bom_high_confidence_share"])
    if coverage < LEVEL3_COVERAGE_THRESHOLD:
        st.warning(
            f"Level 3 is not supported by the data for this product: only {coverage:.0%} of BOM "
            f"lines are high-confidence (threshold {LEVEL3_COVERAGE_THRESHOLD:.0%}). The numbers "
            "below are the same process-based engine at Level 2 confidence. Improve BOM pricing "
            "confidence (see Data Quality page) to justify Level 3.")

st.divider()
st.subheader("Quote vs should-cost comparison")
if comp.empty:
    st.info("No quotes for this product.")
    st.stop()
show_cols = [c for c in comp.columns if c != "bom_high_confidence_share"]
display_table(comp[show_cols], overrides={
    "quoted_price": st.column_config.NumberColumn("Quoted price (EMS scope)", format="$%,.0f"),
    "should_cost": st.column_config.NumberColumn("Should-cost (EMS scope)", format="$%,.0f"),
    "consigned_material": st.column_config.NumberColumn("Consigned mat. (excluded)", format="$%,.0f"),
    "current_standard_cost": st.column_config.NumberColumn("Std cost (all-in)", format="$%,.0f"),
    "variance_usd": st.column_config.NumberColumn("Variance $", format="$%,.0f"),
    "variance_pct": st.column_config.NumberColumn("Variance %", format="%.1f%%"),
})
st.caption(
    f"Numbers produced by: **{comp.iloc[0]['should_cost_method']}**. "
    "Quotes and should-cost are EMS scope (OEM-consigned material excluded and added separately "
    "by the economic engine); standard cost is all-in. Positive variance = quote above "
    "should-cost. **This is not automatically supplier overpricing** — see the interpretation "
    "split below. Comparable-product and historical-cost comparisons can be added to the "
    "assumption register as benchmarks.")

if method.startswith("Level 1"):
    st.subheader("Benchmark decomposition of each quote")
    st.caption("The structure percentages applied to each quoted price — a composition sanity "
               "check, separate from the should-cost above.")
    for _, row in comp.iterrows():
        st.markdown(f"**{row['supplier_name']}** — quoted ${row['quoted_price']:,.0f}")
        display_table(level1_benchmark(row["quoted_price"], structure), overrides={
                         "pct": st.column_config.NumberColumn("% of quote", format="%.0f%%"),
                         "value": st.column_config.NumberColumn("Value", format="$%,.0f")})
else:
    st.subheader("Variance interpretation by supplier")
    supplier = st.selectbox("Supplier", comp["supplier_id"].tolist(),
                            format_func=lambda s: comp.set_index("supplier_id").loc[s, "supplier_name"])
    va = variance_analysis(data, product_id, supplier, volume, settings)
    if va.empty:
        st.info("No quote for this supplier.")
    else:
        display_table(va, overrides={
            "value": st.column_config.NumberColumn("Value $/unit", format="$%,.2f")})
        st.caption(
            "The split is heuristic, meant to structure the negotiation conversation: "
            "the tier gap is real and immediately actionable; the commercial-opportunity share "
            "scales with BOM confidence; low-confidence BOMs push variance into 'possible missing "
            "data'. Confidence-adjusted opportunity = commercial opportunity only.")

formula_expander("Should-cost variance", """
```
Level 1 benchmark should-cost = estimated EMS material ÷ benchmark material share
Level 2/3 process should-cost = EMS-scope BOM material + modeled conversion
Should-cost variance          = supplier quoted cost − selected should-cost
Confidence-adjusted opportunity = variance × BOM-confidence share × commercial share (setting)
```
Distinguished outcomes: likely commercial opportunity · possible specification difference ·
possible volume difference (tier gap) · possible quality or service premium · possible logistics
difference · possible overhead difference · possible missing data · unexplained variance.
""")
