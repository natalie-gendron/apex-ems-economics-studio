"""Cost structure tree: what a platform or board is made of, by cost.

Builds a strict hierarchy whose leaves sum exactly to the modeled economic
cost, so a treemap and the numbers on every other page agree:

    Platform
      Board (QPA x board economics)
        OEM-consigned material   -> BOM lines the OEM buys directly
        EMS-procured material    -> BOM lines inside the supplier quote
        Conversion, overhead & margin (implied)
        Logistics / Duties & tariffs / Quality / Working capital /
        Service / Expected risk
      System material (non-EMS)  -> chassis, backplane, harnesses, ...

Reconciliation rules
--------------------
* Board bucket values come from the engine's annual buckets, so the board
  subtotal equals ``total_economic_cost`` for that board - never a
  re-derivation that could drift.
* Material leaves are scaled to sit exactly inside their bucket: consigned
  BOM lines fill the consigned bucket, EMS BOM lines fill the part of the
  quote they explain, and the remainder becomes the implied conversion node
  (the same residual concept the should-cost page reports).
* Every value is non-negative; if identified material exceeds the quote the
  implied-conversion node is zero and material is scaled to fit, with a flag
  returned in ``meta`` so the UI can say so rather than silently distort.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import pandas as pd

from core import economics_engine

if TYPE_CHECKING:
    from core.economics_engine import ScenarioResult

# Ownership lens values (also the legend order).
OWN_CONSIGNED = "OEM-consigned material"
OWN_EMS_MATERIAL = "EMS-procured material"
OWN_EMS_VALUE_ADD = "EMS conversion & margin"
OWN_INCREMENTAL = "OEM incremental cost"
OWN_DIRECT = "OEM direct purchase (non-EMS)"

ADDER_BUCKETS = [
    ("logistics_cost", "Logistics"),
    ("duty_cost", "Duties & tariffs"),
    ("quality_cost", "Quality (OEM-borne)"),
    ("wc_cost", "Working capital"),
    ("service_cost", "Service"),
    ("risk_cost", "Expected risk"),
]


def _leaf(path: Tuple[str, ...], value: float, **attrs) -> Dict[str, object]:
    return {"path": path, "value": float(value), **attrs}


def _bom_lines(data: Dict[str, pd.DataFrame], product_id: str) -> pd.DataFrame:
    bom = data.get("bom_items", pd.DataFrame())
    if bom is None or bom.empty:
        return pd.DataFrame()
    return bom[bom["product_id"] == product_id].copy()


def _line_cost_per_unit(row: pd.Series) -> float:
    """Same formula the economics engine uses for a BOM line."""
    try:
        qty = float(row.get("qty_per", 1) or 1)
        price = float(row.get("unit_price", 0) or 0)
        scrap = float(row.get("scrap_pct", 0) or 0) / 100.0
        yld = float(row.get("yield_pct", 100) or 100) / 100.0
        freight = float(row.get("freight_pct", 0) or 0) / 100.0
        duty = float(row.get("duty_pct", 0) or 0) / 100.0
    except (TypeError, ValueError):
        return 0.0
    yld = yld if yld > 0 else 1.0
    return qty * price * (1 + scrap) / yld * (1 + freight) * (1 + duty)


def _board_leaves(
    data: Dict[str, pd.DataFrame], board: pd.Series, prefix: Tuple[str, ...],
    warnings: List[str], label: Optional[str] = None, scale: float = 1.0,
) -> List[Dict[str, object]]:
    """Leaves for one allocation line, summing to its total economic cost.

    Works on line items rather than product totals, so a dual-sourced board
    shows each supplier as its own branch instead of a blended average.
    """
    pid = str(board["product_id"])
    board_label = label or str(board["product_name"])
    here = prefix + (board_label,)
    volume = float(board["volume"])
    supplier = str(board.get("supplier_name", ""))
    leaves: List[Dict[str, object]] = []

    lines = _bom_lines(data, pid)
    consigned_bucket = float(board.get("consigned_material_cost", 0) or 0)
    quoted_bucket = float(board.get("quoted_cost", 0) or 0)

    consigned_rows, ems_rows = [], []
    for _, row in lines.iterrows():
        cost = _line_cost_per_unit(row) * volume
        if cost <= 0:
            continue
        target = (consigned_rows if str(row.get("ownership_model", "")).startswith("OEM-owned")
                  else ems_rows)
        target.append((row, cost))

    def _spread(rows, bucket, branch, ownership):
        """Place BOM lines inside their bucket, scaled to fit it exactly."""
        total = sum(c for _, c in rows)
        if bucket <= 0 or not rows:
            return
        scale = bucket / total if total > 0 else 0.0
        for row, cost in rows:
            leaves.append(_leaf(
                here + (branch, str(row.get("component", "component"))),
                cost * scale,
                ownership=ownership,
                confidence=str(row.get("confidence", "Unknown")),
                supplier=str(row.get("component_supplier", "") or supplier),
                category=str(row.get("category", "Uncategorized")),
                detail=f"{row.get('qty_per', 1)} per assembly",
            ))

    consigned_bucket *= scale
    quoted_bucket *= scale
    consigned_rows = [(r, c * scale) for r, c in consigned_rows]
    ems_rows = [(r, c * scale) for r, c in ems_rows]

    _spread(consigned_rows, consigned_bucket, OWN_CONSIGNED, OWN_CONSIGNED)

    ems_material_total = sum(c for _, c in ems_rows)
    implied_conversion = quoted_bucket - ems_material_total
    if implied_conversion < 0:
        warnings.append(
            f"{board_label}: identified BOM material exceeds the quoted price, so material "
            "is scaled to fit the quote and implied conversion shows as zero. The BOM or the "
            "quote needs review.")
        ems_material_total, implied_conversion = quoted_bucket, 0.0
    _spread(ems_rows, ems_material_total, OWN_EMS_MATERIAL, OWN_EMS_MATERIAL)

    quote = economics_engine.get_quote(data, str(board["supplier_id"]), pid)
    quote_conf = str(quote.get("confidence", "Unknown")) if quote is not None else "Unknown"
    if implied_conversion > 0:
        leaves.append(_leaf(
            here + ("Conversion, overhead & margin (implied)",), implied_conversion,
            ownership=OWN_EMS_VALUE_ADD, confidence=quote_conf, supplier=supplier,
            category="Conversion",
            detail="Quoted price minus identified material - the should-cost residual"))

    for col, label in ADDER_BUCKETS:
        value = float(board.get(col, 0) or 0) * scale
        if value > 0:
            leaves.append(_leaf(
                here + (label,), value, ownership=OWN_INCREMENTAL, confidence="Modeled",
                supplier=supplier, category="Economic adder",
                detail="Cost outside the supplier quote"))
    return leaves


def cost_structure(
    data: Dict[str, pd.DataFrame],
    result: "ScenarioResult",
    platform_id: Optional[str] = None,
    product_id: Optional[str] = None,
    basis: str = "annual",
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """Return (nodes, meta) for a treemap / indented structure table.

    ``basis`` is "annual" or "per_system" (per_system requires a platform).
    """
    li = result.line_items
    meta: Dict[str, object] = {"warnings": [], "basis": basis, "divisor": 1.0}
    if li is None or li.empty:
        return pd.DataFrame(), meta

    def _label(row: pd.Series, group: pd.DataFrame) -> str:
        """Add the supplier only when a board is split across suppliers."""
        name = str(row["product_name"])
        return (f"{name} — {row['supplier_name']}"
                if (group["product_id"] == row["product_id"]).sum() > 1 else name)

    products = data.get("products", pd.DataFrame())
    platforms = data.get("tester_platforms", pd.DataFrame())
    warnings: List[str] = meta["warnings"]
    leaves: List[Dict[str, object]] = []

    if product_id:
        rows = li[li["product_id"] == product_id]
        if rows.empty:
            return pd.DataFrame(), meta
        root = str(rows.iloc[0]["product_name"])
        for _, board in rows.iterrows():
            label = str(board["supplier_name"]) if len(rows) > 1 else None
            leaves += _board_leaves(data, board, (root,), warnings, label)
        meta["root"] = root
        meta["scope"] = "board"
    else:
        plat = platforms[platforms["platform_id"] == platform_id]
        if plat.empty:
            return pd.DataFrame(), meta
        plat = plat.iloc[0]
        root = str(plat["platform_name"])
        meta["root"] = root
        meta["scope"] = "platform"
        systems = float(plat.get("annual_units", 0) or 0)
        meta["systems"] = systems

        members = products[(products["platform_id"].astype(str) == str(platform_id))
                           & (products["parent_product_id"].astype(object)
                              .where(products["parent_product_id"].notna(), "")
                              .astype(str).str.strip() == "")]
        member_ids = set(members["product_id"].astype(str))
        board_rows = li[li["product_id"].astype(str).isin(member_ids)]
        qpa_by_product = {str(r["product_id"]): float(r.get("boards_per_tester", 0) or 0)
                          for _, r in members.iterrows()}
        good_by_product = board_rows.groupby("product_id")["good_units"].sum()
        per_system = basis == "per_system"
        for _, board in board_rows.iterrows():
            pid = str(board["product_id"])
            scale = 1.0
            if per_system:
                good = float(good_by_product.get(pid, 0) or 0)
                # QPA good boards are needed per system, so the ship-set is
                # priced per GOOD unit - identical to the Platform Rollup page.
                scale = (qpa_by_product.get(pid, 0) / good) if good > 0 else 0.0
            leaves += _board_leaves(data, board, (root,), warnings,
                                    _label(board, board_rows), scale)

        comps = data.get("system_components", pd.DataFrame())
        if comps is not None and not comps.empty and systems > 0:
            for _, comp in comps[comps["platform_id"].astype(str) == str(platform_id)].iterrows():
                qpa = float(comp.get("qpa_per_system", 0) or 0)
                cost = float(comp.get("unit_cost", 0) or 0)
                if qpa * cost <= 0:
                    continue
                extended = qpa * cost * (1.0 if basis == "per_system" else systems)
                leaves.append(_leaf(
                    (root, "System material (non-EMS)", str(comp["component"])),
                    extended,
                    ownership=OWN_DIRECT,
                    confidence=str(comp.get("confidence", "Unknown")),
                    supplier=str(comp.get("supplier", "")),
                    category=str(comp.get("category", "System")),
                    detail="Bought by OEM procurement, outside the EMS scope"))

    if not leaves:
        return pd.DataFrame(), meta

    divisor = float(meta["divisor"])
    for leaf in leaves:
        leaf["value"] = leaf["value"] / divisor

    return _roll_up(leaves), meta


def _roll_up(leaves: List[Dict[str, object]]) -> pd.DataFrame:
    """Expand leaf paths into every ancestor node, summing values upward."""
    nodes: Dict[Tuple[str, ...], Dict[str, object]] = {}
    for leaf in leaves:
        path: Tuple[str, ...] = leaf["path"]
        for depth in range(1, len(path) + 1):
            key = path[:depth]
            node = nodes.setdefault(key, {
                "id": " / ".join(key),
                "parent": " / ".join(key[:-1]) if depth > 1 else "",
                "label": key[-1],
                "level": depth,
                "value": 0.0,
                "ownership": "", "confidence": "", "supplier": "", "category": "",
                "detail": "",
            })
            node["value"] += leaf["value"]
            if depth == len(path):  # leaf attributes
                for attr in ("ownership", "confidence", "supplier", "category", "detail"):
                    node[attr] = leaf.get(attr, "")
                node["is_leaf"] = True
            else:
                node.setdefault("is_leaf", False)
    df = pd.DataFrame(list(nodes.values()))
    df["is_leaf"] = df["is_leaf"].fillna(False)
    # Deepest first within each level keeps the indented table readable.
    return df.sort_values(["level", "value"], ascending=[True, False]).reset_index(drop=True)


def structure_table(nodes: pd.DataFrame) -> pd.DataFrame:
    """Indented, exact companion to the treemap (parents before children)."""
    if nodes.empty:
        return pd.DataFrame()
    total = float(nodes[nodes["level"] == 1]["value"].sum())
    by_parent: Dict[str, List[pd.Series]] = {}
    for _, row in nodes.iterrows():
        by_parent.setdefault(str(row["parent"]), []).append(row)
    for children in by_parent.values():
        children.sort(key=lambda r: -float(r["value"]))

    rows: List[Dict[str, object]] = []

    def walk(parent_id: str, depth: int) -> None:
        for row in by_parent.get(parent_id, []):
            parent_value = float(
                nodes.loc[nodes["id"] == parent_id, "value"].iloc[0]) if parent_id else total
            rows.append({
                "Structure": ("    " * depth) + str(row["label"]),
                "Cost": float(row["value"]),
                "% of parent": (float(row["value"]) / parent_value * 100) if parent_value else 0.0,
                "% of total": (float(row["value"]) / total * 100) if total else 0.0,
                "Ownership": row["ownership"],
                "Confidence": row["confidence"],
                "Supplier": row["supplier"],
            })
            walk(str(row["id"]), depth + 1)

    walk("", 0)
    return pd.DataFrame(rows)
