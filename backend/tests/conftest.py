from __future__ import annotations

import pytest

from setubiz.config import SAMPLE_DATA_DIR, get_settings
from setubiz.data.loader import get_data_source
from setubiz.finance import load_template, route


@pytest.fixture(autouse=True)
def _clear_settings_cache(monkeypatch):
    """Pin the suite to the synthetic sample dataset.

    The application defaults to `data/real`, which is rebuilt from multi-gigabyte extracts and
    will grow as more states are added. Assertions about specific villages, densities and
    seasonality need a fixed fixture, so the suite pins the sample directory explicitly.
    `test_real_dataset.py` covers the real build separately.
    """
    monkeypatch.setenv("SETUBIZ_DATA_DIR", str(SAMPLE_DATA_DIR))
    get_settings.cache_clear()
    get_data_source.cache_clear()
    yield
    get_settings.cache_clear()
    get_data_source.cache_clear()


@pytest.fixture
def dairy():
    return load_template("dairy_2_animal")


@pytest.fixture
def logic_b_route():
    """The demo persona: ₹1,00,000 of savings → ₹10,00,000 project → ₹9,00,000 max loan."""
    return route(100000)
