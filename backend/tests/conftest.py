from __future__ import annotations

import pytest

from setubiz.config import get_settings
from setubiz.finance import load_template, route


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def dairy():
    return load_template("dairy_2_animal")


@pytest.fixture
def logic_b_route():
    """The demo persona: ₹1,00,000 of savings → ₹10,00,000 project → ₹9,00,000 max loan."""
    return route(100000)
