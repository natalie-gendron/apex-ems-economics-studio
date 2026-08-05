"""Risk-adjusted economics.

    Expected risk cost = probability x estimated financial impact

Expected risk cost is a **decision-analysis measure**, not an accounting
expense: it prices the option value of lower-risk suppliers so that risk can
be compared on the same axis as cost. It must never be booked.

Allocation logic:
  * Supplier-level risks (no product) are spread across that supplier's
    allocation lines in proportion to quoted spend.
  * Product-level risks (no supplier) are spread across that product's
    allocation lines in proportion to allocated volume.
  * Supplier+product risks go entirely to matching lines.
"""
from __future__ import annotations

from typing import Dict

import pandas as pd


def expected_cost(row: pd.Series) -> float:
    try:
        p = float(row.get("probability_pct", 0) or 0) / 100.0
        impact = float(row.get("financial_impact_usd", 0) or 0)
    except (TypeError, ValueError):
        return 0.0
    return p * impact


def risk_register_with_expected_cost(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    risks = data.get("risks", pd.DataFrame())
    if risks is None or risks.empty:
        return pd.DataFrame()
    out = risks.copy()
    out["expected_cost"] = out.apply(expected_cost, axis=1)
    return out.sort_values("expected_cost", ascending=False)


def allocate_risk_costs(
    data: Dict[str, pd.DataFrame], line_items: pd.DataFrame
) -> pd.Series:
    """Return expected risk cost per line-item row (indexed like line_items)."""
    result = pd.Series(0.0, index=line_items.index)
    risks = data.get("risks", pd.DataFrame())
    if risks is None or risks.empty or line_items.empty:
        return result

    spend_by_supplier = line_items.groupby("supplier_id")["quoted_cost"].sum()
    volume_by_product = line_items.groupby("product_id")["volume"].sum()

    for _, risk in risks.iterrows():
        cost = expected_cost(risk)
        if cost <= 0:
            continue
        sup = str(risk.get("supplier_id") or "").strip()
        prod = str(risk.get("product_id") or "").strip()
        sup = "" if sup in ("nan", "None") else sup
        prod = "" if prod in ("nan", "None") else prod

        if sup and prod:
            mask = (line_items["supplier_id"] == sup) & (line_items["product_id"] == prod)
            if mask.any():
                vol = line_items.loc[mask, "volume"].sum()
                weights = line_items.loc[mask, "volume"] / vol if vol else 1.0 / mask.sum()
                result.loc[mask] += cost * weights
        elif sup:
            mask = line_items["supplier_id"] == sup
            total_spend = spend_by_supplier.get(sup, 0.0)
            if mask.any() and total_spend > 0:
                result.loc[mask] += cost * line_items.loc[mask, "quoted_cost"] / total_spend
        elif prod:
            mask = line_items["product_id"] == prod
            total_vol = volume_by_product.get(prod, 0.0)
            if mask.any() and total_vol > 0:
                result.loc[mask] += cost * line_items.loc[mask, "volume"] / total_vol
    return result
