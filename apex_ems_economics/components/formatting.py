"""Number, currency, and percentage formatting helpers."""
from __future__ import annotations

import math


def fmt_currency(value: float, decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.{decimals}f}"


def fmt_currency_compact(value: float) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1_000_000_000:
        return f"{sign}${v / 1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{sign}${v / 1_000_000:.2f}M"
    if v >= 10_000:
        return f"{sign}${v / 1_000:.0f}K"
    return f"{sign}${v:,.0f}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    return f"{value:.{decimals}f}%"


def fmt_units(value: float) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    return f"{value:,.0f}"


def fmt_delta(value: float, invert: bool = False) -> str:
    """Format a delta where negative = favorable (cost down) by default."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    arrow = "▼" if (value < 0) != invert else "▲"
    return f"{arrow} {fmt_currency_compact(abs(value))}"


CONFIDENCE_BADGE = {"High": "🟢 High", "Medium": "🟡 Medium", "Low": "🔴 Low"}


def confidence_badge(conf: str) -> str:
    return CONFIDENCE_BADGE.get(str(conf), str(conf))


def md(text: object) -> str:
    """Escape text for st.markdown / st.caption.

    Streamlit renders markdown with LaTeX enabled, so a line containing two
    dollar signs (e.g. "spend is $824,560,000; cost is $1,274,284,434") is
    parsed as math: both "$" disappear and the text between them is
    italicized. Escaping the dollar signs keeps currency readable.
    """
    return str(text).replace("$", r"\$")
