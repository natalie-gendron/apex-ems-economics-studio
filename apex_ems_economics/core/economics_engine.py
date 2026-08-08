"""Deterministic economic engine: quote -> true economic cost.

This is the heart of the studio. It is UI-independent: it takes the data
dict, a scenario id, and returns a ``ScenarioResult`` that every page (and
any future Apex module) can consume.

Double-counting discipline
--------------------------
The supplier quote is assumed to already contain material and conversion
cost (and freight/duties only when the quote flags say so). Material and
conversion are therefore computed for *transparency and should-cost
analysis* but are NOT added on top of the quote. The incremental adders are:

    total economic cost =
        quoted purchase cost
      + consigned material cost (OEM-purchased material excluded from quote)
      + logistics (routine freight, insurance, brokerage, packaging, ...)
      + duties and tariffs
      + OEM-borne cost of poor quality
      + working-capital cost (carrying, advances, payment-terms effect)
      + service cost (safety stock, expedites, expected stockouts, penalties)
      + expected risk cost                    [decision measure]
      + one-time + transition costs           [scenario level]

Economic cost per unit = total annual economic cost / annual good units,
where good units = volume x final yield.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
import pandas as pd

from core import inventory_engine, logistics_engine, quality_engine, risk_engine, scenario_engine, service_engine
from core.config import load_settings

CONFIDENCE_RANK = {"High": 3, "Medium": 2, "Low": 1}


# ---------------------------------------------------------------------------
# Quote helpers
# ---------------------------------------------------------------------------

def tier_unit_price(quote: pd.Series, volume: float) -> float:
    """Volume-tier price: the deepest tier whose minimum quantity is met."""
    price = float(quote["base_unit_price"])
    for tier in ("tier2", "tier3"):
        min_qty = quote.get(f"{tier}_min_qty")
        tier_price = quote.get(f"{tier}_unit_price")
        try:
            if min_qty is not None and not pd.isna(min_qty) and volume >= float(min_qty):
                if tier_price is not None and not pd.isna(tier_price):
                    price = float(tier_price)
        except (TypeError, ValueError):
            continue
    return price


def get_quote(data: Dict[str, pd.DataFrame], supplier_id: str, product_id: str) -> Optional[pd.Series]:
    quotes = data.get("supplier_quotes", pd.DataFrame())
    if quotes is None or quotes.empty:
        return None
    match = quotes[(quotes["supplier_id"] == supplier_id) & (quotes["product_id"] == product_id)]
    if match.empty:
        return None
    return match.iloc[0]


# ---------------------------------------------------------------------------
# Material and conversion (transparency layers, inside the quote)
# ---------------------------------------------------------------------------

def material_cost_per_unit(data: Dict[str, pd.DataFrame], product_id: str) -> Dict[str, float]:
    """Bottom-up BOM material cost per assembled unit.

    component cost = qty x unit price x (1 + scrap%) / yield%
                     x (1 + freight%) x (1 + duty%)

    Also splits the total into OEM-consigned vs EMS-procured content, which
    the engine uses to add consigned material on top of the quote.
    """
    bom = data.get("bom_items", pd.DataFrame())
    if bom is None or bom.empty:
        return {"material_total": 0.0, "consigned_material": 0.0, "ems_material": 0.0, "bom_lines": 0}
    items = bom[bom["product_id"] == product_id]
    total = consigned = 0.0
    for _, row in items.iterrows():
        try:
            qty = float(row.get("qty_per", 1) or 1)
            price = float(row.get("unit_price", 0) or 0)
            scrap = float(row.get("scrap_pct", 0) or 0) / 100.0
            yld = float(row.get("yield_pct", 100) or 100) / 100.0
            freight = float(row.get("freight_pct", 0) or 0) / 100.0
            duty = float(row.get("duty_pct", 0) or 0) / 100.0
        except (TypeError, ValueError):
            continue
        yld = yld if yld > 0 else 1.0
        cost = qty * price * (1 + scrap) / yld * (1 + freight) * (1 + duty)
        total += cost
        if str(row.get("ownership_model", "")).startswith("OEM-owned"):
            consigned += cost
    return {
        "material_total": total,
        "consigned_material": consigned,
        "ems_material": total - consigned,
        "bom_lines": int(len(items)),
    }


def conversion_cost_per_unit(
    data: Dict[str, pd.DataFrame], product_id: str, supplier_id: str,
    material_base: float = 0.0,
) -> Dict[str, float]:
    """EMS conversion economics per unit.

    direct labor    = labor hours x rate
    burdened labor  = direct labor x (1 + burden%)
    equipment       = machine hours x machine rate
    test            = test hours x test rate
    setup           = setup hours x blended rate / batch size
    indirect        = burdened labor x indirect%
    factory overhead= (burdened labor + equipment) x overhead%
    fees            = program mgmt + procurement (on material) + handling (on material)
    margin          = subtotal x margin%
    """
    cc = data.get("conversion_costs", pd.DataFrame())
    empty = {k: 0.0 for k in (
        "direct_labor", "burdened_labor", "equipment", "test", "setup",
        "inspection", "packaging", "indirect", "factory_overhead",
        "program_mgmt", "procurement_fee", "material_handling",
        "supplier_margin", "conversion_total")}
    if cc is None or cc.empty:
        return {**empty, "conversion_missing": 1.0}
    match = cc[(cc["product_id"] == product_id) & (cc["supplier_id"] == supplier_id)]
    if match.empty:
        return {**empty, "conversion_missing": 1.0}
    row = match.iloc[0]

    def f(key: str, default: float = 0.0) -> float:
        try:
            v = float(row.get(key, default) or default)
        except (TypeError, ValueError):
            return default
        return default if pd.isna(v) else v

    direct = f("labor_hours_per_unit") * f("labor_rate")
    burdened = direct * (1 + f("labor_burden_pct") / 100.0)
    equipment = f("machine_hours_per_unit") * f("machine_rate")
    test = f("test_hours") * f("test_rate")
    blended_rate = f("labor_rate") * (1 + f("labor_burden_pct") / 100.0)
    batch = f("batch_size", 1.0) or 1.0
    setup = f("setup_hours") * blended_rate / batch
    inspection = f("inspection_cost_per_unit")
    packaging = f("packaging_cost_per_unit")
    indirect = burdened * f("indirect_labor_pct") / 100.0
    overhead = (burdened + equipment) * f("factory_overhead_pct") / 100.0
    subtotal = burdened + equipment + test + setup + inspection + packaging + indirect + overhead
    program = subtotal * f("program_mgmt_fee_pct") / 100.0
    procurement = material_base * f("procurement_fee_pct") / 100.0
    handling = material_base * f("material_handling_fee_pct") / 100.0
    margin = (subtotal + program + procurement + handling) * f("supplier_margin_pct") / 100.0
    total = subtotal + program + procurement + handling + margin

    return {
        "direct_labor": direct, "burdened_labor": burdened, "equipment": equipment,
        "test": test, "setup": setup, "inspection": inspection, "packaging": packaging,
        "indirect": indirect, "factory_overhead": overhead, "program_mgmt": program,
        "procurement_fee": procurement, "material_handling": handling,
        "supplier_margin": margin, "conversion_total": total, "conversion_missing": 0.0,
    }


# ---------------------------------------------------------------------------
# Contract term access
# ---------------------------------------------------------------------------

def get_term(
    data: Dict[str, pd.DataFrame], supplier_id: str, term_name: str, default: float = 0.0
) -> float:
    terms = data.get("contract_terms", pd.DataFrame())
    if terms is None or terms.empty:
        return default
    match = terms[(terms["supplier_id"] == supplier_id) & (terms["term_name"] == term_name)]
    if match.empty:
        return default
    try:
        return float(match.iloc[0]["value"])
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Scenario result
# ---------------------------------------------------------------------------

@dataclass
class ScenarioResult:
    scenario_id: str
    scenario_name: str
    line_items: pd.DataFrame
    totals: Dict[str, float] = field(default_factory=dict)
    supplier_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    product_summary: pd.DataFrame = field(default_factory=pd.DataFrame)


PER_UNIT_BUCKETS = [
    ("quoted_per_unit", "Quoted price"),
    ("consigned_material_per_unit", "Consigned material (OEM-purchased)"),
    ("logistics_per_unit", "Logistics"),
    ("duty_per_unit", "Duties & tariffs"),
    ("quality_per_unit", "Quality (OEM-borne COPQ)"),
    ("wc_per_unit", "Working capital"),
    ("service_per_unit", "Service"),
    ("risk_per_unit", "Expected risk"),
]

ANNUAL_BUCKETS = [
    "quoted_cost", "consigned_material_cost", "logistics_cost", "duty_cost",
    "quality_cost", "wc_cost", "service_cost", "risk_cost",
]


def compute_scenario(
    raw_data: Dict[str, pd.DataFrame], scenario_id: str,
    settings: Optional[Dict[str, float]] = None,
) -> ScenarioResult:
    """Run the full deterministic model for one scenario."""
    settings = settings or load_settings(raw_data)
    scenario = scenario_engine.get_scenario_row(raw_data, scenario_id)
    data = scenario_engine.apply_scenario(raw_data, scenario_id)
    allocations = scenario_engine.scenario_allocations(data, scenario_id)
    products = data["products"].set_index("product_id")
    suppliers = data["suppliers"].set_index("supplier_id")

    # Baseline spend per supplier drives inventory-intensity scaling.
    base_id = scenario_engine.baseline_scenario_id(raw_data)
    base_spend = _quoted_spend_by_supplier(raw_data, base_id)
    ownership_profile = inventory_engine.supplier_ownership_profile(
        data, base_spend
    ).set_index("supplier_id")

    rows = []
    for _, alloc in allocations.iterrows():
        pid, sid = str(alloc["product_id"]), str(alloc["supplier_id"])
        if pid not in products.index or sid not in suppliers.index:
            continue
        product = products.loc[pid]
        share = float(alloc["allocation_pct"]) / 100.0
        volume = float(product["annual_volume"]) * share
        if volume <= 0:
            continue

        quote = get_quote(data, sid, pid)
        quote_missing = quote is None
        if quote_missing:
            # Fall back to standard cost so missing quotes never stop the model;
            # flagged so the UI can label it as an estimate.
            unit_price = float(product.get("current_standard_cost", 0) or 0)
            includes_freight = includes_duties = False
        else:
            unit_price = tier_unit_price(quote, float(product["annual_volume"]) * share)
            includes_freight = bool(quote.get("includes_freight", False))
            includes_duties = bool(quote.get("includes_duties", False))

        quoted_cost = unit_price * volume

        material = material_cost_per_unit(data, pid)
        conversion = conversion_cost_per_unit(data, pid, sid, material["material_total"])
        consigned_per_unit = material["consigned_material"]
        consigned_cost = consigned_per_unit * volume

        lane = logistics_engine.get_lane(data, sid, str(alloc.get("site_id", "")))
        logi = logistics_engine.landed_cost_per_unit(lane, unit_price, includes_freight, includes_duties)

        quality_row = quality_engine.get_quality_row(data, sid, pid)
        qual = quality_engine.copq(quality_row, volume, unit_price, settings, volume_share=share)

        revenue = float(product.get("unit_selling_price", 0) or 0) * volume
        service_row = service_engine.get_service_row(data, sid)
        serv = service_engine.service_cost(
            service_row, lane, volume, quoted_cost, revenue, settings, volume_share=share)

        oem_days = float(ownership_profile["oem_days"].get(sid, 0.0)) if not ownership_profile.empty else 0.0
        transit_days = 0.0
        if lane is not None:
            try:
                transit_days = float(lane.get("transit_days", 0) or 0)
            except (TypeError, ValueError):
                transit_days = 0.0
            # In-transit ownership: OEM owns goods in transit under FOB/FCA.
            incoterms = str(lane.get("incoterms", "")).upper()
            if incoterms not in ("FOB", "FCA", "EXW", ""):
                transit_days = 0.0
        payment_days = get_term(data, sid, "payment_terms_days", settings["payment_terms_reference_days"])
        wc = inventory_engine.working_capital_cost(
            annual_spend=quoted_cost + consigned_cost,
            oem_days=oem_days,
            payment_terms_days=payment_days,
            advance_payment_pct=get_term(data, sid, "advance_payment_pct", 0.0),
            settings=settings,
            in_transit_days=transit_days,
        )
        # Payables funding: cash provided by supplier terms beyond the reference
        # days (a balance-sheet cash effect, distinct from the annual wc_cost).
        payables_funding = (payment_days - settings["payment_terms_reference_days"]) / 365.0 \
            * (quoted_cost + consigned_cost)

        good_units = qual["good_units"]
        quality_conf = str(quality_row.get("confidence", "Low")) if quality_row is not None else "Low"
        quote_conf = str(quote.get("confidence", "Low")) if quote is not None else "Low"

        rows.append({
            "scenario_id": scenario_id,
            "product_id": pid,
            "product_name": product["product_name"],
            "supplier_id": sid,
            "supplier_name": suppliers.loc[sid, "supplier_name"],
            "site_id": alloc.get("site_id", ""),
            "allocation_pct": share * 100,
            "volume": volume,
            "good_units": good_units,
            "unit_price": unit_price,
            "quote_missing": quote_missing,
            "quote_confidence": quote_conf,
            "quality_confidence": quality_conf,
            # annual buckets
            "quoted_cost": quoted_cost,
            "consigned_material_cost": consigned_cost,
            "logistics_cost": logi["logistics_per_unit"] * volume,
            "duty_cost": logi["duty_per_unit"] * volume,
            "quality_cost": qual["oem_copq"],
            "total_copq": qual["total_copq"],
            "wc_cost": wc["wc_cost"],
            "wc_carrying": wc["carrying_cost"],
            "wc_advance": wc["advance_payment_cost"],
            "wc_terms_effect": wc["payment_terms_effect"],
            "oem_inventory_value": wc["oem_inventory_value"],
            "payables_funding": payables_funding,
            "service_cost": serv["service_cost"],
            "expedite_cost": serv["expedite_cost"],
            "stockout_expected_cost": serv["stockout_expected_cost"],
            "revenue": revenue,
            # transparency layers (inside the quote - not added)
            "material_per_unit": material["material_total"],
            "ems_material_per_unit": material["ems_material"],
            "consigned_material_per_unit": consigned_per_unit,
            "conversion_per_unit": conversion["conversion_total"],
            "conversion_missing": conversion["conversion_missing"],
            "final_yield_pct": qual["final_yield_pct"],
        })

    line_items = pd.DataFrame(rows)
    if line_items.empty:
        return ScenarioResult(scenario_id, str(scenario["scenario_name"]), line_items)

    # Expected risk cost allocation needs the full line-item table.
    line_items["risk_cost"] = risk_engine.allocate_risk_costs(data, line_items)

    line_items["total_economic_cost"] = line_items[ANNUAL_BUCKETS].sum(axis=1)
    line_items["econ_cost_per_unit"] = np.where(
        line_items["good_units"] > 0,
        line_items["total_economic_cost"] / line_items["good_units"], 0.0)
    line_items["quoted_per_unit"] = line_items["unit_price"]
    for bucket in ("logistics", "duty", "quality", "wc", "service", "risk"):
        line_items[f"{bucket}_per_unit"] = np.where(
            line_items["volume"] > 0,
            line_items[f"{bucket}_cost"] / line_items["volume"], 0.0)
    line_items["incremental_per_unit"] = (
        line_items["econ_cost_per_unit"] - line_items["quoted_per_unit"])

    one_time = float(scenario.get("one_time_cost", 0) or 0)
    transition = float(scenario.get("transition_cost", 0) or 0)

    totals = {bucket: float(line_items[bucket].sum()) for bucket in ANNUAL_BUCKETS}
    totals.update({
        "volume": float(line_items["volume"].sum()),
        "good_units": float(line_items["good_units"].sum()),
        "revenue": float(line_items["revenue"].sum()),
        "one_time_cost": one_time,
        "transition_cost": transition,
        "recurring_economic_cost": float(line_items["total_economic_cost"].sum()),
        "total_economic_cost": float(line_items["total_economic_cost"].sum()) + one_time + transition,
        "oem_inventory_value": float(line_items["oem_inventory_value"].sum()),
        "payables_funding": float(line_items["payables_funding"].sum()),
        # Standard-cost-relevant spend: what would flow into COGS.
        "cogs_relevant_cost": float(
            line_items[["quoted_cost", "consigned_material_cost", "logistics_cost", "duty_cost"]]
            .sum().sum()),
    })
    totals["econ_cost_per_unit"] = (
        totals["total_economic_cost"] / totals["good_units"] if totals["good_units"] else 0.0)

    # System-level costs outside the EMS board scope: purchased system material,
    # in-house assembly/system-test labor, or an EMS box-build fee. Kept OUT of
    # total_economic_cost (which stays EMS-decision scope) and reported
    # separately so the full per-system COGS picture is still available.
    from core import platform_engine  # local import: platform_engine type-hints ScenarioResult

    system = platform_engine.system_cost_totals(data, settings)
    totals.update(system)
    totals["full_system_cogs"] = (
        totals["cogs_relevant_cost"] + system["system_material_cost"]
        + system["inhouse_conversion_cost"] + system["box_build_fee_cost"])
    totals["system_gross_margin"] = system["system_revenue"] - totals["full_system_cogs"]
    totals["system_gross_margin_pct"] = (
        totals["system_gross_margin"] / system["system_revenue"] * 100
        if system["system_revenue"] else 0.0)

    supplier_summary = _summarize(line_items, "supplier_id", "supplier_name")
    product_summary = _summarize(line_items, "product_id", "product_name")

    return ScenarioResult(
        scenario_id=scenario_id,
        scenario_name=str(scenario["scenario_name"]),
        line_items=line_items,
        totals=totals,
        supplier_summary=supplier_summary,
        product_summary=product_summary,
    )


def _summarize(line_items: pd.DataFrame, key: str, name_col: str) -> pd.DataFrame:
    agg = line_items.groupby([key, name_col], as_index=False)[
        ANNUAL_BUCKETS + ["total_economic_cost", "volume", "good_units", "oem_inventory_value"]
    ].sum()
    agg["econ_cost_per_unit"] = np.where(
        agg["good_units"] > 0, agg["total_economic_cost"] / agg["good_units"], 0.0)
    agg["quoted_per_unit"] = np.where(
        agg["volume"] > 0, agg["quoted_cost"] / agg["volume"], 0.0)
    return agg.sort_values("total_economic_cost", ascending=False)


def _quoted_spend_by_supplier(data: Dict[str, pd.DataFrame], scenario_id: str) -> Dict[str, float]:
    """Quoted spend per supplier for the given scenario (no overrides applied).

    Used only to derive baseline inventory intensity, so a lightweight pass is
    sufficient and avoids recursion into compute_scenario.
    """
    allocations = scenario_engine.scenario_allocations(data, scenario_id)
    products = data["products"].set_index("product_id")
    spend: Dict[str, float] = {}
    for _, alloc in allocations.iterrows():
        pid, sid = str(alloc["product_id"]), str(alloc["supplier_id"])
        if pid not in products.index:
            continue
        product = products.loc[pid]
        share = float(alloc["allocation_pct"]) / 100.0
        volume = float(product["annual_volume"]) * share
        quote = get_quote(data, sid, pid)
        price = (tier_unit_price(quote, float(product["annual_volume"]) * share)
                 if quote is not None else float(product.get("current_standard_cost", 0) or 0))
        spend[sid] = spend.get(sid, 0.0) + price * volume
    return spend


# ---------------------------------------------------------------------------
# Cost bridge and scenario deltas
# ---------------------------------------------------------------------------

def cost_bridge(result: ScenarioResult, scope: str = "total") -> pd.DataFrame:
    """Bridge from quoted price to true economic cost (per good unit).

    ``scope`` may be "total" or a supplier_id / product_id present in the
    line items.
    """
    li = result.line_items
    if li.empty:
        return pd.DataFrame()
    if scope != "total":
        li = li[(li["supplier_id"] == scope) | (li["product_id"] == scope)]
        if li.empty:
            return pd.DataFrame()
    good_units = li["good_units"].sum()
    if good_units <= 0:
        return pd.DataFrame()
    steps = [("Quoted price", li["quoted_cost"].sum() / good_units)]
    labels = [
        ("consigned_material_cost", "Consigned material"),
        ("logistics_cost", "Logistics"),
        ("duty_cost", "Duties & tariffs"),
        ("quality_cost", "Quality (COPQ)"),
        ("wc_cost", "Working capital"),
        ("service_cost", "Service"),
        ("risk_cost", "Expected risk"),
    ]
    for col, label in labels:
        steps.append((label, li[col].sum() / good_units))
    if scope == "total":
        one_time = result.totals.get("one_time_cost", 0) + result.totals.get("transition_cost", 0)
        if one_time:
            steps.append(("One-time & transition", one_time / good_units))
    df = pd.DataFrame(steps, columns=["step", "value"])
    df["cumulative"] = df["value"].cumsum()
    return df


def compare_scenarios(results: Dict[str, ScenarioResult], baseline_id: str) -> pd.DataFrame:
    """Comparison table across scenarios with deltas vs the baseline."""
    rows = []
    base = results.get(baseline_id)
    for scenario_id, res in results.items():
        t = res.totals
        row = {
            "scenario_id": scenario_id,
            "scenario_name": res.scenario_name,
            "annual_volume": t.get("volume", 0),
            "good_units": t.get("good_units", 0),
            "quoted_cost": t.get("quoted_cost", 0),
            "consigned_material_cost": t.get("consigned_material_cost", 0),
            "logistics_cost": t.get("logistics_cost", 0),
            "duty_cost": t.get("duty_cost", 0),
            "quality_cost": t.get("quality_cost", 0),
            "wc_cost": t.get("wc_cost", 0),
            "service_cost": t.get("service_cost", 0),
            "risk_cost": t.get("risk_cost", 0),
            "one_time_cost": t.get("one_time_cost", 0) + t.get("transition_cost", 0),
            "total_economic_cost": t.get("total_economic_cost", 0),
            "econ_cost_per_unit": t.get("econ_cost_per_unit", 0),
            "cogs_relevant_cost": t.get("cogs_relevant_cost", 0),
            "system_material_cost": t.get("system_material_cost", 0),
            "inhouse_conversion_cost": t.get("inhouse_conversion_cost", 0),
            "box_build_fee_cost": t.get("box_build_fee_cost", 0),
            "full_system_cogs": t.get("full_system_cogs", 0),
            "system_gross_margin_pct": t.get("system_gross_margin_pct", 0),
            "oem_inventory_value": t.get("oem_inventory_value", 0),
        }
        if base is not None:
            bt = base.totals
            row["delta_total_vs_baseline"] = row["total_economic_cost"] - bt.get("total_economic_cost", 0)
            row["delta_cogs_vs_baseline"] = row["full_system_cogs"] - bt.get("full_system_cogs", 0)
            # Gross margin impact = -delta COGS (revenue held constant in v1).
            row["gross_margin_impact"] = -row["delta_cogs_vs_baseline"]
            row["delta_wc_inventory"] = row["oem_inventory_value"] - bt.get("oem_inventory_value", 0)
            # Cash-flow impact (year 1, positive = cash freed): inventory released
            # + incremental payables funding - one-time cash out.
            row["cash_flow_impact"] = (
                -row["delta_wc_inventory"]
                + (t.get("payables_funding", 0) - bt.get("payables_funding", 0))
                - row["one_time_cost"])
        rows.append(row)
    return pd.DataFrame(rows)
