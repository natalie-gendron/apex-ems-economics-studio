"""Cost-of-poor-quality (COPQ) calculations.

The engine computes the total cost of poor quality and the OEM-borne share.
Contractual responsibility (OEM / Shared / EMS) determines how much of each
cost lands on the OEM: even when the EMS is responsible, a residual OEM
burden applies (configurable in global settings).

Annual formulas for a product-supplier flow of ``volume`` units at
``unit_price``:
    scrap_cost      = volume x scrap_rate x unit_price
    rework_cost     = volume x rework_rate x rework_hours x rework_rate_usd
    retest_cost     = volume x rework_rate x retest_cost_per_unit
    return_cost     = volume x return_rate x unit_price x return_handling_factor
    warranty_cost   = volume x warranty_rate x unit_price
    field_failure   = volume x field_failure_rate x unit_price x repair_multiplier
    downtime_cost   = downtime_hours x downtime_cost_per_hour x volume_share
    premium_freight = events_per_year x cost_per_event x volume_share
    expected_recall = recall_probability x recall_impact x volume_share
                      (expected value - a decision measure, not a booked cost)

``volume_share`` scales supplier-year level figures (downtime, premium
freight events, recall) by the share of the supplier-product volume this
allocation represents, so partial allocations do not double count.
"""
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from core.config import oem_share_for_responsibility


def get_quality_row(
    data: Dict[str, pd.DataFrame], supplier_id: str, product_id: str
) -> Optional[pd.Series]:
    qm = data.get("quality_metrics", pd.DataFrame())
    if qm is None or qm.empty:
        return None
    match = qm[(qm["supplier_id"] == supplier_id) & (qm["product_id"] == product_id)]
    if match.empty:
        return None
    return match.iloc[0]


def copq(
    quality: Optional[pd.Series],
    volume: float,
    unit_price: float,
    settings: Dict[str, float],
    volume_share: float = 1.0,
) -> Dict[str, float]:
    """Annual cost of poor quality for one allocation line.

    Returns both total COPQ and OEM-borne COPQ plus the per-bucket detail
    (OEM-borne values), final yield, and good units.
    """
    if quality is None:
        return {
            "scrap_cost": 0.0, "rework_cost": 0.0, "retest_cost": 0.0,
            "return_cost": 0.0, "warranty_cost": 0.0, "field_failure_cost": 0.0,
            "downtime_cost": 0.0, "premium_freight_cost": 0.0,
            "expected_recall_cost": 0.0, "total_copq": 0.0, "oem_copq": 0.0,
            "copq_per_unit": 0.0, "final_yield_pct": 100.0,
            "good_units": volume, "quality_missing": 1.0,
        }

    def f(key: str) -> float:
        try:
            v = float(quality.get(key, 0) or 0)
        except (TypeError, ValueError):
            v = 0.0
        return 0.0 if pd.isna(v) else v

    repair_mult = settings.get("field_repair_cost_multiplier", 2.5)
    scrap_share = oem_share_for_responsibility(settings, quality.get("scrap_responsibility"))
    rework_share = oem_share_for_responsibility(settings, quality.get("rework_responsibility"))
    warranty_share = oem_share_for_responsibility(settings, quality.get("warranty_responsibility"))

    scrap = volume * f("scrap_rate_pct") / 100.0 * unit_price
    rework = volume * f("rework_rate_pct") / 100.0 * f("rework_hours_per_unit") * f("rework_labor_rate")
    retest = volume * f("rework_rate_pct") / 100.0 * f("retest_cost_per_unit")
    return_factor = settings.get("quality_return_handling_factor", 0.5)
    returns = volume * f("return_rate_pct") / 100.0 * unit_price * return_factor
    warranty = volume * f("warranty_rate_pct") / 100.0 * unit_price
    field_failure = volume * f("field_failure_rate_pct") / 100.0 * unit_price * repair_mult
    downtime = f("downtime_hours_per_year") * f("downtime_cost_per_hour") * volume_share
    premium_freight = f("premium_freight_events_per_year") * f("premium_freight_cost_per_event") * volume_share
    expected_recall = f("recall_probability_pct") / 100.0 * f("recall_impact_usd") * volume_share

    total = (scrap + rework + retest + returns + warranty + field_failure
             + downtime + premium_freight + expected_recall)

    oem_scrap = scrap * scrap_share
    oem_rework = (rework + retest) * rework_share
    oem_warranty = (warranty + field_failure + returns) * warranty_share
    # Downtime at the OEM line, quality expedites, and recall exposure land on
    # the OEM regardless of contractual recovery in this first-pass model.
    oem_total = oem_scrap + oem_rework + oem_warranty + downtime + premium_freight + expected_recall

    final_yield = f("final_yield_pct") or 100.0
    good_units = volume * final_yield / 100.0

    return {
        "scrap_cost": oem_scrap,
        "rework_cost": rework * rework_share,
        "retest_cost": retest * rework_share,
        "return_cost": returns * warranty_share,
        "warranty_cost": warranty * warranty_share,
        "field_failure_cost": field_failure * warranty_share,
        "downtime_cost": downtime,
        "premium_freight_cost": premium_freight,
        "expected_recall_cost": expected_recall,
        "total_copq": total,
        "oem_copq": oem_total,
        "copq_per_unit": oem_total / volume if volume else 0.0,
        "final_yield_pct": final_yield,
        "good_units": good_units,
        "quality_missing": 0.0,
    }
