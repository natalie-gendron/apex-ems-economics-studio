"""Configurable weighted supplier scoring.

The score is a decision-support summary only - it never replaces the
detailed economics. Each dimension is normalized to 0-100 (higher = better)
and combined with editable weights that must sum to 100%.
"""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

RATING_MAP = {"Low": 80.0, "Medium": 55.0, "High": 30.0}  # for risk-like text ratings
TRANSPARENCY_MAP = {
    "Full open-book": 95.0, "Partial open-book": 70.0,
    "Bundled pricing": 30.0, "No cost transparency": 10.0,
}
FIT_MAP = {"High": 90.0, "Medium": 60.0, "Low": 30.0}


def _scale_inverse(series: pd.Series) -> pd.Series:
    """Normalize where lower is better -> 0-100 with best=100."""
    s = series.astype(float)
    lo, hi = s.min(), s.max()
    if hi == lo:
        return pd.Series(100.0, index=s.index)
    return (hi - s) / (hi - lo) * 100.0


def supplier_scores(
    data: Dict[str, pd.DataFrame],
    supplier_summary: pd.DataFrame,
    risk_costs_by_supplier: Optional[pd.Series] = None,
    weights: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Score suppliers that appear in the scenario's supplier summary."""
    if supplier_summary.empty:
        return pd.DataFrame()
    weights = weights if weights is not None else data.get("scoring_weights", pd.DataFrame())
    wmap = {row["dimension"]: float(row["weight_pct"]) for _, row in weights.iterrows()}

    suppliers = data["suppliers"].set_index("supplier_id")
    service = data.get("service_levels", pd.DataFrame())
    service = service.set_index("supplier_id") if service is not None and not service.empty else pd.DataFrame()
    capacity = data.get("capacity_records", pd.DataFrame())

    df = supplier_summary.set_index("supplier_id").copy()
    scores = pd.DataFrame(index=df.index)
    scores["Economic cost"] = _scale_inverse(df["econ_cost_per_unit"])

    def sup_attr(sid, col, default=3.0):
        try:
            return float(suppliers.loc[sid, col])
        except (KeyError, TypeError, ValueError):
            return default

    def svc_attr(sid, col, default=0.0):
        try:
            return float(service.loc[sid, col])
        except (KeyError, TypeError, ValueError):
            return default

    scores["Quality"] = [sup_attr(s, "quality_rating") * 20 for s in df.index]
    scores["Delivery"] = [min(svc_attr(s, "actual_otd_pct", 90.0), 100.0) for s in df.index]
    scores["Service"] = [
        max(0.0, 100.0 - max(svc_attr(s, "actual_lead_time_days", 30.0) - 15.0, 0.0) * 1.5)
        for s in df.index]
    scores["Flexibility"] = [
        min((svc_attr(s, "upside_flex_pct") + svc_attr(s, "downside_flex_pct")) * 2.0, 100.0)
        for s in df.index]

    cap_scores = []
    for sid in df.index:
        rows = capacity[capacity["supplier_id"] == sid] if capacity is not None and not capacity.empty else pd.DataFrame()
        if rows.empty:
            cap_scores.append(50.0)
        else:
            util = float(rows["utilization_pct"].mean())
            max_util = float(rows["max_utilization_pct"].mean()) or 90.0
            headroom = max(max_util - util, 0.0) / max_util
            cap_scores.append(min(headroom * 250.0, 100.0))
    scores["Capacity"] = cap_scores

    # Working capital: normalized inverse of WC cost per dollar of spend.
    wc_intensity = np.where(df["quoted_cost"] > 0, df["wc_cost"] / df["quoted_cost"], 0.0)
    scores["Working capital"] = _scale_inverse(pd.Series(wc_intensity, index=df.index))

    if risk_costs_by_supplier is not None:
        risk_intensity = pd.Series(
            [risk_costs_by_supplier.get(s, 0.0) / max(df.loc[s, "quoted_cost"], 1.0) for s in df.index],
            index=df.index)
        scores["Risk"] = _scale_inverse(risk_intensity)
    else:
        scores["Risk"] = 50.0

    scores["Data transparency"] = [
        TRANSPARENCY_MAP.get(str(suppliers.loc[s, "data_transparency"]) if s in suppliers.index else "", 40.0)
        for s in df.index]
    scores["Strategic fit"] = [
        FIT_MAP.get(str(suppliers.loc[s, "strategic_fit"]) if s in suppliers.index else "", 50.0)
        for s in df.index]

    total_weight = sum(wmap.values()) or 100.0
    weighted = pd.Series(0.0, index=scores.index)
    for dim, w in wmap.items():
        if dim in scores.columns:
            weighted += scores[dim] * w / total_weight
    scores["Weighted score"] = weighted
    scores.insert(0, "supplier_name", [
        suppliers.loc[s, "supplier_name"] if s in suppliers.index else s for s in scores.index])
    return scores.sort_values("Weighted score", ascending=False).reset_index()


def weights_valid(weights: pd.DataFrame) -> bool:
    if weights is None or weights.empty:
        return False
    return abs(float(weights["weight_pct"].sum()) - 100.0) < 0.01
