"""Unit tests for the deterministic calculation engines (sample data)."""
import numpy as np
import pandas as pd
import pytest

from core import economics_engine, inventory_engine, quality_engine, scenario_engine
from core.config import carrying_cost_pct, load_settings
from core.economics_engine import (
    compute_scenario, cost_bridge, get_quote, material_cost_per_unit,
    conversion_cost_per_unit, tier_unit_price)
from core.should_cost_engine import comparison_table, process_based_should_cost
from core.validation_engine import validate, data_quality_score
from repositories.csv_repository import CsvRepository


@pytest.fixture(scope="module")
def data():
    return CsvRepository().load_all()


@pytest.fixture(scope="module")
def settings(data):
    return load_settings(data)


@pytest.fixture(scope="module")
def baseline(data, settings):
    return compute_scenario(data, "SCN-001", settings)


# ---------------------------------------------------------------- material
def test_material_cost_positive_and_split(data):
    mc = material_cost_per_unit(data, "P-100")
    assert mc["bom_lines"] == 10
    assert mc["material_total"] > 0
    # Consigned (OEM-owned models) + EMS-procured must equal the total.
    assert mc["consigned_material"] + mc["ems_material"] == pytest.approx(mc["material_total"])
    # P-100 consigns pin-electronics + timing ASICs: consigned share is large.
    assert mc["consigned_material"] > 5000


def test_material_cost_scrap_yield_adjustments():
    df = {"bom_items": pd.DataFrame([{
        "bom_id": "B1", "product_id": "X", "component": "c", "qty_per": 2,
        "unit_price": 10.0, "scrap_pct": 10.0, "yield_pct": 80.0,
        "freight_pct": 5.0, "duty_pct": 2.0, "ownership_model": "EMS-owned until consumption",
    }])}
    mc = material_cost_per_unit(df, "X")
    expected = 2 * 10 * 1.10 / 0.80 * 1.05 * 1.02
    assert mc["material_total"] == pytest.approx(expected)


# ---------------------------------------------------------------- conversion
def test_conversion_cost_components(data):
    mc = material_cost_per_unit(data, "P-100")
    conv = conversion_cost_per_unit(data, "P-100", "SUP-ATL", mc["material_total"])
    assert conv["conversion_missing"] == 0
    assert conv["direct_labor"] == pytest.approx(14 * 9.50)
    assert conv["burdened_labor"] == pytest.approx(14 * 9.50 * 1.42)
    assert conv["conversion_total"] > conv["burdened_labor"]
    # Margin applies last and must be positive.
    assert conv["supplier_margin"] > 0


# ---------------------------------------------------------------- tier pricing
def test_volume_tier_pricing(data):
    quote = get_quote(data, "SUP-ATL", "P-100")
    assert tier_unit_price(quote, 1000) == 11400    # below tier 2
    assert tier_unit_price(quote, 1800) == 11050    # tier 2 (>= 1500)
    assert tier_unit_price(quote, 3000) == 10750    # tier 3 (>= 2400)


# ---------------------------------------------------------------- quality
def test_quality_copq_and_good_units(data, settings):
    q = quality_engine.get_quality_row(data, "SUP-MER", "P-100")
    result = quality_engine.copq(q, volume=1000, unit_price=10100.0, settings=settings)
    assert result["good_units"] == pytest.approx(1000 * 0.964)
    assert result["total_copq"] > 0
    # OEM-borne can never exceed total.
    assert result["oem_copq"] <= result["total_copq"] + 1e-6
    # Expected recall = probability x impact x share.
    assert result["expected_recall_cost"] == pytest.approx(0.008 * 6_000_000)


def test_quality_responsibility_shifts_oem_share(data, settings):
    """Same physical quality, EMS-responsible vs OEM-responsible: OEM burden differs."""
    row = data["quality_metrics"]
    atl = row[(row["supplier_id"] == "SUP-ATL") & (row["product_id"] == "P-100")].iloc[0]
    modified = atl.copy()
    modified["scrap_responsibility"] = "OEM"
    modified["rework_responsibility"] = "OEM"
    modified["warranty_responsibility"] = "OEM"
    ems_borne = quality_engine.copq(atl, 1000, 11050.0, settings)["oem_copq"]
    oem_borne = quality_engine.copq(modified, 1000, 11050.0, settings)["oem_copq"]
    assert oem_borne > ems_borne


# ---------------------------------------------------------------- working capital
def test_working_capital_payment_terms_effect(settings):
    wc_net30 = inventory_engine.working_capital_cost(
        1_000_000, oem_days=30, payment_terms_days=30, advance_payment_pct=0, settings=settings)
    wc_net75 = inventory_engine.working_capital_cost(
        1_000_000, oem_days=30, payment_terms_days=75, advance_payment_pct=0, settings=settings)
    # Longer terms than the 30-day reference create a financing benefit.
    assert wc_net30["payment_terms_effect"] == pytest.approx(0.0)
    assert wc_net75["payment_terms_effect"] < 0
    assert wc_net75["wc_cost"] < wc_net30["wc_cost"]


def test_carrying_cost_formula(settings):
    wc = inventory_engine.working_capital_cost(
        365_000, oem_days=10, payment_terms_days=30, advance_payment_pct=0, settings=settings)
    expected_inventory = 365_000 / 365 * 10
    assert wc["oem_inventory_value"] == pytest.approx(expected_inventory)
    assert wc["carrying_cost"] == pytest.approx(
        expected_inventory * carrying_cost_pct(settings) / 100.0)


def test_inventory_ownership_vs_location(data, settings):
    exp = inventory_engine.exposure_summary(data, settings)
    # OEM-owned material physically at EMS sites must be non-zero (consignment).
    assert exp["oem_owned_at_ems_sites"] > 0
    # EMS-owned inventory exists and is off-balance-sheet for the OEM.
    assert exp["ems_owned_at_ems_sites"] > 0
    assert exp["off_balance_sheet_exposure"] >= exp["ems_owned_at_ems_sites"]
    assert exp["balance_sheet_inventory"] == pytest.approx(
        exp["oem_owned_at_oem_sites"] + exp["oem_owned_at_ems_sites"] + exp["oem_owned_in_transit"])


# ---------------------------------------------------------------- risk
def test_risk_adjusted_cost(baseline):
    t = baseline.totals
    assert t["risk_cost"] > 0
    # Risk-adjusted = base + expected risk; verify additive structure.
    buckets = ["quoted_cost", "consigned_material_cost", "logistics_cost", "duty_cost",
               "quality_cost", "wc_cost", "service_cost", "risk_cost"]
    assert t["recurring_economic_cost"] == pytest.approx(sum(t[b] for b in buckets), rel=1e-9)


# ---------------------------------------------------------------- should-cost
def test_should_cost_variance(data):
    comp = comparison_table(data, "P-100")
    assert len(comp) == 3
    atlas = comp[comp["supplier_id"] == "SUP-ATL"].iloc[0]
    sc = process_based_should_cost(data, "P-100", "SUP-ATL")
    assert atlas["variance_usd"] == pytest.approx(atlas["quoted_price"] - sc["should_cost"])


# ---------------------------------------------------------------- landed cost / double counting
def test_no_double_counting_freight(data, settings):
    """If a quote includes freight, the logistics adder must drop the freight."""
    modified = {k: v.copy() for k, v in data.items()}
    quotes = modified["supplier_quotes"]
    quotes.loc[quotes["quote_id"] == "Q-ATL-P100", "includes_freight"] = True
    with_incl = compute_scenario(modified, "SCN-001", settings)
    without = compute_scenario(data, "SCN-001", settings)
    li_a = with_incl.line_items
    li_b = without.line_items
    row_a = li_a[(li_a["product_id"] == "P-100")].iloc[0]
    row_b = li_b[(li_b["product_id"] == "P-100")].iloc[0]
    assert row_a["logistics_cost"] < row_b["logistics_cost"]


def test_material_conversion_not_added_to_total(baseline):
    """Material and conversion are transparency layers inside the quote."""
    li = baseline.line_items.iloc[0]
    buckets_sum = (li["quoted_cost"] + li["consigned_material_cost"] + li["logistics_cost"]
                   + li["duty_cost"] + li["quality_cost"] + li["wc_cost"]
                   + li["service_cost"] + li["risk_cost"])
    assert li["total_economic_cost"] == pytest.approx(buckets_sum)


# ---------------------------------------------------------------- yield / good units
def test_good_units_account_for_yield(baseline):
    li = baseline.line_items
    row = li[(li["product_id"] == "P-100") & (li["supplier_id"] == "SUP-ATL")].iloc[0]
    assert row["good_units"] == pytest.approx(row["volume"] * 0.986)
    assert row["econ_cost_per_unit"] > row["total_economic_cost"] / row["volume"]


# ---------------------------------------------------------------- scenarios
def test_scenario_overrides_applied(data):
    patched = scenario_engine.apply_scenario(data, "SCN-003")
    terms = patched["contract_terms"]
    pay = terms[terms["term_id"] == "CT-ATL-PAY"].iloc[0]
    assert float(pay["value"]) == 75.0
    quotes = patched["supplier_quotes"]
    q = quotes[quotes["quote_id"] == "Q-ATL-P100"].iloc[0]
    assert q["base_unit_price"] == pytest.approx(11400 * 1.006)


def test_inventory_ownership_conversion_override(data):
    patched = scenario_engine.apply_scenario(data, "SCN-003")
    inv = patched["inventory_records"]
    original = inv[inv["inv_id"] == "INV-001"].iloc[0]
    converted = inv[inv["inv_id"] == "INV-001-EMS"]
    assert not converted.empty
    # 40% of the consigned pool converts to EMS ownership in SCN-003.
    assert float(original["quantity"]) == pytest.approx(4200 * 0.6)
    assert float(converted.iloc[0]["quantity"]) == pytest.approx(4200 * 0.4)
    assert converted.iloc[0]["ownership"] == "EMS"


# ---------------------------------------------------------------- end-to-end
def test_end_to_end_sample_scenarios(data, settings):
    """Full run of all four sample scenarios with the designed economics story."""
    results = {sid: compute_scenario(data, sid, settings)
               for sid in ["SCN-001", "SCN-002", "SCN-003", "SCN-004"]}
    base = results["SCN-001"]

    # 1) Lowest-quote supplier is not the lowest-economic-cost supplier (P-100 quotes).
    comp = comparison_table(data, "P-100")
    cheapest_quote = comp.sort_values("quoted_price").iloc[0]["supplier_id"]
    assert cheapest_quote == "SUP-MER"
    scn2 = results["SCN-002"].line_items
    mer = scn2[(scn2["product_id"] == "P-100") & (scn2["supplier_id"] == "SUP-MER")].iloc[0]
    atl = scn2[(scn2["product_id"] == "P-100") & (scn2["supplier_id"] == "SUP-ATL")].iloc[0]
    assert mer["quoted_per_unit"] < atl["quoted_per_unit"]
    assert mer["econ_cost_per_unit"] > atl["econ_cost_per_unit"]

    # 2) Renegotiation scenario (SCN-003) creates meaningful cash improvement.
    assert (results["SCN-003"].totals["oem_inventory_value"]
            < base.totals["oem_inventory_value"] * 0.95)
    assert results["SCN-003"].totals["wc_cost"] < base.totals["wc_cost"]

    # 3) Dual-source scenario (SCN-004): running cost excluding risk is higher
    #    (the insurance premium), paid for by a large expected-risk reduction.
    assert results["SCN-004"].totals["risk_cost"] < base.totals["risk_cost"] - 100_000
    ex_risk_scn4 = (results["SCN-004"].totals["recurring_economic_cost"]
                    - results["SCN-004"].totals["risk_cost"])
    ex_risk_base = base.totals["recurring_economic_cost"] - base.totals["risk_cost"]
    assert ex_risk_scn4 > ex_risk_base

    # 4) Bridge reconciles to per-unit economic cost.
    bridge = cost_bridge(base)
    assert bridge["value"].sum() == pytest.approx(
        base.totals["total_economic_cost"] / base.totals["good_units"], rel=1e-6)

    # 5) Every scenario computes per-unit > quoted per-unit (incremental costs positive).
    for res in results.values():
        assert res.totals["total_economic_cost"] > res.totals["quoted_cost"]


# ---------------------------------------------------------------- validation & DQ
def test_validation_runs_and_flags_sample_issues(data):
    issues = validate(data)
    assert not issues.empty
    # Sample data intentionally contains inferred/missing Meridian terms.
    assert (issues["severity"] == "Data-quality issue").any()
    # No hard errors in the shipped sample data.
    assert not (issues["severity"] == "Error").any()


def test_data_quality_score_bounds(data):
    score = data_quality_score(data)
    assert 0 <= score["overall_score"] <= 100
