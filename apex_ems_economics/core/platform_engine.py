"""Roll board-level EMS economics up to the end systems the OEM ships.

Operations framing: the OEM ships **systems** (testers); the EMS builds the
**boards** that go into them. The bridge between the two is QPA - quantity
per assembly - so:

    annual board demand   = systems shipped x QPA
    ship-set cost         = SUM over boards of (QPA x board cost per good unit)
    EMS content per system = ship-set cost at true economic cost

Double-counting guard
---------------------
Subassemblies (rows with a ``parent_product_id``) are consumed inside a
parent board's BOM, so their cost is already inside that parent's economics.
They are therefore EXCLUDED from the ship-set and reported separately as
"carried inside parent boards" - otherwise every ship-set would be
overstated by the subassembly content.

Scope boundary
--------------
The studio models everything the OEM **buys**:
  * EMS-built boards (the ship-set) - full economic cost via the main engine
  * purchased system material (chassis, backplane, harnesses, cooling,
    controller, licenses) - itemized in ``system_components``

It does not itemize what the OEM **builds**: in-house final assembly,
integration, calibration, and system test appear as one clearly-labeled
labor-and-overhead assumption (``inhouse_conversion_pct_of_revenue``).
Routings and internal cost centres belong to a manufacturing-economics
model, not an EMS model.

Box build
---------
When a platform carries a ``box_build_fee_per_system``, the EMS performs
system integration and procures the system material: the OEM's purchased
system material and in-house conversion both drop to zero and the fee
takes their place. That makes make-vs-buy at the system level a directly
comparable scenario.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict

import pandas as pd

if TYPE_CHECKING:  # avoid a circular import; economics_engine imports this module
    from core.economics_engine import ScenarioResult


def _is_blank(series: pd.Series) -> pd.Series:
    """True where a text cell is empty/missing.

    Version-safe: pandas 2 stringifies missing values as 'nan' while pandas 3
    string dtype yields '<NA>', so match on the filled value instead of the
    stringified sentinel.
    """
    filled = series.astype(object).where(series.notna(), "")
    return filled.astype(str).str.strip().isin(["", "nan", "None", "<NA>"])


def _top_level_members(products: pd.DataFrame, platform_id: str) -> pd.DataFrame:
    """Boards on a platform, excluding subassemblies consumed by a parent."""
    same_platform = products["platform_id"].astype(object).where(
        products["platform_id"].notna(), "").astype(str).str.strip() == str(platform_id)
    return products[same_platform & _is_blank(products["parent_product_id"])]


def system_material_per_system(data: Dict[str, pd.DataFrame], platform_id: str) -> float:
    """Purchased non-EMS material per system shipped (QPA x unit cost)."""
    comps = data.get("system_components", pd.DataFrame())
    if comps is None or comps.empty:
        return 0.0
    rows = comps[comps["platform_id"].astype(str) == str(platform_id)]
    if rows.empty:
        return 0.0
    qpa = pd.to_numeric(rows["qpa_per_system"], errors="coerce").fillna(0)
    cost = pd.to_numeric(rows["unit_cost"], errors="coerce").fillna(0)
    return float((qpa * cost).sum())


def system_cost_totals(
    data: Dict[str, pd.DataFrame], settings: Dict[str, float]
) -> Dict[str, float]:
    """Annual OEM system-level costs outside the EMS board scope.

    Returns purchased system material, in-house conversion, and box-build
    fees across all platforms. Used by the economics engine to complete the
    COGS picture without polluting the EMS-scope economic cost.
    """
    platforms = data.get("tester_platforms", pd.DataFrame())
    totals = {"system_material_cost": 0.0, "inhouse_conversion_cost": 0.0,
              "box_build_fee_cost": 0.0, "system_revenue": 0.0}
    if platforms is None or platforms.empty:
        return totals
    pct = settings.get("inhouse_conversion_pct_of_revenue", 0.0) / 100.0
    for _, plat in platforms.iterrows():
        units = float(plat.get("annual_units", 0) or 0)
        asp = float(plat.get("asp_usd", 0) or 0)
        fee = float(plat.get("box_build_fee_per_system", 0) or 0)
        totals["system_revenue"] += units * asp
        if fee > 0:
            totals["box_build_fee_cost"] += fee * units
        else:
            totals["system_material_cost"] += (
                system_material_per_system(data, str(plat["platform_id"])) * units)
            totals["inhouse_conversion_cost"] += asp * pct * units
    return totals


def platform_rollup(
    data: Dict[str, pd.DataFrame], result: "ScenarioResult", settings: Dict[str, float],
) -> pd.DataFrame:
    """Per-platform ship-set economics for one scenario."""
    platforms = data.get("tester_platforms", pd.DataFrame())
    products = data.get("products", pd.DataFrame())
    if platforms is None or platforms.empty or result.line_items.empty:
        return pd.DataFrame()

    # Board economics per product (blend suppliers when volume is split).
    ps = result.product_summary.set_index("product_id")
    prod = products.set_index("product_id")
    internal_pct = settings.get("inhouse_conversion_pct_of_revenue", 0.0) / 100.0

    rows = []
    for _, plat in platforms.iterrows():
        pid = str(plat["platform_id"])
        units = float(plat.get("annual_units", 0) or 0)
        asp = float(plat.get("asp_usd", 0) or 0)
        fee = float(plat.get("box_build_fee_per_system", 0) or 0)
        revenue = units * asp

        members = _top_level_members(prod, pid)
        quoted_ship_set = econ_ship_set = 0.0
        board_count = 0.0
        for board_id, board in members.iterrows():
            if board_id not in ps.index:
                continue
            qpa = float(board.get("boards_per_tester", 0) or 0)
            if qpa <= 0:
                continue
            board_count += qpa
            quoted_ship_set += qpa * float(ps.loc[board_id, "quoted_per_unit"])
            econ_ship_set += qpa * float(ps.loc[board_id, "econ_cost_per_unit"])

        box_build = fee > 0
        if box_build:
            # EMS integrates the system and procures the system material.
            system_material = 0.0
            internal_cost = 0.0
        else:
            system_material = system_material_per_system(data, pid)
            internal_cost = asp * internal_pct
        total_cogs = econ_ship_set + system_material + internal_cost + fee
        rows.append({
            "platform_id": pid,
            "platform_name": plat.get("platform_name", pid),
            "platform_type": plat.get("platform_type", ""),
            "assembled_by": "EMS (box build)" if box_build else "OEM in-house",
            "systems_shipped_per_year": units,
            "boards_per_system_qpa": board_count,
            "asp_per_system": asp,
            "annual_revenue": revenue,
            "quoted_ship_set_per_system": quoted_ship_set,
            "ems_content_per_system": econ_ship_set,
            "ems_premium_per_system": econ_ship_set - quoted_ship_set,
            "ems_content_pct_of_asp": econ_ship_set / asp * 100 if asp else 0.0,
            "system_material_per_system": system_material,
            "inhouse_conversion_per_system": internal_cost,
            "box_build_fee_per_system": fee,
            "total_cogs_per_system": total_cogs,
            "gross_margin_per_system": asp - total_cogs,
            "gross_margin_pct": (asp - total_cogs) / asp * 100 if asp else 0.0,
            "annual_ems_content": econ_ship_set * units,
            "annual_total_cogs": total_cogs * units,
        })
    return pd.DataFrame(rows)


def system_component_detail(data: Dict[str, pd.DataFrame], platform_id: str) -> pd.DataFrame:
    """Purchased non-EMS system material lines for one platform."""
    comps = data.get("system_components", pd.DataFrame())
    if comps is None or comps.empty:
        return pd.DataFrame()
    rows = comps[comps["platform_id"].astype(str) == str(platform_id)].copy()
    if rows.empty:
        return rows
    rows["extended_per_system"] = (
        pd.to_numeric(rows["qpa_per_system"], errors="coerce").fillna(0)
        * pd.to_numeric(rows["unit_cost"], errors="coerce").fillna(0))
    return rows.sort_values("extended_per_system", ascending=False)


def ship_set_detail(
    data: Dict[str, pd.DataFrame], result: ScenarioResult, platform_id: str,
) -> pd.DataFrame:
    """Line-by-line ship-set for one platform: QPA x board economics."""
    products = data.get("products", pd.DataFrame())
    if products is None or products.empty or result.product_summary.empty:
        return pd.DataFrame()
    ps = result.product_summary.set_index("product_id")
    prod = products.set_index("product_id")
    members = _top_level_members(prod, platform_id)
    rows = []
    for board_id, board in members.iterrows():
        if board_id not in ps.index:
            continue
        qpa = float(board.get("boards_per_tester", 0) or 0)
        quoted = float(ps.loc[board_id, "quoted_per_unit"])
        econ = float(ps.loc[board_id, "econ_cost_per_unit"])
        rows.append({
            "product_id": board_id,
            "board": board.get("product_name", board_id),
            "qpa_per_system": qpa,
            "annual_board_demand": float(ps.loc[board_id, "volume"]),
            "quoted_per_board": quoted,
            "economic_per_board": econ,
            "quoted_extended_per_system": qpa * quoted,
            "economic_extended_per_system": qpa * econ,
            "hidden_cost_per_system": qpa * (econ - quoted),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("economic_extended_per_system", ascending=False)
    return df


def subassembly_note(data: Dict[str, pd.DataFrame], result: ScenarioResult) -> pd.DataFrame:
    """Subassemblies excluded from ship-sets because parents already carry them."""
    products = data.get("products", pd.DataFrame())
    if products is None or products.empty or result.product_summary.empty:
        return pd.DataFrame()
    ps = result.product_summary.set_index("product_id")
    subs = products[~_is_blank(products["parent_product_id"])]
    rows = []
    for _, s in subs.iterrows():
        pid = s["product_id"]
        if pid not in ps.index:
            continue
        rows.append({
            "product_id": pid,
            "subassembly": s["product_name"],
            "consumed_by": s["parent_product_id"],
            "annual_volume": float(ps.loc[pid, "volume"]),
            "economic_per_unit": float(ps.loc[pid, "econ_cost_per_unit"]),
            "annual_economic_cost": float(ps.loc[pid, "total_economic_cost"]),
        })
    return pd.DataFrame(rows)
