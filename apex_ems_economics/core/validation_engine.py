"""Validation rules and data-quality scoring.

Issues carry a severity so the UI can differentiate:
  Error              - would corrupt results; block the affected calculation
  Warning            - results run but need judgment
  Information        - notable but harmless
  Data-quality issue - input hygiene / confidence problems
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List

import pandas as pd

SEV_ERROR = "Error"
SEV_WARN = "Warning"
SEV_INFO = "Information"
SEV_DQ = "Data-quality issue"


def validate(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    issues: List[Dict[str, str]] = []

    def add(severity: str, entity: str, message: str) -> None:
        issues.append({"severity": severity, "entity": entity, "message": message})

    today = date.today().isoformat()
    renewal_horizon = (date.today() + timedelta(days=90)).isoformat()

    products = data.get("products", pd.DataFrame())
    if products is not None and not products.empty:
        neg = products[pd.to_numeric(products["annual_volume"], errors="coerce").fillna(0) < 0]
        for _, row in neg.iterrows():
            add(SEV_ERROR, f"products/{row['product_id']}", "Annual volume is negative.")

    allocations = data.get("allocations", pd.DataFrame())
    if allocations is not None and not allocations.empty:
        sums = allocations.groupby(["scenario_id", "product_id"])["allocation_pct"].sum()
        for (scn, pid), total in sums.items():
            if abs(total - 100.0) > 0.01:
                add(SEV_ERROR, f"allocations/{scn}/{pid}",
                    f"Allocation percentages sum to {total:.1f}% (must be 100%).")

    qm = data.get("quality_metrics", pd.DataFrame())
    if qm is not None and not qm.empty:
        for col in ("first_pass_yield_pct", "final_yield_pct", "scrap_rate_pct", "rework_rate_pct"):
            vals = pd.to_numeric(qm[col], errors="coerce")
            bad = qm[(vals < 0) | (vals > 100)]
            for _, row in bad.iterrows():
                add(SEV_ERROR, f"quality_metrics/{row['supplier_id']}/{row['product_id']}",
                    f"{col} outside 0-100%.")

    risks = data.get("risks", pd.DataFrame())
    if risks is not None and not risks.empty:
        vals = pd.to_numeric(risks["probability_pct"], errors="coerce")
        bad = risks[(vals < 0) | (vals > 100)]
        for _, row in bad.iterrows():
            add(SEV_ERROR, f"risks/{row['risk_id']}", "Risk probability outside 0-100%.")

    sites = data.get("sites", pd.DataFrame())
    if sites is not None and not sites.empty:
        for _, row in sites.iterrows():
            start, end = str(row.get("contract_start", "")), str(row.get("contract_end", ""))
            if start and end and start > end:
                add(SEV_ERROR, f"sites/{row['site_id']}", "Contract start is after contract end.")
            elif end and end < renewal_horizon:
                add(SEV_WARN, f"sites/{row['site_id']}",
                    f"Contract ends {end} - renewal window is near or passed; leverage point.")
            if not str(row.get("currency", "")).strip():
                add(SEV_ERROR, f"sites/{row['site_id']}", "Currency is not specified.")

    quotes = data.get("supplier_quotes", pd.DataFrame())
    if quotes is not None and not quotes.empty:
        for _, row in quotes.iterrows():
            t2, t3 = row.get("tier2_min_qty"), row.get("tier3_min_qty")
            if pd.notna(t2) and pd.notna(t3) and float(t3) <= float(t2):
                add(SEV_ERROR, f"supplier_quotes/{row['quote_id']}",
                    "Volume tiers overlap: tier 3 minimum must exceed tier 2 minimum.")
            if not str(row.get("currency", "")).strip():
                add(SEV_ERROR, f"supplier_quotes/{row['quote_id']}", "Currency missing on quote.")
            if str(row.get("valid_until", "")) < today and str(row.get("valid_until", "")):
                add(SEV_DQ, f"supplier_quotes/{row['quote_id']}",
                    f"Quote validity expired {row.get('valid_until')} - refresh pricing.")

    inv = data.get("inventory_records", pd.DataFrame())
    if inv is not None and not inv.empty:
        for _, row in inv.iterrows():
            if str(row.get("ownership", "Unknown")) in ("", "Unknown", "nan"):
                add(SEV_WARN, f"inventory_records/{row['inv_id']}",
                    "Ownership not selected - ownership vs location cannot be modeled.")
            if str(row.get("physical_location", "Unknown")) in ("", "Unknown", "nan"):
                add(SEV_WARN, f"inventory_records/{row['inv_id']}", "Physical location not selected.")

    bom = data.get("bom_items", pd.DataFrame())
    if bom is not None and not bom.empty:
        unknown = bom[bom["ownership_model"].astype(str) == "Unknown"]
        if not unknown.empty:
            pids = ", ".join(sorted(unknown["product_id"].unique()))
            add(SEV_DQ, "bom_items", f"Ownership model Unknown on BOM lines for: {pids}.")
        low_conf = bom[bom["confidence"].astype(str) == "Low"]
        if not low_conf.empty:
            pids = ", ".join(sorted(low_conf["product_id"].unique()))
            add(SEV_DQ, "bom_items", f"Low-confidence BOM pricing for: {pids} (benchmark estimates).")

    weights = data.get("scoring_weights", pd.DataFrame())
    if weights is not None and not weights.empty:
        total = float(pd.to_numeric(weights["weight_pct"], errors="coerce").sum())
        if abs(total - 100.0) > 0.01:
            add(SEV_ERROR, "scoring_weights", f"Scoring weights sum to {total:.1f}% (must be 100%).")

    assumptions = data.get("assumptions", pd.DataFrame())
    if assumptions is not None and not assumptions.empty:
        for _, row in assumptions.iterrows():
            mn, ml, mx = row.get("min_value"), row.get("most_likely_value"), row.get("max_value")
            if pd.notna(mn) and pd.notna(ml) and pd.notna(mx):
                if not (float(mn) <= float(ml) <= float(mx)):
                    add(SEV_ERROR, f"assumptions/{row['assumption_id']}",
                        "Min / most-likely / max are not correctly ordered.")
            if str(row.get("status", "")) == "Stale":
                add(SEV_DQ, f"assumptions/{row['assumption_id']}",
                    f"Stale assumption: {row.get('name', '')}.")
            if str(row.get("status", "")) == "Missing":
                add(SEV_DQ, f"assumptions/{row['assumption_id']}",
                    f"Missing assumption: {row.get('name', '')}.")

    terms = data.get("contract_terms", pd.DataFrame())
    if terms is not None and not terms.empty:
        missing = terms[terms["status"].astype(str) == "Missing"]
        for _, row in missing.iterrows():
            add(SEV_DQ, f"contract_terms/{row['term_id']}",
                f"Missing contract term: {row['term_name']} ({row['supplier_id']}).")
        inferred = terms[terms["status"].astype(str) == "Inferred"]
        for _, row in inferred.iterrows():
            add(SEV_WARN, f"contract_terms/{row['term_id']}",
                f"Inferred (not confirmed) contract term: {row['term_name']} ({row['supplier_id']}).")

    capacity = data.get("capacity_records", pd.DataFrame())
    if capacity is not None and not capacity.empty:
        for _, row in capacity.iterrows():
            util = float(row.get("utilization_pct", 0) or 0)
            max_util = float(row.get("max_utilization_pct", 90) or 90)
            if util > max_util:
                add(SEV_ERROR, f"capacity_records/{row['site_id']}",
                    f"Utilization {util:.0f}% exceeds maximum {max_util:.0f}%.")
            elif util > max_util - 8:
                add(SEV_WARN, f"capacity_records/{row['site_id']}",
                    f"Utilization {util:.0f}% is within 8 points of the {max_util:.0f}% ceiling.")

    return pd.DataFrame(issues, columns=["severity", "entity", "message"])


# ---------------------------------------------------------------------------
# Data-quality scoring
# ---------------------------------------------------------------------------

CONF_POINTS = {"High": 100.0, "Medium": 60.0, "Low": 25.0}
STATUS_POINTS = {
    "Confirmed": 100.0, "Benchmarked": 70.0, "Estimated": 55.0,
    "Inferred": 35.0, "Under review": 45.0, "Stale": 20.0, "Missing": 0.0,
    "Not applicable": 100.0,
}


def data_quality_score(data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
    """Composite 0-100 data-quality score.

    Components:
      completeness     - share of contract terms not Missing
      source_status    - status-weighted average across contract terms
      confidence       - confidence-weighted average across quotes, BOM,
                         quality metrics, and assumptions
      recency          - share of assumptions not Stale
      driver_coverage  - share of quotes with material content visibility
                         (coverage of high-value cost drivers)
    """
    terms = data.get("contract_terms", pd.DataFrame())
    completeness = source_status = 70.0
    if terms is not None and not terms.empty:
        completeness = float((terms["status"] != "Missing").mean() * 100)
        source_status = float(terms["status"].map(STATUS_POINTS).fillna(50).mean())

    conf_values: List[float] = []
    for entity in ("supplier_quotes", "bom_items", "quality_metrics", "assumptions"):
        df = data.get(entity, pd.DataFrame())
        if df is not None and not df.empty and "confidence" in df.columns:
            conf_values.extend(df["confidence"].map(CONF_POINTS).fillna(40).tolist())
    confidence = float(pd.Series(conf_values).mean()) if conf_values else 60.0

    assumptions = data.get("assumptions", pd.DataFrame())
    recency = 80.0
    if assumptions is not None and not assumptions.empty:
        recency = float((assumptions["status"] != "Stale").mean() * 100)

    quotes = data.get("supplier_quotes", pd.DataFrame())
    driver_coverage = 50.0
    if quotes is not None and not quotes.empty:
        driver_coverage = float(quotes["quoted_material_content"].notna().mean() * 100)

    overall = (completeness * 0.25 + source_status * 0.2 + confidence * 0.25
               + recency * 0.15 + driver_coverage * 0.15)
    return {
        "completeness": completeness,
        "source_status": source_status,
        "confidence": confidence,
        "recency": recency,
        "driver_coverage": driver_coverage,
        "overall_score": overall,
    }
