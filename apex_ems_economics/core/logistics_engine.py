"""Logistics, duties, and landed-cost calculations.

All figures are OEM-incremental: if the quote already includes freight or
duties (quote flags), the corresponding component is zeroed so it is never
double counted.

Formulas (per unit):
    freight            = lane freight_cost_per_unit            [if OEM pays]
    insurance          = unit_price x insurance_pct
    brokerage          = brokerage_per_shipment / units_per_shipment
    duties             = unit_price x duty_rate_pct
    tariffs            = unit_price x tariff_rate_pct
    packaging/handling/warehousing = per-unit adders
    logistics_per_unit = sum of the above

Note: expedite/premium freight driven by *service* performance is costed in
the service engine; premium freight caused by *quality* events is costed in
the quality engine. This engine carries only routine logistics.
"""
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd


def get_lane(data: Dict[str, pd.DataFrame], supplier_id: str, site_id: str) -> Optional[pd.Series]:
    lanes = data.get("logistics_assumptions", pd.DataFrame())
    if lanes is None or lanes.empty:
        return None
    match = lanes[(lanes["supplier_id"] == supplier_id) & (lanes["site_id"] == site_id)]
    if match.empty:
        match = lanes[lanes["supplier_id"] == supplier_id]
    if match.empty:
        return None
    return match.iloc[0]


def landed_cost_per_unit(
    lane: Optional[pd.Series],
    unit_price: float,
    includes_freight: bool = False,
    includes_duties: bool = False,
) -> Dict[str, float]:
    """Return the per-unit logistics breakdown for one product-supplier lane."""
    if lane is None:
        return {
            "freight": 0.0, "insurance": 0.0, "brokerage": 0.0,
            "duties": 0.0, "tariffs": 0.0, "packaging": 0.0,
            "handling": 0.0, "warehousing": 0.0,
            "logistics_per_unit": 0.0, "duty_per_unit": 0.0, "lane_missing": 1.0,
        }

    def f(key: str) -> float:
        try:
            v = float(lane.get(key, 0) or 0)
        except (TypeError, ValueError):
            v = 0.0
        return 0.0 if pd.isna(v) else v

    oem_pays_freight = str(lane.get("freight_paid_by", "OEM")).strip().upper() == "OEM"
    freight = f("freight_cost_per_unit") if (oem_pays_freight and not includes_freight) else 0.0
    insurance = unit_price * f("insurance_pct") / 100.0
    units_per_shipment = f("units_per_shipment")
    brokerage = f("brokerage_per_shipment") / units_per_shipment if units_per_shipment else 0.0
    duties = 0.0 if includes_duties else unit_price * f("duty_rate_pct") / 100.0
    tariffs = 0.0 if includes_duties else unit_price * f("tariff_rate_pct") / 100.0
    packaging = f("packaging_cost_per_unit")
    handling = f("handling_cost_per_unit")
    warehousing = f("warehousing_cost_per_unit")

    logistics = freight + insurance + brokerage + packaging + handling + warehousing
    return {
        "freight": freight,
        "insurance": insurance,
        "brokerage": brokerage,
        "duties": duties,
        "tariffs": tariffs,
        "packaging": packaging,
        "handling": handling,
        "warehousing": warehousing,
        "logistics_per_unit": logistics,
        "duty_per_unit": duties + tariffs,
        "lane_missing": 0.0,
    }
