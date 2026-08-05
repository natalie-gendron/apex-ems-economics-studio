"""Service-level economics.

A supplier with a higher unit price can still be economically superior via
better service: less safety stock, fewer expedites, lower stockout exposure.
This engine prices those effects.

Annual formulas for one allocation line (spend = quoted annual spend,
revenue = allocated annual revenue at OEM selling price):
    safety_stock_cost  = safety_stock_days/365 x spend x carrying %
    buffer_stock_cost  = buffer_stock_days/365 x spend x carrying %
    expedite_cost      = expedite_rate % x volume x expedite premium per unit
    stockout_expected  = stockout_prob % x revenue_at_risk % x revenue x margin %
                          (expected lost margin - a decision measure)
    penalty_cost       = contractual customer penalties x volume share
    service_cost       = sum of the above

Expedite premium per unit = lane expedite cost - lane standard freight
(the standard freight is already counted in logistics).
"""
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from core.config import carrying_cost_pct


def get_service_row(data: Dict[str, pd.DataFrame], supplier_id: str) -> Optional[pd.Series]:
    sl = data.get("service_levels", pd.DataFrame())
    if sl is None or sl.empty:
        return None
    match = sl[sl["supplier_id"] == supplier_id]
    if match.empty:
        return None
    return match.iloc[0]


def service_cost(
    service: Optional[pd.Series],
    lane: Optional[pd.Series],
    volume: float,
    annual_spend: float,
    annual_revenue: float,
    settings: Dict[str, float],
    volume_share: float = 1.0,
) -> Dict[str, float]:
    if service is None:
        return {
            "safety_stock_cost": 0.0, "buffer_stock_cost": 0.0,
            "expedite_cost": 0.0, "stockout_expected_cost": 0.0,
            "penalty_cost": 0.0, "service_cost": 0.0,
            "revenue_at_risk": 0.0, "service_missing": 1.0,
        }

    def f(row: Optional[pd.Series], key: str) -> float:
        if row is None:
            return 0.0
        try:
            v = float(row.get(key, 0) or 0)
        except (TypeError, ValueError):
            v = 0.0
        return 0.0 if pd.isna(v) else v

    rate = carrying_cost_pct(settings) / 100.0
    margin = settings.get("gross_margin_reference_pct", 54.0) / 100.0
    daily_spend = annual_spend / 365.0 if annual_spend else 0.0

    safety_stock = f(service, "safety_stock_days") * daily_spend * rate
    buffer_stock = f(service, "buffer_stock_days") * daily_spend * rate

    expedite_premium = max(
        f(lane, "expedite_freight_cost_per_unit") - f(lane, "freight_cost_per_unit"), 0.0
    )
    expedite = f(service, "expedite_rate_pct") / 100.0 * volume * expedite_premium

    revenue_at_risk = f(service, "revenue_at_risk_pct") / 100.0 * annual_revenue
    stockout = f(service, "stockout_probability_pct") / 100.0 * revenue_at_risk * margin
    penalties = f(service, "customer_penalty_annual") * volume_share

    total = safety_stock + buffer_stock + expedite + stockout + penalties
    return {
        "safety_stock_cost": safety_stock,
        "buffer_stock_cost": buffer_stock,
        "expedite_cost": expedite,
        "stockout_expected_cost": stockout,
        "penalty_cost": penalties,
        "service_cost": total,
        "revenue_at_risk": revenue_at_risk,
        "service_missing": 0.0,
    }
