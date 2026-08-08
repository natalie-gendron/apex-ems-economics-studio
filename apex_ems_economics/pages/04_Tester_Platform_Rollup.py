"""Page 4: Tester Platform Rollup - board economics per system shipped."""
import streamlit as st

from components import charts
from components.executive_cards import formula_expander, metric_row
from components.formatting import fmt_currency, fmt_currency_compact, fmt_pct, fmt_units
from components.state import (editable_table, get_data, get_result, get_settings,
                              page_setup, scenario_selector)
from components.tables import money_table
from core.platform_engine import platform_rollup, ship_set_detail, subassembly_note

page_setup("Tester Platform Rollup",
           "What the EMS decisions cost per system shipped: systems × QPA = board demand, "
           "and board economics roll back up into ship-set cost.")

data = get_data()
settings = get_settings()
scenario_id, scenario_name = scenario_selector()
result = get_result(scenario_id)

st.info(
    "**Where the work happens.** The OEM ships complete test systems and performs final "
    "assembly, system integration, calibration, correlation, and system test **in-house**. "
    "The EMS partners build the **boards** that go into those systems. This studio models the "
    "EMS scope; the in-house content is shown separately below so the per-system margin closes.",
    icon=":material/factory:")

rollup = platform_rollup(data, result, settings)
if rollup.empty:
    st.warning("No platform data. Define platforms below and assign products to them.")
    st.stop()

# ------------------------------------------------------------------ headline
testers = rollup[rollup["platform_type"] == "Tester platform"]
metric_row([
    ("Systems shipped per year", fmt_units(testers["systems_shipped_per_year"].sum()), None),
    ("Annual revenue (all platforms)", fmt_currency_compact(rollup["annual_revenue"].sum()), None),
    ("Annual EMS content", fmt_currency_compact(rollup["annual_ems_content"].sum()), None),
    ("EMS content as % of revenue",
     fmt_pct(rollup["annual_ems_content"].sum() / rollup["annual_revenue"].sum() * 100), None),
], columns=4)

st.subheader("Per system shipped")
money_table(
    rollup.drop(columns=["platform_id", "annual_ems_content"]),
    money_cols=["asp_per_system", "annual_revenue", "quoted_ship_set_per_system",
                "ems_content_per_system", "ems_premium_per_system",
                "internal_assembly_test_per_system", "total_cogs_per_system",
                "gross_margin_per_system"],
    pct_cols=["ems_content_pct_of_asp", "gross_margin_pct"],
    rename={"platform_name": "Platform", "platform_type": "Type",
            "systems_shipped_per_year": "Systems shipped/yr",
            "boards_per_system_qpa": "Boards per system (QPA)",
            "asp_per_system": "ASP/system", "annual_revenue": "Annual revenue",
            "quoted_ship_set_per_system": "Quoted ship-set",
            "ems_content_per_system": "EMS content (true economic)",
            "ems_premium_per_system": "Hidden cost vs quote",
            "ems_content_pct_of_asp": "EMS % of ASP",
            "internal_assembly_test_per_system": "In-house assembly & system test",
            "total_cogs_per_system": "Total COGS/system",
            "gross_margin_per_system": "Gross margin/system",
            "gross_margin_pct": "GM %"},
    download_name="platform_rollup")
st.caption(
    "**Ship-set** = one full set of EMS-built boards for one system shipped. *Quoted ship-set* is "
    "what the supplier invoices; *EMS content* is the true economic cost after logistics, duties, "
    "quality, working capital, service, and expected risk. The difference is the **hidden cost per "
    "system** that never appears on a purchase order. In-house assembly & system test is an "
    "explicitly-labeled assumption (`internal_cogs_pct_of_revenue`), not a modeled cost — it is "
    "outside the EMS decision scope but needed to close the margin.")

formula_expander("How the rollup works (ops view)", """
```
Annual board demand      = systems shipped × QPA          (quantity per assembly)
Ship-set cost per system = Σ over boards of (QPA × board cost per GOOD unit)
Hidden cost per system   = economic ship-set − quoted ship-set
Total COGS per system    = EMS content + in-house assembly & system test
Gross margin per system  = ASP − total COGS per system
```
Board cost per good unit already nets out yield and scrap, so a ship-set reflects the boards you
must **buy** to ship one good system, not just the boards that end up in it.

**Subassemblies are excluded from ship-sets on purpose** — their cost is already carried inside
the parent board's BOM (see the table at the bottom). Counting them again would overstate every
ship-set.
""")

# ------------------------------------------------------------------ charts
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(charts.grouped_bar(
        rollup, "platform_name",
        [("quoted_ship_set_per_system", "Quoted ship-set"),
         ("ems_content_per_system", "True economic content"),
         ("internal_assembly_test_per_system", "In-house assembly & test")],
        "Cost per system shipped", y_title="$ per system"), width="stretch")
with col2:
    st.plotly_chart(charts.grouped_bar(
        rollup, "platform_name",
        [("asp_per_system", "ASP"), ("total_cogs_per_system", "Total COGS")],
        "ASP vs COGS per system shipped", y_title="$ per system"), width="stretch")

# ------------------------------------------------------------------ ship-set detail
st.divider()
st.subheader("Ship-set detail")
platform_id = st.selectbox(
    "Platform", rollup["platform_id"].tolist(),
    format_func=lambda p: rollup.set_index("platform_id").loc[p, "platform_name"])
detail = ship_set_detail(data, result, platform_id)
if detail.empty:
    st.info("No boards assigned to this platform.")
else:
    money_table(
        detail.drop(columns=["product_id"]),
        money_cols=["quoted_per_board", "economic_per_board", "quoted_extended_per_system",
                    "economic_extended_per_system", "hidden_cost_per_system"],
        rename={"board": "Board", "qpa_per_system": "QPA",
                "annual_board_demand": "Annual board demand",
                "quoted_per_board": "Quoted/board", "economic_per_board": "Economic/board",
                "quoted_extended_per_system": "Quoted extended",
                "economic_extended_per_system": "Economic extended",
                "hidden_cost_per_system": "Hidden cost"},
        download_name=f"ship_set_{platform_id}")
    row = rollup.set_index("platform_id").loc[platform_id]
    st.caption(
        f"At {fmt_units(row['systems_shipped_per_year'])} systems/yr, every "
        f"{fmt_currency(100)} of ship-set cost is "
        f"{fmt_currency_compact(row['systems_shipped_per_year'] * 100)} of annual spend — "
        "which is why board-level sourcing decisions scale so hard at the platform level.")

# ------------------------------------------------------------------ subassemblies
st.divider()
st.subheader("Subassemblies carried inside parent boards (excluded from ship-sets)")
subs = subassembly_note(data, result)
if subs.empty:
    st.caption("No subassemblies modeled.")
else:
    money_table(subs.drop(columns=["product_id"]),
                money_cols=["economic_per_unit", "annual_economic_cost"],
                rename={"subassembly": "Subassembly", "consumed_by": "Consumed by",
                        "annual_volume": "Annual volume",
                        "economic_per_unit": "Economic $/unit",
                        "annual_economic_cost": "Annual economic cost"},
                download_name="subassembly_detail")
    st.caption("These are modeled as their own supplier flows (so their sourcing, quality, and "
               "logistics economics are visible), but their cost also appears inside the parent "
               "board's BOM — they are excluded from ship-set totals to avoid double counting.")

# ------------------------------------------------------------------ editor
st.divider()
st.subheader("Platform definitions")
editable_table("tester_platforms", column_config={
    "annual_units": st.column_config.NumberColumn("Systems shipped/yr", format="%,.0f"),
    "asp_usd": st.column_config.NumberColumn("ASP per system", format="$%,.0f"),
    "platform_type": st.column_config.SelectboxColumn(
        "Type", options=["Tester platform", "Interface program", "Other"]),
})
st.caption("Assign boards to platforms and set QPA on the **Product Setup** page "
           "(`platform_id`, `boards_per_tester`). Subassemblies should leave `platform_id` blank.")
