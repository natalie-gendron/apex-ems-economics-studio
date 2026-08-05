"""Monte Carlo reproducibility and output tests."""
import pytest

from core.monte_carlo_engine import probability_cheaper, run_simulation
from repositories.csv_repository import CsvRepository


@pytest.fixture(scope="module")
def data():
    return CsvRepository().load_all()


def test_monte_carlo_reproducible_with_seed(data):
    a = run_simulation(data, ["SCN-001"], iterations=25, seed=42)
    b = run_simulation(data, ["SCN-001"], iterations=25, seed=42)
    assert a["totals"]["SCN-001"].tolist() == b["totals"]["SCN-001"].tolist()


def test_monte_carlo_seed_changes_results(data):
    a = run_simulation(data, ["SCN-001"], iterations=25, seed=42)
    b = run_simulation(data, ["SCN-001"], iterations=25, seed=7)
    assert a["totals"]["SCN-001"].tolist() != b["totals"]["SCN-001"].tolist()


def test_monte_carlo_summary_and_probability(data):
    sim = run_simulation(data, ["SCN-001", "SCN-003"], iterations=40, seed=42)
    s = sim["summary"]["SCN-001"]
    assert s["p10"] <= s["p50"] <= s["p90"]
    assert s["min"] <= s["mean"] <= s["max"]
    p = probability_cheaper(sim["totals"], "SCN-003", "SCN-001")
    assert 0.0 <= p <= 1.0
    # SCN-003 (renegotiation) should usually be cheaper than baseline.
    assert p > 0.5
    assert not sim["sensitivities"].empty
