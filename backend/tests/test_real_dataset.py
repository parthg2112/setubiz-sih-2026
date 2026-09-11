"""The real dataset — the one the application serves by default.

`conftest.py` pins every other test to the synthetic sample directory so its assertions stay
deterministic. This file is the exception: it asserts the committed real build actually loads,
validates and declares itself real, because that is what production and the demo run on.
"""

from __future__ import annotations

import pytest

from setubiz.config import REAL_DATA_DIR, Settings, get_settings
from setubiz.data.loader import SampleDataSource
from setubiz.facts.builder import build_facts
from setubiz.schemas import AdvisoryRequest


@pytest.fixture
def real(monkeypatch):
    monkeypatch.setenv("SETUBIZ_DATA_DIR", str(REAL_DATA_DIR))
    get_settings.cache_clear()
    yield SampleDataSource(REAL_DATA_DIR)
    get_settings.cache_clear()


def test_the_application_defaults_to_the_real_dataset():
    """If this flips back to the sample directory, every report regains the synthetic banner.

    Asserts the declared field default rather than a constructed Settings, because the suite sets
    SETUBIZ_DATA_DIR and an instance would just read that back.
    """
    assert Settings.model_fields["data_dir"].default == REAL_DATA_DIR


def test_every_village_validates_and_carries_real_geography(real):
    villages = real.all_villages()
    assert len(villages) > 10_000
    assert all(v.name and v.district and v.block for v in villages)
    # Jharkhand's true extent, as a guard against a broken centroid join silently shipping.
    assert all(21.0 < v.lat < 26.0 and 83.0 < v.lon < 88.5 for v in villages)
    assert all(0 <= v.literacy_rate <= 1 and 0 <= v.st_pct <= 1 for v in villages)


def test_population_matches_the_published_census_total(real):
    """Census 2011 puts Jharkhand's rural population at 25,055,073.

    This is the end-to-end check on the whole join chain — names, centroids, PCA and the
    exclusion of census towns. A regression in any of them moves this number.
    """
    total = sum(v.population_2011 for v in real.all_villages())
    assert abs(total - 25_055_073) < 5_000


def test_every_source_declares_itself_real(real):
    assert real.synthetic is False
    assert all(not s for s in real.source_synthetic.values())


def test_enterprise_density_resolves_by_name_for_every_mapped_category(real):
    for category in ("all", "dairy", "kirana", "tailoring", "flour_mill"):
        density = real.block_density("Jharkhand", "Ranchi", "Ormanjhi", category)
        assert density is not None and density > 0, category
    # Deliberately unmapped: SHRIC has no livestock-rearing code, so competitors.py must fall
    # back to the observed OSM floor and say so, rather than borrow a different industry.
    assert real.block_density("Jharkhand", "Ranchi", "Ormanjhi", "poultry") is None


def test_a_report_on_real_data_carries_no_synthetic_warning(real):
    facts = build_facts(
        AdvisoryRequest(
            village_query="Ormanjhi",
            state="Jharkhand",
            savings=100000,
            business_category="dairy",
            annual_family_income=280000,
            social_category="sc",
        ),
        source=real,
    )
    assert facts.contains_synthetic_data is False
    assert not any(s.synthetic for s in facts.sources)
    assert facts.village.name == "Ormanjhi"
    assert facts.village.district == "Ranchi"


def test_an_unmapped_category_still_states_its_fallback_in_words(real):
    """A 0-0 competitor band without its caveat reads as 'no competition here'."""
    facts = build_facts(
        AdvisoryRequest(
            village_query="Ormanjhi",
            state="Jharkhand",
            savings=100000,
            business_category="poultry",
            annual_family_income=280000,
            social_category="sc",
        ),
        source=real,
    )
    assert any(n.id == "no_ec13_row" for n in facts.competitors.notes)
    assert any(w.id == "no_ec13_row" for w in facts.warnings)
