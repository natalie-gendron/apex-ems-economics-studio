"""Smoke test: every Streamlit page renders without an exception."""
import glob
import os

import pytest
from streamlit.testing.v1 import AppTest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = sorted(glob.glob(os.path.join(ROOT, "pages", "*.py")))


def _run(path: str) -> AppTest:
    at = AppTest.from_file(path, default_timeout=60)
    at.run()
    return at


def test_home_page_renders():
    at = _run(os.path.join(ROOT, "app.py"))
    assert not at.exception


@pytest.mark.parametrize("page", PAGES, ids=[os.path.basename(p) for p in PAGES])
def test_page_renders(page):
    at = _run(page)
    assert not at.exception, f"{os.path.basename(page)} raised: {at.exception}"
