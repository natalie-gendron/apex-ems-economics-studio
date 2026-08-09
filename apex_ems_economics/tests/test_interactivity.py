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


def test_no_table_bypasses_the_column_formatter():
    """Guardrail: tables must render through the auto-formatting helpers.

    A bare st.dataframe / st.data_editor shows raw snake_case headers and
    unformatted dollars, which is what this rule exists to prevent.
    """
    import glob
    import re

    allowed = {
        # A pandas Styler (already currency-formatted) that column_config cannot take.
        "09_Inventory_and_Working_Capital.py": ["matrix.style"],
        # Bespoke grouped settings editor with an explicit config for every column.
        "19_Model_Settings.py": ["st.data_editor("],
    }
    offenders = []
    for path in glob.glob(os.path.join(ROOT, "pages", "*.py")) + [os.path.join(ROOT, "app.py")]:
        name = os.path.basename(path)
        for line in open(path):
            if re.search(r"\bst\.(dataframe|data_editor)\(", line):
                if any(token in line for token in allowed.get(name, [])):
                    continue
                offenders.append(f"{name}: {line.strip()[:70]}")
    assert not offenders, "tables bypassing the formatter:\n" + "\n".join(offenders)


def test_currency_and_labels_are_inferred_correctly():
    """Spot-check the formatter on the cases that were previously wrong."""
    from components.column_config import auto_column_config, humanize
    from repositories.csv_repository import CsvRepository

    data = CsvRepository().load_all()

    def fmt(table, column):
        cfg = auto_column_config(data[table])
        return (cfg[column].get("type_config") or {}).get("format")

    # Currency, with cents only where the magnitude needs them.
    assert fmt("supplier_quotes", "base_unit_price") == "$%,.0f"
    assert fmt("conversion_costs", "labor_rate") == "$%,.2f"      # $9.50, not $10
    # Fractional durations keep their decimals.
    assert fmt("conversion_costs", "machine_hours_per_unit") == "%,.2f"
    # Percentages, booleans, and dates must never be dollars.
    assert fmt("supplier_quotes", "annual_price_reduction_pct") == "%.1f%%"
    assert fmt("supplier_quotes", "includes_freight") is None     # checkbox
    assert fmt("supplier_quotes", "price_effective_date") is None
    # Labels are humanized with acronyms restored.
    assert humanize("econ_cost_per_unit") == "Economic $/unit"
    assert humanize("supplier_id") == "Supplier"
    assert humanize("qpa_per_system") == "QPA per system"
    assert humanize("target_gross_margin_pct") == "Target gross margin %"
    assert humanize("first_pass_yield_pct") == "First pass yield %"


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
