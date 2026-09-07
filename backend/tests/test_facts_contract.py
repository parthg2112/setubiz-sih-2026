"""The facts contract — if a number is not here, the report may not say it (PLAN.md §3)."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from setubiz.facts import build_facts
from setubiz.facts.provenance import SOURCES, resolve, unknown_ids
from setubiz.schemas import AdvisoryRequest


@pytest.fixture
def request_dairy():
    return AdvisoryRequest(
        village_query="Ormanji",
        savings=Decimal("100000"),
        business_category="dairy",
        social_category="sc",
        annual_family_income=Decimal("280000"),
    )


@pytest.fixture
def facts(request_dairy):
    return build_facts(request_dairy)


def test_every_indexed_figure_has_at_least_one_source(facts):
    assert facts.numeric_index
    assert set(facts.provenance) == set(facts.numeric_index)
    assert all(facts.provenance[key] for key in facts.numeric_index)


def test_every_cited_source_id_resolves_to_a_registered_source(facts):
    cited = {sid for ids in facts.provenance.values() for sid in ids}
    assert not unknown_ids(tuple(cited)), f"unregistered source ids: {unknown_ids(tuple(cited))}"
    assert {s.id for s in facts.sources} >= {"finance_engine", "nabard_templates"}
    assert all(s.title for s in facts.sources)


def test_synthetic_data_is_declared_not_hidden(facts):
    assert facts.contains_synthetic_data is True
    assert any(s.synthetic for s in facts.sources)


def test_the_headline_numbers_are_all_indexed(facts):
    for key in (
        "margin",
        "project_cost",
        "max_loan",
        "recommended_loan",
        "headroom",
        "required_capital",
        "debt_need",
        "annual_noi",
        "max_loan_min_dscr",
        "recommended_min_dscr",
        "dscr_threshold",
        "competitors_low",
        "competitors_high",
        "households_now",
        "quarterly_instalment_max",
        "quarterly_instalment_recommended",
    ):
        assert key in facts.numeric_index, key


def test_indexed_values_agree_with_the_engines(facts):
    idx = facts.numeric_index
    assert idx["max_loan"] == facts.right_sizing.max_loan == facts.scheme.max_loan
    assert idx["recommended_loan"] == facts.right_sizing.recommended_loan
    assert idx["required_capital"] == facts.template.required_capital
    assert idx["annual_noi"] == facts.template.annual_noi
    assert idx["households_now"] == facts.market.households_now
    assert idx["quarterly_instalment_max"] == facts.amortization_max.instalment


def test_per_year_dscr_series_is_indexed(facts):
    for row in facts.right_sizing.recommended_dscr:
        assert facts.numeric_index[f"recommended_dscr_year_{row.year}"] == row.dscr
    for row in facts.right_sizing.max_loan_dscr:
        assert facts.numeric_index[f"max_loan_dscr_year_{row.year}"] == row.dscr


def test_allowed_numbers_covers_the_schedule_and_the_cost_lines(facts):
    allowed = facts.allowed_numbers()
    assert facts.amortization_recommended.instalment in allowed
    assert facts.amortization_max.schedule[-1].interest in allowed
    assert facts.template.fixed_capital[0].amount in allowed
    assert Decimal(facts.market.neighbours[1].village.households_2011) in allowed


def test_facts_serialize_to_json_round_trip(facts):
    payload = json.loads(facts.model_dump_json())
    assert payload["village"]["name"] == "Ormanjhi"
    assert payload["numeric_index"]["max_loan"] == "900000.00"
    assert payload["right_sizing"]["binding"] == facts.right_sizing.binding.value
    assert len(payload["sources"]) == len(facts.sources)
    assert payload["contains_synthetic_data"] is True


def test_facts_are_frozen(facts):
    with pytest.raises(ValidationError):
        facts.numeric_index = {}


def test_resolving_by_shrid_skips_the_matcher(request_dairy, facts):
    exact = build_facts(request_dairy.model_copy(update={"village_shrid": facts.village.shrid}))
    assert exact.village.shrid == facts.village.shrid


def test_unknown_village_and_category_fail_loudly(request_dairy):
    with pytest.raises(KeyError, match="unknown village shrid"):
        build_facts(request_dairy.model_copy(update={"village_shrid": "nope"}))
    with pytest.raises(KeyError, match="no village matched"):
        build_facts(request_dairy.model_copy(update={"village_query": "zzzzzzzz"}))
    with pytest.raises(KeyError, match="no cost template"):
        build_facts(request_dairy.model_copy(update={"business_category": "space_tourism"}))


def test_request_requires_a_village():
    with pytest.raises(ValueError, match="village_shrid or village_query"):
        AdvisoryRequest(savings=Decimal("100000"), business_category="dairy")


def test_source_registry_is_self_consistent():
    assert all(sid == source.id for sid, source in SOURCES.items())
    assert resolve(["nsfdc", "nsfdc", "not_a_source"]) == (SOURCES["nsfdc"],)
    assert unknown_ids(["nsfdc", "not_a_source"]) == ("not_a_source",)


def test_verbatim_text_carries_the_locked_reference_strings(facts):
    text = facts.verbatim_text()
    assert facts.template.unit in text
    assert facts.eligibility.sca is not None
    assert facts.eligibility.sca.address in text
