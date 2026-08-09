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
    "quality_return_handling_factor": 0.5,
    "should_cost_commercial_share": 0.6,
    "level3_bom_coverage_threshold_pct": 70.0,
    "fpy_attention_threshold_pct": 94.0,
    "mc_material_passthrough_pct": 67.0,
    "mc_yield_scrap_coupling": 0.5,
    "benchmark_material_pct": 68.0,
    "benchmark_labor_pct": 8.0,
    "benchmark_overhead_pct": 12.0,
    "benchmark_margin_pct": 9.0,
    "benchmark_other_pct": 3.0,
}

# Groups drive the Model Settings page layout and keep related knobs together.
SETTING_GROUPS = {
    "Working capital & carrying cost": [
        "cost_of_capital_pct", "storage_pct", "insurance_pct", "shrinkage_pct",
        "handling_pct", "obsolescence_pct", "admin_pct", "payment_terms_reference_days",
    ],
    "Quality responsibility & cost": [
        "oem_share_when_oem_responsible_pct", "oem_share_when_shared_pct",
        "oem_share_when_ems_responsible_pct", "field_repair_cost_multiplier",
        "quality_return_handling_factor", "fpy_attention_threshold_pct",
    ],
    "System & platform economics": [
        "inhouse_conversion_pct_of_revenue", "gross_margin_reference_pct",
    ],
    "Should-cost": [
        "should_cost_commercial_share", "level3_bom_coverage_threshold_pct",
        "benchmark_material_pct", "benchmark_labor_pct", "benchmark_overhead_pct",
        "benchmark_margin_pct", "benchmark_other_pct",
    ],
    "Monte Carlo": [
        "mc_default_iterations", "mc_default_seed",
        "mc_material_passthrough_pct", "mc_yield_scrap_coupling",
    ],
}


def benchmark_structure(settings: Dict[str, float]) -> Dict[str, float]:
    """Level 1 benchmark cost structure, read from settings."""
    return {
        "material_pct": settings.get("benchmark_material_pct", 68.0),
        "labor_pct": settings.get("benchmark_labor_pct", 8.0),
        "overhead_pct": settings.get("benchmark_overhead_pct", 12.0),
        "margin_pct": settings.get("benchmark_margin_pct", 9.0),
        "other_pct": settings.get("benchmark_other_pct", 3.0),
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
