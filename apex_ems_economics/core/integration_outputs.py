"""Interface-ready output tables for future Apex platform integration.

Standardized frames consumable by the Executive SIOP Decision Engine,
Manufacturing Economics Studio, Margin Intelligence, Working Capital
Optimizer, and Strategic Network Optimizer.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from core.economics_engine import ScenarioResult


def product_cost_output(result: ScenarioResult) -> pd.DataFrame:
    li = result.line_items
    if li.empty:
        return pd.DataFrame()
    out = li[[
        "product_id", "scenario_id", "supplier_id",
        "material_per_unit", "conversion_per_unit",
        "quality_cost", "logistics_cost", "total_economic_cost",
        "econ_cost_per_unit", "quote_confidence",
    ]].rename(columns={
        "material_per_unit": "material_cost_per_unit",
        "conversion_per_unit": "conversion_cost_per_unit",
        "quality_cost": "quality_cost_annual",
        "logistics_cost": "logistics_cost_annual",
        "total_economic_cost": "total_economic_cost_annual",
        "econ_cost_per_unit": "cost_per_unit",
        "quote_confidence": "confidence",
    })
    return out


def inventory_output(result: ScenarioResult, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    li = result.line_items
    if li.empty:
        return pd.DataFrame()
    out = li[["product_id", "supplier_id", "scenario_id",
              "oem_inventory_value", "wc_carrying", "risk_per_unit"]].copy()
    out["ownership"] = "OEM"
    out["location"] = "EMS site + in transit"
    daily = li["quoted_cost"] / 365.0
    out["days_of_supply"] = np.where(daily > 0, li["oem_inventory_value"] / daily, 0.0)
    out = out.rename(columns={
        "oem_inventory_value": "inventory_value",
        "wc_carrying": "carrying_cost_annual",
        "risk_per_unit": "risk_exposure_per_unit",
    })
    return out


def margin_output(result: ScenarioResult, baseline: ScenarioResult) -> pd.DataFrame:
    li = result.line_items
    if li.empty:
        return pd.DataFrame()
    grouped = li.groupby(["product_id", "scenario_id"], as_index=False).agg(
        revenue=("revenue", "sum"),
        cogs=("quoted_cost", "sum"),
        logistics=("logistics_cost", "sum"),
        duties=("duty_cost", "sum"),
        consigned=("consigned_material_cost", "sum"),
    )
    grouped["cogs"] = grouped["cogs"] + grouped["logistics"] + grouped["duties"] + grouped["consigned"]
    grouped = grouped.drop(columns=["logistics", "duties", "consigned"])
    grouped["gross_profit"] = grouped["revenue"] - grouped["cogs"]
    grouped["gross_margin_pct"] = np.where(
        grouped["revenue"] > 0, grouped["gross_profit"] / grouped["revenue"] * 100, 0.0)

    base_li = baseline.line_items
    if not base_li.empty:
        base_cogs = base_li.groupby("product_id").apply(
            lambda g: g["quoted_cost"].sum() + g["logistics_cost"].sum()
            + g["duty_cost"].sum() + g["consigned_material_cost"].sum(),
            include_groups=False)
        grouped["cogs_change_vs_baseline"] = grouped.apply(
            lambda r: r["cogs"] - base_cogs.get(r["product_id"], r["cogs"]), axis=1)
    return grouped


def supply_output(result: ScenarioResult, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    li = result.line_items
    if li.empty:
        return pd.DataFrame()
    service = data.get("service_levels", pd.DataFrame())
    capacity = data.get("capacity_records", pd.DataFrame())
    out = li[["product_id", "supplier_id", "scenario_id", "site_id", "volume", "risk_cost"]].copy()
    out = out.rename(columns={"volume": "allocated_volume", "risk_cost": "expected_risk_cost"})

    def lead_time(sid):
        if service is None or service.empty:
            return np.nan
        m = service[service["supplier_id"] == sid]
        return float(m.iloc[0]["actual_lead_time_days"]) if not m.empty else np.nan

    def otd(sid):
        if service is None or service.empty:
            return np.nan
        m = service[service["supplier_id"] == sid]
        return float(m.iloc[0]["actual_otd_pct"]) if not m.empty else np.nan

    def util(site):
        if capacity is None or capacity.empty:
            return np.nan
        m = capacity[capacity["site_id"] == site]
        return float(m.iloc[0]["utilization_pct"]) if not m.empty else np.nan

    out["lead_time_days"] = out["supplier_id"].map(lead_time)
    out["service_level_otd_pct"] = out["supplier_id"].map(otd)
    out["capacity_utilization_pct"] = out["site_id"].map(util)
    return out
