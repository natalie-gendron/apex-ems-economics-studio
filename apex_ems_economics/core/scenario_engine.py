"""Scenario management: baseline resolution and override application.

A scenario is the baseline data set plus:
  * a demand multiplier (scenarios.demand_multiplier),
  * an allocation table (allocations rows for that scenario),
  * zero or more overrides (scenario_overrides rows) that patch specific
    fields on specific entity rows.

Overrides support three change types:
  * ``absolute``   - replace the field value
  * ``multiplier`` - multiply the field value
  * ``delta``      - add to the field value

Special override fields:
  * entity=quote, field=``price_multiplier``: multiplies the base price and
    every tier price on the quote in one override.
  * entity=inventory, field=``ownership_to_ems_share``: converts the given
    percentage of an OEM-owned inventory record's value to EMS ownership by
    splitting the record (models consignment-to-EMS renegotiations).
  * entity=service uses supplier_id as its entity key.
"""
from __future__ import annotations

from typing import Dict

import pandas as pd

# entity name -> (table, id column)
ENTITY_TABLE_MAP = {
    "product": ("products", "product_id"),
    "quote": ("supplier_quotes", "quote_id"),
    "contract_term": ("contract_terms", "term_id"),
    "inventory": ("inventory_records", "inv_id"),
    "risk": ("risks", "risk_id"),
    "quality": ("quality_metrics", "supplier_id"),
    "logistics": ("logistics_assumptions", "lane_id"),
    "service": ("service_levels", "supplier_id"),
    "capacity": ("capacity_records", "site_id"),
    "platform": ("tester_platforms", "platform_id"),
    "system_component": ("system_components", "system_comp_id"),
}

QUOTE_PRICE_COLUMNS = ["base_unit_price", "tier2_unit_price", "tier3_unit_price"]


def get_scenario_row(data: Dict[str, pd.DataFrame], scenario_id: str) -> pd.Series:
    scenarios = data["scenarios"]
    match = scenarios[scenarios["scenario_id"] == scenario_id]
    if match.empty:
        raise KeyError(f"Unknown scenario: {scenario_id}")
    return match.iloc[0]


def baseline_scenario_id(data: Dict[str, pd.DataFrame]) -> str:
    scenarios = data["scenarios"]
    base = scenarios[scenarios["is_baseline"] == True]  # noqa: E712
    if base.empty:
        return str(scenarios.iloc[0]["scenario_id"])
    return str(base.iloc[0]["scenario_id"])


def scenario_allocations(data: Dict[str, pd.DataFrame], scenario_id: str) -> pd.DataFrame:
    alloc = data["allocations"]
    return alloc[alloc["scenario_id"] == scenario_id].copy()


def apply_scenario(data: Dict[str, pd.DataFrame], scenario_id: str) -> Dict[str, pd.DataFrame]:
    """Return a copy of the data dict with scenario overrides applied.

    The demand multiplier is applied to ``products.annual_volume``. Original
    frames are never mutated.
    """
    scenario = get_scenario_row(data, scenario_id)
    patched = {name: df.copy() for name, df in data.items()}

    demand_mult = float(scenario.get("demand_multiplier", 1.0) or 1.0)
    if demand_mult != 1.0 and not patched["products"].empty:
        patched["products"]["annual_volume"] = (
            patched["products"]["annual_volume"].astype(float) * demand_mult
        )

    overrides = data.get("scenario_overrides", pd.DataFrame())
    if overrides is None or overrides.empty:
        return patched
    for _, ovr in overrides[overrides["scenario_id"] == scenario_id].iterrows():
        _apply_override(patched, ovr)
    return patched


def _apply_override(patched: Dict[str, pd.DataFrame], ovr: pd.Series) -> None:
    entity = str(ovr["entity"]).strip()
    if entity not in ENTITY_TABLE_MAP:
        return
    table, id_col = ENTITY_TABLE_MAP[entity]
    df = patched.get(table)
    if df is None or df.empty:
        return
    mask = df[id_col].astype(str) == str(ovr["entity_id"])
    if not mask.any():
        return

    field = str(ovr["field"]).strip()
    change_type = str(ovr["change_type"]).strip().lower()
    value = float(ovr["value"])

    if entity == "quote" and field == "price_multiplier":
        for col in QUOTE_PRICE_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
                df.loc[mask, col] = df.loc[mask, col] * value
        return

    if entity == "inventory" and field == "ownership_to_ems_share":
        share = value / 100.0
        rows = df[mask]
        for idx, row in rows.iterrows():
            if str(row.get("ownership")) != "OEM" or share <= 0:
                continue
            original_qty = float(row.get("quantity", 0) or 0)
            df.loc[idx, "quantity"] = original_qty * (1 - share)
            ems_row = row.copy()
            ems_row["inv_id"] = f"{row['inv_id']}-EMS"
            ems_row["ownership"] = "EMS"
            ems_row["quantity"] = original_qty * share
            ems_row["liability_status"] = "EMS-owned (scenario conversion)"
            patched[table] = pd.concat(
                [df, ems_row.to_frame().T], ignore_index=True
            )
            df = patched[table]
            mask = df[id_col].astype(str) == str(ovr["entity_id"])
        return

    if field not in df.columns:
        return
    is_numeric_col = pd.api.types.is_numeric_dtype(df[field])
    if is_numeric_col and not pd.api.types.is_float_dtype(df[field]):
        df[field] = df[field].astype(float)
    current = pd.to_numeric(df.loc[mask, field], errors="coerce")
    if change_type == "absolute":
        new_values: object = value
    elif change_type == "multiplier":
        new_values = current * value
    elif change_type == "delta":
        new_values = current + value
    else:
        return
    if is_numeric_col:
        df.loc[mask, field] = new_values
    else:
        # Mixed text columns (e.g. contract_terms.value) are string-dtyped under
        # pandas >= 3, which rejects numeric assignment - write numbers as text.
        if isinstance(new_values, pd.Series):
            df.loc[mask, field] = new_values.map(_number_as_text)
        else:
            df.loc[mask, field] = _number_as_text(new_values)


def _number_as_text(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)
