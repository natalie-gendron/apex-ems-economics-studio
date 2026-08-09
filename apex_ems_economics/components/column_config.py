"""Automatic, consistent column labels and number formats.

Every table in the studio renders through this so a reader never sees a raw
database column name (``econ_cost_per_unit``) or an unformatted dollar
figure. Pages can still override any column explicitly; overrides win.

Rules, in order:
  1. an explicit per-column override passed by the page
  2. an entry in LABEL_OVERRIDES / TEXT_COLUMNS / MONEY_COLUMNS
  3. suffix inference (``*_pct`` -> percent, ``*_usd`` -> currency, ...)
  4. name inference (contains price/cost/fee/value/... -> currency)
  5. humanized sentence-case label with acronyms restored
"""
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd
import streamlit as st

ACRONYMS = {
    "id": "ID", "ids": "IDs", "usd": "USD", "ems": "EMS", "oem": "OEM",
    "qpa": "QPA", "otd": "OTD", "fpy": "FPY", "moq": "MOQ", "ncnr": "NCNR",
    "bom": "BOM", "wc": "WC", "copq": "COPQ", "asp": "ASP", "ppm": "PPM",
    "mc": "MC", "dio": "DIO", "wip": "WIP", "vmi": "VMI", "rf": "RF",
    "pn": "PN", "sla": "SLA", "eol": "EOL", "ltb": "LTB", "fx": "FX",
    "cogs": "COGS", "gm": "GM", "oh": "OH", "pm": "PM", "npi": "NPI",
}

# Labels where humanizing is not good enough.
LABEL_OVERRIDES = {
    "econ_cost_per_unit": "Economic $/unit",
    "quoted_per_unit": "Quoted $/unit",
    "incremental_per_unit": "Incremental $/unit",
    "total_economic_cost": "Total economic cost",
    "recurring_economic_cost": "Recurring economic cost",
    "cogs_relevant_cost": "COGS-relevant cost",
    "full_system_cogs": "Full system COGS",
    "wc_cost": "Working-capital cost",
    "wc_carrying": "Carrying cost",
    "wc_advance": "Advance-payment cost",
    "wc_terms_effect": "Payment-terms effect",
    "oem_inventory_value": "OEM inventory value",
    "consigned_material_cost": "Consigned material",
    "duty_cost": "Duties & tariffs",
    "risk_cost": "Expected risk cost",
    "quality_cost": "Quality cost (OEM-borne)",
    "good_units": "Good units",
    "qty_per": "Qty per assembly",
    "qpa_per_system": "QPA per system",
    "boards_per_tester": "QPA per system",
    "annual_volume": "Annual volume",
    "unit_price": "Unit price",
    "unit_cost": "Unit cost",
    "base_unit_price": "Base unit price",
    "internal_pn": "Internal part number",
    "parent_product_id": "Parent product",
    "platform_id": "Platform",
    "supplier_id": "Supplier",
    "product_id": "Product",
    "site_id": "Site",
    "scenario_id": "Scenario",
    "lane_id": "Lane",
    "risk_id": "Risk",
    "term_id": "Term",
    "quote_id": "Quote",
    "inv_id": "Inventory record",
    "bom_id": "BOM line",
    "conv_id": "Conversion record",
    "lever_id": "Lever",
    "override_id": "Override",
    "assumption_id": "Assumption",
    "decision_id": "Decision",
    "system_comp_id": "Component",
    "conversion_missing": "Conversion data missing",
    "quote_missing": "Quote missing",
    "allocation_pct": "Allocation",
    "is_baseline": "Baseline?",
    "probability_pct": "Probability",
    "expected_cost": "Expected cost",
    "financial_impact_usd": "Financial impact",
    "annual_savings": "Annual savings (P&L)",
    "working_capital_impact": "Cash impact",
    "tier2_min_qty": "Tier 2 min qty",
    "tier2_unit_price": "Tier 2 price",
    "tier3_min_qty": "Tier 3 min qty",
    "tier3_unit_price": "Tier 3 price",
    "asp_usd": "ASP per system",
    "material_desc": "Material",
    "quoted_material_content": "Quoted material content",
    "quoted_conversion_content": "Quoted conversion content",
    "annual_units": "Systems shipped/yr",
    "key": "Setting",
    "value": "Value",
    "unit": "Unit",
    "description": "What it means",
}

# Columns whose names imply money but that hold text.
TEXT_COLUMNS = {
    "risk_impact", "operational_impact", "value", "unit", "description",
    "notes", "price_source", "material_model", "liability_status",
    "constraint_notes", "mitigation_status", "obsolescence_risk",
}

# Explicit currency columns that name inference would miss.
MONEY_COLUMNS = {
    "labor_rate", "machine_rate", "test_rate", "rework_labor_rate",
    "downtime_cost_per_hour", "brokerage_per_shipment", "asp_usd",
    "customer_penalty_annual", "reservation_fee_annual",
    "quoted_conversion_content", "quoted_material_content",
}

DURATION_HINTS = ("_days", "days_", "_hours", "hours_", "_weeks", "_months",
                  "_years", "aging", "_size", "_time")


def _is_duration(column: str) -> bool:
    return any(h in column.lower() for h in DURATION_HINTS)

MONEY_HINTS = ("price", "cost", "fee", "savings", "value", "spend", "revenue",
               "penalty", "impact", "margin_per", "_usd", "asp", "carrying",
               "material", "logistics", "duty", "quality", "service", "freight",
               "warehousing", "packaging", "handling", "insurance", "brokerage")
MONEY_EXCLUDE = ("multiplier", "_pct", "_days", "_share", "_rank", "_model",
                 "_date", "_desc", "_until", "_valid",
                 "_source", "responsibility", "_flag", "location", "_id",
                 "_name", "notes", "index", "confidence", "status")

COUNT_HINTS = ("volume", "quantity", "qty", "units", "_moq", "qpa", "count",
               "systems_shipped", "capacity", "demand", "iterations", "seed")


def humanize(column: str) -> str:
    """snake_case -> sentence case with acronyms restored."""
    if column in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[column]
    parts = str(column).split("_")
    words = []
    for i, part in enumerate(parts):
        low = part.lower()
        if low == "pct":
            words.append("%")
        elif low in ACRONYMS:
            words.append(ACRONYMS[low])
        elif i == 0:
            words.append(part.capitalize())
        else:
            words.append(low)
    label = " ".join(words).replace(" %", " %").strip()
    return label[0].upper() + label[1:] if label else str(column)


def _is_money(column: str) -> bool:
    low = column.lower()
    if low in TEXT_COLUMNS:
        return False
    if low in MONEY_COLUMNS:
        return True
    if any(x in low for x in MONEY_EXCLUDE):
        return False
    return any(h in low for h in MONEY_HINTS)


def _is_percent(column: str) -> bool:
    low = column.lower()
    return low.endswith("_pct") or low.endswith("_percent") or low == "gross_margin_pct"


def _is_count(column: str) -> bool:
    low = column.lower()
    if low in TEXT_COLUMNS or _is_money(low) or _is_percent(low):
        return False
    return any(h in low for h in COUNT_HINTS)


def _decimals(series: pd.Series, money: bool) -> int:
    """Pick decimal places from the data's magnitude.

    A labor rate of $9.50 must not render as $10, and 0.85 machine hours must
    not render as 1 - while a $12,600 board price does not need cents.
    """
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return 0
    largest = float(values.abs().max())
    has_fraction = bool(((values % 1) != 0).any())
    if money:
        return 2 if largest < 100 else 0
    return 2 if has_fraction else 0


def auto_column_config(
    df: pd.DataFrame,
    overrides: Optional[Dict[str, object]] = None,
    money_decimals: Optional[int] = None,
) -> Dict[str, object]:
    """Build a Streamlit column_config for every column, honoring overrides."""
    config: Dict[str, object] = {}
    if df is None or df.empty and not len(df.columns):
        return dict(overrides or {})
    for col in df.columns:
        name = str(col)
        label = humanize(name)
        is_bool = pd.api.types.is_bool_dtype(df[col]) if col in df else False
        numeric = (pd.api.types.is_numeric_dtype(df[col]) and not is_bool) if col in df else False
        if is_bool:
            config[col] = st.column_config.CheckboxColumn(label)
        elif _is_percent(name):
            config[col] = st.column_config.NumberColumn(label, format="%.1f%%")
        elif numeric and _is_money(name):
            dp = money_decimals if money_decimals is not None else _decimals(df[col], True)
            config[col] = st.column_config.NumberColumn(label, format=f"$%,.{dp}f")
        elif numeric and (_is_count(name) or _is_duration(name)):
            dp = _decimals(df[col], False)
            config[col] = st.column_config.NumberColumn(label, format=f"%,.{dp}f")
        else:
            config[col] = st.column_config.Column(label)
    config.update(overrides or {})
    return config
