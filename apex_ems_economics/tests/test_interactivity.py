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


def test_every_entity_is_editable_somewhere():
    """Guardrail: no data table may be reachable only by hand-editing a CSV."""
    import glob
    import re

    from repositories.csv_repository import ENTITY_FILES

    sources = "".join(open(f).read() for f in glob.glob(os.path.join(ROOT, "pages", "*.py")))
    editable = set(re.findall(r'editable_table\(\s*"([a-z_]+)"', sources))
    # global_settings has a bespoke grouped editor rather than editable_table().
    editable.add("global_settings")
    missing = [e for e in ENTITY_FILES if e not in editable]
    assert not missing, f"entities with no UI editor: {missing}"


def test_global_settings_changes_flow_into_the_engines():
    """A settings edit must move real numbers, not just the settings table."""
    from core.config import load_settings
    from core.economics_engine import compute_scenario
    from repositories.csv_repository import CsvRepository

    data = CsvRepository().load_all()
    base = compute_scenario(data, "SCN-001", load_settings(data))

    bumped = {k: v.copy() for k, v in data.items()}
    gs = bumped["global_settings"]
    gs.loc[gs["key"] == "cost_of_capital_pct", "value"] = 16.0
    after = compute_scenario(bumped, "SCN-001", load_settings(bumped))

    # Doubling the cost of capital must raise working-capital cost.
    assert after.totals["wc_cost"] > base.totals["wc_cost"]
