"""Capacity and flexibility analysis."""
from __future__ import annotations

from typing import Dict

import pandas as pd


def capacity_analysis(
    data: Dict[str, pd.DataFrame], line_items: pd.DataFrame
) -> pd.DataFrame:
    """Per-site capacity headroom and feasibility versus allocated volume.

    headroom            = available x max_util% - committed
    allocated (model)   = scenario volume routed to the site
    feasible            = allocated <= headroom + overtime
    reservation cost/unit = reservation fee / allocated volume
    """
    capacity = data.get("capacity_records", pd.DataFrame())
    if capacity is None or capacity.empty:
        return pd.DataFrame()

    alloc_by_site = (
        line_items.groupby("site_id")["volume"].sum()
        if not line_items.empty else pd.Series(dtype=float))

    rows = []
    for _, cap in capacity.iterrows():
        site = str(cap["site_id"])
        available = float(cap.get("available_capacity_units", 0) or 0)
        committed = float(cap.get("committed_capacity_units", 0) or 0)
        max_util = float(cap.get("max_utilization_pct", 90) or 90) / 100.0
        overtime = float(cap.get("overtime_capacity_units", 0) or 0)
        allocated = float(alloc_by_site.get(site, 0.0))
        usable = available * max_util
        headroom = usable - committed
        reservation_fee = float(cap.get("reservation_fee_annual", 0) or 0)

        rows.append({
            "site_id": site,
            "supplier_id": cap.get("supplier_id", ""),
            "available_capacity": available,
            "usable_capacity": usable,
            "committed_capacity": committed,
            "headroom": headroom,
            "overtime_capacity": overtime,
            "allocated_volume_model": allocated,
            "incremental_feasible": max(headroom + overtime - allocated, 0.0),
            "volume_feasible": allocated <= headroom + overtime,
            "utilization_pct": float(cap.get("utilization_pct", 0) or 0),
            "max_utilization_pct": float(cap.get("max_utilization_pct", 90) or 90),
            "reservation_fee_annual": reservation_fee,
            "reservation_cost_per_unit": reservation_fee / allocated if allocated else 0.0,
            "expansion_capacity": float(cap.get("expansion_capacity_units", 0) or 0),
            "expansion_lead_time_months": float(cap.get("expansion_lead_time_months", 0) or 0),
            "ramp_rate_units_per_month": float(cap.get("ramp_rate_units_per_month", 0) or 0),
            "transfer_lead_time_weeks": float(cap.get("transfer_lead_time_weeks", 0) or 0),
            "qualification_lead_time_weeks": float(cap.get("qualification_lead_time_weeks", 0) or 0),
            "constraint_notes": cap.get("constraint_notes", ""),
        })
    return pd.DataFrame(rows)


def volume_shift_feasibility(
    capacity_df: pd.DataFrame, target_site: str, additional_volume: float
) -> Dict[str, object]:
    """Can `additional_volume` move to `target_site`, and how fast?"""
    if capacity_df.empty:
        return {"feasible": False, "reason": "No capacity data."}
    m = capacity_df[capacity_df["site_id"] == target_site]
    if m.empty:
        return {"feasible": False, "reason": f"No capacity record for {target_site}."}
    row = m.iloc[0]
    slack = row["incremental_feasible"]
    ramp = row["ramp_rate_units_per_month"]
    months_to_ramp = additional_volume / 12 / ramp if ramp else float("inf")
    feasible = additional_volume <= slack
    return {
        "feasible": bool(feasible),
        "incremental_feasible": float(slack),
        "months_to_ramp_monthly_rate": float(months_to_ramp),
        "qualification_weeks": float(row["qualification_lead_time_weeks"]),
        "transfer_weeks": float(row["transfer_lead_time_weeks"]),
        "reason": ("Within headroom + overtime" if feasible
                   else f"Exceeds incremental feasible volume by {additional_volume - slack:,.0f} units"),
    }
