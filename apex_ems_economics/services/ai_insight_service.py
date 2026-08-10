"""AI insight service with a deterministic, template-based fallback.

Design contract:
  * The deterministic economic engine NEVER depends on this service.
  * If an ANTHROPIC_API_KEY is present, `narrative_insights` could call an
    LLM (interface stubbed for future integration); without a key it always
    returns deterministic, template-based insights derived from engine
    outputs, so the application runs fully offline.
  * AI output is advisory: interpretation, triangulation, anomaly flags,
    and questions - never financial calculations.
"""
from __future__ import annotations

import os
from typing import Dict, List

import pandas as pd

from core.economics_engine import ScenarioResult


def ai_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


# ---------------------------------------------------------------------------
# Anomaly detection (deterministic)
# ---------------------------------------------------------------------------

def detect_anomalies(data: Dict[str, pd.DataFrame], result: ScenarioResult) -> List[Dict[str, str]]:
    anomalies: List[Dict[str, str]] = []
    li = result.line_items
    if li.empty:
        return anomalies

    # Unusual incremental cost burden vs quote.
    for _, row in li.iterrows():
        if row["quoted_per_unit"] > 0:
            burden = row["incremental_per_unit"] / row["quoted_per_unit"] * 100
            if burden > 20:
                anomalies.append({
                    "type": "High incremental burden",
                    "subject": f"{row['product_name']} @ {row['supplier_name']}",
                    "detail": (f"True economic cost is {burden:.0f}% above the quoted price - "
                               "quote-based comparisons will materially mislead here."),
                })

    # Deteriorating / weak yield.
    qm = data.get("quality_metrics", pd.DataFrame())
    if qm is not None and not qm.empty:
        weak = qm[pd.to_numeric(qm["first_pass_yield_pct"], errors="coerce") < 94]
        for _, row in weak.iterrows():
            anomalies.append({
                "type": "Weak first-pass yield",
                "subject": f"{row['supplier_id']} / {row['product_id']}",
                "detail": f"FPY {row['first_pass_yield_pct']}% is below the 94% attention threshold.",
            })

    # Excess / NCNR inventory.
    inv = data.get("inventory_records", pd.DataFrame())
    if inv is not None and not inv.empty:
        flagged = inv[(inv["excess_flag"] == True)  # noqa: E712
                      | (inv["stage"].astype(str) == "Noncancelable/nonreturnable")]
        for _, row in flagged.iterrows():
            value = float(row.get("quantity", 0) or 0) * float(row.get("unit_cost", 0) or 0)
            anomalies.append({
                "type": "Excess / NCNR exposure",
                "subject": f"{row['inv_id']} ({row.get('material_desc', '')})",
                "detail": f"${value:,.0f} of {row['stage']} inventory with liability status "
                          f"'{row.get('liability_status', '')}'.",
            })

    # Quote residual anomalies handled on the should-cost page.
    return anomalies


# ---------------------------------------------------------------------------
# Narrative insights (template-based fallback)
# ---------------------------------------------------------------------------

def narrative_insights(
    data: Dict[str, pd.DataFrame],
    results: Dict[str, ScenarioResult],
    baseline_id: str,
    comparison: pd.DataFrame,
) -> Dict[str, List[str]]:
    """Executive narrative built deterministically from engine outputs."""
    base = results[baseline_id]
    t = base.totals
    ss = base.supplier_summary

    summary: List[str] = [
        f"Baseline annual EMS spend (quoted) is ${t.get('quoted_cost', 0):,.0f}; "
        f"true economic cost is ${t.get('total_economic_cost', 0):,.0f} "
        f"({(t.get('total_economic_cost', 1) / max(t.get('quoted_cost', 1), 1) - 1) * 100:.0f}% above quote).",
    ]
    if not ss.empty and len(ss) > 1:
        cheapest_quote = ss.sort_values("quoted_per_unit").iloc[0]
        cheapest_econ = ss.sort_values("econ_cost_per_unit").iloc[0]
        if cheapest_quote["supplier_id"] != cheapest_econ["supplier_id"]:
            summary.append(
                f"{cheapest_quote['supplier_name']} quotes the lowest prices, but "
                f"{cheapest_econ['supplier_name']} delivers the lowest true economic cost - "
                "quality, logistics, working capital, service, and risk close the gap.")

    drivers: List[str] = []
    for bucket, label in [
        ("quality_cost", "OEM-borne quality cost"), ("wc_cost", "Working-capital cost"),
        ("service_cost", "service cost"), ("risk_cost", "expected risk cost"),
        ("logistics_cost", "logistics cost"), ("duty_cost", "duties and tariffs"),
    ]:
        val = t.get(bucket, 0)
        if val > 0:
            drivers.append(f"{label[0].upper() + label[1:]}: ${val:,.0f}/yr")
    drivers.sort(key=lambda s: -float(s.split("$")[1].replace(",", "").replace("/yr", "")))

    if not comparison.empty and "delta_total_vs_baseline" in comparison.columns:
        alt = comparison[comparison["scenario_id"] != baseline_id]
        if not alt.empty:
            best = alt.sort_values("delta_total_vs_baseline").iloc[0]
            summary.append(
                f"Best alternative scenario: {best['scenario_name']} "
                f"(total economic cost change ${best['delta_total_vs_baseline']:,.0f} in year 1).")

    questions = {
        "Procurement": [
            "Can Meridian provide a material/labor cost breakdown at the mid-2026 renewal?",
            "Is the P-100 volume-tier reset (already earned at current volume) booked?",
            "What price concession would Atlas accept for net-75 payment terms?",
        ],
        "Quality": [
            "What is the corrective-action plan and timeline for Meridian FPY recovery?",
            "Are warranty responsibilities for Meridian products contractually recoverable?",
        ],
        "Engineering": [
            "Can the consigned RF components be dual-footprinted to enable the Pacific second source?",
            "What is the realistic qualification duration for P-100 at a second EMS?",
        ],
        "EMS suppliers": [
            "Will Meridian commit to a first-pass-yield floor with cost recovery?",
            "Will Pacific hold 75-day terms and EMS-owned material at higher volumes?",
        ],
    }

    return {
        "summary": summary,
        "key_drivers": drivers[:5],
        "questions_procurement": questions["Procurement"],
        "questions_quality": questions["Quality"],
        "questions_engineering": questions["Engineering"],
        "questions_supplier": questions["EMS suppliers"],
    }


def challenge_assumptions(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Rank assumptions needing validation: low confidence x high impact."""
    assumptions = data.get("assumptions", pd.DataFrame())
    if assumptions is None or assumptions.empty:
        return pd.DataFrame()
    conf_rank = {"Low": 3, "Medium": 2, "High": 1}
    impact_rank = {"High": 3, "Medium": 2, "Low": 1}
    df = assumptions.copy()
    df["challenge_score"] = (
        df["confidence"].map(conf_rank).fillna(2)
        * df["financial_impact_rank"].map(impact_rank).fillna(2))
    flagged = df[df["challenge_score"] >= 4].sort_values("challenge_score", ascending=False)
    return flagged[["assumption_id", "name", "category", "status", "confidence",
                    "financial_impact_rank", "owner", "challenge_score", "notes"]]
