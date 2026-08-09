"""Deterministic recommendation engine.

Rule-based (no AI, fully auditable). It never simply picks the cheapest
supplier: rules weigh total economics, working capital, quality, service,
capacity, risk, switching cost, and data confidence, and every
recommendation carries its "why", impacts, risks, conditions, confidence,
and next validation step.
"""
from __future__ import annotations

from typing import Dict, List

import pandas as pd

from core.economics_engine import ScenarioResult


def recommend(
    data: Dict[str, pd.DataFrame],
    results: Dict[str, ScenarioResult],
    baseline_id: str,
    data_quality: Dict[str, float] | None = None,
    settings: Dict[str, float] | None = None,
) -> List[Dict[str, str]]:
    from core.config import load_settings

    settings = settings or load_settings(data)
    fpy_threshold = settings.get("fpy_attention_threshold_pct", 94.0)
    recs: List[Dict[str, str]] = []
    base = results.get(baseline_id)
    if base is None or base.line_items.empty:
        return recs
    dq_score = (data_quality or {}).get("overall_score", 60.0)

    # ------------------------------------------------------------------
    # 1. Scenario-level: best scenario by recurring economics + cash.
    # ------------------------------------------------------------------
    for scenario_id, res in results.items():
        if scenario_id == baseline_id:
            continue
        delta_recurring = (res.totals.get("recurring_economic_cost", 0)
                           - base.totals.get("recurring_economic_cost", 0))
        one_time = res.totals.get("one_time_cost", 0) + res.totals.get("transition_cost", 0)
        delta_wc = (res.totals.get("oem_inventory_value", 0)
                    - base.totals.get("oem_inventory_value", 0))
        delta_risk = res.totals.get("risk_cost", 0) - base.totals.get("risk_cost", 0)

        if delta_recurring < 0 and abs(delta_recurring) * 2 > one_time:
            payback = one_time / abs(delta_recurring) * 12 if delta_recurring else 0
            recs.append({
                "action": f"Adopt scenario: {res.scenario_name}",
                "why": (f"Recurring economic cost improves by ${abs(delta_recurring):,.0f}/yr; "
                        f"one-time cost ${one_time:,.0f} pays back in ~{payback:.0f} months."),
                "financial_impact": f"${abs(delta_recurring):,.0f}/yr recurring; ${one_time:,.0f} one-time",
                "operational_impact": "Requires transition management; see capacity and transfer lead times.",
                "key_risks": "Execution risk during transition; assumptions on quality and service holding.",
                "required_conditions": "Capacity confirmed; qualification complete; contract amendments signed.",
                "confidence": "Medium" if dq_score < 75 else "High",
                "next_step": "Validate the top low-confidence assumptions driving this scenario before committing.",
            })
        elif delta_risk < -50000 and delta_recurring < abs(delta_risk):
            recs.append({
                "action": f"Consider scenario: {res.scenario_name} (risk reduction)",
                "why": (f"Expected risk cost falls by ${abs(delta_risk):,.0f}/yr for a net recurring "
                        f"cost change of ${delta_recurring:,.0f}/yr - an insurance-like trade."),
                "financial_impact": f"${delta_recurring:,.0f}/yr recurring; risk -${abs(delta_risk):,.0f}/yr expected",
                "operational_impact": "Adds a qualified source; more supply-chain coordination.",
                "key_risks": "Expected-risk figures are decision measures, not booked costs.",
                "required_conditions": "Second-source qualification passes; capacity reserved.",
                "confidence": "Medium",
                "next_step": "Pressure-test the disruption probability and impact estimates with Supply Chain.",
            })

    # ------------------------------------------------------------------
    # 2. Supplier-level rules on the baseline.
    # ------------------------------------------------------------------
    li = base.line_items
    ss = base.supplier_summary
    if not ss.empty and len(ss) > 1:
        by_quote = ss.sort_values("quoted_per_unit")
        by_econ = ss.sort_values("econ_cost_per_unit")
        cheapest_quote = by_quote.iloc[0]
        cheapest_econ = by_econ.iloc[0]
        if cheapest_quote["supplier_id"] != cheapest_econ["supplier_id"]:
            recs.append({
                "action": "Do not shift volume on quoted price alone",
                "why": (f"{cheapest_quote['supplier_name']} has the lowest quoted price but "
                        f"{cheapest_econ['supplier_name']} has the lowest true economic cost once "
                        "logistics, quality, working capital, service, and risk are included."),
                "financial_impact": "Prevents value-destroying volume shifts.",
                "operational_impact": "None immediately.",
                "key_risks": "Quoted-price framing in negotiations obscuring total economics.",
                "required_conditions": "Keep the economic model current before sourcing decisions.",
                "confidence": "High",
                "next_step": "Share the quote-to-economic-cost bridge with Procurement.",
            })

    # Bundled pricing / transparency rule.
    quotes = data.get("supplier_quotes", pd.DataFrame())
    if quotes is not None and not quotes.empty:
        bundled = quotes[quotes["quoted_material_content"].isna()]["supplier_id"].unique()
        for sid in bundled:
            sup_name = _supplier_name(data, sid)
            recs.append({
                "action": f"Require cost transparency from {sup_name}",
                "why": "Quotes are bundled with no material/conversion breakdown; should-cost "
                       "and negotiation leverage are limited and residual analysis is low-confidence.",
                "financial_impact": "Enables should-cost-driven negotiation (see Contract Opportunities).",
                "operational_impact": "Contract renewal negotiation effort.",
                "key_risks": "Supplier resistance; may trade transparency for price or volume.",
                "required_conditions": "Contract renewal window or new-business leverage.",
                "confidence": "High",
                "next_step": "Add open-book requirement to the next RFQ/renewal package.",
            })

    # Quality-before-volume rule.
    qm = data.get("quality_metrics", pd.DataFrame())
    if qm is not None and not qm.empty and not li.empty:
        for sid in li["supplier_id"].unique():
            rows = qm[qm["supplier_id"] == sid]
            if rows.empty:
                continue
            fpy = rows["first_pass_yield_pct"].astype(float).mean()
            if fpy < fpy_threshold:
                recs.append({
                    "action": f"Improve quality at {_supplier_name(data, sid)} before shifting more volume",
                    "why": f"Average first-pass yield is {fpy:.1f}%, below the {fpy_threshold:.0f}% attention threshold - added volume would amplify OEM-borne COPQ.",
                    "financial_impact": "COPQ scales with volume; see Quality Economics page.",
                    "operational_impact": "Joint corrective-action program required.",
                    "key_risks": "Yield may degrade further during any ramp.",
                    "required_conditions": "FPY recovery to committed levels for two consecutive quarters.",
                    "confidence": "High",
                    "next_step": "Launch supplier corrective action with milestone gates.",
                })

    # Data-confidence rule.
    if dq_score < 65:
        recs.append({
            "action": "Collect more data before finalizing sourcing decisions",
            "why": f"Overall data-quality score is {dq_score:.0f}/100; key assumptions are low-confidence.",
            "financial_impact": "Reduces risk of deciding on wrong numbers.",
            "operational_impact": "Data-collection effort across functions.",
            "key_risks": "Delay has an option cost if market terms move.",
            "required_conditions": "Owners assigned to the priority data gaps (see Assumption Register).",
            "confidence": "High",
            "next_step": "Work the recommended data-collection priorities on the Data Quality page.",
        })

    return recs


def _supplier_name(data: Dict[str, pd.DataFrame], supplier_id: str) -> str:
    sup = data["suppliers"]
    match = sup[sup["supplier_id"] == supplier_id]
    return str(match.iloc[0]["supplier_name"]) if not match.empty else str(supplier_id)
