"""Inventory and working-capital calculations.

Central design rule: **ownership and physical location are modeled
separately.** A record can be OEM-owned yet physically at an EMS site
(consignment), or EMS-owned at the EMS site until finished-goods transfer.

Key outputs:
  * ownership x location exposure matrix
  * balance-sheet inventory (OEM-owned) vs off-balance-sheet supply exposure
    (EMS/supplier-owned inventory dedicated to OEM demand)
  * carrying cost = average inventory value x annual carrying-cost %
  * supplier "ownership-days" profiles, used by the economics engine to
    scale working capital when scenario allocations differ from the baseline
  * working-capital cost per allocation line:
        carrying cost on OEM-owned inventory
      + advance-payment financing cost
      - payment-terms financing benefit vs the reference terms
"""
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from core.config import carrying_cost_pct

OEM = "OEM"


def inventory_value(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["quantity"], errors="coerce").fillna(0) * pd.to_numeric(
        df["unit_cost"], errors="coerce"
    ).fillna(0)


def ownership_location_matrix(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Pivot of inventory value by ownership (rows) x physical location (cols)."""
    inv = data.get("inventory_records", pd.DataFrame())
    if inv is None or inv.empty:
        return pd.DataFrame()
    inv = inv.copy()
    inv["value"] = inventory_value(inv)
    return inv.pivot_table(
        index="ownership", columns="physical_location", values="value",
        aggfunc="sum", fill_value=0.0, margins=True, margins_name="Total",
    )


def exposure_summary(data: Dict[str, pd.DataFrame], settings: Dict[str, float]) -> Dict[str, float]:
    """Headline inventory exposure figures."""
    inv = data.get("inventory_records", pd.DataFrame())
    if inv is None or inv.empty:
        return {}
    inv = inv.copy()
    inv["value"] = inventory_value(inv)
    own = inv["ownership"].astype(str)
    loc = inv["physical_location"].astype(str)

    oem_at_oem = inv.loc[(own == OEM) & (loc == "OEM site"), "value"].sum()
    oem_at_ems = inv.loc[(own == OEM) & (loc == "EMS site"), "value"].sum()
    oem_transit = inv.loc[(own == OEM) & (loc == "In transit"), "value"].sum()
    ems_at_ems = inv.loc[(own == "EMS"), "value"].sum()
    supplier_owned = inv.loc[(own == "Supplier"), "value"].sum()
    excess = inv.loc[inv["excess_flag"] == True, "value"].sum()  # noqa: E712
    ncnr = inv.loc[inv["stage"].astype(str) == "Noncancelable/nonreturnable", "value"].sum()

    oem_total = oem_at_oem + oem_at_ems + oem_transit
    total_exposure = oem_total + ems_at_ems + supplier_owned
    rate = carrying_cost_pct(settings) / 100.0

    return {
        "oem_owned_at_oem_sites": float(oem_at_oem),
        "oem_owned_at_ems_sites": float(oem_at_ems),
        "oem_owned_in_transit": float(oem_transit),
        "oem_owned_total": float(oem_total),
        "ems_owned_at_ems_sites": float(ems_at_ems),
        "supplier_owned": float(supplier_owned),
        "balance_sheet_inventory": float(oem_total),
        "off_balance_sheet_exposure": float(ems_at_ems + supplier_owned),
        "total_economic_exposure": float(total_exposure),
        "excess_value": float(excess),
        "ncnr_liability_value": float(ncnr),
        "annual_carrying_cost": float(oem_total * rate),
    }


def carrying_cost_decomposition(
    oem_inventory_value: float, settings: Dict[str, float]
) -> pd.DataFrame:
    """Split the annual carrying cost into its configured components."""
    from core.config import CARRYING_COST_COMPONENTS

    rows = []
    for key, label in CARRYING_COST_COMPONENTS:
        pct = settings.get(key, 0.0)
        rows.append({
            "Component": label,
            "Rate %": pct,
            "Annual cost": oem_inventory_value * pct / 100.0,
        })
    df = pd.DataFrame(rows)
    df.loc[len(df)] = {
        "Component": "Total",
        "Rate %": df["Rate %"].sum(),
        "Annual cost": df["Annual cost"].sum(),
    }
    return df


def days_inventory_outstanding(oem_inventory_value: float, annual_cogs: float) -> float:
    if annual_cogs <= 0:
        return 0.0
    return oem_inventory_value / (annual_cogs / 365.0)


def supplier_ownership_profile(
    data: Dict[str, pd.DataFrame],
    baseline_spend_by_supplier: Dict[str, float],
) -> pd.DataFrame:
    """Days of OEM-owned inventory per supplier, derived from records.

    ``oem_days = OEM-owned value tied to supplier / (baseline spend / 365)``

    This "inventory intensity" lets the economics engine estimate working
    capital for allocations that differ from the baseline (e.g. shifting
    volume to a supplier changes the OEM-owned pipeline proportionally).
    In-transit records with no supplier are attributed via product's
    baseline supplier where possible, otherwise excluded from per-supplier
    intensity (still counted in totals).
    """
    inv = data.get("inventory_records", pd.DataFrame())
    rows = []
    for supplier_id, spend in baseline_spend_by_supplier.items():
        if inv is None or inv.empty or spend <= 0:
            rows.append({"supplier_id": supplier_id, "oem_days": 0.0, "oem_value": 0.0})
            continue
        sup_inv = inv[(inv["supplier_id"] == supplier_id) & (inv["ownership"] == OEM)]
        value = float(inventory_value(sup_inv).sum()) if not sup_inv.empty else 0.0
        rows.append({
            "supplier_id": supplier_id,
            "oem_value": value,
            "oem_days": value / (spend / 365.0),
        })
    return pd.DataFrame(rows)


def working_capital_cost(
    annual_spend: float,
    oem_days: float,
    payment_terms_days: float,
    advance_payment_pct: float,
    settings: Dict[str, float],
    in_transit_days: float = 0.0,
) -> Dict[str, float]:
    """Annual working-capital cost for one allocation line.

    carrying     = (oem_days + in_transit_days) / 365 x spend x carrying %
    advance      = advance % x spend x cost of capital
    terms effect = (reference_days - payment_days) / 365 x spend x cost of capital
                   (positive = cost when terms are shorter than reference,
                    negative = benefit when longer)
    """
    daily_spend = annual_spend / 365.0 if annual_spend else 0.0
    rate = carrying_cost_pct(settings) / 100.0
    coc = settings["cost_of_capital_pct"] / 100.0
    ref_days = settings["payment_terms_reference_days"]

    oem_inventory = daily_spend * (oem_days + in_transit_days)
    carrying = oem_inventory * rate
    advance = annual_spend * advance_payment_pct / 100.0 * coc
    terms_effect = (ref_days - payment_terms_days) / 365.0 * annual_spend * coc

    return {
        "oem_inventory_value": oem_inventory,
        "carrying_cost": carrying,
        "advance_payment_cost": advance,
        "payment_terms_effect": terms_effect,
        "wc_cost": carrying + advance + terms_effect,
    }
