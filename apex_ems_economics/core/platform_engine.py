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

Per-system COGS is completed with an explicitly-labeled in-house cost
(final assembly, system integration, calibration, system test) taken from
the ``internal_cogs_pct_of_revenue`` setting. That work never leaves the
OEM, so it is outside the EMS decision scope but needed to show margin.
"""
from __future__ import annotations

from typing import Dict

import pandas as pd

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


def platform_rollup(
    data: Dict[str, pd.DataFrame], result: ScenarioResult, settings: Dict[str, float],
) -> pd.DataFrame:
    """Per-platform ship-set economics for one scenario."""
    platforms = data.get("tester_platforms", pd.DataFrame())
    products = data.get("products", pd.DataFrame())
    if platforms is None or platforms.empty or result.line_items.empty:
        return pd.DataFrame()

    # Board economics per product (blend suppliers when volume is split).
    ps = result.product_summary.set_index("product_id")
    prod = products.set_index("product_id")
    internal_pct = settings.get("internal_cogs_pct_of_revenue", 0.0) / 100.0

    rows = []
    for _, plat in platforms.iterrows():
        pid = str(plat["platform_id"])
        units = float(plat.get("annual_units", 0) or 0)
        asp = float(plat.get("asp_usd", 0) or 0)
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

        internal_cost = asp * internal_pct
        total_cogs = econ_ship_set + internal_cost
        rows.append({
            "platform_id": pid,
            "platform_name": plat.get("platform_name", pid),
            "platform_type": plat.get("platform_type", ""),
            "systems_shipped_per_year": units,
            "boards_per_system_qpa": board_count,
            "asp_per_system": asp,
            "annual_revenue": revenue,
            "quoted_ship_set_per_system": quoted_ship_set,
            "ems_content_per_system": econ_ship_set,
            "ems_premium_per_system": econ_ship_set - quoted_ship_set,
            "ems_content_pct_of_asp": econ_ship_set / asp * 100 if asp else 0.0,
            "internal_assembly_test_per_system": internal_cost,
            "total_cogs_per_system": total_cogs,
            "gross_margin_per_system": asp - total_cogs,
            "gross_margin_pct": (asp - total_cogs) / asp * 100 if asp else 0.0,
            "annual_ems_content": econ_ship_set * units,
        })
    return pd.DataFrame(rows)


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
