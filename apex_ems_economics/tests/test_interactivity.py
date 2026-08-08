"""Interaction regression tests: key widgets must actually drive the numbers.

The page smoke tests only prove pages render; these prove the controls are
live - guarding against 'inert selector' regressions (a radio or dropdown
that renders but changes nothing downstream).
"""
import os

from streamlit.testing.v1 import AppTest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _page(name: str) -> AppTest:
    at = AppTest.from_file(os.path.join(ROOT, "pages", name), default_timeout=60)
    at.run()
    return at


def test_scenario_selector_drives_executive_overview():
    at = _page("01_Executive_Overview.py")
    baseline_value = at.metric[1].value  # "True economic cost"
    at.selectbox(key="scenario_select").select("SCN-002").run()
    assert not at.exception
    assert at.metric[1].value != baseline_value


def test_should_cost_method_drives_comparison_table():
    at = _page("08_Should_Cost_Model.py")
    process_values = at.dataframe[0].value["should_cost"].tolist()
    at.radio[0].set_value("Level 1 — High-level benchmark").run()
    assert not at.exception
    benchmark_values = at.dataframe[0].value["should_cost"].tolist()
    assert benchmark_values != process_values
    # Level 1 is supplier-independent: one benchmark for every supplier row.
    assert len(set(benchmark_values)) == 1


def test_scenario_multiselect_drives_comparison_page():
    at = _page("16_Scenario_Comparison.py")
    rows_before = len(at.dataframe[0].value)
    at.multiselect[0].set_value(["SCN-001", "SCN-003"]).run()
    assert not at.exception
    assert len(at.dataframe[0].value) == 2
    assert rows_before != 2


def test_scenario_selector_drives_inventory_page():
    at = _page("09_Inventory_and_Working_Capital.py")
    at.selectbox(key="scenario_select").select("SCN-003").run()
    assert not at.exception
    # SCN-003 (renegotiated terms) must be reflected in the scenario WC table.
    assert any("SCN-003" in str(h) or "Renegotiate" in str(h)
               for h in [s.value for s in at.subheader])
