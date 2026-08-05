"""Should-cost modeling at three levels of detail.

Level 1 - High-level benchmark: cost-structure percentages applied to the
          quote to sanity-check its composition.
Level 2 - Process-based: BOM material + conversion estimate + logistics +
          margin, using the conversion cost model.
Level 3 - Detailed bottom-up: same structure as Level 2 but only meaningful
          when the BOM and routing are high-confidence; the engine reports
          data coverage so the user can judge.

The variance decomposition deliberately does NOT label all positive variance
as supplier overpricing: it buckets what can be explained (volume tier,
logistics, quality premium, overhead differences) and labels the remainder
"unexplained variance - an analytical estimate, not proof of overcharging".
"""
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from core import economics_engine, logistics_engine

# Level 1 benchmark cost structure for electronics assembly (editable in UI).
DEFAULT_BENCHMARK_STRUCTURE = {
    "material_pct": 68.0,
    "labor_pct": 8.0,
    "overhead_pct": 12.0,
    "margin_pct": 9.0,
    "other_pct": 3.0,
}


def level1_benchmark(quoted_price: float, structure: Optional[Dict[str, float]] = None) -> pd.DataFrame:
    s = structure or DEFAULT_BENCHMARK_STRUCTURE
    rows = [
        {"bucket": "Material", "pct": s["material_pct"], "value": quoted_price * s["material_pct"] / 100},
        {"bucket": "Labor & conversion", "pct": s["labor_pct"], "value": quoted_price * s["labor_pct"] / 100},
        {"bucket": "Overhead", "pct": s["overhead_pct"], "value": quoted_price * s["overhead_pct"] / 100},
        {"bucket": "Supplier margin", "pct": s["margin_pct"], "value": quoted_price * s["margin_pct"] / 100},
        {"bucket": "Other", "pct": s["other_pct"], "value": quoted_price * s["other_pct"] / 100},
    ]
    return pd.DataFrame(rows)


def process_based_should_cost(
    data: Dict[str, pd.DataFrame], product_id: str, supplier_id: str
) -> Dict[str, float]:
    """Level 2/3 should-cost per unit (+ coverage stats).

    Convention: supplier quotes cover the EMS scope only - OEM-consigned
    material is excluded from the quote (the economics engine adds it
    separately). ``should_cost`` is therefore the quote-scope figure
    (EMS material + conversion) so it compares apples-to-apples with the
    quote; ``should_cost_all_in`` adds consigned material back.
    """
    material = economics_engine.material_cost_per_unit(data, product_id)
    conversion = economics_engine.conversion_cost_per_unit(
        data, product_id, supplier_id, material["material_total"])
    should_cost = material["ems_material"] + conversion["conversion_total"]
    should_cost_all_in = material["material_total"] + conversion["conversion_total"]

    bom = data.get("bom_items", pd.DataFrame())
    items = bom[bom["product_id"] == product_id] if bom is not None and not bom.empty else pd.DataFrame()
    high_conf = 0
    if not items.empty and "confidence" in items.columns:
        high_conf = int((items["confidence"] == "High").sum())
    coverage = high_conf / len(items) if len(items) else 0.0

    return {
        "material": material["material_total"],
        "ems_material": material["ems_material"],
        "consigned_material": material["consigned_material"],
        "conversion": conversion["conversion_total"],
        "should_cost": should_cost,
        "should_cost_all_in": should_cost_all_in,
        "bom_lines": material["bom_lines"],
        "bom_high_confidence_share": coverage,
        "conversion_missing": conversion.get("conversion_missing", 1.0),
    }


def unexplained_residual(
    data: Dict[str, pd.DataFrame], product_id: str, supplier_id: str
) -> Dict[str, float]:
    """Residual between the quoted price and everything we can identify.

    residual = quote - identified EMS-scope material - estimated conversion
    (Consigned material is excluded because quotes cover the EMS scope only;
    logistics/duties are excluded because sample quotes exclude them - quotes
    flagged as including freight/duties would need those subtracted.)

    The residual is an analytical estimate. It can reflect missing BOM
    lines, benchmark error, spec differences, or commercial opportunity -
    it is NOT proof of supplier overcharging.
    """
    quote = economics_engine.get_quote(data, supplier_id, product_id)
    if quote is None:
        return {"quoted_price": 0.0, "residual": 0.0, "residual_pct": 0.0, "quote_missing": 1.0}
    price = float(quote["base_unit_price"])
    sc = process_based_should_cost(data, product_id, supplier_id)
    residual = price - sc["ems_material"] - sc["conversion"]
    return {
        "quoted_price": price,
        "identified_material": sc["ems_material"],
        "consigned_material_excluded": sc["consigned_material"],
        "estimated_conversion": sc["conversion"],
        "residual": residual,
        "residual_pct": residual / price * 100 if price else 0.0,
        "quote_missing": 0.0,
    }


VARIANCE_INTERPRETATIONS = [
    "Likely commercial opportunity",
    "Possible specification difference",
    "Possible volume difference",
    "Possible quality or service premium",
    "Possible logistics difference",
    "Possible overhead difference",
    "Possible missing data",
    "Unexplained variance",
]


def variance_analysis(
    data: Dict[str, pd.DataFrame], product_id: str, supplier_id: str,
    annual_volume: float,
) -> pd.DataFrame:
    """Quote vs should-cost variance with a cautious interpretation split.

    The interpretation buckets are heuristic allocations meant to structure
    the negotiation conversation, not accounting truth:
      * volume difference: gap between the quoted tier and best tier
      * quality/service premium: half of the supplier's COPQ+service edge
        versus the cheapest peer is treated as a justified premium proxy
      * the remainer is split between commercial opportunity (when BOM
        confidence is high) and possible missing data (when it is low).
    """
    quote = economics_engine.get_quote(data, supplier_id, product_id)
    if quote is None:
        return pd.DataFrame()
    quoted = float(quote["base_unit_price"])
    tier_best = economics_engine.tier_unit_price(quote, float("inf"))
    sc = process_based_should_cost(data, product_id, supplier_id)
    variance = quoted - sc["should_cost"]

    volume_component = max(quoted - economics_engine.tier_unit_price(quote, annual_volume), 0.0)
    confidence = sc["bom_high_confidence_share"]
    remainder = variance - volume_component
    if remainder > 0:
        commercial = remainder * confidence * 0.6
        missing_data = remainder * (1 - confidence)
        unexplained = remainder - commercial - missing_data
    else:
        commercial = missing_data = 0.0
        unexplained = remainder

    rows = [
        {"component": "Quoted unit price", "value": quoted},
        {"component": "Should-cost (EMS-scope material + conversion)", "value": -sc["should_cost"]},
        {"component": "Total variance", "value": variance},
        {"component": "Possible volume difference (tier gap)", "value": volume_component},
        {"component": "Likely commercial opportunity", "value": commercial},
        {"component": "Possible missing data / model error", "value": missing_data},
        {"component": "Unexplained variance", "value": unexplained},
        {"component": "Best-tier price (reference)", "value": tier_best},
    ]
    return pd.DataFrame(rows)


def comparison_table(data: Dict[str, pd.DataFrame], product_id: str) -> pd.DataFrame:
    """Compare quotes, should-cost, and standard cost across suppliers."""
    products = data["products"]
    prod = products[products["product_id"] == product_id]
    std_cost = float(prod.iloc[0]["current_standard_cost"]) if not prod.empty else 0.0
    volume = float(prod.iloc[0]["annual_volume"]) if not prod.empty else 0.0

    quotes = data.get("supplier_quotes", pd.DataFrame())
    suppliers = data["suppliers"].set_index("supplier_id")
    rows = []
    if quotes is not None and not quotes.empty:
        for _, q in quotes[quotes["product_id"] == product_id].iterrows():
            sid = q["supplier_id"]
            sc = process_based_should_cost(data, product_id, sid)
            quoted = economics_engine.tier_unit_price(q, volume)
            rows.append({
                "supplier_id": sid,
                "supplier_name": suppliers.loc[sid, "supplier_name"] if sid in suppliers.index else sid,
                "quoted_price": quoted,
                "should_cost": sc["should_cost"],
                "consigned_material": sc["consigned_material"],
                "current_standard_cost": std_cost,
                "variance_usd": quoted - sc["should_cost"],
                "variance_pct": (quoted - sc["should_cost"]) / quoted * 100 if quoted else 0.0,
                "quote_status": q.get("status", ""),
                "quote_confidence": q.get("confidence", ""),
                "should_cost_confidence": (
                    "High" if sc["bom_high_confidence_share"] > 0.7 and not sc["conversion_missing"]
                    else "Medium" if sc["bom_high_confidence_share"] > 0.4 else "Low"),
            })
    return pd.DataFrame(rows)
