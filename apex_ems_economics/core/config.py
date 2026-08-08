"""Global settings access for the calculation engines.

Settings live in ``global_settings.csv`` (key/value/unit/description) so they
are editable in the UI, exportable, and auditable like every other input.
"""
from __future__ import annotations

from typing import Dict

import pandas as pd

CARRYING_COST_COMPONENTS = [
    ("cost_of_capital_pct", "Cost of capital"),
    ("storage_pct", "Storage"),
    ("insurance_pct", "Insurance"),
    ("shrinkage_pct", "Shrinkage"),
    ("handling_pct", "Handling"),
    ("obsolescence_pct", "Obsolescence"),
    ("admin_pct", "Administrative"),
]

DEFAULTS: Dict[str, float] = {
    "cost_of_capital_pct": 8.0,
    "storage_pct": 3.0,
    "insurance_pct": 0.5,
    "shrinkage_pct": 0.75,
    "handling_pct": 1.5,
    "obsolescence_pct": 4.0,
    "admin_pct": 1.25,
    "payment_terms_reference_days": 30.0,
    "oem_share_when_oem_responsible_pct": 100.0,
    "oem_share_when_shared_pct": 50.0,
    "oem_share_when_ems_responsible_pct": 20.0,
    "field_repair_cost_multiplier": 2.5,
    "mc_default_iterations": 500.0,
    "mc_default_seed": 42.0,
    "gross_margin_reference_pct": 54.0,
    "inhouse_conversion_pct_of_revenue": 3.5,
}


def load_settings(data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
    """Return settings as a dict of floats, falling back to defaults."""
    settings = dict(DEFAULTS)
    df = data.get("global_settings")
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            try:
                settings[str(row["key"])] = float(row["value"])
            except (TypeError, ValueError):
                continue
    return settings


def carrying_cost_pct(settings: Dict[str, float]) -> float:
    """Total annual inventory carrying-cost percentage (sum of components)."""
    return sum(settings.get(key, 0.0) for key, _ in CARRYING_COST_COMPONENTS)


def oem_share_for_responsibility(settings: Dict[str, float], responsibility: str) -> float:
    """OEM-borne fraction (0-1) of a quality cost given contractual responsibility.

    Even when the EMS is contractually responsible, the OEM typically bears a
    residual burden (disruption, engineering time, imperfect recovery), which
    is why the EMS share is not zero. All three shares are editable settings.
    """
    resp = str(responsibility or "Unknown").strip().lower()
    if resp == "oem":
        return settings["oem_share_when_oem_responsible_pct"] / 100.0
    if resp == "shared":
        return settings["oem_share_when_shared_pct"] / 100.0
    if resp == "ems":
        return settings["oem_share_when_ems_responsible_pct"] / 100.0
    # Unknown responsibility: assume OEM bears it (conservative) at shared rate.
    return settings["oem_share_when_shared_pct"] / 100.0
