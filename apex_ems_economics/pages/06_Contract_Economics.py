"""Page 5: Contract Economics - structured contract-term register."""
import pandas as pd
import streamlit as st

from components.tables import display_table
from components.state import editable_table, get_data, page_setup
from services.contract_parser_service import extract_terms

page_setup("Contract Economics",
           "Structured contract terms per supplier. Every term carries a status "
           "(Confirmed / Estimated / Inferred / Missing / Not applicable), source, and confidence.")

data = get_data()
terms = data["contract_terms"]

# ----------------------------------------------------------------- summary
st.subheader("Term status by supplier")
if not terms.empty:
    pivot = terms.pivot_table(index="supplier_id", columns="status",
                              values="term_id", aggfunc="count", fill_value=0)
    display_table(pivot.reset_index(), hide_index=True)
    inferred = terms[terms["status"].isin(["Inferred", "Missing"])]
    if not inferred.empty:
        st.warning(
            f"{len(inferred)} terms are Inferred or Missing. The model still runs - it uses "
            "clearly labeled assumptions - but these terms are negotiation and validation priorities:")
        display_table(inferred[["supplier_id", "category", "term_name",
                                "status", "confidence", "notes"]])

st.subheader("Supplier quotes (pricing terms)")
st.caption(
    "Quoted prices, volume tiers, and what each quote includes. Quotes cover the **EMS scope "
    "only** — OEM-consigned material is excluded and added separately by the engine. Tick "
    "`includes_freight` / `includes_duties` only when the quote genuinely contains them; the "
    "engine then stops adding those costs so they are never double counted.")
editable_table("supplier_quotes", column_config={
    "base_unit_price": st.column_config.NumberColumn("Base unit price", format="$%,.0f"),
    "tier2_min_qty": st.column_config.NumberColumn("Tier 2 min qty", format="%,.0f"),
    "tier2_unit_price": st.column_config.NumberColumn("Tier 2 price", format="$%,.0f"),
    "tier3_min_qty": st.column_config.NumberColumn("Tier 3 min qty", format="%,.0f"),
    "tier3_unit_price": st.column_config.NumberColumn("Tier 3 price", format="$%,.0f"),
    "quoted_material_content": st.column_config.NumberColumn("Quoted material", format="$%,.0f"),
    "quoted_conversion_content": st.column_config.NumberColumn("Quoted conversion", format="$%,.0f"),
    "includes_freight": st.column_config.CheckboxColumn("Incl. freight"),
    "includes_duties": st.column_config.CheckboxColumn("Incl. duties"),
    "status": st.column_config.SelectboxColumn("Status", options=[
        "Confirmed", "Estimated", "Inferred", "Missing", "Not applicable"]),
    "confidence": st.column_config.SelectboxColumn("Confidence", options=["High", "Medium", "Low"]),
})

st.divider()
st.subheader("Contract term register")
supplier_filter = st.multiselect(
    "Filter suppliers", terms["supplier_id"].unique().tolist() if not terms.empty else [])
category_filter = st.multiselect(
    "Filter categories", sorted(terms["category"].unique()) if not terms.empty else [])
view = terms
if supplier_filter:
    view = view[view["supplier_id"].isin(supplier_filter)]
if category_filter:
    view = view[view["category"].isin(category_filter)]

if supplier_filter or category_filter:
    display_table(view)
    st.caption("Clear filters to edit the full register below.")
else:
    editable_table("contract_terms", column_config={
        "status": st.column_config.SelectboxColumn("Status", options=[
            "Confirmed", "Estimated", "Inferred", "Missing", "Not applicable"]),
        "confidence": st.column_config.SelectboxColumn("Confidence", options=["High", "Medium", "Low"]),
        "category": st.column_config.SelectboxColumn("Category", options=[
            "Pricing", "Volume", "Inventory & liability", "Service", "Quality",
            "Cost transparency", "Contract risk"]),
    })

with st.expander("Terms the engine consumes directly"):
    st.markdown("""
| term_name | Used for |
|---|---|
| `payment_terms_days` | Working-capital payment-terms effect vs the reference days |
| `advance_payment_pct` | Advance/deposit financing cost |
| `raw_material_ownership` / `safety_stock_ownership` | Interpreting inventory records & consignment |
| `ncnr_liability_window_days`, `material_authorization_window_days` | Liability exposure context |
| `first_pass_yield_commitment_pct` | Contract-vs-actual quality comparison |
| `minimum_annual_volume_units` | Volume-commitment validation |

Other terms are registered for governance, negotiation levers, and the evidence package.
""")

st.divider()
st.subheader("Contract text extraction (draft terms - requires human validation)")
st.caption(
    "Paste contract text below. A deterministic keyword extractor proposes candidate terms "
    "(an LLM can back the same interface later - no API key is required). Extracted terms are "
    "always created as **Inferred / Low confidence** drafts.")
pasted = st.text_area("Contract text", height=180, placeholder="Paste contract excerpt here...")
if st.button("Extract candidate terms") and pasted.strip():
    found = extract_terms(pasted)
    st.session_state["extracted_terms"] = found
    if not found:
        st.info("No candidate terms recognized.")

extracted = st.session_state.get("extracted_terms") or []
if extracted:
    display_table(pd.DataFrame([e.__dict__ for e in extracted]))
    col1, col2 = st.columns([2, 3])
    suppliers = data["suppliers"]
    names = dict(zip(suppliers["supplier_id"], suppliers["supplier_name"]))
    draft_supplier = col1.selectbox("Assign drafts to supplier", suppliers["supplier_id"].tolist(),
                                    format_func=lambda s: names.get(s, s))
    if col2.button(f"Append {len(extracted)} draft(s) to the register as Inferred / Low confidence"):
        from components.state import set_table
        terms_df = data["contract_terms"]
        existing_ids = set(terms_df["term_id"].astype(str))
        rows, n = [], 1
        for e in extracted:
            term_id = f"CT-DRAFT-{draft_supplier.split('-')[-1]}-{n:02d}"
            while term_id in existing_ids:
                n += 1
                term_id = f"CT-DRAFT-{draft_supplier.split('-')[-1]}-{n:02d}"
            existing_ids.add(term_id)
            rows.append({
                "term_id": term_id, "supplier_id": draft_supplier, "category": e.category,
                "term_name": e.term_name, "value": e.value, "unit": "",
                "status": "Inferred", "source_reference": "Contract text extraction (draft)",
                "confidence": "Low", "notes": e.evidence[:200],
            })
        set_table("contract_terms", pd.concat([terms_df, pd.DataFrame(rows)], ignore_index=True))
        st.session_state.pop("extracted_terms", None)
        st.success(f"Appended {len(rows)} draft terms for {names.get(draft_supplier)} - "
                   "validate them in the register (they stay Inferred / Low until confirmed).")
        st.rerun()
    st.caption("Drafts are never authoritative: appended terms enter the register as "
               "**Inferred / Low confidence** and appear in the validation and data-quality views "
               "until a human confirms them.")
