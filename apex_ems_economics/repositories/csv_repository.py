"""CSV-backed repository for all model entities.

The repository is the only layer that touches storage. Pages and engines
receive a plain ``dict[str, pd.DataFrame]`` keyed by entity name, so the CSV
backend can later be replaced by a database repository implementing the same
three methods (``load_all``, ``load``, ``save``) without touching any engine
or page code.
"""
from __future__ import annotations

import os
from typing import Dict, List

import pandas as pd

# Entity name -> CSV file name. Order matters only for display.
ENTITY_FILES: Dict[str, str] = {
    "suppliers": "suppliers.csv",
    "sites": "sites.csv",
    "products": "products.csv",
    "tester_platforms": "tester_platforms.csv",
    "scenarios": "scenarios.csv",
    "allocations": "allocations.csv",
    "supplier_quotes": "supplier_quotes.csv",
    "contract_terms": "contract_terms.csv",
    "bom_items": "bom_items.csv",
    "conversion_costs": "conversion_costs.csv",
    "inventory_records": "inventory_records.csv",
    "quality_metrics": "quality_metrics.csv",
    "logistics_assumptions": "logistics_assumptions.csv",
    "service_levels": "service_levels.csv",
    "capacity_records": "capacity_records.csv",
    "risks": "risks.csv",
    "assumptions": "assumptions.csv",
    "negotiation_levers": "negotiation_levers.csv",
    "scenario_overrides": "scenario_overrides.csv",
    "global_settings": "global_settings.csv",
    "scoring_weights": "scoring_weights.csv",
    "decision_records": "decision_records.csv",
}

# Columns that must be parsed as booleans when present.
BOOL_COLUMNS = {"is_baseline", "includes_freight", "includes_duties", "excess_flag"}


def default_data_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "data", "sample")


class CsvRepository:
    """Loads and saves every entity as a CSV file in one directory."""

    def __init__(self, data_dir: str | None = None):
        self.data_dir = data_dir or default_data_dir()

    # -- read ---------------------------------------------------------------
    def entity_names(self) -> List[str]:
        return list(ENTITY_FILES.keys())

    def load(self, entity: str) -> pd.DataFrame:
        path = os.path.join(self.data_dir, ENTITY_FILES[entity])
        if not os.path.exists(path):
            return pd.DataFrame()
        df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
        df = self._coerce_types(df)
        return df

    def load_all(self) -> Dict[str, pd.DataFrame]:
        return {name: self.load(name) for name in ENTITY_FILES}

    # -- write --------------------------------------------------------------
    def save(self, entity: str, df: pd.DataFrame) -> str:
        path = os.path.join(self.data_dir, ENTITY_FILES[entity])
        df.to_csv(path, index=False)
        return path

    def save_all(self, data: Dict[str, pd.DataFrame]) -> None:
        for name, df in data.items():
            if name in ENTITY_FILES:
                self.save(name, df)

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
        """Convert numeric-looking columns to numbers and booleans to bool."""
        for col in df.columns:
            if col in BOOL_COLUMNS:
                df[col] = (
                    df[col].astype(str).str.strip().str.upper().isin(["TRUE", "1", "YES"])
                )
                continue
            converted = pd.to_numeric(df[col], errors="coerce")
            # Treat as numeric only if every non-null original value converts.
            non_null = df[col].notna()
            if non_null.any() and converted[non_null].notna().all():
                df[col] = converted
        return df
