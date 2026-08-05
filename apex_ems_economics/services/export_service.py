"""CSV and multi-tab Excel exports."""
from __future__ import annotations

import io
from typing import Dict

import pandas as pd


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> bytes:
    """Build a multi-tab Excel workbook. Sheet names are truncated to the
    31-character Excel limit; empty frames get a placeholder note."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, df in sheets.items():
            safe = name[:31]
            if df is None or df.empty:
                pd.DataFrame({"note": ["No data available"]}).to_excel(
                    writer, sheet_name=safe, index=False)
            else:
                df.to_excel(writer, sheet_name=safe, index=False)
    buffer.seek(0)
    return buffer.read()


def evidence_package_sheets(
    comparison: pd.DataFrame,
    supplier_summary: pd.DataFrame,
    product_summary: pd.DataFrame,
    line_items: pd.DataFrame,
    inventory: pd.DataFrame,
    quality: pd.DataFrame,
    contract_terms: pd.DataFrame,
    risks: pd.DataFrame,
    assumptions: pd.DataFrame,
    actions: pd.DataFrame,
    executive_summary: pd.DataFrame,
) -> Dict[str, pd.DataFrame]:
    """Assemble the standard evidence-package workbook."""
    return {
        "Executive Summary": executive_summary,
        "Scenario Comparison": comparison,
        "Supplier Economics": supplier_summary,
        "Product Economics": product_summary,
        "Cost Detail": line_items,
        "Inventory": inventory,
        "Quality": quality,
        "Contract Terms": contract_terms,
        "Risks": risks,
        "Assumptions": assumptions,
        "Actions": actions,
    }
