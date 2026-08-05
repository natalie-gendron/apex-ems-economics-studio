"""Page 7: Should-Cost Model."""
import streamlit as st

from components.executive_cards import formula_expander
from components.state import get_data, page_setup
from core.should_cost_engine import (
    DEFAULT_BENCHMARK_STRUCTURE, comparison_table, level1_benchmark, variance_analysis)

page_setup("Should-Cost Model",
           "Three levels of should-cost detail, compared with quotes, standard cost, and peers.")

data = get_data()
products = data["products"]
product_id = st.selectbox(
    "Product", products["product_id"].tolist(),
    format_func=lambda p: f"{p} — {products.set_index('product_id').loc[p, 'product_name']}")
volume = float(products.set_index("product_id").loc[product_id, "annual_volume"])

method = st.radio("Should-cost method", [
    "Level 1 — High-level benchmark",
    "Level 2 — Process-based estimate",
    "Level 3 — Detailed bottom-up"], horizontal=True)
st.caption({
    "Level 1 — High-level benchmark": "Cost-structure percentages applied to the quote. "
                                      "Confidence: Low — a sanity check, not an estimate.",
    "Level 2 — Process-based estimate": "BOM material + modeled conversion. "
                                        "Confidence follows BOM and conversion data quality.",
    "Level 3 — Detailed bottom-up": "Component-level BOM and routing. Only as good as the "
                                    "coverage shown below.",
}[method])

st.divider()
st.subheader("Quote vs should-cost comparison")
comp = comparison_table(data, product_id)
if comp.empty:
    st.info("No quotes for this product.")
    st.stop()
st.dataframe(comp, hide_index=True, width="stretch", column_config={
    "quoted_price": st.column_config.NumberColumn("Quoted price (EMS scope)", format="$%,.0f"),
    "should_cost": st.column_config.NumberColumn("Should-cost (EMS scope)", format="$%,.0f"),
    "consigned_material": st.column_config.NumberColumn("Consigned mat. (excluded)", format="$%,.0f"),
    "current_standard_cost": st.column_config.NumberColumn("Std cost (all-in)", format="$%,.0f"),
    "variance_usd": st.column_config.NumberColumn("Variance $", format="$%,.0f"),
    "variance_pct": st.column_config.NumberColumn("Variance %", format="%.1f%%"),
})
st.caption(
    "Quotes and should-cost are EMS scope (OEM-consigned material excluded and added separately "
    "by the economic engine); standard cost is all-in. Positive variance = quote above "
    "should-cost. **This is not automatically supplier overpricing** — see the interpretation "
    "split below. Comparable-product and historical-cost comparisons can be added to the "
    "assumption register as benchmarks.")

if method.startswith("Level 1"):
    st.subheader("Level 1 benchmark structure")
    cols = st.columns(5)
    structure = {}
    for col, (key, default) in zip(cols, DEFAULT_BENCHMARK_STRUCTURE.items()):
        structure[key] = col.number_input(key.replace("_pct", " %"), value=float(default),
                                          min_value=0.0, max_value=100.0)
    total_pct = sum(structure.values())
    if abs(total_pct - 100) > 0.01:
        st.warning(f"Structure sums to {total_pct:.0f}% (expected 100%).")
    for _, row in comp.iterrows():
        st.markdown(f"**{row['supplier_name']}** — quoted ${row['quoted_price']:,.2f}")
        st.dataframe(level1_benchmark(row["quoted_price"], structure), hide_index=True,
                     width="stretch")
else:
    st.subheader("Variance interpretation by supplier")
    supplier = st.selectbox("Supplier", comp["supplier_id"].tolist(),
                            format_func=lambda s: comp.set_index("supplier_id").loc[s, "supplier_name"])
    va = variance_analysis(data, product_id, supplier, volume)
    if va.empty:
        st.info("No quote for this supplier.")
    else:
        st.dataframe(va, hide_index=True, width="stretch", column_config={
            "value": st.column_config.NumberColumn("Value $/unit", format="$%,.2f")})
        st.caption(
            "The split is heuristic, meant to structure the negotiation conversation: "
            "the tier gap is real and immediately actionable; the commercial-opportunity share "
            "scales with BOM confidence; low-confidence BOMs push variance into 'possible missing "
            "data'. Confidence-adjusted opportunity = commercial opportunity only.")

formula_expander("Should-cost variance", """
```
Should-cost variance = supplier quoted cost − internal should-cost
Confidence-adjusted opportunity = variance × BOM-confidence share × 0.6 (heuristic)
```
Distinguished outcomes: likely commercial opportunity · possible specification difference ·
possible volume difference (tier gap) · possible quality/service premium · possible logistics
difference · possible overhead difference · possible missing data · unexplained variance.
""")
