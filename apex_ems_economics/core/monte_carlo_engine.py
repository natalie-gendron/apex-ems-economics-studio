"""Optional Monte Carlo simulation over the deterministic engine.

Each iteration draws uncertain multipliers/deltas, perturbs a copy of the
input data, and re-runs the full deterministic scenario computation - the
simulation therefore inherits every deterministic relationship (no separate
response-surface approximation). A fixed seed makes runs reproducible.

Simulated outputs are always labeled as simulated; they never replace the
deterministic results.

Supported distributions: Normal, Triangular, Uniform, Lognormal, Bernoulli,
Discrete (via UncertainVariable.values/probabilities).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from core import economics_engine
from core.config import load_settings


@dataclass
class UncertainVariable:
    name: str
    distribution: str  # Normal | Triangular | Uniform | Lognormal | Bernoulli | Discrete
    params: Dict[str, float] = field(default_factory=dict)
    values: Optional[Sequence[float]] = None          # Discrete
    probabilities: Optional[Sequence[float]] = None   # Discrete
    apply: Optional[Callable[[Dict[str, pd.DataFrame], float], None]] = None

    def sample(self, rng: np.random.Generator) -> float:
        d = self.distribution.lower()
        p = self.params
        if d == "normal":
            return float(rng.normal(p.get("mean", 1.0), p.get("std", 0.05)))
        if d == "triangular":
            return float(rng.triangular(p["min"], p["mode"], p["max"]))
        if d == "uniform":
            return float(rng.uniform(p["min"], p["max"]))
        if d == "lognormal":
            return float(rng.lognormal(p.get("mean", 0.0), p.get("sigma", 0.1)))
        if d == "bernoulli":
            return float(rng.random() < p.get("p", 0.5))
        if d == "discrete":
            return float(rng.choice(self.values, p=self.probabilities))
        raise ValueError(f"Unsupported distribution: {self.distribution}")


# ---------------------------------------------------------------------------
# Standard driver set built from the assumption register's ranges
# ---------------------------------------------------------------------------

def _mult_products_volume(data: Dict[str, pd.DataFrame], x: float) -> None:
    data["products"]["annual_volume"] = data["products"]["annual_volume"].astype(float) * x


def _mult_bom_prices(data: Dict[str, pd.DataFrame], x: float) -> None:
    if not data["bom_items"].empty:
        data["bom_items"]["unit_price"] = data["bom_items"]["unit_price"].astype(float) * x
    # Material moves also flow into quoted prices (pass-through approximation:
    # material is ~2/3 of a turnkey quote, so quote moves by 2/3 of the swing).
    for col in ("base_unit_price", "tier2_unit_price", "tier3_unit_price"):
        data["supplier_quotes"][col] = (
            pd.to_numeric(data["supplier_quotes"][col], errors="coerce") * (1 + (x - 1) * 0.67))


def _mult_freight(data: Dict[str, pd.DataFrame], x: float) -> None:
    lanes = data["logistics_assumptions"]
    for col in ("freight_cost_per_unit", "expedite_freight_cost_per_unit"):
        lanes[col] = lanes[col].astype(float) * x


def _mult_expedite_freq(data: Dict[str, pd.DataFrame], x: float) -> None:
    sl = data["service_levels"]
    sl["expedite_rate_pct"] = (sl["expedite_rate_pct"].astype(float) * x).clip(upper=100)


def _delta_yield(data: Dict[str, pd.DataFrame], x: float) -> None:
    """x is a yield delta in points applied to FPY/final yield (bounded)."""
    qm = data["quality_metrics"]
    qm["final_yield_pct"] = (qm["final_yield_pct"].astype(float) + x).clip(50, 100)
    qm["scrap_rate_pct"] = (qm["scrap_rate_pct"].astype(float) - x * 0.5).clip(0, 100)


def _mult_tariff(data: Dict[str, pd.DataFrame], x: float) -> None:
    lanes = data["logistics_assumptions"]
    lanes["tariff_rate_pct"] = lanes["tariff_rate_pct"].astype(float) * x


def default_uncertain_variables(data: Dict[str, pd.DataFrame]) -> List[UncertainVariable]:
    """Build the standard driver set, taking ranges from the assumption register
    where present (by assumption name), else sensible defaults."""
    def rng_from_assumption(name: str, default: tuple) -> tuple:
        assumptions = data.get("assumptions", pd.DataFrame())
        if assumptions is not None and not assumptions.empty:
            m = assumptions[assumptions["name"] == name]
            if not m.empty:
                row = m.iloc[0]
                mn, ml, mx = row.get("min_value"), row.get("most_likely_value"), row.get("max_value")
                if pd.notna(mn) and pd.notna(ml) and pd.notna(mx):
                    return float(mn), float(ml), float(mx)
        return default

    dmn, dml, dmx = rng_from_assumption("Demand multiplier next 12 months", (0.85, 1.0, 1.2))
    mmn, mml, mmx = rng_from_assumption("Material price index change", (0.96, 1.0, 1.08))
    fmn, fml, fmx = rng_from_assumption("Ocean freight rate multiplier", (0.9, 1.0, 1.45))
    emn, eml, emx = rng_from_assumption("Expedite frequency multiplier", (0.7, 1.0, 1.8))

    return [
        UncertainVariable("Demand volume", "Triangular",
                          {"min": dmn, "mode": dml, "max": dmx}, apply=_mult_products_volume),
        UncertainVariable("Material prices", "Triangular",
                          {"min": mmn, "mode": mml, "max": mmx}, apply=_mult_bom_prices),
        UncertainVariable("Freight rates", "Triangular",
                          {"min": fmn, "mode": fml, "max": fmx}, apply=_mult_freight),
        UncertainVariable("Expedite frequency", "Triangular",
                          {"min": emn, "mode": eml, "max": emx}, apply=_mult_expedite_freq),
        UncertainVariable("Yield delta (points)", "Triangular",
                          {"min": -2.5, "mode": 0.0, "max": 1.0}, apply=_delta_yield),
        UncertainVariable("Tariff shock", "Triangular",
                          {"min": 0.0, "mode": 1.0, "max": 3.0}, apply=_mult_tariff),
    ]


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run_simulation(
    data: Dict[str, pd.DataFrame],
    scenario_ids: List[str],
    iterations: int = 500,
    seed: int = 42,
    variables: Optional[List[UncertainVariable]] = None,
) -> Dict[str, object]:
    """Run the Monte Carlo simulation. Returns draws, per-scenario totals,
    summary statistics, and driver sensitivities (correlation of each driver
    with the first scenario's total cost)."""
    settings = load_settings(data)
    variables = variables or default_uncertain_variables(data)
    rng = np.random.default_rng(seed)

    draw_rows = []
    total_rows: Dict[str, List[float]] = {sid: [] for sid in scenario_ids}
    for _ in range(iterations):
        draws = {v.name: v.sample(rng) for v in variables}
        perturbed = {name: df.copy() for name, df in data.items()}
        for v in variables:
            if v.apply is not None:
                v.apply(perturbed, draws[v.name])
        for sid in scenario_ids:
            result = economics_engine.compute_scenario(perturbed, sid, settings)
            total_rows[sid].append(result.totals.get("total_economic_cost", 0.0))
        draw_rows.append(draws)

    draws_df = pd.DataFrame(draw_rows)
    totals_df = pd.DataFrame(total_rows)

    summary = {}
    for sid in scenario_ids:
        s = totals_df[sid]
        summary[sid] = {
            "mean": float(s.mean()), "median": float(s.median()),
            "p10": float(s.quantile(0.10)), "p50": float(s.quantile(0.50)),
            "p90": float(s.quantile(0.90)),
            "min": float(s.min()), "max": float(s.max()), "std": float(s.std()),
        }

    sensitivities = pd.Series(dtype=float)
    if scenario_ids:
        target = totals_df[scenario_ids[0]]
        sens = {}
        for col in draws_df.columns:
            if draws_df[col].std() > 0:
                sens[col] = float(np.corrcoef(draws_df[col], target)[0, 1])
        sensitivities = pd.Series(sens).sort_values(key=abs, ascending=False)

    return {
        "draws": draws_df,
        "totals": totals_df,
        "summary": summary,
        "sensitivities": sensitivities,
        "iterations": iterations,
        "seed": seed,
    }


def probability_cheaper(totals: pd.DataFrame, scenario_a: str, scenario_b: str) -> float:
    """P(total cost of A < total cost of B) across paired iterations."""
    if scenario_a not in totals.columns or scenario_b not in totals.columns:
        return float("nan")
    return float((totals[scenario_a] < totals[scenario_b]).mean())


def probability_savings_exceed(
    totals: pd.DataFrame, scenario: str, baseline: str, target: float
) -> float:
    """P(baseline cost - scenario cost > target)."""
    if scenario not in totals.columns or baseline not in totals.columns:
        return float("nan")
    return float(((totals[baseline] - totals[scenario]) > target).mean())
